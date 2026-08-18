# Live Photo Batch Converter

Create Apple Live Photo `.pvt` packages from an image and a video. The verified pipeline targets iPhone Lock Screen animated wallpapers as well as ordinary Live Photo import.

## Requirements

- macOS
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- Xcode Command Line Tools
- FFmpeg with `hevc_videotoolbox`

## Layout

```text
input/      # Source .jpg/.jpeg/.heic and .mov/.mp4 pairs
output/     # Generated PVT packages
```

The filename stem is only the batch-pairing key: `sunset.jpg` is paired with `sunset.mp4`. The generator can assemble arbitrary still/video resources into an ordinary Live Photo, but that does not establish Lock Screen eligibility. For the target iPhone, the cover must depict the same scene and closely match the video frame at the intended transition point. Extracting the cover from the video opening frame is the most reliable choice.

The still and video may have different pixel dimensions and do not need to be exported from one original asset, provided they remain visually continuous at the transition. The cover is resampled to the video canvas, so pre-crop the source pair to matching aspect ratios when avoiding distortion matters.

## Media Profile

| Property | Input | Generated PVT resource | Status |
| --- | --- | --- | --- |
| Still image format | JPEG, HEIC | HEIC | HEIC is this project's verified output choice, not a claim that every Live Photo must use HEIC. |
| Still-image dimensions | Any dimensions | Exactly the video canvas | A higher-resolution input image is downsampled. Match the video aspect ratio to avoid stretching. |
| Cover/video relationship | Any pair can be packaged | Cover closely matches the transition video frame | Device-verified Lock Screen eligibility requires visual continuity. No universal similarity threshold is known. |
| Video container | MOV or MP4 | MOV | Only the primary video stream is used; audio is removed. |
| Video codec | Any FFmpeg/VideoToolbox-decodable source | HEVC Main, `hvc1`, `yuv420p` | This exact output profile was device-verified. |
| Frame rate | Constant or variable source rate | Constant 60 fps | 30 fps produced an ordinary Live Photo but did not enable wallpaper animation on the target device. |
| Video timebase | Any supported source | `1/600` | At 60 fps, each output frame occupies 10 timebase units. |
| Duration | No policy cap or automatic trim | Source duration after 60 fps normalization | Device-verified inputs range from 1.87 to 2.67 seconds. No maximum has been established. |
| Video resolution | Any VideoToolbox-supported source size | Source video canvas | No fixed minimum or maximum is enforced by the project. |

The converter makes a 60 fps output from every source. A 30 fps source gains duplicated presentation frames as FFmpeg's `fps` filter normalizes timing; a source above 60 fps is sampled down to 60 fps. It preserves the video canvas, so final visual detail is limited by the source video, not by a larger cover image. HDR, 10-bit, wide-gamut preservation, and a universal maximum resolution or duration are not current project guarantees.

The generator does not apply a product-level duration cap or trim video. Container size, memory, and VideoToolbox can still impose practical technical limits. Target-device successes currently cover 1.87 to 2.67 seconds after normalization. Treat longer durations as uncharacterized: generate a fresh PVT and test it in the target iPhone Lock Screen UI before relying on it.

The generator embeds a metadata-only template extracted from a device-verified wallpaper MOV. It contains the required track structure and metadata samples, but no reference still image, video frames, audio, or runtime file dependency.

## Usage

```sh
uv sync
uv run python make_livephotos.py
```

After activating the project environment, the equivalent direct command is:

```sh
python make_livephotos.py
```

To replace existing output packages after a successful new generation:

```sh
uv run python make_livephotos.py --force
```

`makelive` 0.7.0 is pinned as a project dependency, so the batch script invokes the project environment directly rather than creating a temporary `uvx` tool environment for every package. Each packaging operation has a 120-second timeout. A single interrupt resumes unfinished packages; press Ctrl-C again within two seconds to exit and retain completed packages.

The script never changes `input/` files. It creates an HEIC cover, converts the video to 60 fps VideoToolbox HEVC, applies the embedded verified metadata structure, and writes the PVT package to `output/`. It does not measure visual continuity, so choose a cover from the opening video frame or a nearby matching frame before generation when Lock Screen animation matters.

## Verify on iPhone

Structural checks are performed during generation, but iOS makes the final Lock Screen eligibility decision. Import each package into macOS Photos, sync it to the target iPhone, and verify that Lock Screen animation can be enabled.

See [the compatibility rules](RULES.md) for the required media profile, validation steps, and troubleshooting.

## License

MIT license.
