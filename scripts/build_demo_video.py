#!/usr/bin/env python3
"""Build a silent 4-section demo MP4 from *real* GitHub Pages HTML.

Starts a local server on ``html/``, drives Chromium with Playwright (scroll +
dwell on product pages), then stitches title cards + page clips with ffmpeg.

Sections:
  1. Security / vulnerability scan — guide/security.html, examples assertions
  2. Load testing — guide/performance.html
  3. Resilience — guide/resiliency.html, guide/chaos.html
  4. CI/CD dashboard — sample HTML report, home Watch section, integrations

Requires: Pillow, ffmpeg, playwright + Chromium.
"""
from __future__ import annotations

import http.server
import shutil
import socketserver
import subprocess
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "html"
OUT_DIR = ROOT / "html" / "assets" / "video"
OUT_MP4 = OUT_DIR / "mcp-test-harness-4-section-demo.mp4"
W, H = 1920, 1080
FPS = 30

THEME = {
    "intro": ((15, 23, 42), (99, 102, 241)),
    "sec1": ((30, 15, 25), (244, 63, 94)),
    "sec2": ((15, 30, 28), (16, 185, 129)),
    "sec3": ((20, 25, 40), (59, 130, 246)),
    "sec4": ((15, 23, 42), (168, 85, 247)),
    "outro": ((15, 23, 42), (16, 185, 129)),
}


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        p = Path(name)
        if p.is_file():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def title_slide(path: Path, kicker: str, title: str, bullets: list[str], theme: str) -> None:
    bg, accent = THEME[theme]
    im = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, 0, 18, H], fill=accent)
    draw.text((72, 64), "MCP Test Harness  ·  v5.2.0", fill=(148, 163, 184), font=_font(36))
    draw.text((72, 140), kicker.upper(), fill=accent, font=_font(42))
    draw.text((72, 220), title, fill=(248, 250, 252), font=_font(72))
    y = 360
    for b in bullets:
        draw.ellipse([78, y + 18, 98, y + 38], fill=accent)
        draw.text((120, y), b, fill=(203, 213, 225), font=_font(40))
        y += 78
    draw.text(
        (72, H - 90),
        "Real product pages  ·  Deterministic CI gate  ·  MIT",
        fill=(100, 116, 139),
        font=_font(28),
    )
    im.save(path, "PNG")


def png_to_clip(png: Path, mp4: Path, seconds: float) -> None:
    frames = max(1, int(seconds * FPS))
    subprocess.run(
        [
            "ffmpeg", "-y", "-loop", "1", "-i", str(png),
            "-c:v", "libx264", "-t", str(seconds), "-pix_fmt", "yuv420p",
            "-r", str(FPS),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
            "-frames:v", str(frames), str(mp4),
        ],
        check=True,
        capture_output=True,
    )


