---
name: auto-video
description: Run and validate AutoVideo-Agent Markdown-to-video workflows, including the v0.1-compatible deterministic offline command and v0.2 provider mode with ComfyUI media, Mock or Command TTS, scene-level SRT, normalized timelines, FFmpeg, and deterministic QA. Use for build, plan, provider, or QA requests; MiniMax, hosted TTS integrations, and word-level subtitle alignment remain planned.
---

# AutoVideo Pipeline

Use this skill to operate the AutoVideo-Agent repository honestly and reproducibly.

## Workflow

1. Read AGENTS.md and inspect the target Markdown script before running anything.
2. Confirm the script has a top-level '#' title and one or more '##' scene headings. Scene fields may include duration, visual, and narration.
3. Run autovideo run <script.md> for v0.1-compatible offline mode, or add --config <config.yaml> for provider mode. Use --output <dir> when the build must be isolated.
4. Inspect the JSON printed by the CLI and then read <output>/report.json and <output>/manifest.json.
5. Run autovideo qa <build-directory>. Treat PASS as validated, WARNING as usable with declared limitations, and FAIL as incomplete.
6. When changing core behavior, run python -m pytest and git diff --check before reporting completion.

## Mode Boundaries

Without --config, preserve the v0.1 deterministic placeholder PPM cards, silent WAV, manifest, report, and FFmpeg degradation behavior. With a v0.2 config, select placeholder or ComfyUI media plus Mock or Command TTS; generate scene-level SRT from actual audio duration, a contiguous timeline, H.264/AAC MP4, and deterministic QA. Do not claim MiniMax, OpenAI TTS, Volcengine, ElevenLabs, word-level alignment, or generic real-media adapters are implemented.

## Agent Request Example

For a request such as:

> Turn examples/demo-script.md into a video and run QA.

execute the CLI, run autovideo qa on the build directory, verify the report and manifest, and summarize the actual status, output paths, duration, scene count, provider names, and warnings. Do not infer media quality from prompt text or claim a remote provider was tested when only HTTP mocks ran.
