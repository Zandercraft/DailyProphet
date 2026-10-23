"""Analyze and inspect Additional Layouts 1 to 9."""
import cv2
import os
import json
import numpy as np

def analyze_layout(img_path):
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Threshold dark ink lines on vintage parchment
    _, ink = cv2.threshold(gray, 95, 255, cv2.THRESH_BINARY_INV)

    # Detect horizontal lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(w * 0.08), 1))
    h_lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, h_kernel)

    # Detect vertical lines
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(h * 0.06)))
    v_lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, v_kernel)

    grid = cv2.bitwise_or(h_lines, v_lines)
    cell_mask = cv2.bitwise_not(grid)
    cv2.rectangle(cell_mask, (0, 0), (w, h), 0, 10)

    contours, _ = cv2.findContours(cell_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    cells = []
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        area = bw * bh
        if bw > w * 0.1 and bh > h * 0.03 and area < w * h * 0.9:
            roi = gray[y:y+bh, x:x+bw]
            mean_lum = np.mean(roi)
            if mean_lum > 120:
                cells.append({'rect': [int(x), int(y), int(bw), int(bh)], 'lum': float(mean_lum)})

    # Sort cells top-down, left-to-right
    cells = sorted(cells, key=lambda c: (c['rect'][1] // 50, c['rect'][0]))
    return {'size': [w, h], 'cells_count': len(cells), 'cells': cells}

def main():
    results = {}
    for i in range(1, 10):
        p = f"samples/Vintage Wizarding Newspaper Additional Layout-{i}.png"
        if not os.path.exists(p):
            continue
        res = analyze_layout(p)
        results[f"layout_{i}"] = res
        print(f"=== Layout-{i} ({res['size'][0]}x{res['size'][1]}): {res['cells_count']} cells ===")
        for c in res['cells'][:6]:
            r = c['rect']
            print(f"   rect: [x={r[0]:4d}, y={r[1]:4d}, w={r[2]:4d}, h={r[3]:4d}]")

    with open("scratch/layouts_analysis.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
