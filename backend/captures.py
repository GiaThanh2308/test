"""Lưu ảnh chụp tự động, đóng dấu ngày giờ (+ tên, lớp) lên ảnh. Thư mục: data/capture/<yyyy-mm-dd>/."""
import os
import re
import unicodedata
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = [
    os.getenv("CAPTURE_FONT", ""),
    r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf",       # Windows (có tiếng Việt)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial.ttf",
]
_font_cache: dict[int, ImageFont.FreeTypeFont] = {}


def _font(size: int):
    if size not in _font_cache:
        for p in _FONT_CANDIDATES:
            if p and os.path.exists(p):
                _font_cache[size] = ImageFont.truetype(p, size)
                break
        else:
            _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def stamp_image(img_bgr: np.ndarray, when: datetime, lines: list[str]) -> np.ndarray:
    """Dải chữ ở đáy ảnh: dòng đầu là ngày giờ, các dòng sau là tên/lớp."""
    h, w = img_bgr.shape[:2]
    size = max(16, w // 40)
    pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    text = [when.strftime("%d/%m/%Y  %H:%M:%S")] + [l for l in lines if l]
    pad, gap = size // 2, size // 4
    band_h = len(text) * (size + gap) + pad * 2 - gap
    overlay = Image.new("RGBA", pil.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rectangle([0, h - band_h, w, h], fill=(0, 0, 0, 170))
    y = h - band_h + pad
    for i, t in enumerate(text):
        d.text((pad, y), t, font=_font(size), fill=(255, 220, 80, 255) if i == 0 else (255, 255, 255, 255))
        y += size + gap
    out = Image.alpha_composite(pil, overlay).convert("RGB")
    return cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)


def _safe(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name or "")
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c)).replace("đ", "d").replace("Đ", "D")
    return re.sub(r"[^A-Za-z0-9]+", "_", ascii_name).strip("_")[:40] or "khong_ro"


def save_capture(capture_root: str, img_bgr: np.ndarray, when: datetime, who: Optional[str],
                 cls: Optional[str], by: Optional[str]) -> str:
    """Trả về đường dẫn tương đối '<ngày>/<tên file>' (dùng cho API xem ảnh). `when` là giờ địa phương."""
    day = when.strftime("%Y-%m-%d")
    folder = os.path.join(capture_root, day)
    os.makedirs(folder, exist_ok=True)
    fname = f"{when:%H%M%S}_{_safe(who or 'unknown')}_{_safe(cls or '')}_{_safe(by or '')}.jpg".replace("__", "_")
    lines = [l for l in (who, f"Lớp {cls}" if cls else None, f"Ghi bởi: {by}" if by else None) if l]
    stamped = stamp_image(img_bgr, when, lines)
    # imencode + tofile: ghi được đường dẫn có dấu tiếng Việt trên Windows
    ok, buf = cv2.imencode(".jpg", stamped, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise RuntimeError("Không mã hoá được ảnh chụp")
    path = os.path.join(folder, fname)
    n = 1
    while os.path.exists(path):  # cùng giây, cùng người → thêm số
        n += 1
        path = os.path.join(folder, fname.replace(".jpg", f"_{n}.jpg"))
    buf.tofile(path)
    return f"{day}/{os.path.basename(path)}"
