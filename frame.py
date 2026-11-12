from pathlib import Path
import zipfile
from PIL import Image, ImageOps, ImageFilter

# ---------- settings ----------
# "auto"  : whole photo is shown (blurred sides) unless the photo is already wide
# "crop"  : every photo is cropped to fill the gap completely
MODE = "auto"
# ------------------------------

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
PHOTOS = Path("photos")
OUT = Path("framed")
OUT.mkdir(exist_ok=True)

# 1. unzip any zip file in the main folder into photos/
for z in Path(".").glob("*.zip"):
    with zipfile.ZipFile(z) as zf:
        zf.extractall(PHOTOS)

# 2. find the frame file (any picture with "frame" in its name, anywhere in the repo)
SKIP = {"photos", "framed", ".git", ".github"}
candidates = []
for p in Path(".").rglob("*"):
    if p.suffix.lower() in IMG_EXT and "frame" in p.name.lower() and not (set(p.parts[:-1]) & SKIP):
        candidates.append(p)
candidates.sort(key=lambda p: len(p.parts))
if not candidates:
    print("Files in the main folder:", sorted(x.name for x in Path(".").iterdir()))
    raise SystemExit("Frame image not found: upload the frame picture with the word 'frame' in its name")
frame_path = candidates[0]
print("Using frame:", frame_path)
frame = Image.open(frame_path).convert("RGB")
W, H = frame.size

# 3. find the grey gap: same colour as the centre of the picture, grown outwards
cx, cy = W // 2, H // 2
base = frame.getpixel((cx, cy))
def same(px):
    return sum(abs(px[i] - base[i]) for i in range(3)) <= 6
x1 = cx
while x1 > 0 and same(frame.getpixel((x1 - 1, cy))): x1 -= 1
x2 = cx
while x2 < W - 1 and same(frame.getpixel((x2 + 1, cy))): x2 += 1
y1 = cy
while y1 > 0 and same(frame.getpixel((cx, y1 - 1))): y1 -= 1
y2 = cy
while y2 < H - 1 and same(frame.getpixel((cx, y2 + 1))): y2 += 1
x2 += 1
y2 += 1
w, h = x2 - x1, y2 - y1
print("Gap found:", x1, y1, x2, y2, "size", w, "x", h)

def make_tile(photo):
    ratio = photo.width / photo.height
    gap_ratio = w / h
    if MODE == "crop" or ratio >= gap_ratio * 0.85:
        return ImageOps.fit(photo, (w, h), centering=(0.5, 0.3))
    # whole photo, centred, on a blurred copy of itself
    bg = ImageOps.fit(photo, (w, h)).filter(ImageFilter.GaussianBlur(25))
    fg = ImageOps.contain(photo, (w, h))
    bg.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    return bg

count = 0
for p in sorted(PHOTOS.rglob("*")):
    if p.suffix.lower() not in IMG_EXT or p.name.startswith(".") or "__MACOSX" in p.parts:
        continue
    try:
        photo = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
    except Exception as e:
        print("Skipped", p.name, e)
        continue
    canvas = frame.copy()
    canvas.paste(make_tile(photo), (x1, y1))
    canvas.save(OUT / (p.stem + ".jpg"), quality=95)
    count += 1
print("Framed", count, "photos")
