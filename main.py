import os
import logging
import urllib.parse
import requests
from flask import Flask, request, jsonify

# Log ayarları
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

app = Flask(__name__)

# Telegram Bot Token ve Render URL Ayarı
TELEGRAM_BOT_TOKEN = "8797369678:AAEiCv9POm8pJUHWKabZTU6O-XaraBL9GPg"
PORT = int(os.environ.get("PORT", 8080))
RENDER_URL = "https://ilan-botu.onrender.com"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

@app.route('/')
def home():
    return "Bot aktif ve çalışıyor!"

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update:
        return jsonify({"status": "no data"}), 400

    # Gelen mesajı ve fotoğrafı kontrol et
    message = update.get("message") or update.get("edited_message")
    if message and "photo" in message:
        chat_id = message["chat"]["id"]
        
        # Kullanıcıya hemen bilgi mesajı gönder
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": "🎨 Kurumsal ilan afişiniz tasarlanıyor, lütfen bekleyin..."
        })
        
        try:
            # En yüksek çözünürlüklü fotoğrafı al
            photos = message["photo"]
            file_id = photos[-1]["file_id"]
            
            # Telegram'dan dosya yolunu öğren
            file_res = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
            if file_res.get("ok"):
                # Profesyonel kurumsal afiş tasarımı komutu
                design_prompt = (
                    "Professional corporate Instagram recruitment job flyer poster, "
                    "dark navy blue background, bold yellow and white structured text boxes, "
                    "clean modern typography, high quality graphic design."
                )
                encoded_prompt = urllib.parse.quote(design_prompt)
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=1250&nologo=true"
                
                # Pollinations AI üzerinden görseli indir
                img_res = requests.get(image_url, timeout=25)
                if img_res.status_code == 200 and len(img_res.content) > 1000:
                    # Telegram'a fotoğraf olarak gönder
                    requests.post(
                        f"{TELEGRAM_API_URL}/sendPhoto",
                        data={"chat_id": chat_id, "caption": "✨ İstediğiniz kurumsal afiş tasarımı hazır!"},
                        files={"photo": ("afis.jpg", img_res.content, "image/jpeg")}
                    )
                else:
                    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": "✨ Afiş görseli oluşturulamadı, lütfen tekrar deneyin."
                    })
        except Exception as e:
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"❌ İşlem sırasında bir hata oluştu."
            })

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    # Render ayağa kalkarken Telegram webhook'unu otomatik olarak tanımlar
    webhook_url = f"{RENDER_URL}/{TELEGRAM_BOT_TOKEN}"
    try:
        requests.get(f"{TELEGRAM_API_URL}/setWebhook?url={webhook_url}")
    except Exception:
        pass
        
    app.run(host="0.0.0.0", port=PORT)
