#!/usr/bin/env python3
"""
Generate File Converter Pro logo in PNG and ICO formats.
Run this once: python assets/generate_logo.py
Requires: pillow (already in requirements.txt)
"""

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

ASSETS_DIR = Path(__file__).parent


def create_logo(size=256):
    """Create the File Converter Pro logo."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Scale factor
    s = size / 256

    # Background circle - dark charcoal
    pad = int(8 * s)
    draw.ellipse([pad, pad, size - pad, size - pad], fill='#1c1c24')

    # Outer ring - teal accent
    ring_w = int(6 * s)
    draw.ellipse([pad, pad, size - pad, size - pad], outline='#00d4aa', width=ring_w)

    # Two overlapping document shapes to represent conversion
    # Left document (source) - slightly behind
    cx, cy = size // 2, size // 2

    # Left doc
    lx1, ly1 = int(60 * s), int(68 * s)
    lx2, ly2 = int(140 * s), int(188 * s)
    draw.rounded_rectangle([lx1, ly1, lx2, ly2], radius=int(8 * s), fill='#555770')

    # Dog-ear on left doc
    ear_size = int(20 * s)
    draw.polygon([
        (lx2 - ear_size, ly1),
        (lx2, ly1 + ear_size),
        (lx2 - ear_size, ly1 + ear_size)
    ], fill='#3d3d50')

    # Lines on left doc
    for i in range(3):
        y = ly1 + int(40 * s) + i * int(22 * s)
        draw.rounded_rectangle(
            [lx1 + int(14 * s), y, lx2 - int(14 * s), y + int(6 * s)],
            radius=int(3 * s), fill='#3d3d50'
        )

    # Right document (target) - in front
    rx1, ry1 = int(116 * s), int(68 * s)
    rx2, ry2 = int(196 * s), int(188 * s)
    draw.rounded_rectangle([rx1, ry1, rx2, ry2], radius=int(8 * s), fill='#00d4aa')

    # Dog-ear on right doc
    draw.polygon([
        (rx2 - ear_size, ry1),
        (rx2, ry1 + ear_size),
        (rx2 - ear_size, ry1 + ear_size)
    ], fill='#00b894')

    # Lines on right doc
    for i in range(3):
        y = ry1 + int(40 * s) + i * int(22 * s)
        draw.rounded_rectangle(
            [rx1 + int(14 * s), y, rx2 - int(14 * s), y + int(6 * s)],
            radius=int(3 * s), fill='#00b894'
        )

    # Arrow between docs (conversion arrow) - pointing right
    arrow_y = cy
    arrow_x = cx
    arrow_len = int(16 * s)
    arrow_head = int(10 * s)

    # Arrow shaft
    draw.rounded_rectangle(
        [arrow_x - arrow_len, arrow_y - int(3 * s),
         arrow_x + arrow_len - arrow_head, arrow_y + int(3 * s)],
        radius=int(2 * s), fill='#eef0f4'
    )
    # Arrow head
    draw.polygon([
        (arrow_x + arrow_len, arrow_y),
        (arrow_x + arrow_len - arrow_head * 2, arrow_y - arrow_head),
        (arrow_x + arrow_len - arrow_head * 2, arrow_y + arrow_head)
    ], fill='#eef0f4')

    return img


def main():
    print("Generating File Converter Pro logo...")

    # 256x256 PNG
    logo_256 = create_logo(256)
    logo_256.save(ASSETS_DIR / 'logo.png', 'PNG')
    print(f"  Created: assets/logo.png (256x256)")

    # ICO with multiple sizes
    sizes = [16, 32, 48, 64, 128, 256]
    ico_images = []
    for sz in sizes:
        ico_images.append(create_logo(sz))

    ico_images[0].save(
        ASSETS_DIR / 'logo.ico', 'ICO',
        sizes=[(sz, sz) for sz in sizes],
        append_images=ico_images[1:]
    )
    print(f"  Created: assets/logo.ico (multi-size)")

    # 64x64 for small display
    logo_64 = create_logo(64)
    logo_64.save(ASSETS_DIR / 'logo_small.png', 'PNG')
    print(f"  Created: assets/logo_small.png (64x64)")

    print("Done!")


if __name__ == '__main__':
    main()
