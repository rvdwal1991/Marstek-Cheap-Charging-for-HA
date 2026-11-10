"""Tekent het icoon van de integratie (batterij, bliksem en euromunt).

Gebruikt alleen de standaardbibliotheek. Draaien met:
    python3 tools/maak_icoon.py
De PNG's komen in custom_components/marstek_goedkoop_laden/brand/.
"""

from __future__ import annotations

import math
from pathlib import Path
import struct
import zlib

BRAND = Path(__file__).resolve().parent.parent / "custom_components" / "marstek_goedkoop_laden" / "brand"

GREEN = (34, 197, 94)
WHITE = (255, 255, 255)
AMBER = (245, 158, 11)
BOLT = [(292, 150), (204, 296), (254, 296), (230, 408), (322, 256), (268, 256)]
COIN = (376, 396, 96)  # middelpunt x, y en straal
EURO = (382, 396)


def rounded_rect(x, y, x0, y0, x1, y1, r):
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_polygon(x, y, points):
    inside = False
    j = len(points) - 1
    for i, (xi, yi) in enumerate(points):
        xj, yj = points[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def colour_at(x, y, outline):
    """Kleur (r, g, b) op een punt in het 512x512-vlak, of None voor doorzichtig."""
    cx, cy, cr = COIN
    d_coin = math.hypot(x - cx, y - cy)
    if d_coin <= cr:
        ex, ey = EURO
        d = math.hypot(x - ex, y - ey)
        angle = abs(math.degrees(math.atan2(y - ey, x - ex)))
        if 34 <= d <= 52 and angle >= 48:
            return WHITE
        if 318 <= x <= 392 and (378 <= y <= 391 or 401 <= y <= 414):
            return WHITE
        return AMBER
    if d_coin <= cr + 12:
        return None  # doorzichtige rand om de munt
    if in_polygon(x, y, BOLT):
        return WHITE
    if rounded_rect(x, y, 172, 132, 340, 420, 22):
        return GREEN
    if rounded_rect(x, y, 136, 96, 376, 456, 48) and not rounded_rect(x, y, 160, 120, 352, 432, 30):
        return outline
    if rounded_rect(x, y, 208, 56, 304, 110, 16):
        return outline
    return None


def render(size, outline, samples=4):
    scale = 512 / size
    rows = []
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            r = g = b = a = 0
            for sy in range(samples):
                for sx in range(samples):
                    colour = colour_at(
                        (px + (sx + 0.5) / samples) * scale, (py + (sy + 0.5) / samples) * scale, outline
                    )
                    if colour:
                        r += colour[0]
                        g += colour[1]
                        b += colour[2]
                        a += 1
            if a:
                row += bytes((r // a, g // a, b // a, round(255 * a / samples**2)))
            else:
                row += b"\x00\x00\x00\x00"
        rows.append(bytes(row))
    return b"".join(rows)


def write_png(path, size, raw):
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


if __name__ == "__main__":
    BRAND.mkdir(parents=True, exist_ok=True)
    for prefix, outline in (("", (30, 41, 59)), ("dark_", (226, 232, 240))):
        for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
            write_png(BRAND / f"{prefix}{name}", size, render(size, outline))
            print("geschreven", f"{prefix}{name}")
