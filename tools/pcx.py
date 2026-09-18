"""
pcx.py - write 8-bit paletted PCX files that UT99 can import.

UT99 imports only 8-bit indexed PCX or BMP; it does NOT quantise RGB for you,
so the file must already be paletted. Dimensions must be powers of two, and
anything above 256x256 needs mipmaps or the game crashes - so everything here
is authored at 256x256 or smaller.

Palette index 0 is the masked/transparent colour in UE1. We never emit index 0
for opaque pixels, which keeps every texture usable with or without masking.

Generating textures rather than sourcing them sidesteps the licensing question
entirely: stock UT99 has no ceiling tiles, whiteboards or office carpet, and
the CC0 libraries ship 1K+ photos that would need downscaling and quantising
anyway.
"""

import os
import struct


class Texture:
    """An indexed image: a palette plus one byte per pixel."""

    def __init__(self, width=256, height=256):
        if width & (width - 1) or height & (height - 1):
            raise ValueError("UE1 textures must be power-of-two sized")
        self.w = width
        self.h = height
        self.pixels = bytearray(width * height)
        # Index 0 is reserved as UE1's transparent colour; start real colours
        # at 1 so nothing opaque ever lands on it.
        self.palette = [(0, 0, 0)] * 256
        self._next = 1

    def color(self, r, g, b):
        """Add a colour, returning its palette index (deduplicated)."""
        rgb = (r, g, b)
        for i in range(1, self._next):
            if self.palette[i] == rgb:
                return i
        if self._next > 255:
            raise ValueError("palette full (256 colours)")
        idx = self._next
        self.palette[idx] = rgb
        self._next += 1
        return idx

    def fill(self, idx):
        self.pixels = bytearray([idx]) * (self.w * self.h)

    def put(self, x, y, idx):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.pixels[y * self.w + x] = idx

    def rect(self, x0, y0, x1, y1, idx):
        for y in range(max(0, y0), min(self.h, y1)):
            row = y * self.w
            for x in range(max(0, x0), min(self.w, x1)):
                self.pixels[row + x] = idx

    def hline(self, y, x0, x1, idx):
        self.rect(x0, y, x1, y + 1, idx)

    def vline(self, x, y0, y1, idx):
        self.rect(x, y0, x + 1, y1, idx)

    def noise(self, indices, seed=1234, amount=1.0):
        """Sprinkle colours over the image - breaks up flat fills so a big
        wall does not read as a single plastic sheet."""
        state = seed
        n = len(indices)
        for i in range(len(self.pixels)):
            state = (1103515245 * state + 12345) & 0x7FFFFFFF
            if (state >> 16) % 1000 < amount * 1000:
                self.pixels[i] = indices[(state >> 8) % n]

    def save(self, path):
        """Write a 256-colour PCX (version 5, RLE, 1 plane of 8 bits)."""
        hdr = struct.pack(
            "<BBBBHHHHHH48sBBHHHH54s",
            0x0A,            # manufacturer
            5,               # version 5 = 8-bit with a 256-colour palette
            1,               # RLE encoding
            8,               # bits per pixel per plane
            0, 0,            # xmin, ymin
            self.w - 1, self.h - 1,
            72, 72,          # dpi
            b"\0" * 48,      # 16-colour EGA palette, unused
            0,               # reserved
            1,               # number of colour planes
            self.w,          # bytes per line
            1,               # palette type: colour
            0, 0,            # screen size
            b"\0" * 54)

        body = bytearray()
        for y in range(self.h):
            row = self.pixels[y * self.w:(y + 1) * self.w]
            x = 0
            while x < len(row):
                run = 1
                while (x + run < len(row) and row[x + run] == row[x]
                       and run < 63):
                    run += 1
                val = row[x]
                # A run, or any byte with the top two bits set, needs a count.
                if run > 1 or val >= 0xC0:
                    body.append(0xC0 | run)
                body.append(val)
                x += run

        with open(path, "wb") as fh:
            fh.write(hdr)
            fh.write(bytes(body))
            fh.write(b"\x0C")                     # palette marker
            for r, g, b in self.palette:
                fh.write(bytes((r, g, b)))
        return path


# ---------------------------------------------------------------------------
# office texture generators
# ---------------------------------------------------------------------------

def ceiling_tile(size=256, tiles=4):
    """Suspended ceiling: a grid of light panels in metal runners."""
    t = Texture(size, size)
    tile = t.color(140, 138, 130)
    speck = t.color(128, 126, 120)
    speck2 = t.color(152, 150, 142)
    runner = t.color(150, 150, 148)
    shadow = t.color(120, 120, 118)
    t.fill(tile)
    t.noise([speck, speck2], seed=7, amount=0.30)
    step = size // tiles
    for i in range(tiles):
        p = i * step
        t.rect(p, 0, p + 3, size, runner)
        t.rect(0, p, size, p + 3, runner)
        t.rect(p + 3, 0, p + 4, size, shadow)
        t.rect(0, p + 3, size, p + 4, shadow)
    return t


