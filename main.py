import os
import logging
import urllib.parse
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Log ayarları
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# Telegram Bot Token ve Render URL Ayarı
TELEGRAM_BOT_TOKEN = "8797369678:AAEiCv9POm8pJUHWKabZTU6O-XaraBL9GPg"
PORT = int(os.environ.get("PORT", 8080))
RENDER_URL = "https://ilan-botu.onrender.com"

async def handle_job_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    await update.message.reply_text("🎨 Kurumsal ilan afişiniz tasarlanıyor, lütfen bekleyin...")

    try:
        # Doğrudan profesyonel kurumsal afiş komutu
        design_prompt = (
            "Professional corporate Instagram recruitment job flyer poster, "
            "dark navy blue background, bold yellow and white structured text boxes, "
            "clean modern typography, high quality graphic design."
        )
        
        encoded_prompt = urllib.parse.quote(design_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=1250&nologo=true"

        # Görseli Python üzerinden güvenle indir
        image_bytes = None
        for attempt in range(3):
            try:
                res = requests.get(image_url, timeout=25)
                if res.status_code == 200 and len(res.content) > 1000:
                    image_bytes = res.content
                    break
            except Exception:
                continue

        if image_bytes:
            await update.message.reply_photo(
                photo=image_bytes,
                caption="✨ İstediğiniz kurumsal afiş tasarımı hazır!"
            )
        else:
            await update.message.reply_text("✨ Afiş görseli oluşturulamadı, lütfen tekrar deneyin.")

    except Exception as e:
        await update.message.reply_text(f"❌ Bir hata oluştu: {str(e)}")

def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.PHOTO & (~filters.COMMAND), handle_job_image))
    
    print("🤖 Afiş botu webhook modunda başlatılıyor...")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_BOT_TOKEN,
        webhook_url=f"{RENDER_URL}/{TELEGRAM_BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
