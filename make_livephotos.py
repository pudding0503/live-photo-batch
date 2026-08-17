from __future__ import annotations

import argparse
import atexit
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from prepare_wallpaper_video import (
    add_hvc1_track_aperture,
    remove_ffmpeg_encoder_tag,
    set_still_image_time,
)

try:
    from tqdm import tqdm
except ImportError:
    print("tqdm is not installed. Run: uv sync")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
REFERENCE_DIR = ROOT / "reference"
WALLPAPER_CHECKER_SOURCE = ROOT / "check_live_wallpaper.swift"
WALLPAPER_PREPARER = ROOT / "prepare_wallpaper_video.py"
FIXED_LIVE_PHOTO_INFO_MARKER = b"com.apple.quicktime.live-photo-info"
REFERENCE_DIMENSIONS_MARKER = b"live-photo-still-image-transform-reference-dimensions"
WALLPAPER_FRAME_RATE = 60
SSIM_SAMPLE_PATTERN = re.compile(r"(?:^|\s)n:(\d+).*?\sAll:([0-9.]+)")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch convert image and video pairs into Live Photo packages."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Replace existing output packages with newly prepared wallpaper candidates."
        ),
    )
    return parser.parse_args()


def find_matching_video(image: Path) -> Path | None:
    """Find a video with the same filename stem as the image."""
    for extension in (".mov", ".mp4"):
        for candidate in (
            INPUT_DIR / f"{image.stem}{extension}",
            INPUT_DIR / f"{image.stem}{extension.upper()}",
        ):
            if candidate.exists():
                return candidate

    return None


def find_template_video() -> Path | None:
    """Return a reference MOV with fixed-size live-photo-info samples."""
    if not REFERENCE_DIR.is_dir():
        return None

    videos = sorted(
        (
            file
            for file in REFERENCE_DIR.iterdir()
            if file.is_file() and file.suffix.lower() == ".mov"
        ),
        key=lambda file: file.name.lower(),
    )
    for video in videos:
        try:
            data = video.read_bytes()
        except OSError:
            continue

        if (
            FIXED_LIVE_PHOTO_INFO_MARKER in data
            and REFERENCE_DIMENSIONS_MARKER not in data
        ):
            return video

    return None


def video_dimensions(video: Path) -> tuple[int, int]:
    """Return the primary video stream's width and height."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(video),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")

    streams = json.loads(result.stdout).get("streams", [])
    if len(streams) != 1:
        raise RuntimeError("Video does not contain exactly one primary video stream")

    width = streams[0].get("width")
    height = streams[0].get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        raise RuntimeError("Video stream does not report pixel dimensions")

    return width, height


def image_dimensions(image: Path) -> tuple[int, int]:
    """Return an image's encoded pixel dimensions."""
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(image)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "sips dimension lookup failed")

    width_match = re.search(r"pixelWidth:\s*(\d+)", result.stdout)
    height_match = re.search(r"pixelHeight:\s*(\d+)", result.stdout)
    if width_match is None or height_match is None:
        raise RuntimeError("Image does not report pixel dimensions")

    return int(width_match.group(1)), int(height_match.group(1))


def validate_cover_aspect(image: Path, width: int, height: int) -> None:
    """Reject cover/video pairs that would require visible stretching."""
    image_width, image_height = image_dimensions(image)
    image_aspect = image_width / image_height
    video_aspect = width / height
    if abs(image_aspect - video_aspect) > 0.005:
        raise RuntimeError(
            "Image and video aspect ratios differ; crop the input pair to matching frames "
            "before creating a Live Photo"
        )


