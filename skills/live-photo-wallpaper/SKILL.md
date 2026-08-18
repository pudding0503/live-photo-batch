---
name: live-photo-wallpaper
description: Create, repair, and validate batch Apple Live Photo PVT packages that enable iPhone Lock Screen animation. Use when working with matched still-image and video pairs, HEIC/HEVC preparation, Live Photo timed metadata, PVT packaging, or diagnosing Live Photos that import successfully but cannot animate as iOS wallpapers.
---

# Live Photo Wallpaper

Use the generator's built-in metadata-only template extracted from a device-verified MOV for wallpaper mode. Do not add a runtime reference MOV dependency or introduce reference media into a package. Matching filename stems are only the batch-pairing convention. Album mode can package original still/video resources for ordinary Live Photo import, but Lock Screen animation requires the wallpaper mode profile and a cover visually continuous with the transition video frame.

## Workflow

1. Locate the project root and read `README.md` plus `RULES.md`.
2. Choose `wallpaper` (default) or `album` mode. Confirm that `input/` contains matched filename stems and `output/` is disposable generated output.
3. In wallpaper mode, use the normalized video's decoded opening frame as the cover and generate 60 fps VideoToolbox HEVC Main, tagged `hvc1`, with a `1/600` video timebase. In album mode, pass the original still/video to `makelive` without transcoding.
4. In wallpaper mode, convert the frame-aligned video opening frame to HEIC at the video canvas size without stretching it. Treat HEIC as this workflow's verified output choice, not a universal Live Photo requirement.
5. In wallpaper mode, apply the embedded Live Photo metadata structure; in album mode, let `makelive` package the original resources. In both modes, use `makelive --pvt --manual` and a fresh content identifier.
6. Keep the verified embedded still-image-time behavior in wallpaper mode unless an isolated device test demonstrates a needed change.
7. Verify ordinary Live Photo pairing locally. In wallpaper mode, also verify the three required metadata identifiers and Lock Screen animation on the target iPhone separately.

Read [references/workflow.md](references/workflow.md) before changing media preparation or metadata code. It distinguishes implementation limits from device-verified properties, including format, resolution, frame rate, and duration.

## Guardrails

- Treat `makelive --check`, `ffprobe`, and AVFoundation metadata inspection as structural checks only; none measures cover-to-motion continuity.
- Preserve a previously generated package until its forced replacement succeeds.
- Change one property at a time when diagnosing device eligibility.
- Use the decoded normalized video opening frame by default in wallpaper mode. When testing an input still, label it explicitly as `--use-input-cover`; do not use color, SAR, or private metadata changes as a substitute for a frame-aligned cover.
- Treat album mode as ordinary Live Photo packaging only; never report it as wallpaper-verified without a target-device test.
- Do not add camera identity, audio, or arbitrary private metadata without a device-tested reason.
