"""Generates authentic Harry Potter style sample graphics for The Daily Prophet."""

import os
import math
import random
from PIL import Image, ImageDraw


def create_sample_assets(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    sirius_path = os.path.join(output_dir, "sirius_black_wanted.png")
    triwizard_path = os.path.join(output_dir, "triwizard_tournament.png")
    ministry_path = os.path.join(output_dir, "ministry_official_seal.png")
    quidditch_path = os.path.join(output_dir, "golden_snitch.png")

    if not os.path.exists(sirius_path):
        _generate_sirius_image(sirius_path)
    if not os.path.exists(triwizard_path):
        _generate_triwizard_image(triwizard_path)
    if not os.path.exists(ministry_path):
        _generate_ministry_seal(ministry_path)
    if not os.path.exists(quidditch_path):
        _generate_quidditch_image(quidditch_path)

    return {
        "sirius": sirius_path,
        "triwizard": triwizard_path,
        "ministry": ministry_path,
        "quidditch": quidditch_path,
    }


def _add_paper_grain(img: Image.Image, intensity: int = 15) -> Image.Image:
    """Adds vintage newsprint noise and sepia grain."""
    w, h = img.size
    noise = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(noise)
    for _ in range(w * h // 35):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        gray = random.randint(40, 90)
        alpha = random.randint(10, intensity)
        draw.point((x, y), fill=(gray, gray, gray, alpha))
    img.alpha_composite(noise)
    return img


def _generate_sirius_image(path: str):
    """Generates an authentic Azkaban mugshot-style graphic."""
    w, h = 600, 720
    img = Image.new("RGBA", (w, h), (242, 236, 222, 255))
    draw = ImageDraw.Draw(img)

    # Sepia backdrop with height measurement lines
    for y in range(80, 520, 35):
        draw.line([(60, y), (540, y)], fill=(205, 195, 175, 160), width=1)
        draw.text((70, y - 10), f"{(600 - y) // 10}'", fill=(170, 160, 140, 200))

    # Silhouette / Portrait sketch
    # Shoulders
    draw.ellipse([140, 320, 460, 680], fill=(55, 48, 42, 255))
    # Neck
    draw.rectangle([260, 270, 340, 350], fill=(225, 210, 190, 255))
    # Head
    draw.ellipse([210, 130, 390, 310], fill=(225, 210, 190, 255))
    # Wild hair (Azkaban look)
    hair_color = (38, 30, 25, 255)
    for angle in range(-70, 70, 8):
        rad = math.radians(angle)
        ox = 300 + int(95 * math.sin(rad))
        oy = 200 - int(85 * math.cos(rad))
        draw.ellipse([ox - 40, oy - 40, ox + 40, oy + 40], fill=hair_color)
    # Eyes & intense expression
    draw.rectangle([250, 205, 280, 215], fill=(70, 55, 45, 255))
    draw.rectangle([320, 205, 350, 215], fill=(70, 55, 45, 255))
    draw.line([(245, 198), (285, 208)], fill=(40, 30, 25, 255), width=4)
    draw.line([(315, 208), (355, 198)], fill=(40, 30, 25, 255), width=4)
    # Nose & Mouth
    draw.line([(300, 210), (295, 245), (305, 248)], fill=(120, 100, 85, 255), width=2)
    draw.line([(275, 268), (325, 268)], fill=(85, 60, 50, 255), width=3)

    # Azkaban placard board held in front
    draw.rectangle([160, 430, 440, 540], fill=(25, 22, 19, 255), outline=(180, 160, 120, 255), width=3)
    draw.rectangle([165, 435, 435, 535], fill=(35, 30, 25, 255))
    draw.text((215, 450), "AZKABAN PRISON", fill=(245, 240, 225, 255))
    draw.text((230, 485), "XY 390 - DEMENTOR CUSTODY", fill=(215, 195, 150, 255))

    # Border frame
    draw.rectangle([15, 15, w - 16, h - 16], outline=(70, 55, 40, 255), width=4)
    draw.rectangle([22, 22, w - 23, h - 23], outline=(150, 130, 100, 255), width=1)

    # Corner brackets
    for cx, cy in [(15, 15), (w - 15, 15), (15, h - 15), (w - 15, h - 15)]:
        draw.rectangle([cx - 8, cy - 8, cx + 8, cy + 8], fill=(50, 40, 30, 255))

    img = _add_paper_grain(img, intensity=25)
    img.save(path)


def _generate_triwizard_image(path: str):
    """Generates an ornate Triwizard Cup engraving illustration."""
    w, h = 600, 450
    img = Image.new("RGBA", (w, h), (242, 236, 222, 255))
    draw = ImageDraw.Draw(img)

    # Double border
    draw.rectangle([12, 12, w - 13, h - 13], outline=(60, 50, 40, 255), width=3)
    draw.rectangle([18, 18, w - 19, h - 19], outline=(160, 140, 110, 255), width=1)

    # Glow background
    draw.ellipse([180, 80, 420, 340], fill=(255, 248, 220, 200))

    # Goblet / Cup stem & base
    draw.polygon([(260, 330), (340, 330), (370, 380), (230, 380)], fill=(75, 60, 45, 255))
    draw.rectangle([285, 230, 315, 340], fill=(85, 70, 50, 255))
    # Cup bowl
    draw.polygon(
        [(210, 120), (390, 120), (350, 240), (250, 240)], fill=(110, 90, 60, 255), outline=(50, 40, 30, 255), width=2
    )
    # Handles
    draw.arc([160, 130, 230, 230], start=90, end=270, fill=(60, 50, 40, 255), width=8)
    draw.arc([370, 130, 440, 230], start=-90, end=90, fill=(60, 50, 40, 255), width=8)

    # Blue magical fire coming out of the cup
    fire_colors = [(100, 180, 240, 220), (140, 210, 255, 200), (220, 240, 255, 240)]
    for _ in range(40):
        fx = random.randint(250, 350)
        fy = random.randint(60, 120)
        fr = random.randint(8, 26)
        draw.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], fill=random.choice(fire_colors))

    # Text at the bottom
    draw.text((200, 400), "✦ TRIWIZARD TOURNAMENT ✦", fill=(70, 55, 40, 255))

    img = _add_paper_grain(img, intensity=20)
    img.save(path)


