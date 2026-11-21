#!/usr/bin/env python3
"""Passport spread of the Republic of Velmara -- a country that isn't there.

Pure Python 3.13 standard library only. Hand-written PNG encoder, rasterizer
and 5x7 bitmap font. 100% deterministic: fixed seed, no clock, no hash().
Writes /output/entry.png (1024x1024, RGB).

Holder: ELENA MARIS VUKOVIC, passport VM 4829173, issued 14 MAR 2024 in
Porto Velmara, valid to 13 MAR 2034. All stamps are dated on or after the
issue date, in entry/exit pairs, in chronological order.
"""

import math
import os
import random
import struct
import zlib

SEED = 20261121
W, H = 1024, 1024

# ---------------------------------------------------------------- palette
TABLE = (168, 159, 141)      # warm grey tabletop
TABLE_DARK = (132, 123, 107)
PAGE = (245, 241, 230)       # warm off-white paper
PAGE_EDGE = (226, 219, 203)
NAVY = (24, 42, 74)
NAVY_SOFT = (52, 74, 110)
BURGUNDY = (140, 47, 57)
TEAL = (38, 96, 84)
TEAL_SOFT = (88, 138, 126)
GOLD = (176, 138, 66)
INK = (28, 32, 40)
GREY = (96, 96, 92)
SKIN = (224, 186, 152)
SKIN_DARK = (206, 164, 128)
HAIR = (46, 32, 25)
JACKET = (30, 48, 84)
PORTRAIT_BG = (178, 192, 204)
STAMP_BLUE = (31, 78, 121)
STAMP_RED = (150, 52, 48)
STAMP_PURPLE = (91, 58, 140)
STAMP_GREEN = (46, 107, 79)

# ---------------------------------------------------------------- canvas
class Canvas:
    """Simple RGB canvas backed by a bytearray."""

    def __init__(self, w, h, fill=(255, 255, 255)):
        self.w = w
        self.h = h
        self.px = bytearray([fill[0], fill[1], fill[2]] * (w * h))

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            return (self.px[i], self.px[i + 1], self.px[i + 2])
        return (255, 255, 255)

    def blend(self, x, y, color, alpha):
        """Alpha-blend color (0..255) over the pixel at x, y."""
        if alpha <= 0 or not (0 <= x < self.w and 0 <= y < self.h):
            return
        if alpha >= 255:
            self.set(x, y, color)
            return
        i = self._idx(x, y)
        a = alpha / 255.0
        self.px[i] = int(color[0] * a + self.px[i] * (1 - a))
        self.px[i + 1] = int(color[1] * a + self.px[i + 1] * (1 - a))
        self.px[i + 2] = int(color[2] * a + self.px[i + 2] * (1 - a))

    def fill_rect(self, x0, y0, x1, y1, color, alpha=255):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.blend(x, y, color, alpha)

    def rect(self, x0, y0, x1, y1, color, thick=1):
        for t in range(thick):
            self.hline(x0, y0 + t, x1, color)
            self.hline(x0, y1 - 1 - t, x1, color)
            self.vline(x0 + t, y0, y1, color)
            self.vline(x1 - 1 - t, y0, y1, color)

    def hline(self, x0, y, x1, color, alpha=255):
        if x0 > x1:
            x0, x1 = x1, x0
        for x in range(max(0, x0), min(self.w, x1)):
            self.blend(x, y, color, alpha)

    def vline(self, x, y0, y1, color, alpha=255):
        if y0 > y1:
            y0, y1 = y1, y0
        for y in range(max(0, y0), min(self.h, y1)):
            self.blend(x, y, color, alpha)

    def line(self, x0, y0, x1, y1, color, thick=1, alpha=255):
        """Bresenham line with optional thickness."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            if thick <= 1:
                self.blend(x, y, color, alpha)
            else:
                r = thick // 2
                for yy in range(y - r, y + r + 1):
                    for xx in range(x - r, x + r + 1):
                        self.blend(xx, yy, color, alpha)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def ellipse(self, cx, cy, rx, ry, color, alpha=255):
        """Filled ellipse."""
        for y in range(cy - ry, cy + ry + 1):
            t = (y - cy) / ry
            if abs(t) > 1:
                continue
            dx = int(rx * math.sqrt(max(0.0, 1 - t * t)))
            self.hline(cx - dx, y, cx + dx + 1, color, alpha)

    def circle(self, cx, cy, r, color, alpha=255):
        self.ellipse(cx, cy, r, r, color, alpha)

    def ring(self, cx, cy, r, color, thick=1, alpha=255):
        for yy in range(cy - r - 1, cy + r + 2):
            for xx in range(cx - r - 1, cx + r + 2):
                d = math.hypot(xx - cx, yy - cy)
                if abs(d - r) <= thick / 2.0 + 0.4:
                    self.blend(xx, yy, color, alpha)

    def polygon(self, points, color, alpha=255):
        """Scanline fill of a (possibly concave) polygon, even-odd rule."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hline(int(math.ceil(xs[k])), y, int(xs[k + 1]) + 1,
                           color, alpha)

    def star(self, cx, cy, r, color, alpha=255):
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.42
            pts.append((int(cx + rr * math.cos(ang)),
                        int(cy + rr * math.sin(ang))))
        self.polygon(pts, color, alpha)


