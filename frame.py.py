from PIL import Image, ImageOps
from pathlib import Path

PHOTOS = Path("photos")
OUT = Path("framed")
OUT.mkdir(exist_ok=True)

frame = Image.open("frame.png").convert("RGBA")
# finds the see-through gap automatically
mask = frame.split()[3].point(lambda a: 255 if a < 10 else 0)
x1, y1, x2, y2 = mask.getbbox()
w, h = x2 - x1, y2 - y1

for p in PHOTOS.iterdir():
    if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
        continue
    photo = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
    photo = ImageOps.fit(photo, (w, h), centering=(0.5, 0.35))
    canvas = Image.new("RGBA", frame.size, "white")
    canvas.paste(photo, (x1, y1))
    canvas.alpha_composite(frame)
    canvas.convert("RGB").save(OUT / (p.stem + ".jpg"), quality=95)
