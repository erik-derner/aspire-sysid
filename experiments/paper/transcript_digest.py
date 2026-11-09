"""Prints a condensed text of the transcript of a run, for the assessment of a model record.

Plain code, no language model. One block per event of ``transcript.jsonl``, headed by the line
number of the event in the transcript (``L<line>``), which is the reference used in the
assessment files. A response is shown with the text of the agent and the reasoning summaries; a
tool call with its tool and arguments; a tool result with its content; a web search executed by
the vendor with its queries and sources. Long texts are shortened
to ``--chars`` characters (default 1500), with the number of characters left out.

    .venv/Scripts/python.exe experiments/paper/transcript_digest.py experiments/<id>/runs/r01 [--chars N]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def short(text: str, limit: int) -> str:
    text = str(text)
    if len(text) <= limit:
        return text
    head = limit * 2 // 3
    return f"{text[:head]}\n[... {len(text) - limit} characters left out ...]\n{text[-(limit - head):]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--chars", type=int, default=1500)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    path = pathlib.Path(args.run_dir) / "transcript.jsonl"
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            ev = json.loads(line)
            kind, agent, n = ev.get("kind"), ev.get("agent"), ev.get("line")
            if kind in ("transcript_start", "request"):
                continue
            head = f"\n=== L{n} {kind} [{agent}] t={ev.get('elapsed_s', 0):.0f}s"
            if kind == "round_start":
                print(head, "(system prompt, tools and environment not repeated here)")
            elif kind == "user_message":
                print(head)
                print(short(ev.get("text", ""), args.chars))
            elif kind == "response":
                print(head, f"stop={ev.get('stop_reason')} done={ev.get('done')}")
                for summary in ev.get("reasoning") or []:
                    print("[reasoning summary]", short(summary, args.chars))
                for search in ev.get("web_searches") or []:
                    queries = search.get("queries") or [search.get("query")]
                    print(f"[web search by the vendor, {search.get('action')}] queries: {queries}; "
                          f"sources: {short(search.get('sources') or search.get('url') or '', 600)}")
                if ev.get("text"):
                    print("[text]", short(ev["text"], args.chars))
            elif kind == "tool_call":
                arguments = ev.get("arguments") or {}
                print(head, ev.get("tool"))
                for key, value in arguments.items():
                    print(f"[{key}]", short(value, args.chars))
            elif kind == "tool_result":
                print(head, ev.get("tool"), "error" if ev.get("is_error") else "")
                print(short(ev.get("content", ""), args.chars))
            elif kind == "helper_start":
                print(head)
                print("[task of the helper]", short(ev.get("task_text", ""), args.chars))
            else:
                rest = {k: v for k, v in ev.items() if k not in ("schema_version", "task", "session", "round", "pool_version",
                                                                  "candidate", "timestamp", "recorded_at", "kind", "agent", "line", "seq")}
                print(head)
                print(short(json.dumps(rest, ensure_ascii=False), args.chars))


if __name__ == "__main__":
    main()
