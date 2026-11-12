from pathlib import Path
import re, subprocess, sys, zipfile
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ---------- settings ----------
CAPTION_SIZE = 54            # size of the name under the photo
CAPTION_COLOR = (60, 60, 60) # dark grey
# ------------------------------

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
PHOTOS = Path("photos")
OUT = Path("framed")
OUT.mkdir(exist_ok=True)

# face finder (optional): installs itself, and the script still works without it
face_detector = None
try:
    try:
        import cv2
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "opencv-python-headless<5"], check=False)
        import cv2
    import numpy as np
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if not cascade.empty():
        face_detector = cascade
except Exception as e:
    print("Face finder not available, using default centring:", e)

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

def find_faces(photo):
    """returns (left, top, right, bottom) around the main faces, or None"""
    if face_detector is None:
        return None
    scale = 900 / max(photo.size)
    small = photo.resize((int(photo.width * scale), int(photo.height * scale))) if scale < 1 else photo
    gray = cv2.cvtColor(np.array(small), cv2.COLOR_RGB2GRAY)
    faces = face_detector.detectMultiScale(gray, 1.1, 6, minSize=(40, 40))
    if len(faces) == 0:
        return None
    k = (1 / scale) if scale < 1 else 1
    biggest = max(f[2] for f in faces)
    faces = [f for f in faces if f[2] >= biggest * 0.5]
    return (min(f[0] for f in faces) * k, min(f[1] for f in faces) * k,
            max(f[0] + f[2] for f in faces) * k, max(f[1] + f[3] for f in faces) * k)

def fill_gap(photo):
    """enlarge/crop the photo so it covers the whole gap, keeping the faces in view"""
    pw, ph = photo.size
    gap_ratio = w / h
    if pw / ph > gap_ratio:          # photo is wider than the gap
        cw, ch = ph * gap_ratio, ph
    else:                            # photo is taller than the gap
        cw, ch = pw, pw / gap_ratio
    faces = find_faces(photo)
    if faces:
        fx = (faces[0] + faces[2]) / 2
        fy = (faces[1] + faces[3]) / 2
    else:
        fx, fy = pw / 2, ph * 0.38    # people usually stand in the upper-middle
    left = min(max(fx - cw / 2, 0), pw - cw)
    top = min(max(fy - ch * 0.40, 0), ph - ch)
    box = (int(left), int(top), int(left + cw), int(top + ch))
    return photo.crop(box).resize((w, h), Image.LANCZOS)

def load_font(size):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
              "arialbd.ttf", "DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    return ImageFont.load_default()

def write_caption(img, text):
    draw = ImageDraw.Draw(img)
    size = CAPTION_SIZE
    font = load_font(size)
    max_width = w - 40
    while draw.textlength(text, font=font) > max_width and size > 20:
        size -= 2
        font = load_font(size)
    mid_x = (x1 + x2) // 2
    mid_y = y2 + 115
    draw.text((mid_x, mid_y), text, font=font, fill=CAPTION_COLOR, anchor="mm")

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
    canvas.paste(fill_gap(photo), (x1, y1))
    caption = re.sub(r"\s+", " ", p.stem.replace("_", " ")).strip()
    write_caption(canvas, caption)
    canvas.save(OUT / (p.stem + ".jpg"), quality=95)
    count += 1
print("Framed", count, "photos")
