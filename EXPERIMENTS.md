# iOS Lock Screen Live Wallpaper Experiment Log

This is an evidence-first handoff for a Codex Agent. It records device-tested controls as of 2026-08-17. **Success** means that, after importing a PVT into macOS Photos and syncing it to the target iPhone, the Lock Screen wallpaper UI allows animation. **Failure** means animation cannot be enabled.

## Evidence Rules

iOS does not publish the complete eligibility rule for Lock Screen Live Wallpaper animation. A single control can show that one combination succeeds or fails on this device; it cannot establish a universal sufficient condition.

Use these terms precisely:

- **Device-verified**: has an iPhone success or failure result.
- **Required in the current pipeline**: replacing/removing the property caused failure while the input, cover, and metadata path were otherwise controlled. This is only a statement about this pipeline and target device.
- **Proven non-required**: at least one device-verified success lacks the property.
- **Open**: no discriminating device control exists, or existing controls do not isolate the cause.

`makelive --check`, AVFoundation metadata inspection, `ffprobe`, and ISO BMFF atom comparisons are structural diagnostics only. They **do not** prove that iOS will enable wallpaper animation.

## Working Baselines

| Package | Source | Device result | Purpose |
| --- | --- | --- | --- |
| `REFERENCE_DOWNLOAD_RAW.pvt` | Original HEIC/MOV from a downloaded Live Photo; media resources unchanged | Success | Downloaded-sample working baseline |
| `REFERENCE_IPHONE_RAW.pvt` | Original HEIC/MOV from an iPhone-captured Live Photo; media resources unchanged | Success | Native-capture working baseline |

Both baselines pass `makelive --check`. The macOS Photos import, iPhone sync, and test route are therefore not the source of the failures.

## Completed Device Controls

| Package | Controlled change | Device result | Supported conclusion |
| --- | --- | --- | --- |
| `REFERENCE_DOWNLOAD_RAW.pvt` | Package the original downloaded resources directly | Success | A working wallpaper does not need an iPhone-captured asset identity. |
| `REFERENCE_IPHONE_RAW.pvt` | Package the original iPhone resources directly | Success | Provides a second, native structural baseline. |
| `REFERENCE_DOWNLOAD_REWRAPPED.pvt` | Preserve the downloaded sample `mdat`; remove and rebuild the two Live Photo metadata tracks and rewrite `moov` | Success | The current `prepare_wallpaper_video()` metadata/`moov` rewrite is not independently disqualifying. |
| `REFERENCE_DOWNLOAD_REENCODED.pvt` | Keep the downloaded HEIC; re-encode the MOV with `libx265` and inject metadata | Failure | x265 bitstreams are rejected in this pipeline on this device. |
| `REFERENCE_DOWNLOAD_VIDEOTOOLBOX.pvt` | Keep the downloaded HEIC; re-encode the MOV with `hevc_videotoolbox` and inject the same metadata | Success | A VideoToolbox bitstream can pass this pipeline. The metadata rewrite alone is not the failure point. |
| `IMG_0001.pvt` through `IMG_0006.pvt` | User JPG/MP4 inputs, VideoToolbox HEVC Main, `hvc1`, $1/600$ timebase, template metadata | Failure | The user inputs still lack at least one eligibility property even on the known-working VideoToolbox path. |
| `IMG_0001_SHORT.pvt` | Same as `IMG_0001.pvt`, but truncate video to $1.7667$ seconds | Failure | Reducing duration to the native baseline range is not sufficient. |

## Conclusions Supported by the Controls

These are engineering conclusions, not a complete public iOS specification:

1. Ordinary Live Photo pairing and the presence of timed metadata are insufficient. Every generated failure passes `makelive --check` and retains the target metadata keys.
2. `libx265` is unsuitable for this target device and pipeline. With the same downloaded cover and metadata rewrite, replacing x265 with VideoToolbox changed failure to success.
3. VideoToolbox is a device-verified viable encoding path, but it is not proven universally required: both original Apple-encoded baselines also succeed.
4. When the video `mdat` is preserved, the current metadata-track cloning, `cdsc`, and `moov` rewrite can succeed.
5. For the user JPG/MP4 inputs, the combined presence of VideoToolbox HEVC Main, `hvc1`, $1/600$, `tapt`, full-duration `live-photo-info`, and `cdsc` remains insufficient.