def carpet(size=256, r=64, g=70, b=84):
    """Flecked commercial carpet tile - the sound of a thousand meetings."""
    t = Texture(size, size)
    base = t.color(r, g, b)
    dark = t.color(max(0, r - 14), max(0, g - 14), max(0, b - 14))
    light = t.color(min(255, r + 16), min(255, g + 16), min(255, b + 16))
    fleck = t.color(min(255, r + 40), min(255, g + 38), min(255, b + 30))
    t.fill(base)
    t.noise([dark, light], seed=99, amount=0.55)
    t.noise([fleck], seed=451, amount=0.04)
    # Faint seams every half tile so the floor reads as laid squares.
    for p in (0, size // 2):
        t.rect(p, 0, p + 1, size, dark)
        t.rect(0, p, size, p + 1, dark)
    return t


def cubicle_panel(size=256):
    """Fabric-covered partition with a plastic top rail."""
    t = Texture(size, size)
    fabric = t.color(96, 100, 92)
    d = t.color(84, 88, 80)
    l = t.color(110, 114, 104)
    rail = t.color(80, 80, 84)
    rail_hi = t.color(120, 120, 124)
    t.fill(fabric)
    t.noise([d, l], seed=31, amount=0.6)
    # Woven look: alternating vertical and horizontal threads.
    for x in range(0, size, 2):
        for y in range(0, size, 4):
            t.put(x, y, d)
            t.put(x + 1, y + 2, l)
    t.rect(0, 0, size, 10, rail)
    t.rect(0, 8, size, 10, rail_hi)
    return t


def whiteboard(size=256):
    """A whiteboard with an aluminium frame and a ghost of old marker."""
    t = Texture(size, size)
    board = t.color(246, 246, 244)
    frame = t.color(176, 178, 182)
    frame_d = t.color(138, 140, 144)
    tray = t.color(158, 160, 164)
    ghost = t.color(226, 230, 236)
    ghost2 = t.color(232, 228, 236)
    t.fill(board)
    for y in range(40, 90, 14):          # faint wiped-off writing
        t.hline(y, 30, 150 + (y % 40), ghost)
    for y in range(120, 170, 16):
        t.hline(y, 40, 190 - (y % 50), ghost2)
    t.rect(0, 0, size, 8, frame)
    t.rect(0, size - 18, size, size, frame)
    t.rect(0, 0, 8, size, frame)
    t.rect(size - 8, 0, size, size, frame)
    t.rect(0, size - 18, size, size - 14, frame_d)
    t.rect(10, size - 14, size - 10, size - 6, tray)
    return t


def office_wall(size=256, r=104, g=100, b=92):
    """Painted drywall above a darker dado rail - standard corporate two-tone."""
    t = Texture(size, size)
    upper = t.color(r, g, b)
    upper_d = t.color(r - 10, g - 10, b - 10)
    lower = t.color(122, 126, 132)
    lower_d = t.color(112, 116, 122)
    rail = t.color(168, 164, 156)
    t.fill(upper)
    t.noise([upper_d], seed=17, amount=0.25)
    t.rect(0, 176, size, size, lower)
    t.noise_region = None
    for y in range(176, size, 3):
        t.hline(y, 0, size, lower if (y // 3) % 2 else lower_d)
    t.rect(0, 168, size, 176, rail)
    return t


def elevator_door(size=256):
    """Brushed steel lift doors with a centre seam."""
    t = Texture(size, size)
    steel = t.color(150, 152, 158)
    dark = t.color(128, 130, 136)
    light = t.color(176, 178, 184)
    seam = t.color(70, 70, 76)
    t.fill(steel)
    for x in range(size):                # vertical brushing
        if x % 3 == 0:
            t.vline(x, 0, size, dark)
        elif x % 7 == 0:
            t.vline(x, 0, size, light)
    t.rect(size // 2 - 2, 0, size // 2 + 2, size, seam)
    t.rect(0, 0, size, 6, dark)
    t.rect(0, size - 6, size, size, dark)
    return t


def ceiling_light(size=128):
    """A lit fluorescent panel. UE1 has no bloom, so the glow is baked in."""
    t = Texture(size, size)
    glow = t.color(255, 255, 246)
    mid = t.color(238, 240, 228)
    edge = t.color(196, 198, 190)
    frame = t.color(130, 132, 134)
    t.fill(glow)
    t.rect(0, 0, size, 6, frame)
    t.rect(0, size - 6, size, size, frame)
    t.rect(0, 0, 6, size, frame)
    t.rect(size - 6, 0, size, size, frame)
    for i in range(3):                   # diffuser louvres
        x = 6 + i * (size - 12) // 3
        t.rect(x, 6, x + 3, size - 6, edge)
    t.rect(6, 6, size - 6, 10, mid)
    return t


GENERATORS = {
    "OfCeiling": ceiling_tile,
    "OfCarpet": carpet,
    "OfCarpetBlue": lambda: carpet(r=44, g=58, b=96),
    "OfCarpetGrey": lambda: carpet(r=78, g=78, b=76),
    "OfCubicle": cubicle_panel,
    "OfWhiteboard": whiteboard,
    "OfWall": office_wall,
    "OfWallBlue": lambda: office_wall(r=78, g=88, b=104),
    "OfElevator": elevator_door,
    "OfLight": ceiling_light,
}


def generate_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for name, fn in GENERATORS.items():
        made.append(fn().save(os.path.join(out_dir, f"{name}.pcx")))
    return made


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "work/textures"
    for p in generate_all(out):
        print(p, os.path.getsize(p), "bytes")
