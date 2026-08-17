# Live Photo Batch Converter

Create Apple Live Photo `.pvt` packages from an image and a video. The verified pipeline targets iPhone Lock Screen animated wallpapers as well as ordinary Live Photo import.

## Requirements

- macOS
- Python 3.9+
- [uv](https://docs.astral.sh/uv/)
- Xcode Command Line Tools
- FFmpeg with `hevc_videotoolbox`

## Layout

```text
input/      # Source .jpg/.jpeg/.heic and .mov/.mp4 pairs
reference/  # A known-good animated Live Photo MOV metadata template
output/     # Generated PVT packages
```

The generator uses the filename stem only as a batch-pairing key: `sunset.jpg` is paired with `sunset.mp4`. It does not require the image and video to come from the same original asset, camera, or scene. Use an image that is visually close to one video frame when a seamless cover-to-motion transition matters.

The current crop policy is intentionally strict: input image and video aspect ratios must match within 0.005. Their pixel dimensions may differ. The cover is resampled to the video canvas; the video is not upscaled. Crop source media before generation when their aspect ratios differ.

## Media Profile

| Property | Input | Generated PVT resource | Status |
| --- | --- | --- | --- |
| Still image format | JPEG, HEIC | HEIC | HEIC is this project's verified output choice, not a claim that every Live Photo must use HEIC. |
| Still-image dimensions | Any dimensions with the video aspect ratio | Exactly the video canvas | A higher-resolution input image is downsampled. |
| Video container | MOV or MP4 | MOV | Only the primary video stream is used; audio is removed. |
| Video codec | Any FFmpeg/VideoToolbox-decodable source | HEVC Main, `hvc1`, `yuv420p` | This exact output profile was device-verified. |
| Frame rate | Constant or variable source rate | Constant 60 fps | 30 fps produced an ordinary Live Photo but did not enable wallpaper animation on the target device. |
| Video timebase | Any supported source | `1/600` | At 60 fps, each output frame occupies 10 timebase units. |
| Duration | No policy cap or automatic trim | Source duration after 60 fps normalization | No maximum wallpaper-eligible duration has been established for this project. |
| Video resolution | Any VideoToolbox-supported source size | Source video canvas | No fixed minimum or maximum is enforced by the project. |

The converter makes a 60 fps output from every source. A 30 fps source gains duplicated presentation frames as FFmpeg's `fps` filter normalizes timing; a source above 60 fps is sampled down to 60 fps. It preserves the video canvas, so final visual detail is limited by the source video, not by a larger cover image. HDR, 10-bit, wide-gamut preservation, and a universal maximum resolution or duration are not current project guarantees.

The generator does not apply a product-level duration cap or trim video. Container size, memory, and VideoToolbox can still impose practical technical limits. The verified target-device result is a 2.07-second source normalized to 60 fps. Treat longer durations as uncharacterized: generate a fresh PVT and test it in the target iPhone Lock Screen UI before relying on it.

Provide your own device-verified Live Photo MOV in `reference/`. The repository does not require publishing a personal or licensed reference asset.

## Usage

```sh
uv sync
uv run python make_livephotos.py
```

To replace existing output packages after a successful new generation:

```sh
uv run python make_livephotos.py --force
```

The script never changes `input/` files. It creates an HEIC cover, converts the video to 60 fps VideoToolbox HEVC, applies the working Live Photo metadata structure from `reference/`, selects the video frame closest to the cover for the still-image time, and writes the PVT package to `output/`. Unrelated cover/video content can package successfully, but will normally produce a visible hard transition.

## Verify on iPhone

Structural checks are performed during generation, but iOS makes the final Lock Screen eligibility decision. Import each package into macOS Photos, sync it to the target iPhone, and verify that Lock Screen animation can be enabled.

See [the compatibility rules](RULES.md) for the required media profile, validation steps, and troubleshooting.

## License

MIT license.