## Proven Non-Requirements

The properties below are absent from at least one successful baseline, so do not treat them as mandatory rules:

| Property | Evidence |
| --- | --- |
| Captured by an iPhone camera | The downloaded baseline succeeds without an iPhone camera identity. |
| Apple/iPhone EXIF make, model, or camera metadata | The downloaded baseline succeeds without those fields. |
| Audio track | The downloaded baseline succeeds with no audio. |
| `cdsc` track reference | The original downloaded MOV succeeds without `cdsc`. |
| Camera, `live-photo.auto`, vitality, orientation, or similar global private metadata | The downloaded baseline succeeds without the fields present in the iPhone-captured sample. |
| Static metadata reference-dimensions key | The downloaded baseline succeeds without this key. |
| Near pixel-perfect cover-to-video-frame matching | The iPhone baseline succeeds although its best cover/frame SSIM is approximately $0.489$. |
| A duration of approximately one second | The iPhone baseline succeeds at approximately $1.76$ seconds; `IMG_0001_SHORT.pvt` still fails at approximately $1.77$ seconds. Duration alone cannot explain the failure. |

## Observed Differences That Remain Open

| Variable | Successful baselines | User output | Status |
| --- | --- | --- | --- |
| Encoder and detailed HEVC bitstream properties | Native Apple encoding or successful VideoToolbox control | VideoToolbox user output fails; x265 control also fails | There is at least one input-dependent property beyond the encoder. Not isolated. |
| Video dimensions | Download baseline: $886\times1920$; iPhone baseline: $1920\times1440$ | User output: $1080\times1440$ | Dimensions are not proven to be independently causal. |
| Frame rate | Download baseline: approximately $57.14$ fps; iPhone baseline: variable frame rate | User output: $30$ fps | No device test changes only frame rate. |
| Duration | Successful baselines: approximately $1.05$ and $1.76$ seconds | Original user output: approximately $1.87$ to $2.67$ seconds | Truncating `IMG_0001` to $1.77$ seconds still failed; duration is not an isolated cause. |
| JPEG-to-HEIC still-resource structure | Successful controls retain an original HEIC | User output creates HEIC from JPG using `sips` | No independent device control yet: successful MOV plus user-generated HEIC. |
| User-video source characteristics | Baselines have different sources | User source is H.264 MP4, then transcoded to HEVC | GOP, color metadata, VUI/SEI, and sample-table properties have not been isolated. |
| Still-image association time | Successful samples have plausible visual association | `IMG_0001` best SSIM is approximately $0.973$ | High similarity is observed, but no dedicated association-time control exists. |

## Current Implementation and Local Checks

[make_livephotos.py](make_livephotos.py) currently:

1. Uses `sips` to convert the input image to HEIC at the video canvas dimensions.
2. Uses macOS `hevc_videotoolbox` to encode HEVC Main with `hvc1` and a $1/600$ timebase.
3. Uses [prepare_wallpaper_video.py](prepare_wallpaper_video.py) to inject two metadata tracks from the template and expand `live-photo-info` across the video frames.
4. Runs `makelive --pvt --manual` and checks ordinary Live Photo pairing.

The implementation produces ordinary Live Photos and produced a device-verified animated package for the downloaded-sample VideoToolbox control. It has not produced a device-verified animated package for user input sets $1$ through $6$.

## Next Experiments for Codex

Do not change encoding, metadata, and cover resources in the same experiment. Create one fresh-UUID package per control, import each separately into Photos, and obtain an iPhone result before moving on.

1. **Still-resource control**: preserve the successful downloaded MOV and replace only its HEIC with `IMG_0001` converted by `sips`. This isolates whether the JPG-to-HEIC still resource is sufficient to cause failure.
2. **Video-source control**: preserve the successful downloaded HEIC and metadata path while using the `IMG_0001` VideoToolbox video. This retests the user-video path independently.
3. **Frame-rate control**: encode the same `IMG_0001` input at approximately $60$ fps, changing only frame rate.
4. **Static-metadata control**: use the iPhone-native static metadata template instead of the downloaded template, changing only reference-dimensions and orientation-related metadata.

Use a new UUID for every package to avoid deduplication by `content.identifier`.