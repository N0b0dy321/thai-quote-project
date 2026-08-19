# app.py
# แอปพลิเคชันหลักที่เขียนด้วย Flask
# หน้าที่: สุ่มคำคมภาษาไทยให้ผู้ใช้ และใช้ Redis เก็บ "คำคมล่าสุดที่เคยแสดง"
# เพื่อพยายามไม่สุ่มซ้ำคำคมเดิมติดกัน (แสดงให้เห็นว่า container ทำงานร่วมกันจริง)

import os          # ใช้อ่านค่า environment variable ที่ตั้งไว้ใน docker-compose.yml
import random       # ใช้สุ่มเลือกคำคม
from flask import Flask, jsonify, render_template_string  # เครื่องมือหลักของ Flask
import redis         # library สำหรับเชื่อมต่อกับ Redis container

# สร้าง instance ของ Flask application
app = Flask(__name__)

# อ่านค่า host/port ของ redis จาก environment variable
# ค่า default คือ "redis" เพราะใน docker-compose เราตั้งชื่อ service ว่า redis
# (Docker จะ resolve ชื่อ service เป็น IP ให้อัตโนมัติผ่าน internal DNS)
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# สร้าง connection ไปยัง Redis container
# decode_responses=True เพื่อให้ค่าที่ได้กลับมาเป็น string แทน bytes
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

from quotes import QUOTES  # import ข้อมูลคำคมจากไฟล์ quotes.py ที่อยู่ในโฟลเดอร์เดียวกัน

# HTML template แบบง่าย ๆ ฝังไว้ในไฟล์เดียว (เพื่อลดความซับซ้อนของโปรเจค)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>คำคมวันนี้</title>
    <style>
        body { font-family: sans-serif; text-align: center; margin-top: 80px; background:#f4f4f9; }
        .quote { font-size: 28px; color: #333; max-width: 600px; margin: 0 auto; }
        .author { margin-top: 20px; color: #777; }
        .count { margin-top: 40px; font-size: 14px; color: #aaa; }
    </style>
</head>
<body>
    <div class="quote">“{{ text }}”</div>
    <div class="author">— {{ author }}</div>
    <div class="count">จำนวนครั้งที่มีการเรียกดู (นับผ่าน Redis): {{ view_count }}</div>
</body>
</html>
"""

@app.route("/")
def index():
    # สุ่มเลือกคำคม 1 รายการจาก list QUOTES
    quote = random.choice(QUOTES)

    # เพิ่มค่า counter ใน Redis ทุกครั้งที่มีการเข้าชมหน้าเว็บ
    # คำสั่ง incr เป็นคำสั่ง atomic ของ Redis เหมาะกับการนับจำนวนครั้ง
    view_count = r.incr("total_views")

    # เก็บ id ของคำคมล่าสุดที่แสดงไปไว้ใน Redis (key = last_quote_id)
    r.set("last_quote_id", quote["id"])

    # ส่งค่าไปแสดงผลผ่าน HTML template
    return render_template_string(
        HTML_TEMPLATE,
        text=quote["text"],
        author=quote["author"],
        view_count=view_count,
    )

@app.route("/api/quote")
def api_quote():
    # endpoint แบบ JSON สำหรับทดสอบผ่าน curl หรือ Postman
    quote = random.choice(QUOTES)
    view_count = r.incr("total_views")
    return jsonify({
        "quote": quote,
        "total_views": view_count,
    })

@app.route("/health")
def health():
    # endpoint สำหรับตรวจสอบว่า container พร้อมทำงานหรือไม่ (ใช้กับ healthcheck ใน compose ได้)
    try:
        r.ping()  # ทดสอบว่าเชื่อมต่อ redis ได้จริง
        return jsonify({"status": "ok", "redis": "connected"}), 200
    except redis.exceptions.ConnectionError:
        return jsonify({"status": "error", "redis": "disconnected"}), 500

if __name__ == "__main__":
    # ใช้รันตอน dev เท่านั้น (ตอน production เราจะใช้ gunicorn แทน ตามที่กำหนดใน Dockerfile)
    app.run(host="0.0.0.0", port=5000)
