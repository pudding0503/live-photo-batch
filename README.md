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
- Generate Apple-compatible `.pvt` Live Photo packages.
- Store all generated packages in the `output` directory.
- Never modify files in the `input` directory.
- Skip existing `.pvt` files.
- Show a progress bar with `tqdm`.
- Report successful, skipped, missing, and failed files.

## Requirements

- macOS
- Python 3.9+
- [uv](https://docs.astral.sh/uv/)

`makelive` is executed through `uvx`, so it does not need to be installed manually.

## Directory Structure

```text
live-photo-batch/
├── pyproject.toml
├── uv.lock
├── README.md
├── make_livephotos.py
├── input/
│   ├── IMG_0001.JPG
│   ├── IMG_0001.MOV
│   ├── IMG_0002.JPG
│   ├── IMG_0002.MOV
│   └── ...
└── output/
    ├── IMG_0001.pvt
    ├── IMG_0002.pvt
    └── ...
```

The `input` directory contains the original image and video files.

The `output` directory contains the generated `.pvt` packages.

The script never modifies the original files in `input`.

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
├── IMG_0001.MOV
├── IMG_0002.JPG
├── IMG_0002.MOV
└── IMG_0003.JPG
```

Run:

```
uv run python make_livephotos.py
```

The script automatically creates the `output` directory if it does not exist.

For the following pair:

```
input/IMG_0001.JPG
input/IMG_0001.MOV
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
IMG_0001.MOV
```

Also valid:

```
IMG_0002.HEIC
IMG_0002.MP4
```

Invalid:

```
IMG_0003.JPG
IMG_1234.MOV
```

because the filename stems do not match.

## Existing Output

If the corresponding `.pvt` file already exists, the script skips that pair.

For example:

```
input/
├── IMG_0001.JPG
└── IMG_0001.MOV


output/
└── IMG_0001.pvt
```

`IMG_0001` will be skipped.

Delete the existing package if it needs to be regenerated:

```
rm -rf output/IMG_0001.pvt
```

Then run the script again.

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
input/IMG_0007.MOV
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
uvx makelive --check --manual input/IMG_0001.JPG input/IMG_0001.MOV
```

A valid Live Photo pair should produce output similar to:

```
IMG_0001.JPG and IMG_0001.MOV are Live Photos: D7D2D912-454C-4050-B905-306D3921D10B
```

The identifier will vary between Live Photos.

## Manual Conversion

A single `.pvt` package can be generated with:

```
uvx makelive --pvt --manual input/IMG_0001.JPG input/IMG_0001.MOV
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