import os
import re
import io
import json
import math
import subprocess
import sys

# Pillow kütüphanesi yoksa otomatik kur
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw, ImageFont

import logging
import requests
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", 8080))
RENDER_URL = os.environ.get("RENDER_URL", "https://ilan-botu.onrender.com").strip()
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN ortam değişkeni tanımlı değil.")

client = genai.Client()

FONT_BOLD_PATH = "Roboto-Bold.ttf"
FONT_REG_PATH = "Roboto-Regular.ttf"


def _ensure_font(path: str, url: str):
    if not os.path.exists(path):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 10000:
                with open(path, "wb") as f:
                    f.write(r.content)
        except Exception:
            pass


_ensure_font(
    FONT_BOLD_PATH,
    "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf",
)
_ensure_font(
    FONT_REG_PATH,
    "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Regular.ttf",
)


def _load_font(path: str, size: int, bold: bool = True):
    try:
        return ImageFont.truetype(path, size=size)
    except Exception:
        try:
            fallback = FONT_BOLD_PATH if bold else FONT_REG_PATH
            return ImageFont.truetype(fallback, size=size)
        except Exception:
            return ImageFont.load_default()


def strip_forbidden_role(text: str, replacement: str = "Üretim Personeli") -> str:
    if not text:
        return ""
    cleaned = re.sub(
        r"\bbeden\s+i̇?şçisi(?:\s*\([^)]*\))?\b",
        replacement,
        str(text),
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def normalize_phone(raw: str) -> str:
    if not raw:
        return ""
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return ""
    if digits.startswith("0090"):
        digits = digits[4:]
    elif digits.startswith("90") and len(digits) >= 12:
        digits = digits[2:]
    while digits.startswith("09") and len(digits) > 10:
        digits = digits[2:]
    while len(digits) > 10 and digits.startswith("9"):
        digits = digits[1:]
    while len(digits) > 10 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) > 10:
        digits = digits[-10:]
    if len(digits) != 10 or digits[0] not in "2345":
        return ""
    if len(set(digits)) <= 2:
        return ""
    return f"0{digits[:3]} {digits[3:6]} {digits[6:8]} {digits[8:10]}"


def _draw_decorations(draw: ImageDraw.Draw, width: int, height: int):
    accent = "#3b76d8"
    soft = "#275ec2"

    # Nokta matrisleri (sağ üst ve alt orta-sağ)
    for r in range(5):
        for c in range(6):
            cx = width - 165 + c * 22
            cy = 70 + r * 22
            draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=accent)

    for r in range(3):
        for c in range(7):
            cx = int(width * 0.56) + c * 22
            cy = height - 115 + r * 22
            draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=accent)

    # İnce halkalar
    rings = [
        (115, 145, 16),
        (int(width * 0.66), 95, 18),
        (int(width * 0.84), int(height * 0.52), 20),
        (int(width * 0.25), int(height * 0.86), 16),
    ]
    for cx, cy, rad in rings:
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=soft, width=3)

    # Artı / çarpı işaretleri
    crosses = [
        (88, int(height * 0.44), 16, 0.35),
        (width - 95, int(height * 0.32), 18, 0.0),
        (72, int(height * 0.81), 16, 0.0),
        (width - 105, int(height * 0.77), 18, 0.2),
    ]
    for cx, cy, arm, angle in crosses:
        for base_ang in (0.0, math.pi / 2):
            ang = base_ang + angle
            dx = math.cos(ang) * arm
            dy = math.sin(ang) * arm
            draw.line([cx - dx, cy - dy, cx + dx, cy + dy], fill=soft, width=3)


