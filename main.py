import os
import subprocess
import sys

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
    draw.text((70, 70), data.get("firma", "YENİ KARİYER FIRSATI").upper(), fill="#ffb703", font=font_title)

    # Pozisyon Kutusu (Sarı)
    draw.rounded_rectangle([50, 160, 950, 280], radius=12, fill="#ffb703")
    draw.text((70, 180), "ARANAN POZİSYON:", fill="#0b132b", font=font_small)
    draw.text((70, 215
