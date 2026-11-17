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

# Font dosyası yönetimi
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
        font_title = ImageFont.truetype(FONT_PATH, 38)
        font_sub = ImageFont.truetype(FONT_PATH, 26)
        font_text = ImageFont.truetype(FONT_PATH, 20)
        font_small = ImageFont.truetype(FONT_PATH, 16)
    except Exception:
        font_title = font_sub = font_text = font_small = ImageFont.load_default()

    # Üst Şerit (Şirket Adı)
    draw.rectangle([50, 40, 950, 130], fill="#1c2541")
    draw.text((70, 70), str(data.get("firma", "YENİ KARİYER FIRSATI")).upper(), fill="#ffb703", font=font_title)

    # Pozisyon Kutusu (Sarı)
    draw.rounded_rectangle([50, 160, 950, 280], radius=12, fill="#ffb703")
    draw.text((70, 180), "ARANAN POZİSYON:", fill="#0b132b", font=font_small)
    draw.text((70, 215), str(data.get("pozisyon", "Personel Alımı")).upper(), fill="#0b132b", font=font_sub)

    # Şartlar / Aranan Nitelikler Kutusu (Beyaz)
    draw.rounded_rectangle([50, 310, 950, 730], radius=12, fill="#ffffff")
    draw.text((70, 340), "ARANAN NİTELİKLER:", fill="#1d3557", font=font_sub)
    
    y_offset = 390
    nitelikler = data.get("nitelikler", ["• Tecrübeli adaylar aranıyor", "• Vardiyalı çalışma imkanı"])
    for nitelik in nitelikler[:5]:
        draw.text((70, y_offset), f"• {nitelik}", fill="#1d3557", font=font_text)
        y_offset += 55

    # Lokasyon ve Tarih Kutusu
    draw.rounded_rectangle([50, 760, 950, 920], radius=12, fill="#1c2541")
    draw.text((70, 790), f"LOKASYON: {data.get('lokasyon', 'Kocaeli / Çayırova')}", fill="#ffffff", font=font_text)
    draw.text((70, 845), f"SON BAŞVURU: {data.get('tarih', 'Güncel')}", fill="#ffb703", font=font_text)

    # İletişim / Numara Butonu (Sarı)
    draw.rounded_rectangle([100, 960, 900, 1100], radius=16, fill="#ffb703")
    draw.text((130, 985), "İLETİŞİM / BAŞVURU", fill="#0b132b", font=font_small)
    draw.text((130, 1025), str(data.get("iletisim", "İnsan Kaynakları")), fill="#0b132b", font=font_sub)

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
            "text": "🎨 İlan analiz ediliyor ve sade kurumsal afiş hazırlanıyor..."
        })
        
        try:
            photos = message["photo"]
            file_id = photos[-1]["file_id"]
            
            file_res = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
            if file_res.get("ok"):
                file_path = file_res["result"]["file_path"]
                img_bytes = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}").content
                
                flyer_data = {
                    "firma": "YENİ KARİYER FIRSATI",
                    "pozisyon": "Personel Alımı",
                    "nitelikler": ["Tecrübeli / Yetiştirilmek Üzere", "Vardiyalı Çalışma Uygun", "Ekip Çalışmasına Yatkın"],
                    "lokasyon": "Kocaeli / Çayırova",
                    "tarih": "Güncel",
                    "iletisim": "İnsan Kaynakları"
                }
                
                try:
                    analysis_prompt = (
                        "Bu iş ilanından şu bilgileri JSON formatında çıkar: "
                        "firma (şirket adı), pozisyon (pozisyon adı), nitelikler (liste olarak 3-4 madde), "
                        "lokasyon (şehir/ilçe), tarih (son başvuru tarihi), iletisim (telefon veya email/kişi). "
                        "Sadece saf JSON döndür başka hiçbir şey yazma."
                    )
                    
                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
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
                except Exception:
                    pass
                
                final_image_bytes = create_flyer(flyer_data)
                
                requests.post(
                    f"{TELEGRAM_API_URL}/sendPhoto",
                    data={"chat_id": chat_id, "caption": "✨ Sade ve şık kurumsal afişiniz hazır!"},
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
