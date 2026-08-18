# ComfyUI API workflows

AutoVideo-Agent accepts ComfyUI **API Format** JSON. It does not ship a model-specific production workflow.

1. Build and test your workflow in ComfyUI.
2. Enable developer mode in ComfyUI settings.
3. Choose **Save (API Format)** from the workflow menu.
4. Store the exported JSON outside Git if it contains private paths, model names, credentials, or proprietary prompts.
5. Point `providers.media.workflow` at that file and map the relevant node IDs in `node_mapping`.

Supported mapping keys are `prompt_node`, `prompt_input`, `negative_prompt_node`, `negative_prompt_input`, `seed_node`, `seed_input`, `seed`, and `negative_prompt`. Image and video outputs are normalized into the same media artifact contract. The provider reads standard ComfyUI `images`, `gifs`, `videos`, and `audio` output lists and downloads the first media result through `/view`.

`example-api.json` is a structural example only. Its node types are illustrative and it is not guaranteed to run on a ComfyUI installation without the matching nodes and models. Never commit private workflows or local model paths.