def prepare_cover_image(image: Path, destination: Path, width: int, height: int) -> None:
    """Create a temporary HEIC cover image matching the video canvas."""
    result = subprocess.run(
        [
            "sips",
            "-d",
            "description",
            "-s",
            "format",
            "heic",
            "--resampleHeightWidth",
            str(height),
            str(width),
            str(image),
            "--out",
            str(destination),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "sips failed")


def prepare_hevc_video(video: Path, destination: Path) -> None:
    """Create a 60 fps VideoToolbox HEVC Main MOV with a 600-unit timescale."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(video),
            "-map",
            "0:v:0",
            "-an",
            "-vf",
            f"fps={WALLPAPER_FRAME_RATE}:round=near",
            "-c:v",
            "hevc_videotoolbox",
            "-profile:v",
            "main",
            "-pix_fmt",
            "yuv420p",
            "-q:v",
            "65",
            "-tag:v",
            "hvc1",
            "-video_track_timescale",
            "600",
            str(destination),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "HEVC video preparation failed")

    add_hvc1_track_aperture(destination)
    remove_ffmpeg_encoder_tag(destination)


def video_frame_count(video: Path) -> int:
    """Return the frame count for a video produced by this pipeline."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=nb_frames,nb_read_frames",
            "-of",
            "json",
            str(video),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe frame count failed")

    streams = json.loads(result.stdout).get("streams", [])
    if len(streams) != 1:
        raise RuntimeError("prepared video does not contain exactly one primary video stream")

    for key in ("nb_read_frames", "nb_frames"):
        try:
            return int(streams[0].get(key))
        except (TypeError, ValueError):
            continue

    raise RuntimeError("prepared video does not report a frame count")


def best_still_image_time(image: Path, video: Path, directory: Path) -> float:
    """Find the 60 fps video frame most similar to the packaged HEIC cover."""
    cover = directory / f"{image.stem}.cover.png"
    stats = directory / f"{image.stem}.ssim.log"
    frame_count = video_frame_count(video)

    image_result = subprocess.run(
        ["sips", "-s", "format", "png", str(image), "--out", str(cover)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if image_result.returncode != 0:
        raise RuntimeError(image_result.stderr.strip() or "cover image conversion failed")

    comparison_result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-loop",
            "1",
            "-framerate",
            str(WALLPAPER_FRAME_RATE),
            "-i",
            str(cover),
            "-i",
            str(video),
            "-filter_complex",
            (
                "[0:v]setpts=PTS-STARTPTS[cover];"
                "[1:v]setpts=PTS-STARTPTS[video];"
                f"[cover][video]ssim=stats_file={stats}"
            ),
            "-frames:v",
            str(frame_count),
            "-f",
            "null",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if comparison_result.returncode != 0:
        raise RuntimeError(comparison_result.stderr.strip() or "cover comparison failed")

    best_frame = None
    best_score = float("-inf")
    for line in stats.read_text().splitlines():
        match = SSIM_SAMPLE_PATTERN.search(line)
        if match is None:
            continue
        frame, score = int(match.group(1)), float(match.group(2))
        if score > best_score:
            best_frame, best_score = frame, score

    if best_frame is None:
        raise RuntimeError("cover comparison produced no SSIM samples")

    return (best_frame - 1) / WALLPAPER_FRAME_RATE


def compile_wallpaper_checker(directory: Path) -> Path:
    """Compile the read-only AVFoundation metadata checker."""
    if not WALLPAPER_CHECKER_SOURCE.is_file():
        raise RuntimeError(f"Missing checker source: {WALLPAPER_CHECKER_SOURCE}")

    checker = directory / "check-live-wallpaper"
    result = subprocess.run(
        ["xcrun", "swiftc", str(WALLPAPER_CHECKER_SOURCE), "-o", str(checker)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "swiftc failed")

    return checker


def inspect_wallpaper_metadata(checker: Path, video: Path) -> dict[str, object]:
    """Return the observed iOS Lock Screen metadata report for a MOV resource."""
    result = subprocess.run(
        [str(checker), str(video)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "wallpaper metadata check failed")

    return json.loads(result.stdout)


def prepare_wallpaper_video(template: Path, video: Path, prepared_video: Path) -> None:
    """Copy template metadata tracks into a normalized temporary MOV."""
    result = subprocess.run(
        [sys.executable, str(WALLPAPER_PREPARER), str(template), str(video), str(prepared_video)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "wallpaper MOV preparation failed")


def main() -> None:
    arguments = parse_arguments()

    if shutil.which("uv") is None:
        print("Error: uv was not found in PATH.")
        print("Make sure `uv --version` works.")
        sys.exit(1)

    if any(shutil.which(command) is None for command in ("ffmpeg", "ffprobe", "sips")):
        print("Error: ffmpeg, ffprobe, and sips must be available in PATH.")
        sys.exit(1)

    if not INPUT_DIR.is_dir():
        print(f"Error: input directory not found: {INPUT_DIR}")
        sys.exit(1)

    if not WALLPAPER_PREPARER.is_file():
        print(f"Error: wallpaper preparer not found: {WALLPAPER_PREPARER}")
        sys.exit(1)

    template_video = find_template_video()
    if template_video is None:
        print(f"Error: no compatible reference MOV found in {REFERENCE_DIR}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    images = sorted(
        (
            file
            for file in INPUT_DIR.iterdir()
            if file.is_file()
            and file.suffix.lower() in {".jpg", ".jpeg", ".heic"}
        ),
        key=lambda file: file.name.lower(),
    )

    if not images:
        print(f"No image files found in {INPUT_DIR}")
        return

    helper_directory = Path(tempfile.mkdtemp(prefix="live-photo-batch-"))
    try:
        wallpaper_checker = compile_wallpaper_checker(helper_directory)
    except RuntimeError as exc:
        shutil.rmtree(helper_directory, ignore_errors=True)
        print(f"Error: could not build Live Photo metadata checker: {exc}")
        sys.exit(1)
    atexit.register(shutil.rmtree, helper_directory, ignore_errors=True)

    try:
        template_report = inspect_wallpaper_metadata(wallpaper_checker, template_video)
    except RuntimeError as exc:
        print(f"Error: could not inspect reference MOV: {exc}")
        sys.exit(1)
    if not bool(template_report["wallpaperMetadataPresent"]):
        print(f"Error: reference MOV does not contain required wallpaper metadata: {template_video}")
        sys.exit(1)

    success = []
    skipped = []
    missing = []
    failed = []
    prepared = []

    print(f"Input : {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Template: {template_video}")
    print(f"Found {len(images)} image(s)")
    print()

    for image in tqdm(images, desc="Generating Live Photos", unit="file"):
        video = find_matching_video(image)

        if video is None:
            missing.append(image.name)
            tqdm.write(f"Missing video: {image.name}")
            continue

        output = OUTPUT_DIR / f"{image.stem}.pvt"

        if output.exists() and not arguments.force:
            skipped.append(image.name)
            tqdm.write(f"Skipped: {output.name}")
            continue

        hevc_video = helper_directory / f"{image.stem}.hevc.mov"
        prepared_video = helper_directory / f"{image.stem}.mov"
        prepared_image = helper_directory / f"{image.stem}.heic"
        generated_pvt = helper_directory / f"{image.stem}.pvt"
        try:
            width, height = video_dimensions(video)
            validate_cover_aspect(image, width, height)
            prepare_hevc_video(video, hevc_video)
            prepare_cover_image(image, prepared_image, width, height)
            association_time = best_still_image_time(prepared_image, hevc_video, helper_directory)
            prepare_wallpaper_video(template_video, hevc_video, prepared_video)
            prepared_report = inspect_wallpaper_metadata(wallpaper_checker, prepared_video)
        except RuntimeError as exc:
            failed.append(image.name)
            tqdm.write(f"Failed: {image.name}: {exc}")
            continue

        if not bool(prepared_report["wallpaperMetadataPresent"]):
            failed.append(image.name)
            tqdm.write(f"Failed: {image.name}: prepared MOV is missing wallpaper metadata")
            continue
        prepared.append(image.name)

        command = [
            "uvx",
            "makelive",
            "--pvt",
            "--manual",
            str(prepared_image),
            str(prepared_video),
        ]

        try:
            result = subprocess.run(
                command,
                cwd=helper_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except OSError as exc:
            failed.append(image.name)
            tqdm.write(f"Failed: {image.name}: {exc}")
            continue

        if result.returncode != 0:
            failed.append(image.name)

            error = result.stderr.strip()

            if error:
                tqdm.write(
                    f"Failed: {image.name}: {error}"
                )
            else:
                tqdm.write(
                    f"Failed: {image.name}: "
                    f"exit code {result.returncode}"
                )

            continue

        if not generated_pvt.exists():
            failed.append(image.name)

            tqdm.write(
                f"Failed: {image.name}: "
                f"makelive succeeded but {generated_pvt.name} "
                f"was not found"
            )

            continue

        package_video = generated_pvt / prepared_video.name
        try:
            set_still_image_time(package_video, association_time)
            package_report = inspect_wallpaper_metadata(wallpaper_checker, package_video)
        except RuntimeError as exc:
            failed.append(image.name)
            tqdm.write(f"Failed: {image.name}: could not inspect package MOV: {exc}")
            continue

        if not bool(package_report["wallpaperMetadataPresent"]):
            failed.append(image.name)
            tqdm.write(f"Failed: {image.name}: package MOV lost wallpaper metadata")
            continue

        previous_output = None
        try:
            if output.exists():
                previous_output = helper_directory / f"{image.stem}.previous.pvt"
                shutil.move(str(output), str(previous_output))
            shutil.move(str(generated_pvt), str(output))
        except OSError as exc:
            failed.append(image.name)

            if previous_output is not None and previous_output.exists():
                shutil.move(str(previous_output), str(output))

            tqdm.write(
                f"Failed: {image.name}: "
                f"could not move PVT file: {exc}"
            )

            continue

        success.append(image.name)
        tqdm.write(f"Created: {output.name}")

    print()
    print("=" * 60)
    print("Processing complete")
    print("=" * 60)
    print(f"Successful : {len(success)}")
    print(f"Prepared  : {len(prepared)}")
    print(f"Skipped    : {len(skipped)}")
    print(f"Missing    : {len(missing)}")
    print(f"Failed     : {len(failed)}")

    if missing:
        print()
        print("Missing videos:")

        for name in missing:
            print(f"  {name}")

    if failed:
        print()
        print("Failed files:")

        for name in failed:
            print(f"  {name}")

    print("=" * 60)


if __name__ == "__main__":
    main()
