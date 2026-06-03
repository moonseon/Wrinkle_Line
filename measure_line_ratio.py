#!/usr/bin/env python
"""Compare black line lengths against one yellow reference line."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
RESULT_DIR = Path("Result")
FILE_TYPES = [
    ("Image files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp"),
    ("All files", "*.*"),
]


@dataclass
class Result:
    image: str
    black_line_no: int
    yellow_start_x_px: int
    yellow_start_y_px: int
    yellow_end_x_px: int
    yellow_end_y_px: int
    yellow_length_px: float
    black_start_x_px: int
    black_start_y_px: int
    black_end_x_px: int
    black_end_y_px: int
    black_length_px: float
    black_length_when_yellow_is_1: float
    status: str


def image_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(
        item
        for item in path.rglob("*")
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def timestamp_prefix() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def add_prefix(path: Path, prefix: str) -> Path:
    return path.with_name(f"{prefix}_{path.name}")


def select_image_files() -> list[Path]:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    selected = filedialog.askopenfilenames(
        title="Select image files",
        initialdir=str(Path.cwd()),
        filetypes=FILE_TYPES,
    )
    root.destroy()
    return [Path(file) for file in selected]


def color_masks(image: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.int16)
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    max_channel = rgb.max(axis=2)
    min_channel = rgb.min(axis=2)

    yellow = (
        (red >= 130)
        & (green >= 120)
        & (blue <= 150)
        & ((red - blue) >= 45)
        & ((green - blue) >= 35)
    )
    black = (max_channel <= 95) & ((max_channel - min_channel) <= 65)
    return yellow, black


def connected_components(mask: np.ndarray) -> list[np.ndarray]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    components: list[np.ndarray] = []

    for y in range(height):
        for x in range(width):
            if visited[y, x] or not mask[y, x]:
                continue

            pixels = []
            stack = [(y, x)]
            visited[y, x] = True

            while stack:
                cy, cx = stack.pop()
                pixels.append((cy, cx))
                for ny in range(max(0, cy - 1), min(height, cy + 2)):
                    for nx in range(max(0, cx - 1), min(width, cx + 2)):
                        if not visited[ny, nx] and mask[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((ny, nx))

            component = np.zeros_like(mask, dtype=bool)
            yy, xx = zip(*pixels)
            component[yy, xx] = True
            components.append(component)

    return components


def line_endpoints_and_length(component: np.ndarray) -> tuple[int, int, int, int, float]:
    ys, xs = np.nonzero(component)
    if xs.size < 2:
        return 0, 0, 0, 0, 0.0

    coords = np.column_stack((xs, ys)).astype(np.float64)
    centered = coords - coords.mean(axis=0)
    _, _, vectors = np.linalg.svd(centered, full_matrices=False)
    direction = vectors[0]
    projection = centered @ direction

    start = coords[int(np.argmin(projection))]
    end = coords[int(np.argmax(projection))]
    if start[0] > end[0] or (start[0] == end[0] and start[1] > end[1]):
        start, end = end, start

    length = float(np.hypot(end[0] - start[0], end[1] - start[1]))
    return int(start[0]), int(start[1]), int(end[0]), int(end[1]), length


def measured_lines(mask: np.ndarray, min_area: int) -> list[tuple[float, int, int, int, int, float]]:
    lines = []
    for component in connected_components(mask):
        if int(component.sum()) < min_area:
            continue
        start_x, start_y, end_x, end_y, length = line_endpoints_and_length(component)
        if length <= 20:
            continue
        ys, _ = np.nonzero(component)
        lines.append((float(ys.mean()), start_x, start_y, end_x, end_y, length))
    return sorted(lines)


def save_overlay(
    image: Image.Image,
    yellow_mask: np.ndarray,
    black_mask: np.ndarray,
    black_lines: list[tuple[float, int, int, int, int, float]],
    output_path: Path,
) -> None:
    overlay = np.asarray(image.convert("RGB"), dtype=np.float32)
    overlay[yellow_mask] = overlay[yellow_mask] * 0.35 + np.array([255, 230, 20]) * 0.65
    overlay[black_mask] = overlay[black_mask] * 0.25

    output = Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(output)
    font = ImageFont.load_default()

    for index, (_, start_x, start_y, _, _, _) in enumerate(black_lines, 1):
        x = max(6, start_x - 44)
        y = max(6, start_y - 18)
        text = str(index)
        box = draw.textbbox((x, y), text, font=font)
        pad = 5
        draw.rectangle(
            (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad),
            fill=(255, 255, 255),
            outline=(220, 0, 0),
            width=2,
        )
        draw.text((x, y), text, fill=(220, 0, 0), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path)


def measure_image(
    image_path: Path,
    min_area: int,
    overlay_dir: Path | None,
    prefix: str,
) -> list[Result]:
    image = Image.open(image_path)
    yellow_mask, black_mask = color_masks(image)
    yellow_lines = measured_lines(yellow_mask, min_area)
    black_lines = measured_lines(black_mask, min_area)

    if not yellow_lines:
        return [empty_result(image_path.name, "yellow line not found")]
    if not black_lines:
        return [empty_result(image_path.name, "black line not found")]

    if overlay_dir:
        save_overlay(
            image,
            yellow_mask,
            black_mask,
            black_lines,
            overlay_dir / f"{prefix}_{image_path.stem}_line_ratio_overlay.png",
        )

    _, yellow_start_x, yellow_start_y, yellow_end_x, yellow_end_y, yellow_length = max(
        yellow_lines,
        key=lambda line: line[5],
    )

    rows = []
    for index, (_, start_x, start_y, end_x, end_y, black_length) in enumerate(black_lines, 1):
        rows.append(
            Result(
                image=image_path.name,
                black_line_no=index,
                yellow_start_x_px=yellow_start_x,
                yellow_start_y_px=yellow_start_y,
                yellow_end_x_px=yellow_end_x,
                yellow_end_y_px=yellow_end_y,
                yellow_length_px=round(yellow_length, 3),
                black_start_x_px=start_x,
                black_start_y_px=start_y,
                black_end_x_px=end_x,
                black_end_y_px=end_y,
                black_length_px=round(black_length, 3),
                black_length_when_yellow_is_1=round(black_length / yellow_length, 5),
                status="ok",
            )
        )
    return rows


def empty_result(image_name: str, status: str) -> Result:
    return Result(
        image=image_name,
        black_line_no=0,
        yellow_start_x_px=0,
        yellow_start_y_px=0,
        yellow_end_x_px=0,
        yellow_end_y_px=0,
        yellow_length_px=0.0,
        black_start_x_px=0,
        black_start_y_px=0,
        black_end_x_px=0,
        black_end_y_px=0,
        black_length_px=0.0,
        black_length_when_yellow_is_1=0.0,
        status=status,
    )


def write_csv(rows: list[Result], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(Result.__dataclass_fields__.keys())
    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure black line lengths relative to a yellow reference line."
    )
    parser.add_argument("input", type=Path, nargs="?", help="Image file or folder.")
    parser.add_argument("-o", "--output", type=Path, default=Path("line_ratio_metrics.csv"))
    parser.add_argument("--min-area", type=int, default=8)
    parser.add_argument("--save-overlays", action="store_true")
    parser.add_argument("--gui", action="store_true", help="Open a file selection dialog.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prefix = timestamp_prefix()
    use_gui = args.gui
    if use_gui:
        images = select_image_files()
        if not images:
            print("No images selected.")
            return 1
    else:
        if args.input is None:
            print("Input image is required. Use --gui only on desktop Python, not Streamlit Cloud.")
            return 1
        images = image_files(args.input)

    output_path = RESULT_DIR / add_prefix(Path(args.output.name), prefix).name
    overlay_dir = RESULT_DIR if args.save_overlays or use_gui else None
    rows = []
    for image_path in images:
        rows.extend(measure_image(image_path, args.min_area, overlay_dir, prefix))

    if not rows:
        print("No images found.")
        return 1

    write_csv(rows, output_path)
    print(f"Results: {output_path}")
    return 0


def running_in_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except Exception:
        return False
    return get_script_run_ctx() is not None


if __name__ == "__main__":
    if running_in_streamlit():
        from streamlit_app import render_app

        render_app()
    else:
        raise SystemExit(main())
