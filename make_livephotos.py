import argparse
import atexit
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from prepare_wallpaper_video import (
    add_hvc1_track_aperture,
    remove_ffmpeg_encoder_tag,
)
from live_photo_config import (
    DEFAULT_MODE,
    DEFAULT_TARGET_DEVICE,
    IPHONE_MODELS,
    PACKAGE_MODES,
)

try:
    from tqdm import tqdm
except ImportError:
    print("tqdm is not installed. Run: uv sync")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
WALLPAPER_CHECKER_SOURCE = ROOT / "check_live_wallpaper.swift"
WALLPAPER_PREPARER = ROOT / "prepare_wallpaper_video.py"
WALLPAPER_FRAME_RATE = 60
MAKELIVE_TIMEOUT_SECONDS = 120


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch convert image and video pairs into Live Photo packages."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Replace existing output packages with newly prepared candidates."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=PACKAGE_MODES,
        default=DEFAULT_MODE,
        help=(
            "wallpaper uses the verified 60 fps pipeline and video opening frame; "
            "album packages the original still/video for ordinary Live Photo import."
        ),
    )
    parser.add_argument(
        "--target-device",
        choices=tuple(model.key for model in IPHONE_MODELS),
        default=DEFAULT_TARGET_DEVICE,
        help="Target iPhone label for the run report; it does not change encoding yet.",
    )
    parser.add_argument(
        "--use-input-cover",
        action="store_true",
        help=(
            "Use the matched input image as the cover instead of the normalized video's "
            "opening frame. This is intended for ordinary Live Photo or isolated tests."
        ),
    )
    return parser.parse_args()


def selected_device(key: str):
    return next(model for model in IPHONE_MODELS if model.key == key)


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


def find_makelive() -> str | None:
    """Find the packager in the active virtual environment before PATH."""
    environment_command = Path(sys.executable).with_name("makelive")
    if environment_command.is_file():
        return str(environment_command)
    return shutil.which("makelive")


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
        raise RuntimeError("MOV does not contain exactly one primary video stream")

    width = streams[0].get("width")
    height = streams[0].get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        raise RuntimeError("MOV video stream does not report pixel dimensions")

    return width, height


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


def prepare_video_frame_cover(
    video: Path, destination: Path, width: int, height: int
) -> None:
    """Extract the normalized video's opening frame and convert it to HEIC."""
    frame = destination.with_suffix(".frame.png")
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
            "-frames:v",
            "1",
            "-vf",
            "format=rgb24",
            str(frame),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "could not extract video opening frame")

    try:
        prepare_cover_image(frame, destination, width, height)
    finally:
        frame.unlink(missing_ok=True)


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


