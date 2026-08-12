"""
Animation 2 - "Running Man" hero for DC34 badge (128x128, 1-bit), from the R29
AOL running-man image. Big glowing running-man silhouette bobbing/running in place
while the dotted blue speed-trail (like the source art) streams past behind him.
White = lit pixel on the OLED.
"""
import os, math
from PIL import Image, ImageDraw

W = H = 128
FPS = 15
NFRAMES = 30                  # one seamless loop
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)

_MAN = Image.open(os.path.join(HERE, "src_img", "man_silhouette.png")).convert("L")
def man(h):
    r = h / _MAN.height
    return _MAN.resize((max(1, int(_MAN.width * r)), h), Image.LANCZOS).point(lambda v: 255 if v >= 110 else 0)

# a fixed field of "trail" dots (x,y,radius) that scrolls right->left and wraps
def dot_field():
    dots = []
    rng = 1234567
    def rnd():
        nonlocal rng
        rng = (rng * 1103515245 + 12345) & 0x7fffffff
        return rng / 0x7fffffff
    for _ in range(150):
        x = rnd() * (W + 40)
        # concentrate dots in two diagonal bands (the source's swoosh)
        band = 40 + 55 * rnd()
        y = band + 24 * math.sin(x * 0.05)
        r = 1 if rnd() < 0.6 else 2
        dots.append((x, y, r))
    return dots

DOTS = dot_field()

frames = []
MH = 96                       # big hero man
mimg = man(MH)
mx = (W - mimg.width) // 2

for i in range(NFRAMES):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    t = i / NFRAMES
    # scrolling dotted speed-trail behind the man
    shift = (t * (W + 40))
    for (x, y, r) in DOTS:
        xx = (x - shift) % (W + 40) - 20
        d.ellipse([xx - r, y - r, xx + r, y + r], fill=255)
    # a couple of long speed streaks
    for k in range(3):
        yy = 46 + k * 22 + int(3 * math.sin(i * 0.7 + k))
        x2 = (W - ((i * 8 + k * 40) % (W + 30)))
        d.line([(x2, yy), (x2 - 22, yy)], fill=255, width=1)
    # the hero, bobbing as if mid-stride, slight forward lean scale
    bob = int(4 * math.sin(i / NFRAMES * 2 * math.pi))
    scale = 1.0 + 0.03 * math.sin(i / NFRAMES * 2 * math.pi)
    mh = int(MH * scale); mm = man(mh)
    im.paste(Image.new("L", mm.size, 255), ((W - mm.width) // 2, 18 + bob), mm)
    frames.append(im)

def to1(im): return im.point(lambda v: 255 if v >= 128 else 0, mode="1")

gif = [to1(f).convert("P").resize((W * 4, H * 4), Image.NEAREST) for f in frames]
gif[0].save(os.path.join(OUT, "running_man_preview.gif"), save_all=True,
            append_images=gif[1:], duration=1000 // FPS, loop=0)

sheet = Image.new("L", (W * 4, H), 60)
for i, k in enumerate([0, 7, 15, 22]):
    sheet.paste(to1(frames[k]).convert("L"), (i * W, 0))
sheet.save(os.path.join(OUT, "running_man_sheet.png"))

def pack(im1):
    im = im1.transpose(Image.FLIP_LEFT_RIGHT)
    px = list(im.getdata()); words = []; cur = cnt = 0
    for v in px:
        cur |= ((0 if v else 1) << (31 - cnt)); cnt += 1
        if cnt == 32: words.append(cur); cur = cnt = 0
    if cnt: words.append(cur)
    out = bytearray()
    for r in range(len(words) // 4):
        for w in (words[r*4+3], words[r*4+2], words[r*4+1], words[r*4+0]):
            out += w.to_bytes(4, "little")
    return out

with open(os.path.join(OUT, "running_man_frames.bin"), "wb") as fh:
    for f in frames: fh.write(pack(to1(f)))

print(f"Running man: {len(frames)} frames ({len(frames)/FPS:.1f}s loop), {len(frames)*2048//1024} KB")
