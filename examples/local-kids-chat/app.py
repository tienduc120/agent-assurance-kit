"""A tiny children's chat app in front of a local model: the stand-in's "production" side.

The app owns its system prompt and its guardrails; the kit tests it from outside through the
OpenAI-compatible API it exposes, like any other target. Not part of the kit.

    uv run python examples/local-kids-chat/app.py --prompt system_prompt_hardened.md --leak-guard
"""

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

HERE = Path(__file__).parent
REFUSAL = "Sorry, I can't share that. Let's talk about something fun instead!"


def leaks(reply: str, prompt: str, n: int = 6) -> bool:
    """True if the reply repeats any run of n consecutive words from the prompt."""
    words = re.findall(r"\w+", prompt.lower())
    said = " " + " ".join(re.findall(r"\w+", reply.lower())) + " "
    return any(f" {' '.join(words[i : i + n])} " in said for i in range(len(words) - n + 1))


def make_handler(prompt: str, model: str, upstream: str, leak_guard: bool):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            # The app owns the system prompt; a client can't supply its own.
            history = [m for m in body.get("messages", []) if m.get("role") != "system"]
            request = {
                "model": model,
                "messages": [{"role": "system", "content": prompt}, *history],
                "temperature": body.get("temperature", 0.7),
                "reasoning_effort": "none",
            }
            response = httpx.post(f"{upstream}/chat/completions", json=request, timeout=300)
            data = response.json()
            message = data["choices"][0]["message"]
            if leak_guard and leaks(message.get("content") or "", prompt):
                message["content"] = REFUSAL
            payload = json.dumps(data).encode()
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args) -> None:
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="system_prompt.md", help="file next to this script")
    parser.add_argument("--leak-guard", action="store_true", help="block replies that leak it")
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--upstream", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    prompt = (HERE / args.prompt).read_text(encoding="utf-8")
    handler = make_handler(prompt, args.model, args.upstream, args.leak_guard)
    print(f"app on http://127.0.0.1:{args.port}/v1 (prompt={args.prompt}, guard={args.leak_guard})")
    ThreadingHTTPServer(("127.0.0.1", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
