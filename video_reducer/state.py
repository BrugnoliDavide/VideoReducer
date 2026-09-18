import json
import os
import time
from pathlib import Path


STATE_FILENAME = ".video_reducer_state.json"


def default_state(scan_root):
    return {
        "version": "1.0",
        "scan_root": str(scan_root),
        "scan_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "files": {},
        "stats": {
            "total_original_size": 0,
            "total_converted_size": 0,
            "space_saved": 0,
        },
    }


def default_file_entry(path, size, codec, duration, resolution, bitrate, categories):
    return {
        "original_size": size,
        "codec": codec,
        "duration": duration,
        "resolution": resolution,
        "bitrate": bitrate,
        "categories": categories,
        "status": "pending",
        "converted_path": None,
        "converted_size": None,
        "conversion_date": None,
        "original_deleted": False,
    }


def state_path(scan_root):
    return Path(scan_root) / STATE_FILENAME


def load_state(scan_root):
    p = state_path(scan_root)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(st):
    p = state_path(st["scan_root"])
    tmp = p.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2, ensure_ascii=False)
    tmp.replace(p)


def recalc_stats(st):
    total_orig = 0
    total_conv = 0
    for entry in st["files"].values():
        total_orig += entry["original_size"]
        if entry["status"] == "converted" and entry["converted_size"] is not None:
            total_conv += entry["converted_size"]
    st["stats"]["total_original_size"] = total_orig
    converted_orig = sum(
        e["original_size"]
        for e in st["files"].values()
        if e["status"] == "converted" and e["converted_size"] is not None
    )
    st["stats"]["total_converted_size"] = total_conv
    st["stats"]["space_saved"] = converted_orig - total_conv
