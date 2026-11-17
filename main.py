import os
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
import io
import json
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "8797369678:AAEiCv9POm8pJUHWKabZTU6O-XaraBL9GPg"
PORT = int(os.environ.get("PORT", 8080))
RENDER_URL = "https://ilan-botu.onrender.com"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

client = genai.Client()

FONT_PATH = "DejaVuSans-Bold.ttf"
if not os.path.exists(FONT_PATH):
    try:
        font_url = "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf"
        r = requests.get(font_url)
        if r.status_code == 200:
            with open(FONT_PATH, "wb") as f:
                f.write(r.content)
    except Exception:
        pass

def create_dynamic_flyer(data):
    img_width, img_height = 1000, 1250
    # Derin endüstriyel kurumsal lacivert tuval
    image = Image.new("RGB", (img_width, img_height), color="#070f2b")
    draw = ImageDraw.Draw(image)

    try:
        font_header = ImageFont.truetype(FONT_PATH, 20)
        font_title = ImageFont.truetype(FONT_PATH, 32)
        font_sub = ImageFont.truetype(FONT_PATH, 22)
        font_text = ImageFont.truetype(FONT_PATH, 17)
        font_small = ImageFont.truetype(FONT_PATH, 14)
    except Exception:
        font_header = font_title = font_sub = font_text = font_small = ImageFont.load_default()

    def draw_text_box(x, y, text, fill, font, max_width, lines=1, align="left"):
        words = str(text).split()
        wrapped_lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] <= max_width:
                current_line.append(word)
            else:
                wrapped_lines.append(' '.join(current_line))
                current_line = [word]
        wrapped_lines.append(' '.join(current_line))
        
        y_pos = y
        for i in range(min(len(wrapped_lines), lines)):
            line_text = wrapped_lines[i]
            line_bbox = draw.textbbox((0, 0), line_text, font=font)
            if align == "center":
                x_pos = x + (max_width - line_bbox[2]) / 2
            else:
                x_pos = x
            draw.text((x_pos, y_pos), line_text, fill=fill, font=font)
            y_pos += line_bbox[3] - line_bbox[1] + 6

    # --- 1. ÜST FİRMA / SEKTÖR BANDI ---
    draw.rectangle([40, 30, 960, 120], fill="#1b1a55")
    firma_adi = data.get("firma", "YENİ İŞ İLANI FIRSATI")
    draw_text_box(65, 50, firma_adi, fill="#ffc107", font=font_header, max_width=850, lines=1)

    # --- 2. POZİSYON VURGUSU (Çarpıcı Sarı Alan) ---
    draw.rounded_rectangle([40, 140, 960, 270], radius=14, fill="#ffc107")
    draw.text((70, 160), "ARANAN POZİSYON", fill="#070f2b", font=font_small)
    pozisyon = data.get("pozisyon", "Personel Alımı")
    draw_text_box(70, 195, pozisyon, fill="#070f2b", font=font_title, max_width=870, lines=2)

    # --- 3. İŞ TANIMI & NİTELİKLER (Esnek İki Sütun) ---
    draw.rounded_rectangle([40, 300, 490, 630], radius=12, fill="#1b1a55")
    draw.text((65, 325), "📋 İŞ TANIMI & ŞARTLAR", fill="#ffc107", font=font_sub)
    y_off = 385
    gorevler = data.get("gorevler", ["• Endüstriyel üretim süreçlerinde görev almak.", "• Vardiyalı düzene uyum sağlamak."])
    for g in gorevler[:4]:
        draw_text_box(65, y_off, str(g), fill="#ffffff", font=font_text, max_width=410, lines=3)
        y_off += 50

    draw.rounded_rectangle([510, 300, 960, 630], radius=12, fill="#1b1a55")
    draw.text((535, 325), "💼 ARANAN NİTELİKLER", fill="#ffc107", font=font_sub)
    y_off_n = 385
    nitelikler = data.get("nitelikler", ["✔ İlgili bölümlerden mezun.", "✔ Ekip çalışmasına yatkın ve tecrübeli."])
    for n in nitelikler[:4]:
        draw_text_box(535, y_off_n, str(n), fill="#ffffff", font=font_text, max_width=410, lines=3)
        y_off_n += 55

    # --- 4. MAAŞ / ÜCRET VURGUSU ---
    draw.rounded_rectangle([40, 660, 960, 790], radius=14, fill="#ffc107")
    draw.text((70, 682), "MAAŞ & YAN HAKLAR", fill="#070f2b", font=font_small)
    maas_metni = data.get("maas", "Güncel ve Tatminkar Ücret")
    draw_text_box(70, 715, maas_metni, fill="#070f2b", font=font_title, max_width=870, lines=1)

    # --- 5. SERVİS GÜZERGAHI & İLETİŞİM ---
    draw.rounded_rectangle([40, 820, 490, 1050], radius=12, fill="#1b1a55")
    draw.text((65, 845), "📍 SERVİS GÜZERGAHI", fill="#ffc107", font=font_sub)
    guzergahlar = data.get("guzergah", "Kocaeli ve Çevre İlçeler")
    if isinstance(guzergahlar, str):
        guzergahlar = guzergahlar.split(",")
    y_off_g = 900
    for durak in guzergahlar[:7]:
        draw.text((65, y_off_g), f"• {str(durak).strip()}", fill="#ffffff", font=font_text)
        y_off_g += 45

    draw.rounded_rectangle([510, 820, 960, 1050], radius=12, fill="#1b1a55")
    draw.text((535, 845), "📞 İLETİŞİM / BAŞVURU", fill="#ffc107", font=font_sub)
    
    iletisim_adi = data.get("iletisim_kisi", "İnsan Kaynakları")
    iletisim_tel = data.get("iletisim_tel", "İlan Detayında")
    iletisim_email = data.get("iletisim_email", "")

    draw_text_box(535, 900, str(iletisim_adi), fill="#ffffff", font=font_sub, max_width=410, lines=2)
    draw_text_box(535, 960, str(iletisim_tel), fill="#ffc107", font=font_sub, max_width=410, lines=1)
    if iletisim_email:
        draw_text_box(535, 1005, str(iletisim_email), fill="#cccccc", font=font_small, max_width=410, lines=1)

    # Alt Bilgi Bandı
    draw.rectangle([40, 1080, 960, 1160], fill="#040712")
    draw.text((70, 1102), "PROFESYONEL İŞ İLANI OTOMASYON SİSTEMİ", fill="#6c7c8c", font=font_small)

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95)
    output.seek(0)
    return output.read()

