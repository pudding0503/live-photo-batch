# Live Photo Wallpaper Workflow

## Media Contract

Use these roles consistently:

- `input/`: source pairs. Matching stems select pairs for batch processing; the cover and motion can be independently produced and need not depict the same scene.
- `output/`: generated PVTs only.

The generator embeds a metadata-only template extracted from a device-verified MOV. It contains the required Live Photo metadata tracks and samples, but no reference still image, video frames, audio, or runtime file dependency.

## Source Constraints

Accept JPEG or HEIC covers and MOV or MP4 video sources. The current batch script uses matching filename stems and accepts different image and video pixel dimensions. It resamples the cover to the video canvas without cropping, so callers should pre-crop mismatched aspect ratios to avoid stretching.

An HEIC cover is the current generated output and target-device-verified choice. Do not represent it as an iOS-wide requirement for every possible Live Photo. A JPEG cover may be suitable for ordinary Live Photo workflows, but this skill's wallpaper profile has not been verified with a generated JPEG cover.

The video canvas is authoritative. Resample the cover to the video dimensions; preserve the video dimensions through transcoding. Do not expect a larger still image to improve video detail. The pipeline outputs 8-bit `yuv420p` and does not promise HDR, 10-bit, or wide-gamut preservation.

## Proven Processing Profile

Use macOS `hevc_videotoolbox` with HEVC Main, `hvc1`, `yuv420p`, a `1/600` video track timebase, and a 60 fps output. The source may be 30 fps; the output frame rate is what was device-verified.

Create the HEIC cover at the video canvas size. Pre-crop incompatible aspect ratios rather than relying on resampling to preserve composition.

Normalize every source to constant 60 fps. A lower-rate source is timing-normalized to 60 fps, while a higher-rate source is sampled down. With the `1/600` timebase, each 60 fps frame has 10 timing units.

Do not impose or claim a maximum video duration: the current implementation processes the complete source duration and does not trim or apply a product-level cap. MOV container size, memory, and VideoToolbox can still impose practical technical limits. The target-device success was 2.07 seconds. Treat longer durations as uncharacterized until a fresh PVT is tested on the intended iPhone and iOS version.

Clone the two-track embedded Live Photo metadata structure. Retain the generated video media data, add metadata-to-video `cdsc` references, and package with the pinned project `makelive` dependency using `makelive --pvt --manual`.

## Still-Image Association

The still-image-time metadata track selects the video timestamp used to transition from the cover into motion. Preserve the timestamp behavior from the embedded verified template. Tune source cover/video alignment before changing this metadata, and change it only in an isolated device experiment.

## Acceptance

Check these metadata identifiers in the package MOV:

- `mdta/com.apple.quicktime.live-photo-info`
- `mdta/com.apple.quicktime.live-photo-still-image-transform`
- `mdta/com.apple.quicktime.still-image-time`

Then import each PVT into macOS Photos, sync it to the target iPhone, and confirm the Lock Screen UI enables animation. A local success is not a device acceptance result.

## Diagnostic Order

When animation is unavailable, first confirm 60 fps, HEVC Main, `hvc1`, `1/600`, and required metadata. Test a fresh UUID package on the device. Only then alter one variable at a time; do not simultaneously change cover, video, metadata, and frame rate.
