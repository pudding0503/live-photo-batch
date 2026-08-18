# iOS Live Photo Wallpaper Rules

This project creates `.pvt` Live Photo packages from matching image/video pairs. The current pipeline is device-verified on the target iPhone for Lock Screen animation, but iOS remains the final eligibility authority.

## Project Contract

| Directory | Purpose |
| --- | --- |
| `input/` | Source image/video pairs. A pair must share a filename stem. The image selects the pair and remains available as an optional cover; the default wallpaper cover comes from the normalized video opening frame. These files are never modified. |
| `output/` | Generated `.pvt` packages. Each package receives a fresh Live Photo content identifier. |

## Required Environment

- macOS with `sips`, Xcode Command Line Tools, FFmpeg, and VideoToolbox HEVC support
- Python 3.10+ and `uv`

## Package Modes

| Mode | Cover | Video | Intended result |
| --- | --- | --- | --- |
| `wallpaper` (default) | Opening frame of the normalized 60 fps video, converted to HEIC | VideoToolbox HEVC Main, `hvc1`, 60 fps, `1/600`, embedded wallpaper metadata | Target-device Lock Screen animation profile |
| `album` | Original JPG/HEIC | Original MP4/MOV | Ordinary Live Photo import/playback; wallpaper eligibility is not guaranteed |

`--use-input-cover` is a wallpaper-mode diagnostic/compatibility override. It preserves the matched still but can recreate the cover/video mismatch that prevents Lock Screen animation.

## Target Device Selection

Use `--target-device` to select a label from `live_photo_config.py`. The selection is printed in the run report and is intended to organize device testing. Add or rename entries in that tuple when maintaining a device list. It does not currently change encoding parameters: all listed models use the same verified wallpaper profile, and only `target` is marked device-tested in this repository. Add a model-specific profile only after an isolated real-device experiment.

## Verified Output Profile

The generator produces the following profile:

- HEIC cover at the input video canvas dimensions. By default it is extracted from the normalized video's opening frame. HEIC is the project's verified output format, rather than a claim that it is universally required for every Live Photo.
- JPEG, HEIC, and differently sized input still images are accepted as pairing inputs and as an explicit optional cover. The default wallpaper path does not use their pixels.
- The generated cover is resampled to the input video canvas. Match input aspect ratios when using `--use-input-cover` to avoid stretching; the current generator does not crop automatically.
- HEVC Main through `hevc_videotoolbox`, tagged `hvc1`
- 60 fps output at a `1/600` video timebase
- Embedded timed `live-photo-info`, still-image transform, and still-image time metadata tracks extracted from a device-verified MOV
- A `cdsc` reference from metadata tracks to the video track
- Still-image time carried by the verified embedded template

On the target device, the same user input failed at 30 fps and enabled Lock Screen animation at 60 fps. Treat 60 fps as a required property of this pipeline, not as a published universal iOS rule.

## Target-Device Evidence

These observations apply to the iPhone and iOS version used to validate this repository. They are implementation evidence, not a public Apple compatibility specification.

| Control | Lock Screen result | Interpretation |
| --- | --- | --- |
| 30 fps video with otherwise valid Live Photo pairing | Unavailable | The package can import as a Live Photo, but this profile requires 60 fps for wallpaper animation. |
| 60 fps HEVC Main, `hvc1`, `1/600`, and verified timed metadata | Available | This is the baseline output profile. |
| 1.87-second video with a cover decoded from its opening frame | Available | The tested duration range is at least 1.87 to 2.67 seconds; no maximum is known. |
| Visually mismatched cover and opening video frame | Unavailable | Resource continuity is an eligibility condition, not only a transition-quality concern. |
| The mismatched pair after color, wide-gamut, and sample-aspect-ratio experiments | Unavailable | Do not treat color normalization or SAR removal as a substitute for a frame-aligned cover. |
| The same video with only its cover replaced by the decoded opening frame | Available | Use this as the first isolation control when a structurally valid package cannot animate. |

## Input Flexibility And Limits

### Image and video relationship

The filename is the pairing mechanism, not an assertion of provenance. `cover.jpg` with `cover.mp4` can be assembled even when the resources are independently produced. That describes PVT packaging only, not target-device Lock Screen eligibility.

