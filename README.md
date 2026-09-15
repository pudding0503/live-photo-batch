<p align="center">
 <img width="100px" src="logo.svg" align="center" alt="Logo" />
 <h2 align="center">Live Photo Batch Converter</h2>
 <p align="center">Create Apple Live Photo for iOS 26+</p>
</p>
<p align="center"> <img alt="version" src="https://img.shields.io/github/release/pudding0503/live-photo-batch"> <img alt="issues" src="https://img.shields.io/github/issues/pudding0503/live-photo-batch?color=F48D73"> <img alt="license" src="https://img.shields.io/github/license/pudding0503/live-photo-batch"> </p>

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

The still and video may have different pixel dimensions and do not need to be exported from one original asset, provided they remain visually continuous at the transition. In wallpaper mode, an explicitly selected input cover is resampled to the video canvas, so pre-crop the source pair to matching aspect ratios when avoiding distortion matters. Album mode keeps the original resources.

By default, the generator extracts the opening frame from the normalized video and uses that frame as the HEIC cover. The matched input image remains the pairing key, but is not used as the wallpaper cover unless explicitly requested. Use `--use-input-cover` only when preserving the supplied still is more important than target-device wallpaper eligibility or when running an isolated experiment.

The `wallpaper` mode is the default. Use `--mode album` when you only need Photos to recognize an ordinary Live Photo: it passes the original JPG/HEIC and MP4/MOV to `makelive` without transcoding or replacing the cover. Album mode may import and play normally but is not guaranteed to qualify as an animated Lock Screen wallpaper.

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

To create ordinary Live Photos from the original resources:

```sh
uv run python make_livephotos.py --mode album
```

To preserve the matched input image as the cover:

```sh
uv run python make_livephotos.py --use-input-cover
```

Select the target iPhone label for the run report:

```sh
uv run python make_livephotos.py --target-device iphone-16
```

The device list is configuration only. All currently listed models use the same verified wallpaper profile; only `target` is marked as device-tested in this repository. Add or rename entries in `live_photo_config.py`; selecting a model currently changes the report label, not the media encoding.

`makelive` 0.7.0 is pinned as a project dependency, so the batch script invokes the project environment directly rather than creating a temporary `uvx` tool environment for every package. Each packaging operation has a 120-second timeout. A single interrupt resumes unfinished packages; press Ctrl-C again within two seconds to exit and retain completed packages.

The script never changes `input/` files. Wallpaper mode converts the video to 60 fps VideoToolbox HEVC, extracts the normalized opening frame as the default HEIC cover, applies the embedded verified metadata structure, and writes the PVT package to `output/`. Album mode preserves the original still/video resources and delegates ordinary packaging to `makelive`. The optional input-cover path does not measure visual continuity and may produce an ordinary Live Photo that cannot be selected as an animated wallpaper.

## Verify on iPhone

Structural checks are performed during generation, but iOS makes the final Lock Screen eligibility decision. Import each package into macOS Photos, sync it to the target iPhone, and verify that Lock Screen animation can be enabled.

See [the compatibility rules](RULES.md) for the required media profile, validation steps, and troubleshooting.

## License

[MIT license](https://github.com/pudding0503/live-photo-batch/blob/main/LICENSE)
