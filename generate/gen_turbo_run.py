"""
Animation 4 - "Turbo Run" for DC34 badge (128x128, 1-bit).
The AOL running man BLASTS across the screen with a comic-book motion trail:
the lead man is solid/glowing, trailed by fading ghost-echoes (outline only),
converging speed lines, and a dotted burst. He exits right, loops in from left.
White = lit pixel on the OLED.
"""
import os, math
from PIL import Image, ImageDraw, ImageFilter

W = H = 128
FPS = 15
NFRAMES = 30
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)

_MAN = Image.open(os.path.join(HERE, "src_img", "man_silhouette.png")).convert("L")
MH = 58
_solid = _MAN.resize((int(_MAN.width * MH / _MAN.height), MH), Image.LANCZOS).point(lambda v: 255 if v >= 110 else 0)
# outline = solid minus its erosion
_erode = _solid.filter(ImageFilter.MinFilter(5))
import numpy as np
_out = ((np.asarray(_solid) > 128) & ~(np.asarray(_erode) > 128))
_outline = Image.fromarray((_out * 255).astype("uint8"), "L")
MW = _solid.width

def put(frame, img, x, y):
    frame.paste(Image.new("L", img.size, 255), (int(x), int(y)), img)

frames = []
Y = (H - MH) // 2 + 4
span = W + MW + 30
for i in range(NFRAMES):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    lead = -MW + span * (i / NFRAMES)          # lead man x, wraps across
    bob = int(3 * math.sin(i / NFRAMES * 2 * math.pi * 2))
    # converging speed lines from the left edge toward the man
    for k in range(5):
        yy = Y + 6 + k * 11
        x2 = lead - 6
        d.line([(max(0, x2 - 40 - (i % 4) * 4), yy), (x2, yy)], fill=255, width=1)
    # dotted burst behind
    for k in range(14):
        dx = (k * 37 + i * 9) % (int(lead) + 40) if lead > 0 else 0
        d.point((lead - 8 - dx, Y + (k * 13) % MH), fill=255)
    # ghost echoes (outline only), fading back
    for g in range(4, 0, -1):
        gx = lead - g * 12
        if gx < -MW: continue
        if g % 2 == 0:   # thin the trail: skip alternate for a sparser look
            put(im, _outline, gx, Y + int(bob * 0.5))
        else:
            put(im, _outline, gx, Y + int(bob * 0.7))
    # lead man, solid + glowing
    put(im, _solid, lead, Y + bob)
    frames.append(im)

# ---- emit ----
def to1(im): return im.point(lambda v: 255 if v >= 128 else 0, mode="1")
gif = [to1(f).convert("P").resize((W * 4, H * 4), Image.NEAREST) for f in frames]
gif[0].save(os.path.join(OUT, "turbo_run_preview.gif"), save_all=True,
            append_images=gif[1:], duration=1000 // FPS, loop=0)
sheet = Image.new("L", (W * 4, H), 60)
for i, k in enumerate([6, 13, 20, 27]):
    sheet.paste(to1(frames[k]).convert("L"), (i * W, 0))
sheet.save(os.path.join(OUT, "turbo_run_sheet.png"))
def pack(im1):
    im = im1.transpose(Image.FLIP_LEFT_RIGHT); px = list(im.getdata())
    words = []; cur = cnt = 0
    for v in px:
        cur |= ((0 if v else 1) << (31 - cnt)); cnt += 1
        if cnt == 32: words.append(cur); cur = cnt = 0
    if cnt: words.append(cur)
    out = bytearray()
    for r in range(len(words) // 4):
        for w in (words[r*4+3], words[r*4+2], words[r*4+1], words[r*4+0]):
            out += w.to_bytes(4, "little")
    return out
with open(os.path.join(OUT, "turbo_run_frames.bin"), "wb") as fh:
    for f in frames: fh.write(pack(to1(f)))
print(f"Turbo Run: {len(frames)} frames ({len(frames)/FPS:.1f}s loop), {len(frames)*2048//1024} KB")