def _generate_ministry_seal(path: str):
    """Generates an official Ministry of Magic wax seal / stamp."""
    w, h = 500, 500
    img = Image.new("RGBA", (w, h), (242, 236, 222, 255))
    draw = ImageDraw.Draw(img)

    cx, cy, r = 250, 250, 190
    # Outer ring
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(100, 30, 30, 240), width=6)
    draw.ellipse([cx - r + 15, cy - r + 15, cx + r - 15, cy + r - 15], outline=(100, 30, 30, 220), width=2)

    # Large prominent 'M' in center
    draw.text((cx - 85, cy - 110), "M", fill=(110, 30, 30, 240), font_size=150)

    # Circular text imitation / stars
    draw.text((cx - 130, cy + 60), "MINISTRY OF MAGIC", fill=(120, 35, 35, 255))
    draw.text((cx - 100, cy + 90), "OFFICIAL DECREE", fill=(140, 45, 45, 230))
    draw.text((cx - 65, cy - 145), "★ ★ ★ ★ ★", fill=(120, 35, 35, 220))

    img = _add_paper_grain(img, intensity=25)
    img.save(path)


def _generate_quidditch_image(path: str):
    """Generates a vintage Golden Snitch woodcut engraving."""
    w, h = 600, 400
    img = Image.new("RGBA", (w, h), (242, 236, 222, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([12, 12, w - 13, h - 13], outline=(60, 50, 40, 255), width=3)
    draw.rectangle([18, 18, w - 19, h - 19], outline=(160, 140, 110, 255), width=1)

    cx, cy = 300, 200
    # Left wing
    draw.polygon(
        [(cx - 30, cy - 10), (cx - 180, cy - 90), (cx - 240, cy - 70), (cx - 120, cy + 20), (cx - 30, cy)],
        fill=(130, 115, 90, 220),
        outline=(60, 50, 40, 255),
        width=2,
    )
    # Right wing
    draw.polygon(
        [(cx + 30, cy - 10), (cx + 180, cy - 90), (cx + 240, cy - 70), (cx + 120, cy + 20), (cx + 30, cy)],
        fill=(130, 115, 90, 220),
        outline=(60, 50, 40, 255),
        width=2,
    )

    # Ball
    draw.ellipse([cx - 45, cy - 45, cx + 45, cy + 45], fill=(210, 175, 75, 255), outline=(70, 55, 35, 255), width=3)
    draw.arc([cx - 35, cy - 35, cx + 35, cy + 35], start=-30, end=140, fill=(255, 235, 150, 255), width=4)

    draw.text((210, 330), "QUIDDITCH WORLD CUP", fill=(60, 48, 36, 255))
    draw.text((235, 355), "150 POINTS TO GRYFFINDOR", fill=(120, 100, 80, 230))

    img = _add_paper_grain(img, intensity=20)
    img.save(path)
