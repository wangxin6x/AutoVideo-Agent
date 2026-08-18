# AutoVideo-Agent

[![Tests](https://github.com/wangxin6x/AutoVideo-Agent/actions/workflows/test.yml/badge.svg)](https://github.com/wangxin6x/AutoVideo-Agent/actions/workflows/test.yml)
[![Latest Release](https://img.shields.io/github/v/release/wangxin6x/AutoVideo-Agent?display_name=tag)](https://github.com/wangxin6x/AutoVideo-Agent/releases/latest)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![MIT License](https://img.shields.io/github/license/wangxin6x/AutoVideo-Agent.svg)](LICENSE)

**把 Markdown 脚本变成可复现的视频流水线：分镜、场景资产、时间轴、QA 和 MP4。**

面向 Codex、Claude Code、Gemini CLI 及其他 coding-agent 工作流。v0.1 是本地优先、确定性的首版：生成可检查的占位场景资产，并在安装 FFmpeg 时合成视频，不需要 API Key 或云账号。

~~~text
Markdown 脚本 -> Storyboard -> Scene Manifest -> Media -> Timeline -> FFmpeg -> QA -> MP4
~~~

> 默认的 v0.1 兼容命令不宣传 AI 视频生成。v0.2 provider 模式新增 ComfyUI API 媒体，MiniMax 等托管 provider 仍在计划中。

## Demo

Demo 使用 [examples/demo-script.md](examples/demo-script.md)，包含 3 个场景、7 秒总时长。

~~~text
输入                          流水线                           输出
examples/demo-script.md  ->  autovideo run               ->  video.mp4
                              解析 + manifest + assets       manifest.json
                              静音 WAV + FFmpeg              report.json
~~~

![确定性场景卡片 Demo](docs/assets/demo.gif)

~~~powershell
autovideo run examples/demo-script.md
~~~

构建目录为 build/demo-script/。FFmpeg 存在时生成 video.mp4；否则保留可检查资产并报告 status: degraded。

## 快速开始

从 PyPI 安装：

~~~powershell
python -m pip install autovideo-agent
~~~

如需运行仓库 Demo，请克隆仓库以取得示例脚本：

~~~powershell
git clone https://github.com/wangxin6x/AutoVideo-Agent.git
cd AutoVideo-Agent
autovideo run examples/demo-script.md
~~~

wheel 包含 `autovideo` CLI 和运行时包；`examples/` 是仓库中的演示输入。安装 PyPI 包后可以直接使用自己的 Markdown 脚本，或克隆仓库运行上述 Demo。

## Features

| 状态 | 能力 | 证据 |
| --- | --- | --- |
| ✅ 当前可用 | Markdown 分镜解析 | src/autovideo/parser.py |
| ✅ 当前可用 | Scene manifest | manifest.json |
| ✅ 当前可用 | 确定性离线资产 | PPM 场景卡片 |
| ✅ 当前可用 | 静音 WAV 时间轴 | audio-silence.wav |
| ✅ 当前可用 | FFmpeg MP4 渲染 | src/autovideo/render.py |
| ✅ 当前可用 | 优雅降级 | report.json |
| ✅ 当前可用 | CLI | autovideo run <script.md> |
| ✅ 当前可用 | QA 报告 | report.json |
| ✅ 当前可用 | Codex Skill / AGENTS integration | AGENTS.md 与 skills/auto-video/SKILL.md |
| 🧪 Experimental | ComfyUI API 媒体 provider | 已实现，等待真实 workflow 联调；包含提交、轮询、重试、resume 与下载 |
| ✅ 当前可用 | Mock 与 Command TTS | 静音 fallback 或任意本地 TTS CLI |
| ✅ 当前可用 | Scene-level SRT 字幕 | 使用真实 TTS 音频时长 |
| 🚧 计划中 | MiniMax | [#1](https://github.com/wangxin6x/AutoVideo-Agent/issues/1) |
| 🚧 计划中 | 托管 TTS 集成 | OpenAI、火山与 ElevenLabs |
| 🚧 计划中 | 词级字幕对齐 | [#4](https://github.com/wangxin6x/AutoVideo-Agent/issues/4) |
| 🚧 计划中 | 真实媒体适配器 | [#5](https://github.com/wangxin6x/AutoVideo-Agent/issues/5) |

## Architecture

~~~mermaid
flowchart LR
    Script[Markdown Script] --> Parser[Script Parser]
    Parser --> Storyboard[Storyboard]
    Storyboard --> Manifest[Scene Manifest]
    Storyboard --> Providers[Provider Interface]
    Providers --> Media[Media assets]
    Media --> Timeline[Timeline]
    Timeline --> Renderer[Renderer]
    Renderer --> QA[QA report]
    QA --> MP4[MP4 output]
    VideoProvider[ComfyUI Media Provider - Experimental] -. media .-> Providers
    TTSProvider[Mock / Command TTS] -. audio .-> Providers
    AssetProvider[Asset Provider - Planned] -. slot .-> Providers
~~~

当前渲染器只写入确定性占位卡片和静音音轨；provider 插槽是文档化方向，不代表已交付集成。

### ComfyUI 验证状态

ComfyUI API 行为已有 mock integration tests 覆盖，但 `v0.2.0-beta.1` 尚未针对真实 ComfyUI workflow 验证。Provider 已实现但仍属 Experimental，不应视为 production-ready；真实 image/video 联调记录在 [Issue #12](https://github.com/wangxin6x/AutoVideo-Agent/issues/12)。

## 在 Codex 中使用

先读取 AGENTS.md，再按需读取 skills/auto-video/SKILL.md：

> Turn examples/demo-script.md into a video and run QA. Use skills/auto-video/SKILL.md.

实际 CLI：

~~~powershell
autovideo run examples/demo-script.md
~~~

QA 指检查命令结果以及 report.json/manifest.json，不代表已有独立 AI 质量评分器。这是仓库工作流，不是 Codex 或模型厂商的官方背书。

## Roadmap

- **v0.1 ✅**：本地解析、确定性场景卡片、静音时间轴、FFmpeg MP4、降级报告、测试和 Agent onboarding。
- **v0.2（当前开发分支）**：Provider 合同、ComfyUI 媒体、Mock/Command TTS、scene-level SRT、标准 timeline、混合 renderer 与确定性 QA。MiniMax 和托管 TTS 仍在计划中。
- **v0.3**：媒体适配器 [#5](https://github.com/wangxin6x/AutoVideo-Agent/issues/5)、跨平台 FFmpeg [#6](https://github.com/wangxin6x/AutoVideo-Agent/issues/6)、CI 渲染 [#9](https://github.com/wangxin6x/AutoVideo-Agent/issues/9)、更多格式 [#10](https://github.com/wangxin6x/AutoVideo-Agent/issues/10)。

## 社区

- [Issues](https://github.com/wangxin6x/AutoVideo-Agent/issues)
- [Good First Issues](https://github.com/wangxin6x/AutoVideo-Agent/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
- [Feature Requests](https://github.com/wangxin6x/AutoVideo-Agent/issues/new?labels=enhancement&template=feature_request.md)
- [Bug Reports](https://github.com/wangxin6x/AutoVideo-Agent/issues/new?labels=bug&template=bug_report.md)

欢迎贡献文档、示例、跨平台改进和 provider 边界设计。提交前请运行 python -m pytest 和 git diff --check。

## 中文与英文

英文首页：[README.md](README.md)。

## 许可证

MIT，见 [LICENSE](LICENSE)。
