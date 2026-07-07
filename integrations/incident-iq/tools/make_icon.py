#!/usr/bin/env python3
"""Generate the placeholder icon for the Incident iQ integration.

Produces a 64x64 PNG (flat slate-blue tile with a white lowercase "i")
using only the Python standard library, then prints the data URI to
paste into the `icon:` key of incident-iq.yaml.

The design is deliberately generic to avoid shipping Incident iQ's
trademarked logo. To use the real logo instead, run:

    base64 -i logo.png

and replace the `icon:` value with `data:image/png;base64,<output>`
(keep the PNG small, a few KB), then re-upload the integration YAML.

Usage:
    python3 make_icon.py > icon.txt
"""

import base64
import struct
import sys
import zlib

SIZE = 64
BACKGROUND = (45, 91, 138)   # slate blue
GLYPH = (255, 255, 255)

# Lowercase "i" drawn as two rectangles: (x0, y0, x1, y1) inclusive.
DOT = (28, 12, 35, 19)
STEM = (28, 26, 35, 51)


def in_rect(x, y, rect):
    x0, y0, x1, y1 = rect
    return x0 <= x <= x1 and y0 <= y <= y1


def build_pixels():
    rows = []
    for y in range(SIZE):
        row = bytearray()
        for x in range(SIZE):
            color = GLYPH if in_rect(x, y, DOT) or in_rect(x, y, STEM) else BACKGROUND
            row.extend(color)
        rows.append(bytes(row))
    return rows


def png_chunk(tag, payload):
    chunk = tag + payload
    return struct.pack(">I", len(payload)) + chunk + struct.pack(">I", zlib.crc32(chunk))


def make_png():
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b"".join(b"\x00" + row for row in build_pixels())    # filter 0 per scanline
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    data = make_png()
    uri = "data:image/png;base64," + base64.b64encode(data).decode("ascii")
    sys.stdout.write(uri + "\n")
