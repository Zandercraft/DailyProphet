"""Detects borders, frames, dividers, and content slots in newspaper layout templates."""

import cv2
import numpy as np
import json
import os


def analyze_template_structure(img_path):
    img = cv2.imread(img_path)
    h, w, _ = img.shape
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Detect outer border margins
    # The outer border is typically an ornate rectangular frame
    # Compute horizontal and vertical projection of gradients
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    grad_mag = np.sqrt(sobelx**2 + sobely**2)

    # Margins
    left_m = 40
    right_m = w - 40
    top_m = 30
    bot_m = h - 30

    # Search for sharpest margin lines in the outer 10%
    _x_grads = np.mean(grad_mag, axis=0)
    _y_grads = np.mean(grad_mag, axis=1)

    # 2. Detect prominent horizontal divider lines across the page
    # Threshold for dark ink lines
    _, dark_ink = cv2.threshold(gray, 105, 255, cv2.THRESH_BINARY_INV)

    # Find horizontal lines of width at least 25% of page
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(w * 0.25), 1))
    h_lines = cv2.morphologyEx(dark_ink, cv2.MORPH_OPEN, h_kernel)

    # Horizontal divider y-positions
    h_proj = np.sum(h_lines, axis=1) / 255
    divider_ys = []
    in_line = False
    start_y = 0
    for y in range(top_m, bot_m):
        if h_proj[y] > w * 0.2:
            if not in_line:
                in_line = True
                start_y = y
        else:
            if in_line:
                in_line = False
                divider_ys.append((start_y + y) // 2)

    # Merge very close horizontal lines (< 15px)
    merged_dividers = []
    for dy in divider_ys:
        if not merged_dividers or dy - merged_dividers[-1] > 20:
            merged_dividers.append(dy)

    # 3. Detect rectangular frames (photos, callouts, ads)
    # Using contour detection on adaptive threshold
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5)

    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    frames = []
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        if 140 < bw < w - 60 and 80 < bh < h * 0.45:
            # Check aspect ratio
            aspect = bw / bh
            if 0.4 < aspect < 3.5:
                # Check if it has a noticeable border / inner content area
                frames.append((x, y, bw, bh))

    # Deduplicate frames
    clean_frames = []
    for f in sorted(frames, key=lambda f: f[2] * f[3], reverse=True):
        dup = False
        for cf in clean_frames:
            if abs(f[0] - cf[0]) < 25 and abs(f[1] - cf[1]) < 25 and abs(f[2] - cf[2]) < 35 and abs(f[3] - cf[3]) < 35:
                dup = True
                break
        if not dup:
            clean_frames.append(f)

    # 4. Detect columns in vertical bands between horizontal dividers
    bands = []
    band_limits = [top_m] + merged_dividers + [bot_m]
    for i in range(len(band_limits) - 1):
        by1 = band_limits[i]
        by2 = band_limits[i + 1]
        bh = by2 - by1
        if bh < 40:
            continue

        # Look for vertical lines inside this band
        band_roi = dark_ink[by1:by2, left_m:right_m]
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, int(bh * 0.4))))
        v_lines = cv2.morphologyEx(band_roi, cv2.MORPH_OPEN, v_kernel)
        v_proj = np.sum(v_lines, axis=0) / 255

        v_divs = []
        in_vline = False
        v_start = 0
        for x_rel in range(len(v_proj)):
            if v_proj[x_rel] > bh * 0.35:
                if not in_vline:
                    in_vline = True
                    v_start = x_rel
            else:
                if in_vline:
                    in_vline = False
                    v_divs.append(left_m + (v_start + x_rel) // 2)

        # Merge close vertical dividers
        merged_v = []
        for vx in v_divs:
            if not merged_v or vx - merged_v[-1] > 30:
                merged_v.append(vx)

        bands.append(
            {
                "y_top": int(by1),
                "y_bot": int(by2),
                "height": int(bh),
                "v_dividers": [int(vx) for vx in merged_v],
                "num_columns": len(merged_v) + 1,
            }
        )

    return {
        "width": int(w),
        "height": int(h),
        "dividers": [int(d) for d in merged_dividers],
        "frames": clean_frames,
        "bands": bands,
    }


def main():
    os.makedirs("scratch/layout_details", exist_ok=True)
    summary = {}
    for i in range(1, 10):
        p = f"samples/Vintage Wizarding Newspaper Additional Layout-{i}.png"
        if not os.path.exists(p):
            continue
        data = analyze_template_structure(p)
        summary[f"layout_{i}"] = data
        print(f"=== Layout-{i} ({data['width']}x{data['height']}) ===")
        print(f"  Horizontal Dividers ({len(data['dividers'])}): {data['dividers']}")
        print(f"  Bands ({len(data['bands'])}):")
        for b in data["bands"]:
            print(
                f"    y: {b['y_top']:4d}..{b['y_bot']:4d} (h={b['height']:3d}) -> {b['num_columns']} cols (dividers: {b['v_dividers']})"
            )
        print(f"  Frames ({len(data['frames'])}):")
        for f in data["frames"]:
            print(f"    [x={f[0]:4d}, y={f[1]:4d}, w={f[2]:4d}, h={f[3]:4d}]")

    with open("scratch/layout_details/summary.json", "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
