from __future__ import annotations

import csv
from dataclasses import asdict
from io import BytesIO, StringIO
from pathlib import Path

import streamlit as st
from PIL import Image

from measure_line_ratio import (
    RESULT_DIR,
    color_masks,
    measured_lines,
    measure_image,
    save_overlay,
    timestamp_prefix,
    write_csv,
)


st.set_page_config(page_title="Line Ratio Measurement", layout="wide")


def rows_to_csv_text(rows) -> str:
    if not rows:
        return ""
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(asdict(rows[0]).keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow(asdict(row))
    return buffer.getvalue()


def image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_overlay_preview(image: Image.Image, min_area: int) -> Image.Image | None:
    yellow_mask, black_mask = color_masks(image)
    black_lines = measured_lines(black_mask, min_area)
    if not black_lines:
        return None

    temp_path = RESULT_DIR / "_streamlit_preview_overlay.png"
    save_overlay(image, yellow_mask, black_mask, black_lines, temp_path)
    preview = Image.open(temp_path).copy()
    try:
        temp_path.unlink()
    except OSError:
        pass
    return preview


st.title("Line Ratio Measurement")
st.caption("Yellow reference line = 1. Black line lengths are measured as relative ratios.")

uploaded_files = st.file_uploader(
    "Select image files",
    type=["png", "jpg", "jpeg", "tif", "tiff", "bmp"],
    accept_multiple_files=True,
)

min_area = st.number_input("Minimum line area (px)", min_value=1, max_value=10000, value=8)
save_files = st.checkbox("Save CSV and overlay PNG files to Result folder", value=True)

if st.button("Measure", type="primary", disabled=not uploaded_files):
    prefix = timestamp_prefix()
    all_rows = []
    previews = []

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file).convert("RGB")
        image_path = RESULT_DIR / uploaded_file.name
        image.save(image_path)

        rows = measure_image(
            image_path=image_path,
            min_area=int(min_area),
            overlay_dir=RESULT_DIR if save_files else None,
            prefix=prefix,
        )
        all_rows.extend(rows)

        preview = make_overlay_preview(image, int(min_area))
        if preview:
            previews.append((uploaded_file.name, preview))

        try:
            image_path.unlink()
        except OSError:
            pass

    csv_name = f"{prefix}_line_ratio_metrics.csv"
    csv_path = RESULT_DIR / csv_name
    csv_text = rows_to_csv_text(all_rows)
    if save_files:
        write_csv(all_rows, csv_path)

    st.subheader("Results")
    st.dataframe([asdict(row) for row in all_rows], use_container_width=True)
    st.download_button(
        "Download CSV",
        data=csv_text.encode("utf-8-sig"),
        file_name=csv_name,
        mime="text/csv",
    )

    st.subheader("Overlay")
    for name, preview in previews:
        st.image(preview, caption=name, use_container_width=True)
        st.download_button(
            f"Download overlay PNG - {name}",
            data=image_to_png_bytes(preview),
            file_name=f"{prefix}_{Path(name).stem}_line_ratio_overlay.png",
            mime="image/png",
        )

    if save_files:
        st.success(f"Saved files to {RESULT_DIR.resolve()}")
