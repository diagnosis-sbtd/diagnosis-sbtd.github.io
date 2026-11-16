#!/usr/bin/env python3
"""Render the static Graphviz decision-tree figure for the Diagnosis website."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOT = ROOT / "tools" / "decision-tree.dot"
MEDIA = ROOT / "assets" / "media"
SVG = MEDIA / "decision-tree.svg"
PNG = MEDIA / "decision-tree.png"

PAD = 14


def render_graphviz_svg() -> tuple[str, tuple[float, float, float, float]]:
    with tempfile.TemporaryDirectory() as tmp:
        raw_svg = Path(tmp) / "decision-tree.raw.svg"
        subprocess.run(["dot", "-Tsvg", str(DOT), "-o", str(raw_svg)], check=True)
        content = raw_svg.read_text(encoding="utf-8")

    viewbox_match = re.search(r'viewBox="([^"]+)"', content)
    if not viewbox_match:
        raise RuntimeError("Graphviz SVG did not include a viewBox")
    min_x, min_y, width, height = (float(v) for v in viewbox_match.group(1).split())

    graph_match = re.search(r'(<g id="graph0".*</g>)\s*</svg>', content, re.S)
    if not graph_match:
        raise RuntimeError("Graphviz SVG did not include a graph0 group")
    return graph_match.group(1), (min_x, min_y, width, height)


def build_svg() -> None:
    graph, (min_x, min_y, width, height) = render_graphviz_svg()
    canvas_w = round(width + 2 * PAD)
    canvas_h = round(height + 2 * PAD)
    tx = PAD - min_x
    ty = PAD - min_y

    SVG.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}" role="img" aria-labelledby="title desc">
  <title id="title">Diagnosis decision tree</title>
  <desc id="desc">Decision tree learned for requirement phi3 on the retry trace of the lane-change example. Internal nodes are mutated elements of phi3; leaves give the verdict and the number of training samples.</desc>
  <g transform="translate({tx:.3f} {ty:.3f})">
{graph}
  </g>
</svg>
''',
        encoding="utf-8",
    )


def build_png() -> None:
    content = SVG.read_text(encoding="utf-8")
    match = re.search(r'width="(\d+)" height="(\d+)"', content)
    if not match:
        raise RuntimeError("Wrapped SVG did not include width and height")
    canvas_w, canvas_h = match.groups()
    with tempfile.TemporaryDirectory() as tmp:
        png_svg = Path(tmp) / "decision-tree.png.svg"
        png_svg.write_text(
            content.replace(
                '<g transform="translate(',
                '<rect width="100%" height="100%" fill="#fbfbf7"/>\n  <g transform="translate(',
                1,
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                "rsvg-convert",
                "-w",
                canvas_w,
                "-h",
                canvas_h,
                "-o",
                str(PNG),
                str(png_svg),
            ],
            check=True,
        )


def main() -> None:
    MEDIA.mkdir(parents=True, exist_ok=True)
    build_svg()
    build_png()


if __name__ == "__main__":
    main()
