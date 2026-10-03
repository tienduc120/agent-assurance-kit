# Working rules

- This repo is public. Never commit secrets, target access keys, real personal data, or details
  of a finding before it is fixed.
- Synthetic test data only.
- Never run anything against Gemini or any paid model API, and never run the `pikapi`
  engagement live. The owner runs live tests themselves, with a separate key and model.
  Develop against the mock, scripted and fake-server targets and free local models (Ollama).
- Keep adapters decoupled from any one app, key or model: everything app-specific comes from
  target.yaml and its gitignored *.local.yaml files.
- Only test systems the owner controls or has written permission to test.
- Commit and push only when the owner asks.
- The roadmap and decision log are kept locally and not pushed: `.idea/ROADMAP.md`,
  `.idea/DECISIONS.md`. Read them before planning work, and log new decisions there.
- Keep the kit/target boundary: no target code is imported here. A target is reached only through
  an adapter and its `target.yaml`.
- Comments: short, and only the non-obvious why.
- Check before handing work back: `uv run ruff check && uv run ruff format --check && uv run pytest`
