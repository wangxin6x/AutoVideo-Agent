from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .parser import ScriptParseError, parse_script_file
from .pipeline import build_with_providers, plan_project
from .providers import ProviderError
from .qa import qa_build
from .render import DEFAULT_FPS, DEFAULT_HEIGHT, DEFAULT_WIDTH, render_project
from .renderer_v2 import RenderError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autovideo", description="Build a local video from a Markdown storyboard.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="parse a Markdown script and render it")
    run.add_argument("script", type=Path, help="path to a Markdown storyboard")
    run.add_argument("-o", "--output", type=Path, help="build directory (default: build/<script-name>)")
    run.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    run.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    run.add_argument("--fps", type=int, default=DEFAULT_FPS)
    run.add_argument("--config", type=Path, help="YAML provider configuration (enables the v0.2 pipeline)")
    subparsers.add_parser("providers", help="list available provider implementations")
    plan = subparsers.add_parser("plan", help="print a provider plan without calling providers")
    plan.add_argument("script", type=Path)
    plan.add_argument("--config", type=Path)
    qa = subparsers.add_parser("qa", help="validate an existing build directory")
    qa.add_argument("build_directory", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "providers":
        print("media:\n  placeholder\n  comfyui\ntts:\n  mock\n  command")
        return 0
    if args.command == "qa":
        report = qa_build(args.build_directory)
        print(json.dumps(report, indent=2))
        return 1 if report["status"] == "FAIL" else 0
    if args.command == "plan":
        try:
            project = parse_script_file(args.script)
            config = load_config(args.config) if args.config else {}
            print(json.dumps(plan_project(project, config), indent=2))
            return 0
        except (FileNotFoundError, ScriptParseError, ConfigError, ValueError, OSError) as exc:
            print(f"autovideo: error: {exc}", file=sys.stderr)
            return 2
    if args.command == "run":
        output = args.output or Path("build") / args.script.stem
        try:
            project = parse_script_file(args.script)
            if args.config:
                config = load_config(args.config)
                render_config = config.setdefault("render", {})
                if isinstance(render_config, dict):
                    render_config.setdefault("width", args.width)
                    render_config.setdefault("height", args.height)
                    render_config.setdefault("fps", args.fps)
                report = build_with_providers(project, config, output, config_dir=args.config.resolve().parent)
            else:
                report = render_project(project, output, width=args.width, height=args.height, fps=args.fps)
        except (FileNotFoundError, ScriptParseError, ConfigError, ProviderError, RenderError, ValueError, OSError) as exc:
            print(f"autovideo: error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(report, indent=2))
        if report["status"] in {"degraded", "WARNING"}:
            print(f"autovideo: warning: {report.get('warning') or report.get('warnings')}", file=sys.stderr)
        return 0
    return 2
