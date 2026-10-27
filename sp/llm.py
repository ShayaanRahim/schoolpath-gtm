"""
llm calls. two backends:
- anthropic: calls the messages api with ANTHROPIC_API_KEY.
- file: no api key needed. writes each prompt to shadow/pending_prompts/ and reads answers from
  shadow/llm_responses.jsonl (keyed by prompt hash). lets anyone run the pipeline by pasting prompts
  into a chat model. this is how the submitted shadow run was produced.
"""
import json
import os
import re

import requests

from .common import ROOT, short_hash

BACKEND = os.environ.get("LLM_BACKEND", "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "file")
RESP_FILE = ROOT / "shadow" / "llm_responses.jsonl"
PENDING = ROOT / "shadow" / "pending_prompts"


def _parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else None


def _file_backend(prompt_text):
    key = short_hash(prompt_text, 16)
    if RESP_FILE.exists():
        for line in RESP_FILE.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                if rec["key"] == key:
                    return rec["response"]
    PENDING.mkdir(parents=True, exist_ok=True)
    (PENDING / f"{key}.md").write_text(prompt_text)
    return None


def _anthropic(prompt_text, model):
    r = requests.post(
        os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com") + "/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": model, "max_tokens": 700, "messages": [{"role": "user", "content": prompt_text}]},
        timeout=60,
    )
    r.raise_for_status()
    return _parse_json(r.json()["content"][0]["text"])


def ask(prompt_text, model):
    """
    sends one prompt and returns the parsed json answer, or None if the file backend is still waiting.
    input: the filled prompt and a model name. returns a dict or None.
    """
    if BACKEND == "file":
        return _file_backend(prompt_text)
    return _anthropic(prompt_text, model)


def record(key, response):
    # used when answering pending prompts by hand
    RESP_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RESP_FILE.open("a") as f:
        f.write(json.dumps({"key": key, "response": response}) + "\n")