def prepare_wallpaper_video(video: Path, prepared_video: Path) -> None:
    """Add the built-in metadata template to a normalized temporary MOV."""
    result = subprocess.run(
        [sys.executable, str(WALLPAPER_PREPARER), str(video), str(prepared_video)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "wallpaper MOV preparation failed")


def main() -> None:
    arguments = parse_arguments()
    device = selected_device(arguments.target_device)
    wallpaper_mode = arguments.mode == "wallpaper"

    makelive = find_makelive()
    if makelive is None:
        print("Error: makelive 0.7.0 was not found in PATH.")
        print("Run `uv sync` before running this script.")
        sys.exit(1)

    required_commands = ("ffmpeg", "ffprobe", "sips") if wallpaper_mode else ()
    if any(shutil.which(command) is None for command in required_commands):
        print("Error: ffmpeg, ffprobe, and sips must be available in PATH.")
        sys.exit(1)

    if not INPUT_DIR.is_dir():
        print(f"Error: input directory not found: {INPUT_DIR}")
        sys.exit(1)

    if wallpaper_mode and not WALLPAPER_PREPARER.is_file():
        print(f"Error: wallpaper preparer not found: {WALLPAPER_PREPARER}")
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
    wallpaper_checker = None
    if wallpaper_mode:
        try:
            wallpaper_checker = compile_wallpaper_checker(helper_directory)
        except RuntimeError as exc:
            shutil.rmtree(helper_directory, ignore_errors=True)
            print(f"Error: could not build Live Photo metadata checker: {exc}")
            sys.exit(1)
    atexit.register(shutil.rmtree, helper_directory, ignore_errors=True)

    success = []
    skipped = []
    missing = []
    failed = []
    prepared = []

    print(f"Input : {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Mode: {arguments.mode}")
    print(f"Target iPhone: {device.label}")
    if wallpaper_mode:
        print("Metadata: built-in device-verified template")
        print(
            "Cover: matched input image"
            if arguments.use_input_cover
            else "Cover: normalized video opening frame"
        )
    else:
        print("Resources: original input still and video")
        print("Metadata: makelive ordinary Live Photo packaging")
    if wallpaper_mode and not device.device_verified:
        print("Note: this iPhone model is a label only; no model-specific profile is verified.")
    print(f"Found {len(images)} image(s)")
    print()

    for image in tqdm(images, desc="Generating Live Photos", unit="file"):
        video = find_matching_video(image)

        if video is None:
            missing.append(image.name)
            tqdm.write(f"Missing video: {image.name}")
            continue

        output = OUTPUT_DIR / f"{image.stem}.pvt"

        if output.exists():
            if arguments.force:
                try:
                    shutil.rmtree(output)
                except OSError as exc:
                    failed.append(image.name)
                    tqdm.write(f"Failed: {output.name}: could not remove existing package: {exc}")
                    continue
            else:
                skipped.append(image.name)
                tqdm.write(f"Skipped: {output.name}")
                continue

        hevc_video = helper_directory / f"{image.stem}.hevc.mov"
        prepared_video = helper_directory / f"{image.stem}.mov"
        prepared_image = helper_directory / f"{image.stem}.heic"
        try:
            if wallpaper_mode:
                width, height = video_dimensions(video)
                prepare_hevc_video(video, hevc_video)
                if arguments.use_input_cover:
                    prepare_cover_image(image, prepared_image, width, height)
                else:
                    prepare_video_frame_cover(hevc_video, prepared_image, width, height)
                prepare_wallpaper_video(hevc_video, prepared_video)
                prepared_report = inspect_wallpaper_metadata(wallpaper_checker, prepared_video)
                if not bool(prepared_report["wallpaperMetadataPresent"]):
                    raise RuntimeError(
                        "prepared MOV is missing wallpaper metadata"
                    )
                prepared.append(image.name)
                command = [
                    makelive,
                    "--pvt",
                    "--manual",
                    str(prepared_image),
                    str(prepared_video),
                ]
            else:
                album_image = helper_directory / image.name
                album_video = helper_directory / video.name
                shutil.copy2(image, album_image)
                shutil.copy2(video, album_video)
                command = [
                    makelive,
                    "--pvt",
                    "--manual",
                    str(album_image),
                    str(album_video),
                ]
        except (OSError, RuntimeError) as exc:
            failed.append(image.name)
            tqdm.write(f"Failed: {image.name}: {exc}")
            continue

        existing_packages = set(helper_directory.glob("*.pvt"))
        try:
            result = subprocess.run(
                command,
                cwd=helper_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=MAKELIVE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            failed.append(image.name)
            tqdm.write(
                f"Failed: {image.name}: makelive exceeded "
                f"{MAKELIVE_TIMEOUT_SECONDS} seconds"
            )
            continue
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

        generated_packages = [
            package
            for package in helper_directory.glob("*.pvt")
            if package not in existing_packages and package.is_dir()
        ]
        if len(generated_packages) != 1:
            failed.append(image.name)
            tqdm.write(
                f"Failed: {image.name}: expected one new PVT package, found "
                f"{len(generated_packages)}"
            )
            continue
        generated_pvt = generated_packages[0]

        if not generated_pvt.exists():
            failed.append(image.name)

            tqdm.write(
                f"Failed: {image.name}: "
                f"makelive succeeded but {generated_pvt.name} "
                f"was not found"
            )

            continue

        if wallpaper_mode:
            package_video = generated_pvt / prepared_video.name
            try:
                package_report = inspect_wallpaper_metadata(wallpaper_checker, package_video)
            except RuntimeError as exc:
                failed.append(image.name)
                tqdm.write(f"Failed: {image.name}: could not inspect package MOV: {exc}")
                continue

            if not bool(package_report["wallpaperMetadataPresent"]):
                failed.append(image.name)
                tqdm.write(f"Failed: {image.name}: package MOV lost wallpaper metadata")
                continue

        try:
            shutil.move(str(generated_pvt), str(output))
        except OSError as exc:
            failed.append(image.name)

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


def run() -> int:
    """Resume after one transient terminal interrupt; require a second to stop."""
    previous_interrupt: float | None = None

    while True:
        try:
            main()
            return 0
        except KeyboardInterrupt:
            now = time.monotonic()
            if previous_interrupt is not None and now - previous_interrupt <= 2:
                print("\nInterrupted. Existing completed packages were retained.")
                return 130

            previous_interrupt = now
            print(
                "\nInterrupted. Resuming unfinished packages. "
                "Press Ctrl-C again within 2 seconds to stop."
            )


if __name__ == "__main__":
    sys.exit(run())
