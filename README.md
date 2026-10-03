# Agent Assurance Kit

A reusable kit for testing AI chat and voice agents from the outside: evaluation, red teaming,
and the evidence an audit or security review asks for.

> **Status:** early development (October 2026).

## Design

- **Black box first.** The kit reaches a target only through an adapter (HTTP chat,
  OpenAI-compatible API, Gemini Live WebSocket, browser voice) and a `target.yaml`. It never
  imports the target's code, so the same kit works on any product.
- **Test packs switch on by capability.** Each pack declares what a target must have
  (actions, user data, roles, voice, web search...). Each target declares what it has. Packs
  that can't apply are reported as *not applicable*, with the reason, never silently skipped.
- **Measured, not asserted.** Rule-based checks first. LLM judges are calibrated against human
  labels. Cases run several times to measure reliability (pass^k).
- **Built on open tools:** [Inspect AI](https://inspect.aisi.org.uk),
  [garak](https://github.com/NVIDIA/garak), [PyRIT](https://github.com/Azure/PyRIT).
  Findings map to the OWASP Top 10 for LLM and Agentic Applications and to MITRE ATLAS.

## Engagements

| Target | What it is | Status |
|---|---|---|
| `pikapi` | The author's children's voice chat app (Gemini Live), private code | Scoping |

Results are published only after any findings are fixed.

## Quick start

```sh
uv sync
uv run pytest
```

## Rules of use

Only test systems you own or have written permission to test. Use synthetic data only.

## License

[MIT](LICENSE)
