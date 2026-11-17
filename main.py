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
    # Derin endüstriyel lacivert arka plan
    image = Image.new("RGB", (img_width, img_height), color="#050c21")
    draw = ImageDraw.Draw(image)

    # Fontları yükle
    try:
        font_header = ImageFont.truetype(FONT_PATH, 20)
        font_title = ImageFont.truetype(FONT_PATH, 34)
        font_sub = ImageFont.truetype(FONT_PATH, 22)
        font_text = ImageFont.truetype(FONT_PATH, 17)
        font_small = ImageFont.truetype(FONT_PATH, 14)
    except Exception:
        font_header = font_title = font_sub = font_text = font_small = ImageFont.load_default()

    # --- 1. ÜST KURUMSAL BANNER (Daha Profesyonel) ---
    draw.rectangle([40, 30, 960, 120], fill="#111736")
    firma_adi = str(data.get("firma", "ÖZ GAYRİMTENKUL GIDA... LİMİTED ŞİRKETİ")).upper()
    
    # Metni kutuya sığdırmak için yardımcı fonksiyon
    def draw_text_in_box(x, y, text, fill, font, max_width, lines=1, align="left"):
        words = text.split()
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
            if align == "center": x_pos = x + (max_width - line_bbox[2]) / 2
            else: x_pos = x
            draw.text((x_pos, y_pos), line_text, fill=fill, font=font)
            y_pos += line_bbox[3] - line_bbox[1] + 5

    draw_text_in_box(65, 50, firma_adi, fill="#ffc107", font=font_header, max_width=850, lines=1, align="left")

    # --- 2. POZİSYON BANNER'I (Sarı Dikkat Alanı) ---
    draw.rounded_rectangle([40, 140, 960, 270], radius=14, fill="#ffc107")
    draw.text((70, 160), "ARANAN POZİSYON", fill="#050c21", font=font_small)
    pozisyon = str(data.get("pozisyon", "Metal Mamuller İmalat İşçisi")).upper()
    draw_text_in_box(70, 195, pozisyon, fill="#050c21", font=font_title, max_width=870, lines=2, align="left")

    # --- 3. ŞARTLAR VE İMKANLAR (İki Sütunlü Temiz Yerleşim) ---
    # Sol Kutu: İŞ TANIMI & ŞARTLAR
    draw.rounded_rectangle([40, 300, 490, 630], radius=12, fill="#111736")
    draw.text((65, 325), "📋 İŞ TANIMI & ŞARTLAR", fill="#ffc107", font=font_sub)
    
    y_offset = 385
    gorevler = [
        "• Endüstriyel tesislerde üretim sürecini yönetmek.",
        "• Tolerans ve kalite kontrol raporlaması.",
        "• Metal montaj ve birleştirme işlemleri.",
        "• Vardiyalı çalışma düzenine uygunluk."
    ]
    for gorev in gorevler:
        draw_text_in_box(65, y_offset, gorev, fill="#ffffff", font=font_text, max_width=410, lines=3)
        y_offset += 50
    
    # Sağ Kutu: ARANAN NİTELİKLER
    draw.rounded_rectangle([510, 300, 960, 630], radius=12, fill="#111736")
    draw.text((535, 325), "💼 ARANAN NİTELİKLER", fill="#ffc107", font=font_sub)
    
    y_offset_n = 385
    nitelikler = [
        "✔ Meslek Yüksek Okulu veya Endüstri Meslek Lisesi mezunu.",
        "✔ 3-5 yıl benzer sektör tecrübesi.",
        "✔ Teknik resim okuma ve ölçü aleti kullanımı.",
        "✔ 30-45 yaş aralığında."
    ]
    for nitelik in nitelikikler:
        draw_text_in_box(535, y_offset_n, nitelik, fill="#ffffff", font=font_text, max_width=410, lines=3)
        y_offset_n += 55

    # --- 4. MAAŞ VURGUSU (Çarpıcı Sarı Kutu) ---
    draw.rounded_rectangle([40, 660, 960, 790], radius=14, fill="#ffc107")
    draw.text((70, 682), "MAAŞ & ÜCRET", fill="#050c21", font=font_small)
    maas_metni = str(data.get("maas", "28075,5 TL (AGR Dahil Değil)"))
    draw_text_in_box(70, 715, maas_metni.upper(), fill="#050c21", font=font_title, max_width=870, lines=1)

    # --- 5. SERVİS GÜZERGAHI (Sol) & İLETİŞİM (Sağ) ---
    # Güzergah
    draw.rounded_rectangle([40, 820, 490, 1050], radius=12, fill="#111736")
    draw.text((65, 845), "📍 SERVİS GÜZERGAHI", fill="#ffc107", font=font_sub)
    guzergahlar = data.get("guzergah", ["Gebze", "Kandıra", "Körfez", "Derince", "İzmit", "Kartepe", "Dilovası", "Çayırova"])
    if isinstance(guzergahlar, str): guzergahlar = guzergahlar.split(",")
    y_offset_g = 900
    for durak in guzergahlar[:7]:
        draw.text((65, y_offset_g), f"• {durak.strip()}", fill="#ffffff", font=font_text)
        y_offset_g += 45

    # İletişim
    draw.rounded_rectangle([510, 820, 960, 1050], radius=12, fill="#111736")
    draw.text((535, 845), "📞 İLETİŞİM / BAŞVURU", fill="#ffc107", font=font_sub)
    
    iletisim_adi = str(data.get("iletisim_kisi", "Hakan CEBECİ"))
    iletisim_unvan = str(data.get("iletisim_unvan", "İnsan Kaynakları Yöneticisi"))
    iletisim_tel = str(data.get("iletisim_tel", "0 533 975 46 93"))
    iletisim_email = str(data.get("iletisim_email", "ik@oztahsildar.com.tr"))

    draw.text((535, 900), iletisim_adi, fill="#ffffff", font=font_sub)
    draw.text((535, 935), iletisim_unvan, fill="#cccccc", font=font_text)
    draw.text((535, 980), iletisim_tel, fill="#ffc107", font=font_sub)
    draw.text((535, 1020), iletisim_email, fill="#ffffff", font=font_text)

    # Alt Kurumsal Damga Bandı
    draw.rectangle([40, 1080, 960, 1160], fill="#040712")
    draw.text((70, 1102), "OZT OZTÜRK TAŞIMACILIK VE LOJİSTİK A.Ş. • GÜNCEL İŞ İLANI", fill="#6c7c8c", font=font_small)

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
            "text": "🎨 İlan analiz ediliyor, profesyonel kurumsal afiş hazırlanıyor..."
        })
        
        try:
            photos = message["photo"]
            file_id = photos[-1]["file_id"]
            
            file_res = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
            if file_res.get("ok"):
                file_path = file_res["result"]["file_path"]
                img_bytes = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}").content
                
                flyer_data = {
                    "firma": "ÖZ GAYRİMTENKUL GIDA SANAYİ VE TİCARET LİMİTED ŞİRKETİ",
                    "pozisyon": "METAL MAMULLER İMALAT İŞÇİSİ",
                    "maas": "28075,5 TL (AGR Dahil Değil)",
                    "guzergah": "Gebze, Kandıra, Körfez, Derince, İzmit, Kartepe, Dilovası, Çayırova",
                    "iletisim_kisi": "Hakan CEBECİ",
                    "iletisim_unvan": "İnsan Kaynakları Yöneticisi",
                    "iletisim_tel": "0 533 975 46 93",
                    "iletisim_email": "ik@oztahsildar.com.tr"
                }
                
                try:
                    analysis_prompt = (
                        "Bu iş ilanından şu bilgileri JSON formatında çıkar: "
                        "firma (şirket adı), pozisyon (pozisyon adı), "
                        "maas (maaş bilgisi), guzergah (servis güzergahı listesi), "
                        "iletisim_kisi (ilgili kişi adı), iletisim_unvan (kişinin unvanı), "
                        "iletisim_tel (telefon numarası), iletisim_email (email adresi). "
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
                    data={"chat_id": chat_id, "caption": "✨ İşte istediğiniz profesyonel kurumsal afişiniz!"},
                    files={"photo": ("afis.jpg", final_image_bytes, "image/jpeg")}
                )
        except Exception as e:
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"❌ İşlem tamamlanırken bir hata oluştu."
            })

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    webhook_url = f"{RENDER_URL}/{TELEGRAM_BOT_TOKEN}"
    try:
        requests.get(f"{TELEGRAM_API_URL}/setWebhook?url={webhook_url}")
    except Exception:
        pass
        
    app.run(host="0.0.0.0", port=PORT)
