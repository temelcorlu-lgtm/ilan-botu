import os
import logging
import urllib.parse
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from google import genai
from google.genai import types

# Log ayarları
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# Telegram Bot Token ve Render URL Ayarı
TELEGRAM_BOT_TOKEN = "8797369678:AAEiCv9POm8pJUHWKabZTU6O-XaraBL9GPg"
PORT = int(os.environ.get("PORT", 8080))
RENDER_URL = "https://ilan-botu.onrender.com"  # Render servis adresin

client = genai.Client()

async def handle_job_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    # Kullanıcının attığı ham görseli al
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    await update.message.reply_text("🎨 İlan analiz ediliyor, afişiniz hazırlanıyor...")

    try:
        analysis_prompt = "Bu iş ilanı görselindeki firma adını, pozisyonu ve temel şartları kısa ve net maddeler halinde çıkar."
        
        response = None
        for m_name in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-3.8-flash"]:
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
            except Exception:
                continue
                
        if not response or not response.text:
            raise Exception("Tüm Gemini modelleri şu an yoğun, lütfen tekrar deneyin.")
            
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
            await update.message.reply_text(f"✨ **İlan Analiz Sonucu:**\n\n{ilan_ozeti}")

    except Exception as e:
        await update.message.reply_text(f"❌ Bir hata oluştu: {str(e)}")

def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.PHOTO & (~filters.COMMAND), handle_job_image))
    
    print("🤖 Afiş botu webhook modunda başlatılıyor...")
    
    # Render üzerinde çakışma (Conflict) yaratmayan Webhook sistemi
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_BOT_TOKEN,
        webhook_url=f"{RENDER_URL}/{TELEGRAM_BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
