# Live Photo Wallpaper Workflow

## Media Contract

Use these roles consistently:

- `input/`: source pairs. Matching stems select pairs for batch processing. Arbitrary resources can be packaged, but target-device Lock Screen animation requires a cover visually continuous with the transition video frame.
- `output/`: generated PVTs only.

Wallpaper mode embeds a metadata-only template extracted from a device-verified MOV. It contains the required Live Photo metadata tracks and samples, but no reference still image, video frames, audio, or runtime file dependency. Album mode delegates original-resource packaging to `makelive` and does not claim wallpaper eligibility.

## Source Constraints

Accept JPEG or HEIC covers and MOV or MP4 video sources. The current batch script uses matching filename stems and accepts different image and video pixel dimensions. It resamples the cover to the video canvas without cropping, so callers should pre-crop mismatched aspect ratios to avoid stretching.

For animated wallpaper, derive the cover from the decoded opening frame of the normalized video by default. A frame from the same shot may work after target-device testing, but a different pose, framing, or scene is not a supported wallpaper input. The two resources do not need to be exported from one original asset, but they must remain visually continuous at the transition. The project's `--use-input-cover` option is an explicit exception for ordinary Live Photo or diagnostic use.

For ordinary album packaging, use `--mode album`. This keeps the original still and video, including their source codec and frame rate, and relies on `makelive` for the Live Photo container. A successful album import is only a structural/Photos result, not evidence that iOS will enable Lock Screen animation.

An HEIC cover is the current generated output and target-device-verified choice. Do not represent it as an iOS-wide requirement for every possible Live Photo. A JPEG cover may be suitable for ordinary Live Photo workflows, but this skill's wallpaper profile has not been verified with a generated JPEG cover.

The video canvas is authoritative. Resample the cover to the video dimensions; preserve the video dimensions through transcoding. Do not expect a larger still image to improve video detail. The pipeline outputs 8-bit `yuv420p` and does not promise HDR, 10-bit, or wide-gamut preservation.

An aligned-cover control with Display P3 resources enabled animation on the target device, so P3 is not established as a standalone blocker. Treat color conversion as an isolated experiment, never as a replacement for a frame-aligned cover.

## Proven Processing Profile

Use macOS `hevc_videotoolbox` with HEVC Main, `hvc1`, `yuv420p`, a `1/600` video track timebase, and a 60 fps output. The source may be 30 fps; the output frame rate is what was device-verified.

Create the HEIC cover from the normalized video's opening frame at the video canvas size. Pre-crop incompatible aspect ratios when using `--use-input-cover`; the default frame cover already matches the video canvas.

Normalize every source to constant 60 fps. A lower-rate source is timing-normalized to 60 fps, while a higher-rate source is sampled down. With the `1/600` timebase, each 60 fps frame has 10 timing units.

Do not impose or claim a maximum video duration: the current implementation processes the complete source duration and does not trim or apply a product-level cap. MOV container size, memory, and VideoToolbox can still impose practical technical limits. Target-device successes currently span 1.87 to 2.67 seconds. Treat longer durations as uncharacterized until a fresh PVT is tested on the intended iPhone and iOS version.

Clone the two-track embedded Live Photo metadata structure. Retain the generated video media data, add metadata-to-video `cdsc` references, and package with the pinned project `makelive` dependency using `makelive --pvt --manual`.

## Still-Image Association

The still-image-time metadata track selects the video timestamp used to transition from the cover into motion. Preserve the timestamp behavior from the embedded verified template. Target-device testing showed that a PVT with a visually mismatched cover failed to animate even after color and sample-aspect-ratio normalization; replacing only the cover with the decoded opening video frame enabled animation. Treat frame-aligned cover selection as an eligibility condition before altering metadata.

No numeric similarity threshold has been established. Do not infer one from local image metrics. For diagnosis, keep the video and package structure unchanged, replace only the cover with a decoded first frame, regenerate with a fresh content identifier, and test on the target iPhone.

## Device-Tested Controls

Use these results as a diagnostic order, not as universal Apple requirements:

| Control | Target-device result | Use in future work |
| --- | --- | --- |
| 30 fps otherwise-valid package | Cannot animate | Always normalize this workflow to 60 fps. |
| 60 fps HEVC Main, `hvc1`, `1/600`, and embedded metadata | Can animate | Preserve this output profile. |
| 1.87-second video with a decoded first-frame cover | Can animate | Do not reject short sources solely because they are below two seconds. |
| Mismatched cover and opening frame | Cannot animate | Diagnose the cover before changing container metadata. |
| Mismatched pair after color and SAR normalization | Cannot animate | Do not use color or SAR changes as a proxy for cover continuity. |
| Same video with only a decoded first-frame cover | Can animate | This is the decisive control for a suspected cover mismatch. |

## Acceptance

Check these metadata identifiers in the package MOV:

- `mdta/com.apple.quicktime.live-photo-info`
- `mdta/com.apple.quicktime.live-photo-still-image-transform`
- `mdta/com.apple.quicktime.still-image-time`

Then import each PVT into macOS Photos, sync it to the target iPhone, and confirm the Lock Screen UI enables animation. A local success is not a device acceptance result.

## Diagnostic Order

When animation is unavailable, confirm that the package was generated with `--mode wallpaper` and without `--use-input-cover`, then test a fresh package using the decoded normalized opening frame. If that enables animation, the supplied still is not a supported wallpaper cover; do not change metadata or encoding to compensate. Otherwise confirm 60 fps, HEVC Main, `hvc1`, `1/600`, and required metadata. Test every candidate with a fresh UUID on the device and alter one variable at a time.