@app.route('/')
def home():
    return "Bot aktif ve çalışıyor!"

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update:
        return jsonify({"status": "no data"}), 400

    message = update.get("message") or update.get("edited_message")
    if message and "photo" in message:
        chat_id = message["chat"]["id"]
        
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": "🎨 İlanın yapısı inceleniyor ve profesyonel afiş hazırlanıyor..."
        })
        
        try:
            photos = message["photo"]
            file_id = photos[-1]["file_id"]
            
            file_res = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
            if file_res.get("ok"):
                file_path = file_res["result"]["file_path"]
                img_bytes = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}").content
                
                flyer_data = {
                    "firma": "YENİ İŞ FIRSATI",
                    "pozisyon": "PERSONEL ALIMI",
                    "maas": "Güncel Şartlar",
                    "gorevler": ["Üretim ve operasyon süreçleri"],
                    "nitelikler": ["İlgili pozisyona uygun nitelikler"],
                    "guzergah": "Gebze, Çayırova",
                    "iletisim_kisi": "İnsan Kaynakları",
                    "iletisim_tel": "İletişim Bilgisi"
                }
                
                try:
                    analysis_prompt = (
                        "Bu iş ilanından şu bilgileri eksiksiz olarak JSON formatında çıkar: "
                        "firma (şirket adı), pozisyon (pozisyon adı), "
                        "maas (maaş veya yan hak bilgisi), gorevler (liste olarak iş tanımı veya şartlar), "
                        "nitelikler (liste olarak aranan nitelikler), guzergah (servis güzergahı), "
                        "iletisim_kisi (ilgili kişi veya departman), iletisim_tel (telefon numarası), iletisim_email (varsa email). "
                        "Sadece saf JSON döndür başka hiçbir açıklama yazma."
                    )
                    
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                            analysis_prompt
                        ]
                    )
                    
                    if response and response.text:
                        clean_text = response.text.replace("```json", "").replace("```", "").strip()
                        parsed_data = json.loads(clean_text)
                        if isinstance(parsed_data, dict):
                            flyer_data.update(parsed_data)
                except Exception as e:
                    logging.error(f"AI Analiz Hatası: {e}")
                
                final_image_bytes = create_dynamic_flyer(flyer_data)
                
                requests.post(
                    f"{TELEGRAM_API_URL}/sendPhoto",
                    data={"chat_id": chat_id, "caption": "✨ İstediğiniz profesyonel kurumsal afişiniz hazır!"},
                    files={"photo": ("afis.jpg", final_image_bytes, "image/jpeg")}
                )
        except Exception as e:
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"❌ İşlem sırasında bir hata oluştu."
            })

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    webhook_url = f"{RENDER_URL}/{TELEGRAM_BOT_TOKEN}"
    try:
        requests.get(f"{TELEGRAM_API_URL}/setWebhook?url={webhook_url}")
    except Exception:
        pass
        
    app.run(host="0.0.0.0", port=PORT)
