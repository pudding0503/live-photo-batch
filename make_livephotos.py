from pathlib import Path
import shutil
import subprocess
import sys

try:
    from tqdm import tqdm
except ImportError:
    print("tqdm is not installed. Run: uv sync")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"


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


def main() -> None:
    if shutil.which("uv") is None:
        print("Error: uv was not found in PATH.")
        print("Make sure `uv --version` works.")
        sys.exit(1)

    if not INPUT_DIR.is_dir():
        print(f"Error: input directory not found: {INPUT_DIR}")
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

    success = []
    skipped = []
    missing = []
    failed = []

    print(f"Input : {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
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
            skipped.append(image.name)
            tqdm.write(f"Skipped: {output.name}")
            continue

        generated_pvt = INPUT_DIR / f"{image.stem}.pvt"

        command = [
            "uvx",
            "makelive",
            "--pvt",
            "--manual",
            str(image),
            str(video),
        ]

        try:
            result = subprocess.run(
                command,
                cwd=INPUT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as exc:
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