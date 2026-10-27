"""
shared helpers: config loading, the shadow/live switch, prompt filling, and csv io.
"""
import csv
import hashlib
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_env(path=ROOT / ".env"):
    # tiny .env reader so we don't need another dependency
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
CONFIG = yaml.safe_load((ROOT / "config.yaml").read_text())

# the single switch. shadow = write to local csv, nothing reaches the ops sheet or redirect table.
MODE = os.environ.get("MODE", "shadow").lower()
assert MODE in ("shadow", "live"), "MODE must be shadow or live"


def is_live():
    return MODE == "live"


def fill(template: str, **values) -> str:
    """
    fills {key} placeholders without touching other braces (the prompts contain json examples).
    input: template text and the values to insert. returns the filled text.
    """
    for k, v in values.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def prompt(name: str) -> str:
    return (ROOT / "prompts" / f"{name}.md").read_text()


def short_hash(text: str, n=10) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
