---
name: live-photo-wallpaper
description: Create, repair, and validate batch Apple Live Photo PVT packages that enable iPhone Lock Screen animation. Use when working with matched still-image and video pairs, HEIC/HEVC preparation, Live Photo timed metadata, PVT packaging, or diagnosing Live Photos that import successfully but cannot animate as iOS wallpapers.
---

# Live Photo Wallpaper

Use the generator's built-in metadata-only template. Do not add a runtime reference MOV dependency or introduce reference media into a package. The source still and source video may be independently produced; matching filename stems are only the batch-pairing convention.

## Workflow

1. Locate the project root and read `README.md` plus `RULES.md`.
2. Confirm that `input/` contains matched filename stems, the cover/video aspect ratios match, and `output/` is disposable generated output. Do not require the cover and video to be the same source or scene.
3. Generate video as 60 fps VideoToolbox HEVC Main, tagged `hvc1`, with a `1/600` video timebase.
4. Convert the cover to HEIC at the video canvas size without stretching it. Treat HEIC as this workflow's verified output choice, not a universal Live Photo requirement.
5. Apply the embedded Live Photo metadata structure, package with `makelive --pvt --manual`, and use a fresh content identifier.
6. Match the cover against the prepared video frames and set still-image time to the closest frame after PVT packaging.
7. Verify the three required metadata identifiers and ordinary Live Photo pairing locally. Verify Lock Screen animation on the target iPhone separately.

Read [references/workflow.md](references/workflow.md) before changing media preparation or metadata code. It distinguishes implementation limits from device-verified properties, including format, resolution, frame rate, and duration.

## Guardrails

- Treat `makelive --check`, `ffprobe`, and AVFoundation metadata inspection as structural checks only.
- Preserve a previously generated package until its forced replacement succeeds.
- Change one property at a time when diagnosing device eligibility.
- Do not add camera identity, audio, or arbitrary private metadata without a device-tested reason.