For iOS Lock Screen animation, use a cover that depicts the same scene and closely matches the frame selected for the transition. The default script path extracts the normalized video's opening frame automatically. A nearby frame from the same shot is acceptable only after device testing. Do not claim that unrelated content qualifies for animated wallpaper.

### Cover-to-motion continuity

This is a target-device eligibility condition, not just a visual-quality preference. In a controlled test, an otherwise valid P3 package with a visually different cover and video opening frame failed to enable animation. Replacing only that cover with the decoded opening video frame enabled animation. Color normalization, explicit sample-aspect-ratio removal, and the same structural metadata did not repair the mismatched-cover package.

No universal SSIM or pixel-difference threshold is known. Do not invent one. When eligibility matters, derive the cover from the video frame that should lead into motion and test the resulting fresh PVT on the intended iPhone.

### HEIC, JPEG, and dimensions

Input covers may be JPEG (`.jpg` or `.jpeg`) or HEIC. The generated cover is always HEIC because that is the profile exercised by the successful target-device package. A JPEG cover might be valid for an ordinary Live Photo, but it is not an alternative that this repository currently generates or claims to have verified for iOS 26 wallpaper animation.

The image and video may have different pixel dimensions. The video canvas is authoritative: a 3066 x 4080 JPEG paired with a 1080 x 1440 video becomes a 1080 x 1440 HEIC cover. The generator does not crop automatically, so pre-crop the sources to the same aspect ratio to avoid stretching.

### Resolution and quality

There is no project-enforced minimum or maximum resolution. The output video retains the source video width and height, while the cover is resampled to those dimensions. Therefore, a larger cover does not add live-motion detail, and the source video should be at the desired final resolution before conversion.

The output video is 8-bit `yuv420p` HEVC Main. It is designed for the verified compatibility profile, not as an HDR, 10-bit, or wide-gamut preservation workflow. Do not promise that those source properties survive conversion without a dedicated device test.

The successful aligned-cover control retained Display P3 cover/video resources, so P3 is not established as a standalone wallpaper blocker. Do not normalize color as a substitute for cover-to-motion continuity.

### Frame rate and duration

Every generated video is normalized to constant 60 fps. A 30 fps source gains duplicated presentation frames through FFmpeg timing normalization; footage above 60 fps is sampled down. The 60 fps output uses a `1/600` timebase, so each frame has a 10-unit duration.

The generator does not trim input video or apply a product-level duration cap. It writes metadata samples for the complete normalized video, although MOV container size, memory, and VideoToolbox may impose practical technical limits. Target-device successes currently span 1.87 to 2.67 seconds. A project-wide longest supported duration has not been measured. Do not state a maximum duration in public documentation until it has been tested on the intended iPhone and iOS version.

## Generate Packages

```sh
uv sync
uv run python make_livephotos.py
```

The default command uses wallpaper mode and the normalized video opening frame as the cover. Use `--mode album` for original JPG/MP4 packaging, `--use-input-cover` to preserve the matched still in wallpaper mode, and `--force` to regenerate existing packages. The existing package is removed before replacement, so keep a copy when it is valuable.

## Local Validation

For every package, the generator verifies that the packaged MOV exposes:

- `com.apple.quicktime.live-photo-info`
- `com.apple.quicktime.live-photo-still-image-transform`
- `com.apple.quicktime.still-image-time`

It also relies on `makelive` to create a valid PVT pairing. These checks cannot assess cover-to-video visual continuity, so they are necessary structural diagnostics, not proof of Lock Screen eligibility.

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
| Photos imports a Live Photo but Lock Screen animation is unavailable | First replace the cover with the decoded opening video frame and test a fresh PVT. If it succeeds, the source cover was not visually continuous enough for wallpaper eligibility. Otherwise verify 60 fps HEVC `hvc1` and the expected metadata tracks. |
| The cover jumps when motion starts | Use the default video-frame cover. If `--use-input-cover` was selected, replace the still with the decoded opening frame or a nearby frame from the same shot. Do not change encoding or metadata structure while tuning source media. |
| `--force` generation fails | Regenerate after inspecting the reported per-file error; the prior PVT may already have been removed. |