def _draw_icon(draw: ImageDraw.Draw, kind: str, cx: int, cy: int, color: str = "#ffffff"):
    if kind == "graduation":
        # Mezuniyet kepi
        pts = [(cx, cy - 16), (cx + 26, cy - 4), (cx, cy + 8), (cx - 26, cy - 4)]
        draw.polygon(pts, fill=color)
        draw.rounded_rectangle([cx - 14, cy + 3, cx + 14, cy + 15], radius=4, fill=color)
        draw.line([cx + 22, cy - 2, cx + 22, cy + 16], fill=color, width=3)
    elif kind == "briefcase":
        # Çanta / deneyim
        draw.rounded_rectangle([cx - 22, cy - 10, cx + 22, cy + 16], radius=5, outline=color, width=3)
        draw.rounded_rectangle([cx - 9, cy - 17, cx + 9, cy - 9], radius=3, outline=color, width=3)
        draw.line([cx - 20, cy + 2, cx + 20, cy + 2], fill=color, width=2)
    elif kind == "pin":
        # Konum pini
        draw.ellipse([cx - 14, cy - 20, cx + 14, cy + 8], outline=color, width=3)
        draw.ellipse([cx - 5, cy - 11, cx + 5, cy - 1], fill=color)
        draw.polygon([(cx - 11, cy + 3), (cx + 11, cy + 3), (cx, cy + 22)], fill=color)
    else:
        # Bilgi / saat / kontrol işareti
        draw.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], outline=color, width=3)
        draw.line([cx - 7, cy, cx - 2, cy + 6], fill=color, width=3)
        draw.line([cx - 2, cy + 6, cx + 8, cy - 6], fill=color, width=3)


def _wrap_text(draw: ImageDraw.Draw, text: str, font, max_width: int) -> list:
    words = str(text).split()
    if not words:
        return []
    lines = []
    current = []
    for w in words:
        trial = " ".join(current + [w])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
                current = [w]
            else:
                lines.append(w)
    if current:
        lines.append(" ".join(current))
    return lines


