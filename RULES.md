# iOS Live Photo Wallpaper Rules

This project creates `.pvt` Live Photo packages from matching image/video pairs. The current pipeline is device-verified on the target iPhone for Lock Screen animation, but iOS remains the final eligibility authority.

## Project Contract

| Directory | Purpose |
| --- | --- |
| `input/` | Source image/video pairs. A pair must share a filename stem for this batch script; the image and video do not need to come from the same original asset or depict the same scene. These files are never modified. |
| `output/` | Generated `.pvt` packages. Each package receives a fresh Live Photo content identifier. |

## Required Environment

- macOS with `sips`, Xcode Command Line Tools, FFmpeg, and VideoToolbox HEVC support
- Python 3.9+ and `uv`

## Verified Output Profile

The generator produces the following profile:

- HEIC cover at the input video canvas dimensions. HEIC is the project's verified output format, rather than a claim that it is universally required for every Live Photo.
- JPEG, HEIC, and differently sized input still images are accepted. The generator resamples the cover to the video canvas.
- Matching input cover/video aspect ratio; the current generator rejects pairs that would be visibly stretched. This is an implementation policy, not a requirement that the two inputs originate from one source.
- HEVC Main through `hevc_videotoolbox`, tagged `hvc1`
- 60 fps output at a `1/600` video timebase
- Built-in `live-photo-info`, still-image transform, and still-image time metadata tracks, derived once from a device-verified reference MOV and containing no media samples
- A `cdsc` reference from metadata tracks to the video track
- Still-image time set to the video frame most similar to the final HEIC cover

On the target device, the same user input failed at 30 fps and enabled Lock Screen animation at 60 fps. Treat 60 fps as a required property of this pipeline, not as a published universal iOS rule.

## Input Flexibility And Limits

### Image and video relationship

The filename is the pairing mechanism, not an assertion of provenance. `cover.jpg` with `cover.mp4` can be assembled even when they are independently produced or show different subjects. The Live Photo format does not use a same-source relationship as a validation key in this pipeline.

For a smooth transition, choose a cover that matches a video frame. The generator compares the final HEIC cover against the normalized video and writes the highest-SSIM frame timestamp as the still-image time. When the cover and video are unrelated, the package may still import and qualify, but the transition will look like a cut.

### HEIC, JPEG, and dimensions

Input covers may be JPEG (`.jpg` or `.jpeg`) or HEIC. The generated cover is always HEIC because that is the profile exercised by the successful target-device package. A JPEG cover might be valid for an ordinary Live Photo, but it is not an alternative that this repository currently generates or claims to have verified for iOS 26 wallpaper animation.

The image and video may have different pixel dimensions. The video canvas is authoritative: a 3066 x 4080 JPEG paired with a 1080 x 1440 video becomes a 1080 x 1440 HEIC cover. The input aspect ratios must remain within 0.005 because this version deliberately refuses to crop or stretch either asset. Pre-crop the two assets to the same aspect ratio to support other compositions.

### Resolution and quality

There is no project-enforced minimum or maximum resolution. The output video retains the source video width and height, while the cover is resampled to those dimensions. Therefore, a larger cover does not add live-motion detail, and the source video should be at the desired final resolution before conversion.

The output video is 8-bit `yuv420p` HEVC Main. It is designed for the verified compatibility profile, not as an HDR, 10-bit, or wide-gamut preservation workflow. Do not promise that those source properties survive conversion without a dedicated device test.

### Frame rate and duration

Every generated video is normalized to constant 60 fps. A 30 fps source gains duplicated presentation frames through FFmpeg timing normalization; footage above 60 fps is sampled down. The 60 fps output uses a `1/600` timebase, so each frame has a 10-unit duration.

The generator does not trim input video or apply a product-level duration cap. It writes metadata samples for the complete normalized video, although MOV container size, memory, and VideoToolbox may impose practical technical limits. The target-device success was a 2.07-second input; a project-wide longest supported duration has not been measured. Do not state a maximum duration in public documentation until it has been tested on the intended iPhone and iOS version.

## Generate Packages

```sh
uv sync
uv run python make_livephotos.py
```

Use `--force` to regenerate existing packages. The prior package is retained until its replacement has been generated and validated locally.

## Local Validation

For every package, the generator verifies that the packaged MOV exposes:

- `com.apple.quicktime.live-photo-info`
- `com.apple.quicktime.live-photo-still-image-transform`
- `com.apple.quicktime.still-image-time`

It also relies on `makelive` to create a valid PVT pairing. These checks are necessary structural diagnostics, not proof of Lock Screen eligibility.

## Device Acceptance

1. Import one PVT into macOS Photos.
2. Confirm it is one Live Photo and that long-press playback works.
3. Sync it to the target iPhone.
4. Select it in the Lock Screen wallpaper UI and confirm animation can be enabled.

Use a new package for each device test so Photos cannot deduplicate by content identifier.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| The cover is stretched | Crop the source image and video to the same aspect ratio before running the generator. |
| Photos imports a Live Photo but Lock Screen animation is unavailable | Verify the output is 60 fps HEVC `hvc1` with the expected metadata tracks, then retest with a fresh package. |
| The cover jumps when motion starts | Inspect the automatically selected still-image time. Do not change encoding or metadata structure while tuning this value. |
| `--force` generation fails | The prior PVT remains in `output/`; inspect the reported per-file error and retry. |
