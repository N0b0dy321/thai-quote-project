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

# HTML template ฝังไว้ในไฟล์เดียว (เพื่อลดความซับซ้อนของโปรเจค ไม่ต้องแยกโฟลเดอร์ templates/)
# แนวคิดดีไซน์: อิงบรรยากาศ "ใบลาน + ตราประทับวัด" — พื้นหยกเข้ม ตัวอักษรทอง
# คำคมใช้ฟอนต์เซริฟไทย (Noto Serif Thai) ให้ความรู้สึกขลังแบบต้นฉบับโบราณ
# ตัวเลขจำนวนการเข้าชมแสดงเป็น "ตราประทับ" วงกลมสีทอง แทนตัวเลขธรรมดา
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>คำคมวันนี้</title>
    <!-- โหลดฟอนต์ไทย 3 บทบาท: เซริฟสำหรับตัวคำคม (display), Sarabun สำหรับ UI (body),
         และ IBM Plex Mono สำหรับตัวเลขบนตราประทับ (utility) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Thai:wght@400;600;700&family=Sarabun:wght@300;400;600&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
    <style>
        /* ---------- DESIGN TOKENS ---------- */
        :root {
            --jade-deep: #0e2e2b;      /* พื้นหลังหลัก โทนหยกเข้ม */
            --jade-panel: #123b36;     /* พื้นการ์ด เข้มรองลงมาเล็กน้อย */
            --gold: #c9a227;           /* สีทอง ใช้กับเส้นกรอบและตราประทับ */
            --gold-soft: #e4c766;      /* ทองอ่อน ใช้ hover/highlight */
            --ivory: #f4ede0;          /* สีตัวอักษรคำคม */
            --rust: #c07a4a;           /* สีสำหรับชื่อผู้แต่ง */
            --muted: #7fa69c;          /* สีตัวอักษรรอง/คำอธิบาย */
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 32px 16px;
            font-family: 'Sarabun', sans-serif;
            color: var(--ivory);
            /* ไล่เฉดพื้นหลังแบบแสงจันทร์กระทบกระเบื้องหยก */
            background:
                radial-gradient(circle at 15% 10%, rgba(201,162,39,0.10), transparent 45%),
                radial-gradient(circle at 85% 90%, rgba(201,162,39,0.08), transparent 50%),
                var(--jade-deep);
        }

        /* ---------- การ์ดคำคม ---------- */
        .card {
            position: relative;
            width: 100%;
            max-width: 620px;
            background: var(--jade-panel);
            border: 1px solid rgba(201,162,39,0.35);
            border-radius: 4px;
            padding: 64px 48px 56px;
            box-shadow: 0 30px 60px rgba(0,0,0,0.35);
            animation: rise 0.7s ease-out both;
        }

        /* กรอบทองบางซ้อนด้านในอีกชั้น ให้ความรู้สึกกรอบต้นฉบับใบลาน */
        .card::before {
            content: "";
            position: absolute;
            inset: 10px;
            border: 1px solid rgba(201,162,39,0.22);
            border-radius: 2px;
            pointer-events: none;
        }

        @keyframes rise {
            from { opacity: 0; transform: translateY(14px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        .eyebrow {
            font-family: 'Sarabun', sans-serif;
            font-size: 13px;
            letter-spacing: 0.16em;
            color: var(--muted);
            text-align: center;
            margin: 0 0 28px;
        }

        /* เครื่องหมายคำพูดขนาดใหญ่ สไตล์ต้นฉบับ ไม่ใช่ฟอนต์ default ของเบราว์เซอร์ */
        .mark {
            display: block;
            text-align: center;
            font-family: 'Noto Serif Thai', serif;
            font-size: 56px;
            line-height: 1;
            color: var(--gold);
            opacity: 0.8;
            margin-bottom: 8px;
        }

        .quote {
            font-family: 'Noto Serif Thai', serif;
            font-weight: 600;
            font-size: clamp(22px, 4vw, 30px);
            line-height: 1.6;
            text-align: center;
            color: var(--ivory);
            margin: 0;
            min-height: 3.2em;
            transition: opacity 0.25s ease;
        }

        .author {
            margin-top: 28px;
            text-align: center;
            font-size: 15px;
            font-weight: 300;
            color: var(--rust);
            letter-spacing: 0.03em;
            transition: opacity 0.25s ease;
        }
        .author::before { content: "— "; }

        /* ---------- ปุ่มสุ่มคำคมใหม่ ---------- */
        .actions { text-align: center; margin-top: 40px; }

        button#reroll {
            font-family: 'Sarabun', sans-serif;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.04em;
            color: var(--jade-deep);
            background: var(--gold);
            border: none;
            border-radius: 2px;
            padding: 12px 28px;
            cursor: pointer;
            transition: background 0.2s ease, transform 0.15s ease;
        }
        button#reroll:hover { background: var(--gold-soft); }
        button#reroll:active { transform: scale(0.97); }
        button#reroll:focus-visible {
            outline: 2px solid var(--ivory);
            outline-offset: 3px;
        }

        /* ---------- ตราประทับ (signature element) ---------- */
        /* วงกลมสีทองซ้อนมุมขวาล่างของการ์ด แสดงจำนวนครั้งที่เข้าชมแบบ "ตราประทับ" */
        .seal {
            position: absolute;
            right: -18px;
            bottom: -18px;
            width: 96px;
            height: 96px;
            border-radius: 50%;
            background: var(--jade-deep);
            border: 2px solid var(--gold);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }
        .seal::before {
            /* วงแหวนชั้นในของตราประทับ */
            content: "";
            position: absolute;
            inset: 7px;
            border: 1px solid rgba(201,162,39,0.5);
            border-radius: 50%;
        }
        .seal-label {
            font-family: 'Sarabun', sans-serif;
            font-size: 8px;
            letter-spacing: 0.08em;
            color: var(--muted);
            margin-bottom: 2px;
        }
        .seal-number {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 18px;
            font-weight: 500;
            color: var(--gold-soft);
        }

        @media (max-width: 480px) {
            .card { padding: 48px 24px 44px; }
            .seal { width: 80px; height: 80px; right: -12px; bottom: -12px; }
        }

        @media (prefers-reduced-motion: reduce) {
            .card { animation: none; }
            .quote, .author { transition: none; }
        }
    </style>
</head>
<body>
    <div class="card">
        <p class="eyebrow">คำคมประจำขณะนี้</p>
        <span class="mark" aria-hidden="true">“</span>
        <p class="quote" id="quote-text">{{ text }}</p>
        <p class="author" id="quote-author">{{ author }}</p>

        <div class="actions">
            <button id="reroll" type="button">สุ่มคำคมใหม่</button>
        </div>

        <div class="seal" aria-label="จำนวนครั้งที่มีการเรียกดู">
            <span class="seal-label">เข้าชม</span>
            <span class="seal-number" id="view-count">{{ view_count }}</span>
        </div>
    </div>

    <script>
        // เมื่อกดปุ่ม "สุ่มคำคมใหม่" ให้เรียก endpoint /api/quote แบบ JSON
        // แล้วอัปเดตข้อความในหน้าโดยไม่ต้อง reload หน้าเว็บทั้งหมด
        // (endpoint /api/quote ยังคงเพิ่มค่า counter ใน Redis เหมือนเดิม)
        const button = document.getElementById('reroll');
        const quoteEl = document.getElementById('quote-text');
        const authorEl = document.getElementById('quote-author');
        const countEl = document.getElementById('view-count');

        button.addEventListener('click', async () => {
            button.disabled = true;
            quoteEl.style.opacity = 0.2;
            authorEl.style.opacity = 0.2;

            try {
                const res = await fetch('/api/quote');
                const data = await res.json();
                quoteEl.textContent = data.quote.text;
                authorEl.textContent = data.quote.author;
                countEl.textContent = data.total_views;
            } catch (err) {
                // ถ้าเรียก API ไม่สำเร็จ ให้แจ้งในคอนโซลแทนที่จะทำให้หน้าเว็บพัง
                console.error('ไม่สามารถโหลดคำคมใหม่ได้:', err);
            } finally {
                quoteEl.style.opacity = 1;
                authorEl.style.opacity = 1;
                button.disabled = false;
            }
        });
    </script>
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
