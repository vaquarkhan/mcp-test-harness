#!/usr/bin/env python3
"""Build a silent 4-section product demo MP4 for GitHub Pages.

Sections (nature-safe CI gate framing — not live red-team):
  1. Security / vulnerability scan (SARIF, Suites A–D, agents scan, audit)
  2. Load testing (latency, throughput, load phases)
  3. Resilience testing (chaos, degrade, load resilience)
  4. Security + CI/CD dashboard (HTML report, Action, JUnit/SARIF)

Requires: Pillow, ffmpeg on PATH.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "html" / "assets" / "images"
OUT_DIR = ROOT / "html" / "assets" / "video"
OUT_MP4 = OUT_DIR / "mcp-test-harness-4-section-demo.mp4"
W, H = 1920, 1080
FPS = 30

# (bg_rgb, accent_rgb)
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


def title_slide(
    path: Path,
    kicker: str,
    title: str,
    bullets: list[str],
    theme: str,
) -> None:
    bg, accent = THEME[theme]
    im = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(im)
    # left accent bar
    draw.rectangle([0, 0, 18, H], fill=accent)
    # brand
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
        "Deterministic CI gate  ·  No live model required  ·  MIT",
        fill=(100, 116, 139),
        font=_font(28),
    )
    im.save(path, "PNG")


def image_slide(src: Path, path: Path, caption: str, theme: str) -> None:
    bg, accent = THEME[theme]
    canvas = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, 18, H], fill=accent)
    if src.is_file():
        photo = Image.open(src).convert("RGB")
        # fit into 1760x820 box
        box_w, box_h = 1760, 820
        photo.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)
        x = 80 + (box_w - photo.width) // 2
        y = 80 + (box_h - photo.height) // 2
        canvas.paste(photo, (x, y))
    draw.rectangle([0, H - 110, W, H], fill=(2, 6, 23))
    draw.text((72, H - 78), caption, fill=(226, 232, 240), font=_font(36))
    canvas.save(path, "PNG")


def png_to_clip(png: Path, mp4: Path, seconds: float) -> None:
    frames = max(1, int(seconds * FPS))
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(png),
            "-c:v",
            "libx264",
            "-t",
            str(seconds),
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-vf",
            f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
            "-frames:v",
            str(frames),
            str(mp4),
        ],
        check=True,
        capture_output=True,
    )


def concat(clips: list[Path], out: Path) -> None:
    listing = out.with_suffix(".txt")
    listing.write_text(
        "".join(f"file '{c.resolve().as_posix()}'\n" for c in clips),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-crf",
            "23",
            "-preset",
            "medium",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    listing.unlink(missing_ok=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mth-demo-") as tmp:
        td = Path(tmp)
        slides: list[tuple[Path, float]] = []

        def add_title(name: str, seconds: float, **kw: object) -> None:
            p = td / f"{name}.png"
            title_slide(p, **kw)  # type: ignore[arg-type]
            slides.append((p, seconds))

        def add_img(name: str, src: str, caption: str, theme: str, seconds: float = 5.0) -> None:
            p = td / f"{name}.png"
            image_slide(IMG / src, p, caption, theme)
            slides.append((p, seconds))

        add_title(
            "00_intro",
            4.5,
            kicker="Product demo",
            title="Four CI gates for MCP",
            bullets=[
                "1  Security / vulnerability scan",
                "2  Load testing",
                "3  Resilience testing",
                "4  Security features → CI/CD dashboard",
            ],
            theme="intro",
        )

        # Section 1
        add_title(
            "01_title",
            4.0,
            kicker="Section 1 of 4",
            title="Security / vulnerability scan",
            bullets=[
                "Suites A–D · incident E–K · AGENTS.md Unicode",
                "quality_gate + SARIF · mcp-test scan-agents",
                "mcp-test audit verify — recorded-verdict CI",
            ],
            theme="sec1",
        )
        add_img(
            "01a",
            "harness-bastion-pairing.png",
            "CI gate (Harness) + runtime (Bastion) — scan before enforce",
            "sec1",
            5.5,
        )
        add_img(
            "01b",
            "assertions-grid.png",
            "Deterministic security assertions — no live model in the PR gate",
            "sec1",
            5.5,
        )

        # Section 2
        add_title(
            "02_title",
            4.0,
            kicker="Section 2 of 4",
            title="Load testing",
            bullets=[
                "assert_latency — p90 / p95 / p99 gates",
                "assert_throughput — concurrent RPS + error-rate",
                "assert_load_phases — concurrency ramps in CI",
            ],
            theme="sec2",
        )
        add_img(
            "02a",
            "three-testing-modes.png",
            "Functional · Regression · Performance — one MCP-aware tool",
            "sec2",
            5.5,
        )
        add_img(
            "02b",
            "parallel-execution.png",
            "Parallel workers · SLO enforcement on every push",
            "sec2",
            5.5,
        )

        # Section 3
        add_title(
            "03_title",
            4.0,
            kicker="Section 3 of 4",
            title="Resilience testing",
            bullets=[
                "Chaos faults — delay · 503 · truncate · schema drift",
                "assert_degrades_gracefully · reconnect · crash survival",
                "Load resilience — deny-codes · no-fail-open · fairness",
            ],
            theme="sec3",
        )
        add_img(
            "03a",
            "end-to-end-flow.png",
            "End-to-end loop — faults and SLOs stay inside the CI test path",
            "sec3",
            5.5,
        )
        add_img(
            "03b",
            "testherness.png",
            "Dogfood e2e — 1000+ tests · 100% library coverage gate",
            "sec3",
            5.5,
        )

        # Section 4
        add_title(
            "04_title",
            4.0,
            kicker="Section 4 of 4",
            title="Security → CI/CD dashboard",
            bullets=[
                "HTML report · JUnit · JSON · SARIF upload",
                "GitHub Action + pre-commit · PR comments",
                "Evidence for merge gates — not a hosted multi-tenant app",
            ],
            theme="sec4",
        )
        add_img(
            "04a",
            "ci-pipeline.png",
            "GitHub Actions PR gate — fail the merge when the corpus breaks",
            "sec4",
            5.5,
        )
        add_img(
            "04b",
            "html-dashboard.png",
            "Self-contained HTML dashboard — security · load · chaos panels",
            "sec4",
            5.5,
        )
        add_img(
            "04c",
            "report-formats.png",
            "Console · JUnit · JSON · HTML · PDF — artifacts your CI already knows",
            "sec4",
            5.5,
        )

        add_title(
            "99_outro",
            5.0,
            kicker="Get started",
            title="pip install · mcp-test · gate",
            bullets=[
                "pip install mcp-test-harness==5.2.0",
                "vaquarkhan.github.io/mcp-test-harness",
                "MIT · No LLM required · Sister: MCP-Bastion",
            ],
            theme="outro",
        )

        clips: list[Path] = []
        for i, (png, secs) in enumerate(slides):
            clip = td / f"clip_{i:02d}.mp4"
            print(f"encode {png.name} ({secs}s)…")
            png_to_clip(png, clip, secs)
            clips.append(clip)

        print(f"concat -> {OUT_MP4}")
        concat(clips, OUT_MP4)
        size_mb = OUT_MP4.stat().st_size / (1024 * 1024)
        print(f"done: {OUT_MP4} ({size_mb:.1f} MiB)")


if __name__ == "__main__":
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg not found on PATH")
    main()
