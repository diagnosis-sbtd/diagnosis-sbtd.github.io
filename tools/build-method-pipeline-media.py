#!/usr/bin/env python3
"""Generate the method animation for the Diagnosis website.

The animation shows three generations of the search on the running example
(requirement phi3 on the retry trace): mutants are sampled, checked against
the trace, and the decision tree is relearned from the accumulated verdicts.
The final tree is the upper part of the tree in the paper's running example.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR = ROOT / "assets" / "media"
TMP_DIR = Path("/private/tmp/diagnosis-method-pipeline")
SVG_DIR = TMP_DIR / "svg"
PNG_DIR = TMP_DIR / "png"

# Displayed at about 820 px wide, so 22 px here renders at about 13 px.
W, H = 1400, 560
FPS = 12
DURATION_S = 16
FRAMES = FPS * DURATION_S

# Same palette as the page and the decision-tree figure.
BG = "#fbfbf7"
INK = "#1d2321"
MUTED = "#5b6561"
RULE = "#c9cec9"
SAT = "#1f4e79"
UNSAT = "#a8442f"
CODE_BG = "#f0f1ec"
TINT = "#dfe6ee"

SANS = "Helvetica, Arial, sans-serif"
MONO = "Menlo, SFMono-Regular, Consolas, monospace"
MONO_ADVANCE = 0.602  # Menlo glyph advance, in em

# Columns: Mutate, Check, Explain.
C1, C2, C3 = 40, 545, 935
C1_W, C2_W, C3_W = 440, 320, 425

GEN_START = 0.8
GEN_LEN = 4.0
FADE_OUT = 15.6

# Each generation samples three mutants of phi3 (one token changed each).
# Verdicts follow the tree in the paper: sat if the mutant lands in a True leaf.
GENERATIONS = [
    [("∞ → 6.2 s", "unsat"), ("3.5 → 3.1 m", "unsat"), ("and → or", "unsat")],
    [("∞ → 4.1 s", "sat"), ("∞ → 3.6 s", "sat"), ("0 → 0.8 s", "unsat")],
    [("∞ → 5.0 s", "sat"), ("3.5 → 2.6 m", "sat"), ("3.5 → 2.9 m", "unsat")],
]


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def smoothstep(x: float) -> float:
    x = clamp(x)
    return x * x * (3 - 2 * x)


def pop(t: float, start: float, length: float = 0.4) -> float:
    return smoothstep((t - start) / length)


def pulse(t: float, start: float, duration: float) -> float:
    return pop(t, start, 0.25) * (1 - smoothstep((t - start - duration) / 0.35))


def gen_time(g: int, offset: float) -> float:
    return GEN_START + g * GEN_LEN + offset


def esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x: float, y: float, value: str, size: int = 22, fill: str = INK, weight: int = 400,
         anchor: str = "start", opacity: float = 1.0, family: str = SANS) -> str:
    if opacity <= 0:
        return ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" xml:space="preserve" '
        f'font-family="{family}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" opacity="{opacity:.2f}">{esc(value)}</text>'
    )


def mono(x: float, y: float, value: str, size: int = 22, fill: str = INK, anchor: str = "start",
         opacity: float = 1.0) -> str:
    return text(x, y, value, size, fill, 400, anchor, opacity, MONO)


def rect(x: float, y: float, w: float, h: float, fill: str, stroke: str = "none", sw: float = 1.0,
         opacity: float = 1.0) -> str:
    if opacity <= 0:
        return ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}" opacity="{opacity:.2f}"/>'
    )


def line(x1: float, y1: float, x2: float, y2: float, color: str = RULE, width: float = 1.5,
         opacity: float = 1.0, dashed: bool = False, marker: bool = False) -> str:
    if opacity <= 0:
        return ""
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    end = ' marker-end="url(#head)"' if marker else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
        f'stroke-width="{width}"{dash}{end} opacity="{opacity:.2f}"/>'
    )


def defs() -> str:
    return f"""<defs>
  <marker id="head" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="userSpaceOnUse">
    <path d="M1,1 L9,5 L1,9" fill="none" stroke="{MUTED}" stroke-width="1.6"/>
  </marker>
