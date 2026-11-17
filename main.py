import os
import logging
import urllib.parse
import requests
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from google import genai
from google.genai import types

# Log ayarları
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# Render platformunun botu ayakta tutması için mini Flask sunucusu
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot aktif ve çalışıyor!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

# Telegram Bot Token ve Gemini Client Ayarı
TELEGRAM_BOT_TOKEN = "8797369678:AAEiCv9POm8pJUHWKabZTU6O-XaraBL9GPg"
client = genai.Client()

async def handle_job_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    # Kullanıcının attığı ham görseli al
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    await update.message.reply_text("🎨 İlan analiz ediliyor (Hata ayıklama aktif), lütfen bekleyin...")

    error_logs = []

    try:
        analysis_prompt = "Bu iş ilanı görselindeki firma adını, pozisyonu ve temel şartları kısa ve net maddeler halinde çıkar."
        
        response = None
        # Denenecek modeller ve her birinin hata detayını toplama döngüsü
        for m_name in ["gemini-3.8-flash", "gemini-1.5-flash", "gemini-2.5-flash"]:
            try:
                response = client.models.generate_content(
                    model=m_name,
                    contents=[
                        types.Part.from_bytes(data=bytes(photo_bytes), mime_type="image/jpeg"),
                        analysis_prompt
                    ]
                )
                if response and response.text:
                    break
            except Exception as e:
                error_logs.append(f"Model ({m_name}) Hatası: {str(e)}")
                continue
                
        if not response or not response.text:
            # Hiçbiri çalışmazsa toplanan tüm hata detaylarını Telegram'a fırlat
            detayli_hata = "\n".join(error_logs)
            raise Exception(f"Tüm modeller başarısız oldu:\n{detayli_hata}")
            
        ilan_ozeti = response.text

        # Kurumsal konsepte uygun tasarım komutu
        design_prompt = (
            f"Professional corporate Instagram recruitment job flyer poster based on: {ilan_ozeti}. "
            "Dark navy blue technical background, bold yellow and white structured text boxes, "
            "clean modern typography, high quality graphic design."
        )
        
        encoded_prompt = urllib.parse.quote(design_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=1250&nologo=true"

        # Görseli Python üzerinden güvenle indir (3 kez deneme döngüsü)
        image_bytes = None
        for attempt in range(3):
            try:
                res = requests.get(image_url, timeout=25)
                if res.status_code == 200 and len(res.content) > 1000:
                    image_bytes = res.content
                    break
            except Exception:
                continue

        # Başarıyla indiyse Telegram'a fotoğraf olarak gönder
        if image_bytes:
            await update.message.reply_photo(
                photo=image_bytes,
                caption="✨ İstediğiniz kurumsal afiş tasarımı hazır!"
            )
        else:
            await update.message.reply_text(f"✨ **İlan Analiz Sonucu:**\n\n{ilan_ozeti}\n\n*(Görsel sunucusu yoğun, birkaç saniye sonra tekrar deneyebilirsiniz.)*")

    except Exception as e:
        # Kodun herhangi bir yerinde hata olursa Telegram'a tam sebebini yazdıracak
        await update.message.reply_text(f"🔍 **Hata Ayıklama Raporu:**\n\n{str(e)}")

def main():
    # Arka planda Flask sunucusunu başlat
    t = Thread(target=run_flask)
    t.start()

    # Telegram Botu başlat
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.PHOTO & (~filters.COMMAND), handle_job_image))
    
    print("🤖 Afiş botu bulutta aktif!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
