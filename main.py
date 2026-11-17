import os
import logging
import requests
import io
import json
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types

# Log ayarları
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "8797369678:AAEiCv9POm8pJUHWKabZTU6O-XaraBL9GPg"
PORT = int(os.environ.get("PORT", 8080))
RENDER_URL = "https://ilan-botu.onrender.com"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

client = genai.Client()

# Font dosyası
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

def create_flyer(data):
    img_width, img_height = 1000, 1250
    image = Image.new("RGB", (img_width, img_height), color="#0b132b")
    draw = ImageDraw.Draw(image)

    try:
        font_title = ImageFont.truetype(FONT_PATH, 42)
        font_sub = ImageFont.truetype(FONT_PATH, 28)
        font_text = ImageFont.truetype(FONT_PATH, 22)
        font_small = ImageFont.truetype(FONT_PATH, 18)
    except Exception:
        font_title = font_sub = font_text = font_small = ImageFont.load_default()

    # Üst Başlık Şeridi
    draw.rectangle([50, 50, 950, 150], fill="#1c2541")
    draw.text((80, 75), "YENİ KARİYER FIRSATI!", fill="#ffb703", font=font_title)

    # Pozisyon Kutusu (Sarı)
    draw.rounded_rectangle([50, 180, 950, 320], radius=15, fill="#ffb703")
    draw.text((80, 200), "POZİSYON:", fill="#0b132b", font=font_small)
    draw.text((80, 235), data.get("pozisyon", "Personel Alımı").upper(), fill="#0b132b", font=font_sub)

    # Şartlar / Aranan Nitelikler Kutusu (Beyaz)
    draw.rounded_rectangle([50, 350, 950, 750], radius=15, fill="#ffffff")
    draw.text((80, 380), "ARANAN NİTELİKLER & ŞARTLAR:", fill="#1d3557", font=font_sub)
    
    y_offset = 430
    for nitelik in data.get("nitelikler", ["• Tecrübeli adaylar aranıyor", "• Vardiyalı çalışma imkanı"]):
        draw.text((80, y_offset), f"• {nitelik}", fill="#1d3557", font=font_text)
        y_offset += 45

    # İletişim / Lokasyon Kutusu
    draw.rounded_rectangle([50, 780, 950, 950], radius=15, fill="#1c2541")
    draw.text((80, 800), f"LOKASYON: {data.get('lokasyon', 'Kocaeli / Çayırova')}", fill="#ffffff", font=font_text)
    draw.text((80, 850), f"SON BAŞVURU: {data.get('tarih', 'Belirtilmemiş')}", fill="#ffb703", font=font_text)

    # Alt İletişim Butonu (Sarı)
    draw.rounded_rectangle([150, 1000, 850, 1120], radius=20, fill="#ffb703")
    draw.text((220, 1025), "İLETİŞİM / BAŞVURU", fill="#0b132b", font=font_sub)
    draw.text((250, 1070), data.get("iletisim", "0262 751 24 24"), fill="#0b132b", font=font_text)

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
        return jsonify({"status": "no data"}), 400  # Düzeltildi

    message = update.get("message") or update.get("edited_message")
    if message and "photo" in message:
        chat_id = message["chat"]["id"]
        
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": "🎨 İlan analiz ediliyor ve kurumsal afişiniz tasarlanıyor..."
        })
        
        try:
            photos = message["photo"]
            file_id = photos[-1]["file_id"]
            
            file_res = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
            if file_res.get("ok"):
                file_path = file_res["result"]["file_path"]
                img_bytes = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}").content
                
                analysis_prompt = (
                    "Bu iş ilanından şu bilgileri JSON formatında çıkar: "
                    "pozisyon (string), nitelikler (liste olarak 3-4 madde), lokasyon (string), tarih (string), iletisim (string). "
                    "Sadece saf JSON döndür."
                )
                
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=[
                        types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                        analysis_prompt
                    ]
                )
                
                flyer_data = {
                    "pozisyon": "Personel Alımı",
                    "nitelikler": ["Tecrübeli / Yetiştirilmek Üzere", "Esnek Çalışma Saatlerine Uygun", "Takım Çalışmasına Yatkın"],
                    "lokasyon": "Kocaeli / Çayırova",
                    "tarih": "Güncel",
                    "iletisim": "İnsan Kaynakları"
                }
                
                if response and response.text:
                    try:
                        clean_text = response.text.replace("```json", "").replace("```", "").strip()
                        flyer_data = json.loads(clean_text)
                    except Exception:
                        pass
                
                final_image_bytes = create_flyer(flyer_data)
                
                requests.post(
                    f"{TELEGRAM_API_URL}/sendPhoto",
                    data={"chat_id": chat_id, "caption": "✨ İstediğiniz kurumsal afişiniz hazır!"},
                    files={"photo": ("afis.jpg", final_image_bytes, "image/jpeg")}
                )
        except Exception as e:
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"❌ Bir hata oluştu: {str(e)}"
            })

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    webhook_url = f"{RENDER_URL}/{TELEGRAM_BOT_TOKEN}"
    try:
        requests.get(f"{TELEGRAM_API_URL}/setWebhook?url={webhook_url}")
    except Exception:
        pass
        
    app.run(host="0.0.0.0", port=PORT)
