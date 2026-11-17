import os
import logging
import requests
import io
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

# Türkçe karakterleri destekleyen temiz bir font indirelim (Yoksa varsayılan kullanılır)
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
    # 1000x1250 Instagram dikey afiş boyutu
    img_width, img_height = 1000, 1250
    image = Image.new("RGB", (img_width, img_height), color="#0b132b") # Koyu lacivert kurumsal arka plan
    draw = ImageDraw.Draw(image)

    # Font ayarları
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
    draw.text((80, 2
