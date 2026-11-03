"""The boot splash: "Public" in the instrument's lettering, filling the 128 x 64 screen.

    python boot_public.py [font.otf]      writes boot_public.png beside this file

The face is the boards' (elec/silk.py SILK_FACE): Rennie Mackintosh Public Steel Guitar Bold,
licensed, installed, and not in the repository. The PNG is not committed either (.gitignore):
run this on a machine that has the face.

STRICT ON/OFF, NOT GREY (user, 2026-11-03): the SSD1322 shows 16 greys, and an antialiased
render was set beside this one; the user picked on/off. A pixel is lit when half or more of it
is ink, measured on a 16x supersample. The word is as large as fits inside a 2 px border:
width bound, 124 x 35 of the 128 x 64.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = r"C:/Windows/Fonts/RennieMackintoshPublicSteelGuitar-Bold.otf"
TEXT = "Public"
W, H = 128, 64            # NHD-2.7-12864WDW3
S = 16                    # supersampling per screen pixel
MARGIN = 2


def render(font_path=FONT) -> Image.Image:
    lo, hi = 10, 2000
    while hi - lo > 1:                     # the largest size whose ink fits
        mid = (lo + hi) // 2
        l, t, r, b = ImageFont.truetype(font_path, mid).getbbox(TEXT)
        if r - l <= (W - 2 * MARGIN) * S and b - t <= (H - 2 * MARGIN) * S:
            lo = mid
        else:
            hi = mid
    f = ImageFont.truetype(font_path, lo)
    l, t, r, b = f.getbbox(TEXT)
    big = Image.new("L", (W * S, H * S), 0)
    ImageDraw.Draw(big).text(((W * S - (r - l)) / 2 - l, (H * S - (b - t)) / 2 - t), TEXT, font=f, fill=255)
    return big.reduce(S).point(lambda v: 255 if v >= 128 else 0).convert("1")


if __name__ == "__main__":
    img = render(sys.argv[1] if len(sys.argv) > 1 else FONT)
    img.save(os.path.join(HERE, "boot_public.png"))
    print("boot_public.png: %d x %d, %d pixels lit" % (W, H, img.histogram()[255]))