def blit_rotated(dst, src, cx, cy, angle_deg, alpha=255):
    """Blit src canvas onto dst, rotated around (cx, cy) by angle_deg.

    White (255,255,255) in src is treated as transparent.
    """
    ang = math.radians(angle_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    hw, hh = src.w / 2.0, src.h / 2.0
    # bounding box of the rotated source
    corners = []
    for sx, sy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        corners.append((sx * ca - sy * sa, sx * sa + sy * ca))
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    x0 = int(cx + min(xs)) - 1
    x1 = int(cx + max(xs)) + 1
    y0 = int(cy + min(ys)) - 1
    y1 = int(cy + max(ys)) + 1
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dx, dy = x - cx, y - cy
            sx = dx * ca + dy * sa + hw
            sy = -dx * sa + dy * ca + hh
            ix, iy = int(sx), int(sy)
            if 0 <= ix < src.w and 0 <= iy < src.h:
                c = src.get(ix, iy)
                if c != (255, 255, 255):
                    dst.blend(x, y, c, alpha)


# ---------------------------------------------------------------- PNG encoder
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(canvas, path):
    w, h = canvas.w, canvas.h
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    prev = bytearray(w * 3)
    for y in range(h):
        row = bytes(canvas.px[y * w * 3:(y + 1) * w * 3])
        # pick the filter (none / sub / up) with the smallest signed sum
        best = None
        for ftype in (0, 1, 2):
            if ftype == 0:
                frow = row
            elif ftype == 1:
                buf = bytearray(w * 3)
                for i in range(w * 3):
                    left = row[i - 3] if i >= 3 else 0
                    buf[i] = (row[i] - left) & 0xFF
                frow = bytes(buf)
            else:
                buf = bytearray(w * 3)
                for i in range(w * 3):
                    buf[i] = (row[i] - prev[i]) & 0xFF
                frow = bytes(buf)
            score = sum(b if b < 128 else 256 - b for b in frow)
            if best is None or score < best[0]:
                best = (score, ftype, frow)
        raw.append(best[1])
        raw += best[2]
        prev = bytearray(row)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


# ---------------------------------------------------------------- 5x7 bitmap font
# Each glyph: 7 rows of 5 cells, '#' = ink.
def _g(rows):
    return rows

FONT = {
    "A": _g([".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"]),
    "B": _g(["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."]),
    "C": _g([".####", "#....", "#....", "#....", "#....", "#....", ".####"]),
    "D": _g(["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."]),
    "E": _g(["#####", "#....", "#....", "####.", "#....", "#....", "#####"]),
    "F": _g(["#####", "#....", "#....", "####.", "#....", "#....", "#...."]),
    "G": _g([".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."]),
    "H": _g(["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"]),
    "I": _g(["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"]),
    "J": _g(["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."]),
    "K": _g(["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"]),
    "L": _g(["#....", "#....", "#....", "#....", "#....", "#....", "#####"]),
    "M": _g(["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"]),
    "N": _g(["#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"]),
    "O": _g([".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."]),
    "P": _g(["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."]),
    "Q": _g([".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"]),
    "R": _g(["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"]),
    "S": _g([".####", "#....", "#....", ".###.", "....#", "....#", "####."]),
    "T": _g(["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."]),
    "U": _g(["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."]),
    "V": _g(["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."]),
    "W": _g(["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"]),
    "X": _g(["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"]),
    "Y": _g(["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."]),
    "Z": _g(["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"]),
    "0": _g([".###.", "#..##", "#.#.#", "#.#.#", "##..#", "#...#", ".###."]),
    "1": _g(["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."]),
    "2": _g([".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"]),
    "3": _g(["####.", "....#", "....#", ".###.", "....#", "....#", "####."]),
    "4": _g(["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."]),
    "5": _g(["#####", "#....", "####.", "....#", "....#", "#...#", ".###."]),
    "6": _g([".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."]),
    "7": _g(["#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."]),
    "8": _g([".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."]),
    "9": _g([".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."]),
    " ": _g([".....", ".....", ".....", ".....", ".....", ".....", "....."]),
    "-": _g([".....", ".....", ".....", "#####", ".....", ".....", "....."]),
    ".": _g([".....", ".....", ".....", ".....", ".....", ".##..", ".##.."]),
    ",": _g([".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."]),
    "(": _g(["...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"]),
    ")": _g(["##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."]),
    "&": _g([".###.", "#...#", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"]),
    "'": _g(["..#..", "..#..", ".#...", ".....", ".....", ".....", "....."]),
    ":": _g([".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."]),
    "<": _g(["...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."]),
    "/": _g(["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."]),
    "Ć": _g(["...##", "..#..", ".####", "#....", "#....", "#....", ".####"]),
}


def text_width(text, scale=1, spacing=None):
    if spacing is None:
        spacing = scale
    return len(text) * (5 * scale + spacing) - spacing


def draw_text(cv, x, y, text, color, scale=1, spacing=None, alpha=255):
    """Draw text with the bitmap font. Returns the x after the last char."""
    if spacing is None:
        spacing = scale
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            glyph = FONT[" "]
        for row in range(7):
            line = glyph[row]
            for col in range(5):
                if line[col] == "#":
                    cv.fill_rect(cx + col * scale, y + row * scale,
                                 cx + (col + 1) * scale,
                                 y + (row + 1) * scale, color, alpha)
        cx += 5 * scale + spacing
    return cx


def draw_text_centered(cv, cx, y, text, color, scale=1, spacing=None,
                       alpha=255):
    w = text_width(text, scale, spacing)
    return draw_text(cv, cx - w // 2, y, text, color, scale, spacing, alpha)


# ---------------------------------------------------------------- coat of arms
def draw_arms(cv, x, y, s):
    """Shield with anchor + mountains + star. (x, y) = top-left, s = scale."""
    w = 44 * s
    h = 52 * s
    # shield outline
    pts = [(x, y), (x + w, y), (x + w, y + 34 * s),
           (x + w // 2, y + h), (x, y + 34 * s)]
    cv.polygon(pts, NAVY)
    cv.polygon([(x + 2 * s, y + 2 * s), (x + w - 2 * s, y + 2 * s),
                (x + w - 2 * s, y + 32 * s),
                (x + w // 2, y + h - 3 * s), (x + 2 * s, y + 32 * s)],
               TEAL)
    # mountains (white peaks on the teal shield)
    cv.polygon([(x + 6 * s, y + 30 * s), (x + 16 * s, y + 14 * s),
                (x + 26 * s, y + 30 * s)], (245, 241, 230))
    cv.polygon([(x + 18 * s, y + 30 * s), (x + 30 * s, y + 18 * s),
                (x + 40 * s, y + 30 * s)], (245, 241, 230))
    # anchor in cream: vertical shaft, crossbar, ring, flukes
    ax = x + w // 2
    cv.line(ax, y + 8 * s, ax, y + 30 * s, (240, 236, 222), thick=max(1, s))
    cv.line(ax - 6 * s, y + 12 * s, ax + 6 * s, y + 12 * s, (240, 236, 222),
            thick=max(1, s))
    cv.ring(ax, y + 6 * s, 2 * s, (240, 236, 222), thick=max(1, s))
    cv.line(ax - 7 * s, y + 24 * s, ax - 4 * s, y + 31 * s, (240, 236, 222),
            thick=max(1, s))
    cv.line(ax + 7 * s, y + 24 * s, ax + 4 * s, y + 31 * s, (240, 236, 222),
            thick=max(1, s))
    cv.line(ax - 7 * s, y + 24 * s, ax + 7 * s, y + 24 * s, (240, 236, 222),
            thick=max(1, s))
    # star above the shield
    cv.star(ax, y - 6 * s, 5 * s, GOLD)


# ---------------------------------------------------------------- portrait
def draw_portrait(cv, x0, y0, x1, y1):
    """Flat-vector passport portrait: Mediterranean woman, dark hair in a
    bun, navy jacket, pale blue-grey background."""
    # background: soft vertical gradient, pale blue-grey top to lighter
    top = (172, 188, 202)
    bot = (198, 210, 218)
    bands = 12
    for i in range(bands):
        t = i / (bands - 1)
        c = tuple(int(top[k] + t * (bot[k] - top[k])) for k in range(3))
        yy0 = y0 + i * (y1 - y0) // bands
        yy1 = y0 + (i + 1) * (y1 - y0) // bands
        cv.fill_rect(x0, yy0, x1, yy1, c)
    cx = (x0 + x1) // 2
    # shoulders / navy jacket
    cv.polygon([(x0 + 6, y1), (x0 + 18, y1 - 62), (cx - 26, y1 - 96),
                (cx + 26, y1 - 96), (x1 - 18, y1 - 62), (x1 - 6, y1)],
               JACKET)
    # shirt V + lapels
    cv.polygon([(cx - 14, y1 - 94), (cx + 14, y1 - 94), (cx, y1 - 62)],
               (238, 236, 228))
    cv.polygon([(cx - 26, y1 - 96), (cx - 6, y1 - 70), (cx - 16, y1 - 44),
                (cx - 30, y1 - 74)], (44, 66, 108))
    cv.polygon([(cx + 26, y1 - 96), (cx + 6, y1 - 70), (cx + 16, y1 - 44),
                (cx + 30, y1 - 74)], (44, 66, 108))
    # neck
    cv.fill_rect(cx - 13, y1 - 108, cx + 13, y1 - 84, SKIN_DARK)
    # head
    cv.ellipse(cx, y0 + 74, 33, 41, SKIN)
    # ears
    cv.ellipse(cx - 33, y0 + 76, 5, 8, SKIN)
    cv.ellipse(cx + 33, y0 + 76, 5, 8, SKIN)
    # hair: cap over the top + sides, bun on top
    cv.ellipse(cx, y0 + 52, 36, 34, HAIR)
    cv.ellipse(cx, y0 + 40, 17, 15, HAIR)          # bun
    cv.ellipse(cx - 30, y0 + 82, 9, 22, HAIR)      # left fall
    cv.ellipse(cx + 30, y0 + 82, 9, 22, HAIR)      # right fall
    # face opening: skin over the lower hair cap
    cv.ellipse(cx, y0 + 80, 28, 36, SKIN)
    # fringe dip: a soft hairline over the forehead
    cv.ellipse(cx, y0 + 50, 15, 9, HAIR)
    # eyebrows
    cv.line(cx - 20, y0 + 68, cx - 8, y0 + 66, HAIR, thick=2)
    cv.line(cx + 8, y0 + 66, cx + 20, y0 + 68, HAIR, thick=2)
    # eyes
    cv.ellipse(cx - 14, y0 + 74, 4, 3, (30, 28, 26))
    cv.ellipse(cx + 14, y0 + 74, 4, 3, (30, 28, 26))
    cv.ellipse(cx - 13, y0 + 73, 1, 1, (255, 255, 255))
    cv.ellipse(cx + 15, y0 + 73, 1, 1, (255, 255, 255))
    # nose
    cv.line(cx, y0 + 76, cx - 2, y0 + 88, SKIN_DARK, thick=2)
    cv.line(cx - 2, y0 + 88, cx + 3, y0 + 89, SKIN_DARK, thick=2)
    # lips
    cv.line(cx - 7, y0 + 99, cx + 7, y0 + 99, (168, 84, 78), thick=2)
    # soft cheek shading
    cv.ellipse(cx - 20, y0 + 90, 6, 4, (226, 170, 140), alpha=110)
    cv.ellipse(cx + 20, y0 + 90, 6, 4, (226, 170, 140), alpha=110)


# ---------------------------------------------------------------- page decoration
def guilloche(cv, x0, y0, x1, y1, color, alpha=16, step=16, amp=3.0,
              wave=46.0, rng=None):
    """Fine sine-wave guilloche lines across a page."""
    y = y0 + 4
    while y < y1 - 2:
        prev = None
        for x in range(x0, x1, 2):
            yy = int(y + amp * math.sin((x - x0) * 2 * math.pi / wave))
            if prev is not None:
                cv.line(prev[0], prev[1], x, yy, color, alpha=alpha)
            prev = (x, yy)
        y += step


def watermark(cv, cx, cy, text, scale, color, alpha, angle=-28):
    """Large faint diagonal watermark, drawn via a rotated temp canvas."""
    w = text_width(text, scale) + 8
    h = 7 * scale + 8
    tmp = Canvas(w, h, fill=(255, 255, 255))
    draw_text(tmp, 4, 4, text, color, scale=scale)
    blit_rotated(cv, tmp, cx, cy, angle, alpha=alpha)


def speckle(cv, x0, y0, x1, y1, rng, n, color, alpha_lo=18, alpha_hi=60):
    """Sparse deterministic paper grain."""
    for _ in range(n):
        x = rng.randint(x0, x1 - 1)
        y = rng.randint(y0, y1 - 1)
        cv.blend(x, y, color, rng.randint(alpha_lo, alpha_hi))


# ---------------------------------------------------------------- stamps
def make_stamp(w, h, country, kind, date, color, rng, grunge=0.10):
    """A rectangular entry/exit stamp on its own white canvas."""
    c = Canvas(w, h, fill=(255, 255, 255))
    # double border
    c.rect(3, 3, w - 3, h - 3, color, thick=2)
    c.rect(7, 7, w - 7, h - 7, color, thick=1)
    # country name
    draw_text_centered(c, w // 2, 12, country, color, scale=2)
    # kind + date
    draw_text_centered(c, w // 2, 30, kind, color, scale=1)
    draw_text_centered(c, w // 2, 41, date, color, scale=2)
    # grunge: knock out random stamp pixels
    for _ in range(int(w * h * grunge)):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        if c.get(x, y) != (255, 255, 255):
            if rng.random() < 0.55:
                c.set(x, y, (255, 255, 255))
    return c


def place_stamp(cv, stamp, cx, cy, angle, alpha=205):
    blit_rotated(cv, stamp, cx, cy, angle, alpha=alpha)


# ---------------------------------------------------------------- visa sticker
def draw_visa_sticker(cv, x0, y0, x1, y1, rng):
    w, h = x1 - x0, y1 - y0
    # sticker body: deep teal with a lighter inner frame
    cv.fill_rect(x0, y0, x1, y1, (36, 84, 72))
    cv.rect(x0 + 2, y0 + 2, x1 - 2, y1 - 2, (214, 228, 216), thick=1)
    cv.rect(x0 + 6, y0 + 6, x1 - 6, y1 - 6, (140, 178, 164), thick=1)
    # small star + VELMARA crest mark
    cv.star(x0 + 24, y0 + 22, 9, GOLD)
    draw_text(cv, x0 + 40, y0 + 13, "VISA", (240, 236, 222), scale=2)
    draw_text(cv, x0 + 40, y0 + 31, "OSTARA", (214, 228, 216), scale=2)
    draw_text(cv, x0 + 12, y0 + 52, "MULTIPLE ENTRY", (240, 236, 222),
              scale=1)
    draw_text(cv, x0 + 12, y0 + 66, "VALID 03 MAY 2025 - 02 AUG 2025",
              (240, 236, 222), scale=1)
    cv.hline(x0 + 12, y0 + 84, x1 - 12, (140, 178, 164))
    draw_text(cv, x0 + 12, y0 + 90, "CONDITIONS:", (214, 228, 216), scale=1)
    draw_text(cv, x0 + 12, y0 + 102, "EMPLOYMENT PROHIBITED",
              (240, 236, 222), scale=1)
    draw_text(cv, x0 + 12, y0 + 114, "SEAFARER'S ENDORSEMENT:",
              (240, 236, 222), scale=1)
    draw_text(cv, x0 + 12, y0 + 126, "VALID FOR CREW OF VELMARAN",
              (240, 236, 222), scale=1)
    draw_text(cv, x0 + 12, y0 + 138, "MERCHANT FLEET ONLY",
              (240, 236, 222), scale=1)
    # faint guilloche inside the sticker
    for yy in range(y0 + 8, y1 - 8, 9):
        for xx in range(x0 + 8, x1 - 8, 3):
            yv = int(yy + 2 * math.sin(xx * 0.11))
            cv.blend(xx, yv, (214, 228, 216), 14)


def draw_qr(cv, x0, y0, size, rng):
    """Decorative QR-style code block (pattern only, not a real code)."""
    n = 21
    cell = size // n
    cv.fill_rect(x0, y0, x0 + size, y0 + size, (255, 255, 255))
    cv.rect(x0, y0, x0 + size, y0 + size, INK, thick=1)
    for r in range(n):
        for col in range(n):
            # finder squares in three corners
            in_finder = ((r < 7 and col < 7) or (r < 7 and col >= n - 7)
                         or (r >= n - 7 and col < 7))
            if in_finder:
                on = (r in (0, 6) or col in (0, 6) or
                      (2 <= r <= 4 and 2 <= col <= 4) or
                      (r in (0, 6) and col < 7) or (col in (0, 6)))
                if r < 7 and col >= n - 7:
                    on = (r in (0, 6) or col in (n - 7, n - 1) or
                          (2 <= r <= 4 and n - 5 <= col <= n - 3))
                if r >= n - 7 and col < 7:
                    on = (r in (n - 7, n - 1) or col in (0, 6) or
                          (n - 5 <= r <= n - 3 and 2 <= col <= 4))
                if on:
                    cv.fill_rect(x0 + col * cell, y0 + r * cell,
                                 x0 + (col + 1) * cell,
                                 y0 + (r + 1) * cell, INK)
            elif rng.random() < 0.45:
                cv.fill_rect(x0 + col * cell, y0 + r * cell,
                             x0 + (col + 1) * cell,
                             y0 + (r + 1) * cell, INK)


# ---------------------------------------------------------------- MRZ (ICAO 9303, check digits 7-3-1 verified)
MRZ_LINE1 = "P<VLMVUKOVIC<<ELENA<MARIS<<<<<<<<<<<<<<<<<<<"
MRZ_LINE2 = "VM48291739VLM9806124F3403130<<<<<<<<<<<<<<05"


def signature_scribble(cv, x0, x1, y, color):
    """A hand-signature-like wavy stroke."""
    prev = None
    for x in range(x0, x1):
        yy = int(y + 4 * math.sin(x * 0.11) + 2 * math.sin(x * 0.031))
        if prev is not None:
            cv.line(prev[0], prev[1], x, yy, color, thick=2)
        prev = (x, yy)
    # a loop at the start, a flourish at the end
    cv.ring(x0 + 14, y - 2, 7, color, thick=2)
    cv.line(x1 - 26, y - 6, x1 - 4, y + 8, color, thick=2)


def field(cv, x, y, label, value, color=INK, vscale=2):
    draw_text(cv, x, y, label, GREY, scale=1)
    draw_text(cv, x, y + 12, value, color, scale=vscale)


def build_spread():
    rng = random.Random(SEED)
    cv = Canvas(W, H, fill=TABLE)

    # --- tabletop grain + soft shadow under the spread
    speckle(cv, 0, 0, W, H, rng, 2600, (90, 84, 72), 10, 34)
    cv.fill_rect(30, 170, 1024, 900, (88, 81, 68), alpha=110)
    cv.fill_rect(26, 164, 1020, 894, (100, 93, 79), alpha=70)

    # --- the open passport: two pages
    SX0, SY0, SX1, SY1 = 14, 150, 1010, 880
    SPINE = 512
    cv.fill_rect(SX0, SY0, SX1, SY1, PAGE)
    guilloche(cv, SX0 + 8, SY0 + 8, SPINE - 8, SY1 - 8, NAVY, alpha=13)
    guilloche(cv, SPINE + 8, SY0 + 8, SX1 - 8, SY1 - 8, NAVY, alpha=13)
    watermark(cv, 263, 560, "VELMARA", 5, NAVY, 15)
    watermark(cv, 761, 560, "VELMARA", 5, NAVY, 15)
    speckle(cv, SX0, SY0, SX1, SY1, rng, 900, (120, 110, 90), 8, 26)
    # page inner borders
    cv.rect(SX0 + 7, SY0 + 7, SPINE - 7, SY1 - 7, NAVY_SOFT, thick=1)
    cv.rect(SPINE + 7, SY0 + 7, SX1 - 7, SY1 - 7, NAVY_SOFT, thick=1)
    # spine shading + centre crease
    for i in range(10):
        cv.vline(SPINE - 10 + i, SY0, SY1, (60, 54, 44), alpha=26 - i * 2)
        cv.vline(SPINE + i, SY0, SY1, (60, 54, 44), alpha=26 - i * 2)
    cv.vline(SPINE, SY0, SY1, (70, 62, 50), alpha=120)
    cv.rect(SX0, SY0, SX1, SY1, NAVY, thick=2)

    # ============================================================ LEFT: data page
    # header: arms + trilingual title
    draw_arms(cv, 52, 172, 1)
    draw_text_centered(cv, 300, 172, "REPUBLIK VELMARA", NAVY, scale=2)
    draw_text_centered(cv, 300, 194, "REPUBLIC OF VELMARA", NAVY_SOFT,
                       scale=1)
    draw_text_centered(cv, 300, 206, "REPUBLIQUE DE VELMARA", NAVY_SOFT,
                       scale=1)
    draw_text_centered(cv, 300, 222, "MARE ET MONTES", GOLD, scale=1)
    draw_text_centered(cv, 300, 238, "PASSPORT", NAVY, scale=3)
    cv.hline(34, 266, 492, NAVY, alpha=200)

    # portrait, framed
    cv.fill_rect(34, 276, 176, 460, PORTRAIT_BG)
    draw_portrait(cv, 36, 278, 174, 458)
    cv.rect(34, 276, 176, 460, NAVY, thick=2)
    cv.rect(37, 279, 173, 457, NAVY_SOFT, thick=1)

    # data fields
    FX = 192
    field(cv, FX, 276, "TYPE", "P")
    field(cv, FX + 58, 276, "CODE", "VLM")
    field(cv, FX + 118, 276, "PASSPORT NO.", "VM 4829173")
    field(cv, FX, 316, "SURNAME", "VUKOVIĆ")
    field(cv, FX, 356, "GIVEN NAMES", "ELENA MARIS")
    field(cv, FX, 396, "NATIONALITY", "VELMARAN")
    field(cv, FX + 190, 396, "SEX", "F")
    field(cv, FX, 436, "DATE OF BIRTH", "12 JUN 1998")
    field(cv, FX + 148, 436, "PLACE OF BIRTH", "PORTO VELMARA")
    field(cv, FX, 476, "DATE OF ISSUE", "14 MAR 2024")
    field(cv, FX + 148, 476, "DATE OF EXPIRY", "13 MAR 2034")
    field(cv, FX, 516, "AUTHORITY", "PORTO VELMARA")
    # signature
    draw_text(cv, FX, 556, "HOLDER'S SIGNATURE", GREY, scale=1)
    signature_scribble(cv, FX, FX + 220, 578, NAVY)
    cv.hline(FX, 592, FX + 220, NAVY_SOFT, alpha=160)

    # notes block
    cv.hline(34, 616, 492, NAVY, alpha=160)
    draw_text(cv, 34, 624, "NOTES", GREY, scale=1)
    notes = [
        "THIS PASSPORT REMAINS THE PROPERTY OF THE",
        "REPUBLIC OF VELMARA.",
        "HOLDER IS A REGISTERED SEAFARER OF THE",
        "VELMARAN MERCHANT FLEET.",
        "LOST OR STOLEN PASSPORTS MUST BE REPORTED",
        "TO THE NEAREST VELMARAN CONSULATE OR",
        "HARBOUR MASTER.",
    ]
    for i, line in enumerate(notes):
        draw_text(cv, 34, 638 + i * 12, line, INK, scale=1)
    cv.hline(34, 736, 492, NAVY, alpha=120)
    cv.star(263, 756, 7, GOLD)
    draw_text_centered(cv, 263, 770, "MARE ET MONTES", GOLD, scale=1)

    # machine-readable zone
    cv.fill_rect(20, 798, 504, 856, (232, 229, 220))
    draw_text(cv, 20, 806, MRZ_LINE1, INK, scale=2, spacing=1)
    draw_text(cv, 20, 826, MRZ_LINE2, INK, scale=2, spacing=1)

    # ============================================================ RIGHT: visa page
    draw_text(cv, 540, 172, "VISAS", NAVY, scale=3)
    draw_text(cv, 540, 198, "VISA - VISAS", NAVY_SOFT, scale=1)
    draw_text(cv, 880, 178, "VM 4829173", NAVY, scale=2)
    cv.hline(540, 214, 990, NAVY, alpha=200)

    # Ostara visa sticker (top-left) + Soravia stamps (top-right)
    draw_visa_sticker(cv, 540, 228, 775, 384, rng)
    s = make_stamp(200, 64, "SORAVIA", "ENTRY", "02 JUN 2024",
                   STAMP_BLUE, rng)
    place_stamp(cv, s, 890, 260, -5)
    s = make_stamp(200, 64, "SORAVIA", "EXIT", "09 JUN 2024",
                   STAMP_BLUE, rng)
    place_stamp(cv, s, 890, 340, 6)

    # stamp grid: two columns, entry/exit pairs in chronological order
    rows = [
        ("TALMERE", "ENTRY", "18 SEP 2024", STAMP_PURPLE, -4),
        ("TALMERE", "EXIT", "25 SEP 2024", STAMP_PURPLE, 5),
        ("KOSTRIN", "ENTRY", "11 JAN 2025", STAMP_RED, 6),
        ("KOSTRIN", "EXIT", "19 JAN 2025", STAMP_RED, -6),
        ("OSTARA", "ENTRY", "07 MAY 2025", STAMP_GREEN, -5),
        ("OSTARA", "EXIT", "21 MAY 2025", STAMP_GREEN, 4),
    ]
    centres = [(647, 424), (883, 424), (647, 498), (883, 498),
               (647, 572), (883, 572)]
    for (country, kind, date, color, ang), (cx, cy) in zip(rows, centres):
        st = make_stamp(215, 64, country, kind, date, color, rng)
        place_stamp(cv, st, cx, cy, ang)

    # harbour-tax fee stamp (the paperwork detail that reveals Velmara)
    st = make_stamp(215, 64, "HARBOUR TAX PAID", "12,00 VMD",
                    "PORTO VELMARA", BURGUNDY, rng)
    place_stamp(cv, st, 647, 646, -7)

    # decorative code block + number, bottom-right
    draw_qr(cv, 800, 604, 84, rng)
    draw_text(cv, 892, 620, "VM 4829173", INK, scale=1)
    draw_text(cv, 892, 636, "PORTO", INK, scale=1)
    draw_text(cv, 892, 648, "VELMARA", INK, scale=1)

    # home arrival stamp: back in Porto Velmara the day Ostara was left
    st = make_stamp(215, 64, "PORTO VELMARA", "ARRIVAL", "21 MAY 2025",
                    NAVY, rng)
    place_stamp(cv, st, 883, 790, -4)

    # small print at the foot of the visa page
    draw_text(cv, 540, 716, "HOLDER MUST PRESENT THIS PASSPORT AT",
              GREY, scale=1)
    draw_text(cv, 540, 730, "HARBOUR CONTROL ON DEPARTURE.", GREY, scale=1)
    draw_text(cv, 540, 748, "PAGES 12-13", GREY, scale=1)
    draw_text(cv, 920, 830, "VM 4829173", GREY, scale=1)

    return cv


def main():
    out = os.environ.get("OUTPUT_PATH", "/output/entry.png")
    cv = build_spread()
    size = write_png(cv, out)
    print(f"wrote {out}: {cv.w}x{cv.h}, {size} bytes")


if __name__ == "__main__":
    main()
