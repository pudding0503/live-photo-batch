# Live Photo Batch Converter

Batch convert image and video pairs into Apple Live Photo `.pvt` packages.

The project uses [uv](https://docs.astral.sh/uv/) for Python project and dependency management.

## Features

- Scan the `input` directory automatically.
- Match images and videos by filename.
- Support:
  - `.jpg`
  - `.jpeg`
  - `.heic`
  - `.mov`
  - `.mp4`
  - Normalize temporary resources to HEIC and HEVC (`hvc1`) before packaging.
  - Prepare each temporary MOV with a known-working Live Photo metadata template.
- Verify the prepared package keeps the required motion metadata.
- Store all generated packages in the `output` directory.
- Never modify files in the `input` directory.
- Show a progress bar with `tqdm`.
- Report standard Live Photo and Lock Screen metadata eligibility separately.

## Requirements

- macOS
- Python 3.9+
- [uv](https://docs.astral.sh/uv/)
- Xcode Command Line Tools (`xcrun swiftc`)
- FFmpeg with `libx265`

`makelive` is executed through `uvx`, so it does not need to be installed manually.

## Directory Structure

```text
live-photo-batch/
├── pyproject.toml
├── uv.lock
├── README.md
├── make_livephotos.py
├── prepare_wallpaper_video.py
├── check_live_wallpaper.swift
├── input/
│   ├── IMG_0001.JPG
│   ├── IMG_0001.MP4
│   ├── IMG_0002.JPG
│   ├── IMG_0002.MP4
│   └── ...
├── reference/
│   └── WORKING_LIVE_PHOTO.MOV
└── output/
    ├── IMG_0001.pvt
    ├── IMG_0002.pvt
    └── ...
```

The `input` directory contains the original image and video files.

The `output` directory contains the generated `.pvt` packages.

The script never modifies the original files in `input`.

The `reference` directory must contain an exported MOV from a Live Photo that is known to enable the Lock Screen Animate control on the target iPhone. The batch script selects a compatible fixed-sample metadata template.

## Installation

Initialize the project:

```
uv sync
```

If the project has not been initialized yet:

```
uv init
uv add tqdm
uv sync
```

## Usage

Place matching image and video files in `input`.

For example:

```
input/
├── IMG_0001.JPG
├── IMG_0001.MP4
├── IMG_0002.JPG
├── IMG_0002.MP4
└── IMG_0003.JPG
```

Run:

```
uv run python make_livephotos.py
```

To replace already-generated output packages:

```
uv run python make_livephotos.py --force
```

The script automatically creates the `output` directory if it does not exist.

For the following pair:

```
input/IMG_0001.JPG
input/IMG_0001.MP4
```

the output will be:

```
output/IMG_0001.pvt
```

## Filename Matching

The image and video must have the same filename stem.

Valid:

```
IMG_0001.JPG
IMG_0001.MP4
```

Invalid:

```
IMG_0003.JPG
IMG_1234.MP4
```

because the filename stems do not match.

## Existing Output

If the corresponding `.pvt` file already exists, the script skips that pair. Pass `--force` to replace it.

For example:

```
input/
├── IMG_0001.JPG
└── IMG_0001.MP4


output/
└── IMG_0001.pvt
```

`IMG_0001` will be skipped.

## iOS Lock Screen Animation

For each input pair, the script creates temporary resources without changing `input`:

1. Convert the cover image to HEIC at the video canvas dimensions.
2. Encode the source video stream as HEVC Main with an `hvc1` tag and a 600-unit time scale.
3. Copy the compatible Live Photo metadata template, expand its frame metadata to the source video duration, and add `cdsc` references from metadata tracks to the video track.
4. Package the temporary HEIC/MOV pair with `makelive` and verify the packaged MOV retains the metadata.

The template and each generated package are checked for these Apple timed metadata identifiers:

- `com.apple.quicktime.live-photo-info`
- `com.apple.quicktime.live-photo-still-image-transform`
- `com.apple.quicktime.still-image-time`

The final Lock Screen decision remains with iOS, so import a regenerated package and test it on the target iPhone. Metadata and Live Photo pairing checks do not prove that iOS will enable Lock Screen animation.

This workflow accepts matching `.mov` or `.mp4` input. Both are normalized into a temporary MOV before `makelive` runs, so the original input files are unchanged.

## Progress

The script displays a progress bar while processing the files.

Example:

```
Generating Live Photos: 100%|████████████████████| 6/6
```

A summary is printed after processing:

```
============================================================
Processing complete
============================================================
Successful : 6
Skipped    : 0
Missing    : 0
Failed     : 0
============================================================
```

## Missing Videos

If an image does not have a matching video, it is reported and skipped.

Example:

```
input/
└── IMG_0007.JPG
```

without:

```
input/IMG_0007.MP4
```

will produce:

```
Missing video: IMG_0007.JPG
```

The remaining files will continue to process.

## Failed Files

If `makelive` returns an error or the expected `.pvt` package is not generated, the file is reported as failed.

The script continues processing the remaining pairs.

## Manual Verification

A single image/video pair can be checked with:

```
uvx makelive --check --manual input/IMG_0001.JPG input/IMG_0001.MP4
```

A valid Live Photo pair should produce output similar to:

```
IMG_0001.JPG and IMG_0001.MP4 are Live Photos: D7D2D912-454C-4050-B905-306D3921D10B
```

The identifier will vary between Live Photos.

## Manual Conversion

A single `.pvt` package can be generated with:

```
uvx makelive --pvt --manual input/IMG_0001.JPG input/IMG_0001.MP4
```

When using the batch script, the generated package is placed in `output`.

## Importing into Apple Photos

After processing, open the `output` directory in Finder.

Double-click a `.pvt` package:

```
output/IMG_0001.pvt
```

macOS Photos should import it as a single Live Photo.

After importing, verify that:

- The photo appears as one item.
- The Live Photo indicator is shown.
- Pressing and holding the photo plays the motion portion.

## Safety

The script uses `makelive --pvt`.

This means the original image and video files in `input` are not modified.

Only `.pvt` packages are created in `output`.

This makes the `input` directory suitable for keeping the original downloaded files.

## License

MIT license.