def normalize_clip(src: Path, dst: Path) -> None:
    """Re-encode Playwright webm/mp4 to H.264 1920x1080 @ FPS."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(src),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-an", str(dst),
        ],
        check=True,
        capture_output=True,
    )


def concat(clips: list[Path], out: Path) -> None:
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-crf", "23", "-preset", "medium", str(out),
        ],
        check=True,
        capture_output=True,
    )
    listing.unlink(missing_ok=True)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HTML), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def start_server() -> tuple[socketserver.TCPServer, int]:
    httpd = socketserver.TCPServer(("127.0.0.1", 0), _QuietHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, port


def _scroll_tour(page, steps: int = 6, dy: int = 420, pause_ms: int = 450) -> None:
    page.wait_for_timeout(700)
    for _ in range(steps):
        page.mouse.wheel(0, dy)
        page.wait_for_timeout(pause_ms)
    page.wait_for_timeout(600)


def record_pages(base: str, video_dir: Path) -> dict[str, Path]:
    """Return map of clip key -> recorded video path (Playwright webm)."""
    video_dir.mkdir(parents=True, exist_ok=True)
    tours = {
        "sec1": [
            ("guide/security.html", 5),
            ("examples.html", 4),
        ],
        "sec2": [
            ("guide/performance.html", 7),
        ],
        "sec3": [
            ("guide/resiliency.html", 5),
            ("guide/chaos.html", 4),
        ],
        "sec4": [
            ("reports/sample_mcp_test_report.html", 7),
            ("index.html#demo-video", 3),
            ("integrations.html", 4),
        ],
    }
    out: dict[str, Path] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for key, stops in tours.items():
            context = browser.new_context(
                viewport={"width": W, "height": H},
                device_scale_factor=1,
                record_video_dir=str(video_dir / key),
                record_video_size={"width": W, "height": H},
            )
            page = context.new_page()
            for rel, scroll_steps in stops:
                url = f"{base}/{rel}"
                print(f"  navigate {rel}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(900)
                # Hide live badge noise that can flash empty
                page.add_style_tag(
                    content="#pypi-stats-bar{opacity:.85} .pypi-stat-live{visibility:hidden}"
                )
                _scroll_tour(page, steps=scroll_steps)
            context.close()
            # Playwright writes one webm per page; after context close, pick largest
            clips = sorted((video_dir / key).glob("*.webm"), key=lambda x: x.stat().st_size, reverse=True)
            if not clips:
                raise RuntimeError(f"No video recorded for {key}")
            out[key] = clips[0]
            print(f"  recorded {key}: {out[key].name} ({out[key].stat().st_size // 1024} KiB)")
        browser.close()
    return out


def main() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg not found on PATH")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    print(f"Serving {HTML} at {base}")

    with tempfile.TemporaryDirectory(prefix="mth-demo-pages-") as tmp:
        td = Path(tmp)
        try:
            print("Recording real product pages…")
            page_clips = record_pages(base, td / "raw")
        finally:
            httpd.shutdown()

        clips: list[Path] = []

        def add_title(name: str, seconds: float, **kw: object) -> None:
            png = td / f"{name}.png"
            title_slide(png, **kw)  # type: ignore[arg-type]
            mp4 = td / f"{name}.mp4"
            png_to_clip(png, mp4, seconds)
            clips.append(mp4)

        add_title(
            "00_intro",
            4.0,
            kicker="Product demo · real pages",
            title="Four CI gates for MCP",
            bullets=[
                "1  Security scan — docs + examples",
                "2  Load testing — performance guide",
                "3  Resilience — resiliency + chaos",
                "4  CI/CD dashboard — HTML report",
            ],
            theme="intro",
        )

        add_title(
            "01_title",
            3.2,
            kicker="Section 1 of 4",
            title="Security / vulnerability scan",
            bullets=[
                "guide/security.html — Suites A–D · audit verify",
                "examples.html — assertion table",
                "mcp-test scan-agents · SARIF quality_gate",
            ],
            theme="sec1",
        )
        norm = td / "sec1.mp4"
        normalize_clip(page_clips["sec1"], norm)
        clips.append(norm)

        add_title(
            "02_title",
            3.2,
            kicker="Section 2 of 4",
            title="Load testing",
            bullets=[
                "guide/performance.html",
                "assert_latency · throughput · load_phases",
                "SLO gates on every PR",
            ],
            theme="sec2",
        )
        norm = td / "sec2.mp4"
        normalize_clip(page_clips["sec2"], norm)
        clips.append(norm)

        add_title(
            "03_title",
            3.2,
            kicker="Section 3 of 4",
            title="Resilience testing",
            bullets=[
                "guide/resiliency.html · guide/chaos.html",
                "Chaos faults · degrade · reconnect",
                "Load resilience — no-fail-open",
            ],
            theme="sec3",
        )
        norm = td / "sec3.mp4"
        normalize_clip(page_clips["sec3"], norm)
        clips.append(norm)

        add_title(
            "04_title",
            3.2,
            kicker="Section 4 of 4",
            title="Security → CI/CD dashboard",
            bullets=[
                "Sample HTML report dashboard",
                "Home Watch section · Integrations",
                "JUnit · SARIF · GitHub Action",
            ],
            theme="sec4",
        )
        norm = td / "sec4.mp4"
        normalize_clip(page_clips["sec4"], norm)
        clips.append(norm)

        add_title(
            "99_outro",
            4.0,
            kicker="Get started",
            title="pip install · mcp-test · gate",
            bullets=[
                "pip install mcp-test-harness==5.2.0",
                "vaquarkhan.github.io/mcp-test-harness",
                "MIT · Sister runtime: MCP-Bastion",
            ],
            theme="outro",
        )

        print(f"concat -> {OUT_MP4}")
        concat(clips, OUT_MP4)
        size_mb = OUT_MP4.stat().st_size / (1024 * 1024)
        # duration
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(OUT_MP4),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"done: {OUT_MP4} ({size_mb:.1f} MiB, {float(probe.stdout.strip()):.1f}s)")


if __name__ == "__main__":
    main()
