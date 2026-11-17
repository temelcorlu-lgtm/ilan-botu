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
RENDER_URL = "https://ilan-botu.onrender.com"

client = genai.Client()

async def handle_job_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    # Kullanıcının attığı ham görseli al
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    await update.message.reply_text("🎨 İlan işleniyor ve afiş tasarlanıyor...")

    try:
        # Tek deneme ve en sade komutla Gemini üzerinden hızlı özet alma
        analysis_prompt = "Bu iş ilanındaki pozisyonu ve aranan nitelikleri kısaca yaz."
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                types.Part.from_bytes(data=bytes(photo_bytes), mime_type="image/jpeg"),
                analysis_prompt
            ]
        )
        
        ilan_ozeti = response.text if response and response.text else "Personel Alımı ve İş İlanı"

        # Kurumsal konsepte uygun tasarım komutu
        design_prompt = (
            f"Professional corporate Instagram recruitment job flyer poster based on: {ilan_ozeti}. "
            "Dark navy blue background, bold yellow and white text, modern graphic design."
        )
        
        encoded_prompt = urllib.parse.quote(design_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=1250&nologo=true"

        # Görseli Python üzerinden indir
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
            await update.message.reply_text("✨ Afiş görseli oluşturulamadı ancak sistem aktif.")

    except Exception as e:
        # Gemini kotası takılsa bile süreci durdurmayıp doğrudan varsayılan afiş üreten yedek mekanizma
        try:
            fallback_prompt = "Professional corporate recruitment job flyer poster, dark navy blue background, modern graphic design."
            encoded_prompt = urllib.parse.quote(fallback_prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=1250&nologo=true"
            res = requests.get(image_url, timeout=25)
            if res.status_code == 200:
                await update.message.reply_photo(photo=res.content, caption="✨ Kurumsal afişiniz (Yedek mod) hazır!")
                return
        except Exception:
            pass
            
        await update.message.reply_text(f"❌ İşlem sırasında yoğunluk oluştu. Lütfen tekrar deneyin.")

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
