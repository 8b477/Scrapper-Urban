"""
merge_events.py
---------------
Combines JSON event files from two scrapers (quefaire.be and site de la ville)
for the same city and date, then removes duplicates.

Usage:
  python merge_events.py                        # process all matching city/date pairs
  python merge_events.py --city charleroi       # one city only
  python merge_events.py --city charleroi --date 08-04-26  # one city + one date

Output files are written to:  combined/<City>/<city>_combined_<date>.json
"""

import json
import os
import re
import unicodedata
import argparse
from pathlib import Path
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
DIR_QUEFAIRE   = ROOT / "quefaire.be"
DIR_VILLE      = ROOT / "site de la ville"
DIR_OUTPUT     = ROOT / "combined"

# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """Lowercase, strip accents, keep only alphanum + spaces."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def city_slug(name: str) -> str:
    """Produce a comparable slug from a city name or folder name."""
    return normalize(name).replace(" ", "")


def extract_date_from_filename(filename: str) -> str | None:
    """
    Extract the date part from filenames like:
      charleroi-08-04-26.json  →  08-04-26
      charleroi_08-04-26.json  →  08-04-26
    """
    m = re.search(r"(\d{2}-\d{2}-\d{2})", filename)
    return m.group(1) if m else None


def list_json_files(root_dir: Path) -> list[Path]:
    """Recursively list all .json files under root_dir."""
    return list(root_dir.rglob("*.json"))


def dedup_key(event: dict) -> str:
    """
    Unique key used to detect duplicate events across sources.
    Based on normalised title + start date (day only).
    """
    title = normalize(event.get("title", ""))
    start = event.get("dates", {}).get("start", "")
    # keep only the date part (DD-MM-YYYY)
    day = start[:10] if start else ""
    return f"{title}|{day}"


# ── Core logic ────────────────────────────────────────────────────────────────

def build_index(files: list[Path]) -> dict[tuple[str, str], Path]:
    """
    Build a dict: (city_slug, date) → Path
    from a list of JSON file paths.
    """
    index: dict[tuple[str, str], Path] = {}
    for f in files:
        date = extract_date_from_filename(f.name)
        if date is None:
            continue
        # city is the parent folder name
        city = city_slug(f.parent.name)
        index[(city, date)] = f
    return index


def load_events(path: Path) -> tuple[dict, list[dict]]:
    """Return (metadata_dict, events_list) from a JSON file."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("metadata", {}), data.get("events", [])


def merge_and_dedup(
    path_a: Path,
    path_b: Path,
) -> dict:
    """
    Load both files, merge their events, remove duplicates,
    and return a new combined dict.
    """
    meta_a, events_a = load_events(path_a)
    meta_b, events_b = load_events(path_b)

    seen: set[str] = set()
    merged: list[dict] = []

    for event in events_a + events_b:
        key = dedup_key(event)
        if key not in seen:
            seen.add(key)
            merged.append(event)

    combined_meta = {
        "region": meta_a.get("region") or meta_b.get("region", ""),
        "sources": [
            meta_a.get("source", str(path_a)),
            meta_b.get("source", str(path_b)),
        ],
        "merge_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_events_before_dedup": len(events_a) + len(events_b),
        "duplicates_removed": (len(events_a) + len(events_b)) - len(merged),
        "total_events": len(merged),
    }

    return {
        "metadata": combined_meta,
        "events": merged,
    }


def save(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"  -> saved {output_path}  ({data['metadata']['total_events']} events, "
          f"{data['metadata']['duplicates_removed']} duplicates removed)")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Merge quefaire.be + site de la ville events")
    parser.add_argument("--city", default=None,
                        help="Filter by city slug, e.g. 'charleroi' or 'lalouviere'")
    parser.add_argument("--date", default=None,
                        help="Filter by date string, e.g. '08-04-26'")
    args = parser.parse_args()

    quefaire_index = build_index(list_json_files(DIR_QUEFAIRE))
    ville_index    = build_index(list_json_files(DIR_VILLE))

    # Keys present in BOTH sources
    common_keys = set(quefaire_index) & set(ville_index)

    if not common_keys:
        print("No matching city/date pairs found between the two sources.")
        return

    # Apply optional filters
    if args.city:
        slug = city_slug(args.city)
        common_keys = {k for k in common_keys if k[0] == slug}
    if args.date:
        common_keys = {k for k in common_keys if k[1] == args.date}

    if not common_keys:
        print("No matching pairs after applying filters.")
        return

    print(f"Found {len(common_keys)} city/date pair(s) to process.\n")

    for city_key, date in sorted(common_keys):
        path_q = quefaire_index[(city_key, date)]
        path_v = ville_index[(city_key, date)]

        # Use the parent folder of the quefaire file as the display city name
        display_city = path_q.parent.name.replace("_", " ")

        print(f"[{display_city}  |  {date}]")
        print(f"  quefaire : {path_q.relative_to(ROOT)}")
        print(f"  ville    : {path_v.relative_to(ROOT)}")

        combined = merge_and_dedup(path_q, path_v)

        out_filename = f"{city_key}_combined_{date}.json"
        out_path = DIR_OUTPUT / display_city / out_filename
        save(combined, out_path)
        print()


if __name__ == "__main__":
    main()