</defs>"""


def header(x: float, n: str, title: str, subtitle: str) -> str:
    return "\n".join([
        text(x, 52, f"{n}  {title}", 30, INK, 600),
        text(x, 84, subtitle, 22, MUTED),
    ])


def moving_dot(t: float, start: float, x1: float, y1: float, x2: float, y2: float) -> str:
    a = pulse(t, start, 0.6)
    if a <= 0:
        return ""
    u = smoothstep((t - start) / 0.6)
    return f'<circle cx="{x1 + (x2 - x1) * u:.1f}" cy="{y1 + (y2 - y1) * u:.1f}" r="6" fill="{INK}" opacity="{a:.2f}"/>'


# 1  Mutate

REQ_LINES = [
    "forall τ0 in [0, ∞):",
    "  y_pos > 0.5 and y_pos < 3.5",
    "  and (x_gap < 2.0 and y_gap < 1.5)",
    "implies exists τ1 in [τ0, τ0+1]:",
    "  y_gap > 1.0",
]
# (line, column, token) of the tokens in the mutation space.
REQ_TOKENS = [(0, 14, "0"), (0, 17, "∞"), (1, 26, "3.5"), (2, 19, "and"), (4, 10, "1.0")]


def requirement(t: float) -> str:
    x, y, size, lh = C1, 112, 20, 31
    adv = size * MONO_ADVANCE
    parts = [rect(x, y, C1_W, 22 + lh * len(REQ_LINES), CODE_BG)]
    for li, col, token in REQ_TOKENS:
        parts.append(rect(x + 14 + col * adv - 2, y + 12 + li * lh, len(token) * adv + 4, lh - 6, TINT))
    for i, value in enumerate(REQ_LINES):
        parts.append(mono(x + 14, y + 34 + i * lh, value, size))
    return "\n".join(parts)


def mutants(t: float) -> str:
    parts: list[str] = []
    for g, gen in enumerate(GENERATIONS):
        start = gen_time(g, 0.0)
        end = gen_time(g + 1, 0.0) if g + 1 < len(GENERATIONS) else FADE_OUT + 1
        visible = pop(t, start, 0.3) * (1 - pop(t, end - 0.3, 0.3))
        if visible <= 0:
            continue
        parts.append(text(C1, 330, f"Generation {g + 1}: mutants of φ3", 22, MUTED, opacity=visible))
        for i, (label, _) in enumerate(gen):
            a = visible * pop(t, start + 0.15 + 0.25 * i, 0.3)
            parts.append(mono(C1 + 14, 372 + i * 36, label, 22, INK, opacity=a))
    return "\n".join(parts)


# 2  Check

def trace(x: float, y: float) -> str:
    w, h = C2_W, 70
    pts_a, pts_b = [], []
    for i in range(60):
        u = i / 59
        pts_a.append(f"{x + u * w:.1f},{y + h - 12 - 40 * smoothstep((u - 0.45) / 0.3):.1f}")
        pts_b.append(f"{x + u * w:.1f},{y + 18 + 36 * smoothstep((u - 0.5) / 0.3):.1f}")
    return "\n".join([
        text(x, y - 12, "trace π", 22, MUTED),
        line(x, y + h, x + w, y + h, RULE),
        f'<polyline points="{" ".join(pts_a)}" fill="none" stroke="{SAT}" stroke-width="2.5"/>',
        f'<polyline points="{" ".join(pts_b)}" fill="none" stroke="{MUTED}" stroke-width="2.5"/>',
    ])


def verdicts(t: float) -> str:
    x, y = C2, 250
    parts: list[str] = []
    count = 0
    for g, gen in enumerate(GENERATIONS):
        for i, (label, verdict) in enumerate(gen):
            start = gen_time(g, 1.6 + 0.3 * i)
            a = pop(t, start, 0.3)
            if a > 0:
                count += 1
            row = g * 3 + i
            color = SAT if verdict == "sat" else UNSAT
            parts.append(mono(x, y + 30 + row * 31, label, 22, INK, opacity=a))
            parts.append(mono(x + C2_W, y + 30 + row * 31, verdict, 22, color, "end", a))
    parts.insert(0, text(x, y, f"verdicts Δ  ({count})", 22, MUTED))
    return "\n".join(parts)


# 3  Explain

def node(x: float, y: float, label: str, a: float) -> str:
    if a <= 0:
        return ""
    rx = 14 + len(label) * 6.6
    return (
        f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="21" fill="#ffffff" stroke="{INK}" '
        f'stroke-width="1.5" opacity="{a:.2f}"/>' + text(x, y + 8, label, 22, INK, anchor="middle", opacity=a)
    )


def leaf(x: float, y: float, verdict: bool, a: float) -> str:
    if a <= 0:
        return ""
    label, color = ("True", SAT) if verdict else ("False", UNSAT)
    return rect(x - 36, y - 19, 72, 38, "#ffffff", color, 1.5, a) + text(x, y + 8, label, 22, color, anchor="middle", opacity=a)


def edge(x1: float, y1: float, x2: float, y2: float, label: str, a: float, side: str) -> str:
    if a <= 0:
        return ""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    lx = mx - 16 if side == "left" else mx + 16
    anchor = "end" if side == "left" else "start"
    return line(x1, y1, x2, y2, MUTED, 1.4, a) + text(lx, my + 6, label, 20, MUTED, anchor=anchor, opacity=a)


def tree(t: float) -> str:
    small = pop(t, gen_time(1, 3.0), 0.5) * (1 - pop(t, gen_time(2, 3.0), 0.4))
    full = pop(t, gen_time(2, 3.0), 0.5)
    parts: list[str] = []

    # After generation 1 every verdict is unsat: no tree can be learned yet.
    empty = 1 - pop(t, gen_time(0, 2.9), 0.3)
    pending = pop(t, gen_time(0, 3.0), 0.4) * (1 - pop(t, gen_time(1, 2.9), 0.3))
    parts.append(text(C3, 150, "no verdicts yet", 22, MUTED, opacity=empty))
    parts.append(text(C3, 150, "one class only: no tree yet", 22, MUTED, opacity=pending))

    cx = C3 + 170
    y0, dy = 150, 92

    # Generation 2: a single split on the end of the time window.
    parts += [
        edge(cx, y0 + 21, cx - 100, y0 + dy - 19, "≤ 4.6998 s", small, "left"),
        edge(cx, y0 + 21, cx + 100, y0 + dy - 19, "> 4.6998 s", small, "right"),
        node(cx, y0, "φ3(∞)", small),
        leaf(cx - 100, y0 + dy, True, small),
        leaf(cx + 100, y0 + dy, False, small),
    ]

    # Generation 3: the upper part of the tree in the paper.
    root, conn = (cx, y0), (cx + 110, y0 + dy)
    inf2, orl = (cx + 20, y0 + 2 * dy), (cx + 220, y0 + 2 * dy)
    pos, t2 = (cx + 110, y0 + 3 * dy), (cx - 60, y0 + 3 * dy)
    t3, f3 = (cx + 40, y0 + 4 * dy), (cx + 190, y0 + 4 * dy)
    parts += [
        edge(*root, cx - 100, y0 + dy - 19, "≤ 4.6998 s", full, "left"),
        edge(root[0], root[1] + 21, conn[0], conn[1] - 21, "> 4.6998 s", full, "right"),
        edge(conn[0], conn[1] + 21, inf2[0], inf2[1] - 21, "and", full, "left"),
        edge(conn[0], conn[1] + 21, orl[0], orl[1] - 19, "or", full, "right"),
        edge(inf2[0], inf2[1] + 21, t2[0], t2[1] - 19, "≤ 5.2003 s", full, "left"),
        edge(inf2[0], inf2[1] + 21, pos[0], pos[1] - 21, "> 5.2003 s", full, "right"),
        edge(pos[0], pos[1] + 21, t3[0], t3[1] - 19, "≤ 2.8006 m", full, "left"),
        edge(pos[0], pos[1] + 21, f3[0], f3[1] - 19, "> 2.8006 m", full, "right"),
        node(*root, "φ3(∞)", full),
        leaf(cx - 100, y0 + dy, True, full),
        node(*conn, "φ3(and)", full),
        node(*inf2, "φ3(∞)", full),
        leaf(*orl, False, full),
        leaf(*t2, True, full),
        node(*pos, "φ3(3.5)", full),
        leaf(*t3, True, full),
        leaf(*f3, False, full),
    ]
    return "\n".join(parts)


def loop(t: float) -> str:
    """Dashed return path from Check back into the mutant list, emphasised between generations."""
    emphasis = max(pulse(t, gen_time(g, 3.3), 0.6) for g in range(len(GENERATIONS) - 1))
    a = 0.75 + 0.25 * emphasis
    y = 494
    x1, x2 = C2 - 12, C1 + 14
    return "\n".join([
        line(x1, y, x2, y, MUTED, 1.5, a, dashed=True),
        line(x2, y, x2, 462, MUTED, 1.5, a, dashed=True, marker=True),
        text(x2 + 16, y + 30, "next generation", 22, MUTED, opacity=a),
    ])


def scene(t: float) -> str:
    fade = pop(t, FADE_OUT, 0.4)
    arrow_y = 300
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        defs(),
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        header(C1, "1", "Mutate", "Generator of Mutations"),
        header(C2, "2", "Check", "Trace-Checker"),
        header(C3, "3", "Explain", "Diagnostic Generator"),
        requirement(t),
        mutants(t),
        trace(C2, 140),
        verdicts(t),
        tree(t),
        line(C1 + C1_W + 8, arrow_y, C2 - 12, arrow_y, MUTED, 1.5, marker=True),
        line(C2 + C2_W + 10, arrow_y, C3 - 12, arrow_y, MUTED, 1.5, marker=True),
        loop(t),
    ]
    for g in range(len(GENERATIONS)):
        parts.append(moving_dot(t, gen_time(g, 1.0), C1 + C1_W + 8, arrow_y, C2 - 12, arrow_y))
        parts.append(moving_dot(t, gen_time(g, 2.6), C2 + C2_W + 10, arrow_y, C3 - 12, arrow_y))
    if fade > 0:
        parts.append(f'<rect width="{W}" height="{H}" fill="{BG}" opacity="{fade:.2f}"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def poster() -> str:
    """The last fully drawn frame, used as the video's poster image."""
    return scene(FADE_OUT - 0.1)


def build() -> None:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    SVG_DIR.mkdir(parents=True)
    PNG_DIR.mkdir(parents=True)

    for i in range(FRAMES):
        svg = SVG_DIR / f"frame-{i:04d}.svg"
        svg.write_text(scene(i / FPS), encoding="utf-8")
        subprocess.run(
            ["rsvg-convert", "-w", str(W), "-h", str(H), "-o", str(PNG_DIR / f"frame-{i:04d}.png"), str(svg)],
            check=True,
        )

    (MEDIA_DIR / "method-pipeline-poster.svg").write_text(poster(), encoding="utf-8")

    ffmpeg = shutil.which("ffmpeg")
    try:
        import imageio_ffmpeg  # type: ignore

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to encode MP4; install imageio-ffmpeg or repair system ffmpeg")

    subprocess.run(
        [
            ffmpeg, "-y", "-framerate", str(FPS), "-i", str(PNG_DIR / "frame-%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart",
            str(MEDIA_DIR / "method-pipeline.mp4"),
        ],
        check=True,
    )


if __name__ == "__main__":
    build()
