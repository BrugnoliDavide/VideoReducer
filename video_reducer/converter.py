import json
import os
import platform
import subprocess
import time
from pathlib import Path

from . import state as st_mod

_low_priority = False


def set_low_priority(enabled):
    global _low_priority
    _low_priority = enabled


def _get_popen_kwargs():
    kwargs = {}
    if not _low_priority:
        return kwargs
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.IDLE_PRIORITY_CLASS
    else:
        kwargs["preexec_fn"] = lambda: os.nice(19)
    return kwargs

PRESETS = {
    "lossy": {
        "description": "H.265 lossy (CRF 23, buona qualità, massima riduzione)",
        "vcodec": "libx265",
        "vparams": ["-crf", "23", "-preset", "medium"],
        "acodec": "aac",
        "aparams": ["-b:a", "128k"],
        "container": ".mp4",
    },
    "lossy_light": {
        "description": "H.265 lossy leggero (CRF 18, qualità quasi identica)",
        "vcodec": "libx265",
        "vparams": ["-crf", "18", "-preset", "slow"],
        "acodec": "copy",
        "aparams": [],
        "container": ".mp4",
    },
    "lossless": {
        "description": "H.265 lossless (zero perdita, riduzione moderata)",
        "vcodec": "libx265",
        "vparams": ["-x265-params", "lossless=1"],
        "acodec": "flac",
        "aparams": [],
        "container": ".mkv",
    },
    "av1_lossy": {
        "description": "AV1 lossy (CRF 30, ottima compressione, lento)",
        "vcodec": "libsvtav1",
        "vparams": ["-crf", "30", "-preset", "6"],
        "acodec": "opus",
        "aparams": ["-b:a", "128k"],
        "container": ".mkv",
    },
    "av1_lossless": {
        "description": "AV1 lossless (zero perdita)",
        "vcodec": "libsvtav1",
        "vparams": ["-crf", "0"],
        "acodec": "flac",
        "aparams": [],
        "container": ".mkv",
    },
}


def output_path_for(original, preset_name):
    p = Path(original)
    preset = PRESETS[preset_name]
    suffix = preset["container"]
    new_name = f"{p.stem}_reduced{suffix}"
    return p.parent / new_name


def convert_file(filepath, preset_name, progress_cb=None):
    preset = PRESETS[preset_name]
    out = output_path_for(filepath, preset_name)

    if out.exists():
        out = out.parent / f"{out.stem}_{int(time.time())}{out.suffix}"

    cmd = [
        "ffmpeg", "-y", "-i", str(filepath),
        "-c:v", preset["vcodec"],
    ] + preset["vparams"] + [
        "-c:a", preset["acodec"],
    ] + preset["aparams"] + [
        "-movflags", "+faststart" if preset["container"] == ".mp4" else "",
        str(out),
    ]
    cmd = [c for c in cmd if c]

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **_get_popen_kwargs(),
        )
        _, stderr = proc.communicate()
        if proc.returncode != 0:
            return None, stderr.decode(errors="replace")
        return str(out), None
    except FileNotFoundError:
        return None, "ffmpeg non trovato. Installare ffmpeg e assicurarsi che sia nel PATH."


def verify_integrity(original, converted):
    orig_info = _probe_duration(original)
    conv_info = _probe_duration(converted)

    if orig_info is None or conv_info is None:
        return False, "Impossibile leggere i metadati"

    orig_dur = orig_info
    conv_dur = conv_info

    if orig_dur > 0:
        diff = abs(orig_dur - conv_dur)
        tolerance = max(1.0, orig_dur * 0.01)
        if diff > tolerance:
            return False, f"Durata diversa: originale={orig_dur:.1f}s, convertito={conv_dur:.1f}s"

    if not Path(converted).exists() or Path(converted).stat().st_size == 0:
        return False, "File convertito vuoto o mancante"

    return True, "OK"


def _probe_duration(filepath):
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", str(filepath),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


def process_files(state, file_keys, preset_name, delete_originals=False, progress_cb=None):
    total = len(file_keys)
    for i, fpath in enumerate(file_keys):
        entry = state["files"].get(fpath)
        if not entry:
            continue
        if entry["status"] == "converted":
            if progress_cb:
                progress_cb(i + 1, total, fpath, "già convertito")
            continue
        if not Path(fpath).exists():
            entry["status"] = "missing"
            st_mod.save_state(state)
            if progress_cb:
                progress_cb(i + 1, total, fpath, "file mancante")
            continue

        entry["status"] = "converting"
        st_mod.save_state(state)

        if progress_cb:
            progress_cb(i + 1, total, fpath, "conversione in corso...")

        out, err = convert_file(fpath, preset_name)
        if out is None:
            entry["status"] = "error"
            entry["error"] = err
            st_mod.save_state(state)
            if progress_cb:
                progress_cb(i + 1, total, fpath, f"ERRORE: {err[:80]}")
            continue

        ok, msg = verify_integrity(fpath, out)
        if not ok:
            entry["status"] = "error"
            entry["error"] = f"Verifica fallita: {msg}"
            try:
                os.remove(out)
            except OSError:
                pass
            st_mod.save_state(state)
            if progress_cb:
                progress_cb(i + 1, total, fpath, f"ERRORE integrità: {msg}")
            continue

        conv_size = Path(out).stat().st_size
        entry["status"] = "converted"
        entry["converted_path"] = str(out)
        entry["converted_size"] = conv_size
        entry["conversion_date"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        entry.pop("error", None)

        if delete_originals:
            try:
                os.remove(fpath)
                entry["original_deleted"] = True
            except OSError as e:
                entry["error"] = f"Conversione OK ma eliminazione fallita: {e}"

        st_mod.recalc_stats(state)
        st_mod.save_state(state)

        saved = entry["original_size"] - conv_size
        pct = (saved / entry["original_size"] * 100) if entry["original_size"] > 0 else 0
        if progress_cb:
            progress_cb(i + 1, total, fpath, f"OK (-{format_size(saved)}, -{pct:.1f}%)")


def delete_originals(state, file_keys=None):
    if file_keys is None:
        file_keys = list(state["files"].keys())

    deleted = 0
    errors = []
    not_converted = []

    for fpath in file_keys:
        entry = state["files"].get(fpath)
        if not entry:
            continue
        if entry["original_deleted"]:
            continue
        if entry["status"] != "converted":
            not_converted.append(fpath)
            continue

        conv_path = entry.get("converted_path")
        if not conv_path or not Path(conv_path).exists():
            errors.append((fpath, "File convertito non trovato"))
            continue

        ok, msg = verify_integrity(fpath, conv_path)
        if not ok:
            errors.append((fpath, f"Verifica fallita: {msg}"))
            continue

        try:
            os.remove(fpath)
            entry["original_deleted"] = True
            deleted += 1
        except OSError as e:
            errors.append((fpath, str(e)))

    st_mod.recalc_stats(state)
    st_mod.save_state(state)
    return deleted, errors, not_converted


def format_size(size_bytes):
    if size_bytes < 0:
        return f"-{format_size(-size_bytes)}"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"
