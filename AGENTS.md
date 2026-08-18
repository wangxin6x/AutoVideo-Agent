# AGENTS.md

## Project rules

- Keep the default pipeline local and deterministic.
- Never commit API keys, tokens, passwords, cookies, or machine-specific paths.
- Keep CLI behavior backwards compatible within a minor release.
- Add or update tests for every core behavior change.
- Keep providers limited to normalized MediaArtifact/AudioArtifact outputs; the renderer owns final composition.
- Never commit private ComfyUI workflows, model files, endpoints, or generated build directories.
- Run `python -m pytest`, `autovideo run examples/demo-script.md`, and `autovideo qa <build-directory>` before a release.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m pytest
autovideo run examples/demo-script.md
autovideo run examples/demo-script.md --config examples/config-offline.yaml
autovideo qa build/demo-script
```
