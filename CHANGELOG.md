# Changelog

All notable changes to AutoVideo-Agent are documented here.

## [0.2.0]

- Added provider interfaces for normalized media and audio artifacts.
- Added the experimental ComfyUI media provider with mocked API integration coverage.
- Added Mock and Command TTS providers, scene-level SRT subtitles, and mixed image/video rendering.
- Kept the deterministic, offline pipeline and CLI compatible with v0.1.

Live ComfyUI workflow validation is still pending. See [Issue #12](https://github.com/wangxin6x/AutoVideo-Agent/issues/12).

## [0.1.0]

- Initial local-first Markdown-to-video pipeline with deterministic scene assets, silent timeline, FFmpeg rendering, and QA reports.
