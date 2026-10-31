#!/usr/bin/env python3
"""
Generates dark_mode.svg and light_mode.svg for the GitHub profile.

    python3 generate.py                        # public stats only
    GITHUB_TOKEN=ghp_xxx python3 generate.py   # full stats + LOC

Edit config.py to personalise the output.
The ASCII art in ascii.txt was generated with art/img2ascii.py from art/user-secret.svg.
"""
from pathlib import Path

from config import USER, HOST, BIRTHDAY, WIDTH, INFO, CONTACT, GITHUB_STATS, THEMES
from github import TOKEN, fetch_stats
from render import build_info, render

ROOT      = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def main():
    """Fetches GitHub stats and writes both SVG themes to the art/ directory."""
    if TOKEN:
        print("Token found. Fetching full stats + LOC.")
    else:
        print("No GITHUB_TOKEN — public stats only, LOC unavailable.")

    art_file = ROOT / "art" / "ascii.txt"
    art  = art_file.read_text(encoding="utf-8").rstrip("\n").split("\n") if art_file.exists() else []
    stats = fetch_stats(USER, CACHE_DIR)
    info  = build_info(USER, HOST, BIRTHDAY, WIDTH, INFO, CONTACT, GITHUB_STATS, stats)

    for name, theme in THEMES.items():
        (ROOT / "art" / name).write_text(render(theme, art, info, WIDTH), encoding="utf-8")

    print("done.")


if __name__ == "__main__":
    main()
