import json
import os
import subprocess
from pathlib import Path

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".3gp", ".ts", ".mts", ".m2ts", ".vob", ".ogv",
    ".rm", ".rmvb", ".asf", ".divx", ".f4v",
}

HEAVY_CODECS = {
    "mjpeg", "rawvideo", "prores", "dnxhd", "dnxhr", "huffyuv",
    "ffvhuff", "utvideo", "v210", "v410", "r210", "dpx",
    "png", "tiff", "bmp", "gif", "qtrle", "msmpeg4v3",
    "msvideo1", "cinepak", "indeo3", "indeo5",
    "mpeg1video", "mpeg2video", "vc1", "wmv1", "wmv2", "wmv3",
    "theora", "svq1", "svq3", "rv10", "rv20", "rv30", "rv40",
}

EFFICIENT_CODECS = {"hevc", "h265", "av1", "vp9"}


def probe_file(filepath):
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(filepath),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


def extract_video_info(probe_data):
    video_stream = None
    for s in probe_data.get("streams", []):
        if s.get("codec_type") == "video":
            video_stream = s
            break
    if not video_stream:
        return None

    codec = video_stream.get("codec_name", "unknown").lower()
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    resolution = f"{width}x{height}" if width and height else "unknown"

    fmt = probe_data.get("format", {})
    duration = float(fmt.get("duration", 0))
    bitrate = int(fmt.get("bit_rate", 0))
    size = int(fmt.get("size", 0))

    return {
        "codec": codec,
        "resolution": resolution,
        "duration": duration,
        "bitrate": bitrate,
        "size": size,
    }


def categorize(info, size_threshold_mb=500):
    cats = []
    if info["codec"] in HEAVY_CODECS:
        cats.append("heavy_codec")
    if info["codec"] not in EFFICIENT_CODECS:
        cats.append("not_efficient")
    if info["size"] > size_threshold_mb * 1024 * 1024:
        cats.append("large_file")
    if info["bitrate"] > 0 and info["duration"] > 0:
        expected_bitrate = _expected_bitrate(info["resolution"])
        if expected_bitrate and info["bitrate"] > expected_bitrate * 3:
            cats.append("high_bitrate")
    return cats


def _expected_bitrate(resolution):
    try:
        w, h = map(int, resolution.split("x"))
        pixels = w * h
    except (ValueError, AttributeError):
        return None
    if pixels >= 3840 * 2160:
        return 15_000_000
    if pixels >= 1920 * 1080:
        return 5_000_000
    if pixels >= 1280 * 720:
        return 2_500_000
    return 1_000_000


def scan_folder(root, size_threshold_mb=500, recursive=True):
    root = Path(root)
    results = {}
    pattern = root.rglob("*") if recursive else root.glob("*")

    for p in pattern:
        if not p.is_file():
            continue
        if p.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if ".video_reducer" in str(p):
            continue

        probe_data = probe_file(p)
        if not probe_data:
            continue

        info = extract_video_info(probe_data)
        if not info:
            continue

        cats = categorize(info, size_threshold_mb)
        results[str(p)] = {
            "size": info["size"] or p.stat().st_size,
            "codec": info["codec"],
            "duration": info["duration"],
            "resolution": info["resolution"],
            "bitrate": info["bitrate"],
            "categories": cats,
        }

    return results