def create_dynamic_flyer(data: dict) -> bytes:
    # Gönderi + Reels ortak dikey boyut (3:4)
    w, h = 1080, 1440
    bg_blue = "#1657b8"
    white = "#ffffff"
    search_bar_bg = "#f8faff"
    text_dark = "#1f2937"
    muted_icon = "#3b4252"

    image = Image.new("RGB", (w, h), color=bg_blue)
    draw = ImageDraw.Draw(image)
    _draw_decorations(draw, w, h)

    font_brand = _load_font(FONT_BOLD_PATH, 42, bold=True)
    font_headline = _load_font(FONT_BOLD_PATH, 56, bold=True)
    font_role = _load_font(FONT_REG_PATH, 34, bold=False)
    font_bullet = _load_font(FONT_REG_PATH, 28, bold=False)
    font_apply_title = _load_font(FONT_BOLD_PATH, 36, bold=True)
    font_apply_box = _load_font(FONT_REG_PATH, 30, bold=False)

    # 1. Üst Marka / Firma Adı
    firma = strip_forbidden_role(str(data.get("firma") or "İŞ İLANI"), replacement="Üretim Personeli").strip()
    brand_bbox = draw.textbbox((0, 0), firma, font=font_brand)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text(((w - brand_w) / 2, 130), firma, fill=white, font=font_brand)

    # 2. Ana Başlık
    headline_lines = ["EKİP ARKADAŞI", "ARIYORUZ!"]
    y_head = 215
    for hl in headline_lines:
        hb = draw.textbbox((0, 0), hl, font=font_headline)
        draw.text(((w - (hb[2] - hb[0])) / 2, y_head), hl, fill=white, font=font_headline)
        y_head += (hb[3] - hb[1]) + 10

    # 3. Ortada Büyüteçli Beyaz Arama Çubuğu (Pozisyon)
    pozisyon = strip_forbidden_role(str(data.get("pozisyon") or "Personel"), replacement="Üretim Personeli").strip()
    bar_x0, bar_y0, bar_x1, bar_y1 = 135, 395, w - 135, 495
    draw.rounded_rectangle([bar_x0, bar_y0, bar_x1, bar_y1], radius=(bar_y1 - bar_y0) // 2, fill=search_bar_bg)

    role_lines = _wrap_text(draw, pozisyon, font_role, (bar_x1 - bar_x0) - 125)
    role_text = role_lines[0] if role_lines else pozisyon
    rb = draw.textbbox((0, 0), role_text, font=font_role)
    role_y = bar_y0 + ((bar_y1 - bar_y0) - (rb[3] - rb[1])) / 2 - 2
    draw.text((bar_x0 + 44, role_y), role_text, fill=text_dark, font=font_role)

    # Sağda büyüteç ikonu
    mag_cx, mag_cy, mag_r = bar_x1 - 56, (bar_y0 + bar_y1) // 2 - 3, 16
    draw.ellipse([mag_cx - mag_r, mag_cy - mag_r, mag_cx + mag_r, mag_cy + mag_r], outline=muted_icon, width=4)
    draw.line(
        [mag_cx + int(mag_r * 0.7), mag_cy + int(mag_r * 0.7), mag_cx + mag_r + 11, mag_cy + mag_r + 11],
        fill=muted_icon,
        width=5,
    )

    # 4. İkonlu Şart / Deneyim / Konum Maddeleri
    raw_items = []
    egitim = strip_forbidden_role(str(data.get("egitim") or ""), replacement="Üretim Personeli").strip()
    if egitim:
        raw_items.append(("graduation", egitim))

    deneyim_list = data.get("nitelikler") or data.get("gorevler") or []
    if isinstance(deneyim_list, str):
        deneyim_list = [x.strip() for x in deneyim_list.split(",") if x.strip()]
    for entry in deneyim_list[:2]:
        cleaned_entry = strip_forbidden_role(str(entry), replacement="Üretim Personeli").lstrip("-•+* ").strip()
        if cleaned_entry:
            raw_items.append(("briefcase", cleaned_entry))

    konum = strip_forbidden_role(str(data.get("konum") or data.get("guzergah") or ""), replacement="Üretim Personeli").strip()
    if konum:
        raw_items.append(("pin", konum))

    if not raw_items:
        raw_items.append(("check", "İlan detaylarına uygun adaylar değerlendirilecektir."))

    y_cursor = 565
    icon_col_x = 175
    text_col_x = 245
    text_max_w = w - text_col_x - 125

    for icon_kind, item_text in raw_items[:4]:
        wrapped = _wrap_text(draw, item_text, font_bullet, text_max_w)[:3]
        if not wrapped:
            continue
        line_h = 38
        block_h = len(wrapped) * line_h
        _draw_icon(draw, icon_kind, icon_col_x, y_cursor + min(block_h // 2, 22), color=white)
        for idx, line in enumerate(wrapped):
            draw.text((text_col_x, y_cursor + idx * line_h), line, fill=white, font=font_bullet)
        y_cursor += block_h + 28
        if y_cursor > 1060:
            break

    # 5. Alt BAŞVURU Alanı ve Beyaz Kapsül
    apply_label = "BAŞVURU"
    al_b = draw.textbbox((0, 0), apply_label, font=font_apply_title)
    apply_y = max(y_cursor + 20, 1110)
    draw.text(((w - (al_b[2] - al_b[0])) / 2, apply_y), apply_label, fill=white, font=font_apply_title)

    tel_norm = normalize_phone(str(data.get("iletisim_tel") or data.get("telefon") or ""))
    email_str = str(data.get("iletisim_email") or "").strip()
    kisi_str = strip_forbidden_role(str(data.get("iletisim_kisi") or ""), replacement="Üretim Personeli").strip()

    contact_parts = []
    if tel_norm:
        contact_parts.append(tel_norm)
    if email_str:
        contact_parts.append(email_str)
    if not contact_parts and kisi_str:
        contact_parts.append(kisi_str)
    if not contact_parts:
        contact_parts.append("İlan Detayından Başvuru")

    contact_display = "  |  ".join(contact_parts)
    cap_x0, cap_y0, cap_x1, cap_y1 = 230, apply_y + 62, w - 230, apply_y + 146
    draw.rounded_rectangle([cap_x0, cap_y0, cap_x1, cap_y1], radius=(cap_y1 - cap_y0) // 2, fill=search_bar_bg)

    c_lines = _wrap_text(draw, contact_display, font_apply_box, (cap_x1 - cap_x0) - 50)
    c_text = c_lines[0] if c_lines else contact_display
    cb = draw.textbbox((0, 0), c_text, font=font_apply_box)
    draw.text(
        (cap_x0 + ((cap_x1 - cap_x0) - (cb[2] - cb[0])) / 2, cap_y0 + ((cap_y1 - cap_y0) - (cb[3] - cb[1])) / 2 - 2),
        c_text,
        fill=text_dark,
        font=font_apply_box,
    )

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95, optimize=True)
    output.seek(0)
    return output.read()


@app.route("/")
def home():
    return "Bot aktif ve calisiyor!"


@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return jsonify({"status": "no data"}), 400

    message = update.get("message") or update.get("edited_message")
    if message and "photo" in message:
        chat_id = message["chat"]["id"]

        requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": "İlan analiz ediliyor ve afiş hazırlanıyor..."},
            timeout=15,
        )

        try:
            photos = message["photo"]
            file_id = photos[-1]["file_id"]

            file_res = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}", timeout=15).json()
            if file_res.get("ok"):
                file_path = file_res["result"]["file_path"]
                img_bytes = requests.get(
                    f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
                    timeout=20,
                ).content

                flyer_data = {
                    "firma": "İŞ İLANI",
                    "pozisyon": "Üretim Personeli",
                    "egitim": "",
                    "nitelikler": [],
                    "gorevler": [],
                    "konum": "",
                    "guzergah": "",
                    "iletisim_kisi": "",
                    "iletisim_tel": "",
                    "iletisim_email": "",
                }

                try:
                    analysis_prompt = (
                        "Bu iş ilanından şu bilgileri JSON olarak çıkar: "
                        "firma (şirket adı), pozisyon (ilan/iş tanımındaki gerçek görev adı; 'Beden İşçisi' ifadesini asla kullanma), "
                        "egitim (öğrenim/bölüm şartı), nitelikler (liste olarak aranan nitelikler/deneyim), "
                        "gorevler (liste olarak iş tanımı), konum (il/ilçe/adres), guzergah (servis güzergahı), "
                        "iletisim_kisi (irtibat kişisi/birim), iletisim_tel (telefon numarası), iletisim_email (varsa e-posta). "
                        "Görselde olmayan bilgiyi uydurma, boş bırak. Sadece saf JSON döndür."
                    )

                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                            analysis_prompt,
                        ],
                    )

                    if response and response.text:
                        clean_text = response.text.replace("```json", "").replace("```", "").strip()
                        parsed_data = json.loads(clean_text)
                        if isinstance(parsed_data, dict):
                            flyer_data.update(parsed_data)
                except Exception as e:
                    logging.error(f"AI Analiz Hatasi: {e}")

                final_image_bytes = create_dynamic_flyer(flyer_data)

                requests.post(
                    f"{TELEGRAM_API_URL}/sendPhoto",
                    data={"chat_id": chat_id},
                    files={"photo": ("afis.jpg", final_image_bytes, "image/jpeg")},
                    timeout=30,
                )
        except Exception as e:
            logging.error(f"Islem Hatasi: {e}")
            requests.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={"chat_id": chat_id, "text": "İşlem sırasında bir hata oluştu."},
                timeout=15,
            )

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    webhook_url = f"{RENDER_URL}/{TELEGRAM_BOT_TOKEN}"
    try:
        requests.get(f"{TELEGRAM_API_URL}/setWebhook?url={webhook_url}", timeout=15)
    except Exception:
        pass

    app.run(host="0.0.0.0", port=PORT)
