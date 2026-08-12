"""
Animation 1 - "AOL Connecting" for DC34 badge (128x128, 1-bit), rebuilt from the
authentic Tenor AOL sign-on gif: America Online logo (running-man pyramid) up top,
the real AOL running man dashing across with speed lines, and the classic
Dialing... -> Connecting... -> Connected! status with a filling progress bar.
White = lit pixel on the OLED.
"""
import os, math
from PIL import Image, ImageDraw, ImageFont

W = H = 128
FPS = 15
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)

# Retro MS-Sans look on Windows; graceful fallbacks on Linux/macOS so this runs
# anywhere (Windows gives the most authentic look).
_REG_FONTS = ("C:/Windows/Fonts/micross.ttf", "C:/Windows/Fonts/arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
              "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf")
_BLD_FONTS = ("C:/Windows/Fonts/arialbd.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
              "/Library/Fonts/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")

def font(sz, bold=False):
    for p in (_BLD_FONTS if bold else _REG_FONTS):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

F_HDR  = font(9, bold=True)
F_STAT = font(12, bold=True)
F_TINY = font(8)

_MAN = Image.open(os.path.join(HERE, "src_img", "man_silhouette.png")).convert("L")
def man(h, flip=False):
    r = h / _MAN.height
    m = _MAN.resize((max(1, int(_MAN.width * r)), h), Image.LANCZOS).point(lambda v: 255 if v >= 110 else 0)
    return m.transpose(Image.FLIP_LEFT_RIGHT) if flip else m

def put_man(frame, m, x, y):
    frame.paste(Image.new("L", m.size, 255), (int(x), int(y)), m)

def ctext(d, cx, y, s, f):
    d.text((cx - d.textlength(s, font=f) / 2, y), s, font=f, fill=255)

def logo(d, frame):
    # AOL "running man in a pyramid" mark, top-center, + AMERICA ONLINE
    cx = W // 2
    d.polygon([(cx, 4), (cx - 20, 34), (cx + 20, 34)], outline=255)
    sm = man(18)
    put_man(frame, sm, cx - sm.width // 2, 15)
    ctext(d, cx, 37, "AMERICA ONLINE", F_HDR)

def speedlines(d, x, y, n, length):
    for i in range(n):
        yy = y + i * 5 - (n - 1) * 2
        d.line([(x - length, yy), (x, yy)], fill=255, width=1)

def progress(d, frac):
    x0, x1, y = 12, W - 12, 118
    d.rectangle([x0, y, x1, y + 6], outline=255)
    fw = int((x1 - x0 - 2) * max(0.0, min(1.0, frac)))
    if fw > 0:
        d.rectangle([x0 + 1, y + 1, x0 + 1 + fw, y + 5], fill=255)

frames = []
def add(im): frames.append(im)

MH = 34                       # running-man height in the action band
band_y = 74                   # vertical center of the run band
x_left, x_right = 8, W - 8 - int(_MAN.width * MH / _MAN.height)
run_span = x_right - x_left   # the man runs left->right ACROSS Dialing + Connecting as ONE path
fi = 0                        # global frame counter -> one continuous bob (no hitch at the seam)

# The runner's horizontal position is a SINGLE continuous path over the whole run so Dialing
# hands off to Connecting seamlessly: Dialing covers 0..30% of the run, Connecting 30..90%.
# (The old code scaled Dialing by W*0.30 but Connecting by run_span*0.30 — that mismatch made
#  the man jump BACKWARDS ~9px the instant "Connecting" appeared. That was the stutter.)

# ---- Phase A: Dialing (man jogs in from the left, first 30% of the run) ----
NA = 22
for i in range(NA):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    logo(d, im)
    x = x_left + run_span * (0.30 * (i / NA))       # 0 -> ~0.286, flows straight into Phase B
    bob = int(2.5 * math.sin(fi * 0.9)); fi += 1
    put_man(im, man(MH), x, band_y - MH // 2 + bob)
    speedlines(d, x, band_y, 2, 6 + (i % 3) * 3)
    ctext(d, W // 2, 92, "Dialing" + "." * (1 + (i // 2) % 3), F_STAT)
    progress(d, 0.05 + 0.25 * (i / NA))             # 0.05 -> ~0.29
    add(im)

# ---- Phase B: Connecting (man sprints across, 30..90% of the run, big speed lines) ----
NB = 26
for i in range(NB):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    logo(d, im)
    x = x_left + run_span * (0.30 + 0.60 * (i / NB))  # picks up exactly where Dialing ended
    bob = int(2.5 * math.sin(fi * 0.9)); fi += 1
    speedlines(d, x, band_y, 3, 14 + int(8 * abs(math.sin(i * 0.8))))
    put_man(im, man(MH), x, band_y - MH // 2 + bob)
    ctext(d, W // 2, 92, "Connecting" + "." * (1 + (i // 2) % 3), F_STAT)
    progress(d, 0.30 + 0.58 * (i / NB))             # 0.30 -> ~0.86, continuous with Dialing
    add(im)

# ---- Phase C: Connected! (man lands right, flashes, checkmark) ----
NC = 16
for i in range(NC):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    logo(d, im)
    put_man(im, man(MH), x_right, band_y - MH // 2)
    if i % 4 < 3:
        ctext(d, W // 2, 90, "Connected!", F_STAT)
    # checkmark by the man
    cxp, cyp = x_right - 10, band_y - 14
    d.line([cxp - 5, cyp, cxp - 1, cyp + 4], fill=255, width=2)
    d.line([cxp - 1, cyp + 4, cxp + 6, cyp - 5], fill=255, width=2)
    progress(d, 1.0)
    add(im)

# ---------------- emit ----------------
def to1(im): return im.point(lambda v: 255 if v >= 128 else 0, mode="1")

gif = [to1(f).convert("P").resize((W * 4, H * 4), Image.NEAREST) for f in frames]
gif[0].save(os.path.join(OUT, "aol_connect_preview.gif"), save_all=True,
            append_images=gif[1:], duration=1000 // FPS, loop=0)

keys = [3, NA - 1, NA + 8, NA + NB - 2, len(frames) - 10, len(frames) - 1]
sheet = Image.new("L", (W * 3, H * 2), 60)
for i, k in enumerate(keys):
    sheet.paste(to1(frames[k]).convert("L"), ((i % 3) * W, (i // 3) * H))
sheet.save(os.path.join(OUT, "aol_connect_sheet.png"))

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

with open(os.path.join(OUT, "aol_connect_frames.bin"), "wb") as fh:
    for f in frames: fh.write(pack(to1(f)))

print(f"AOL connect: {len(frames)} frames ({len(frames)/FPS:.1f}s), {len(frames)*2048//1024} KB")
