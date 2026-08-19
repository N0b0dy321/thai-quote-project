# Dockerfile
# ใช้สำหรับ build image ของ Flask application (Thai Quote App)
# นี่คือ image ที่สร้างขึ้นเองทั้งหมด ไม่ได้ copy มาจากที่อื่น

# ---------- STAGE 1: BASE IMAGE ----------
# เลือกใช้ python:3.12-slim เป็น base image
# "slim" คือเวอร์ชันที่ตัดไลบรารีที่ไม่จำเป็นออก ทำให้ image มีขนาดเล็กลง
FROM python:3.12-slim

# ---------- METADATA ----------
# กำหนดผู้ดูแล/เจ้าของ image (เปลี่ยนเป็นชื่อ-นักศึกษาของตัวเอง)
LABEL maintainer="student@example.com"
LABEL description="Thai Quote of the Day - Flask backend image"

# ---------- ENVIRONMENT VARIABLES ----------
# ปิดการสร้างไฟล์ .pyc เพื่อลดขนาด image และลด I/O ที่ไม่จำเป็น
ENV PYTHONDONTWRITEBYTECODE=1
# บังคับให้ output ของ Python ถูก flush ออกทันที ไม่ถูก buffer
# ทำให้เราเห็น log แบบ real-time เวลารัน container
ENV PYTHONUNBUFFERED=1

# ---------- WORKING DIRECTORY ----------
# ตั้ง working directory ภายใน container เป็น /app
# คำสั่งถัดไปทั้งหมดจะทำงานภายใต้ path นี้
WORKDIR /app

# ---------- CACHE LAYER OPTIMIZATION ----------
# copy เฉพาะไฟล์ requirements.txt เข้ามาก่อน แล้วค่อย install
# เหตุผล: ถ้าโค้ดใน app.py เปลี่ยนแต่ requirements.txt ไม่เปลี่ยน
# Docker จะใช้ cache ของ layer นี้ ไม่ต้อง pip install ใหม่ทุกครั้ง ทำให้ build เร็วขึ้น
COPY requirements.txt .

# ---------- INSTALL DEPENDENCIES ----------
# --no-cache-dir : ไม่เก็บ cache ของ pip ไว้ใน image เพื่อลดขนาด image
# --upgrade pip  : อัปเดต pip ให้เป็นเวอร์ชันล่าสุดก่อน install package อื่น
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---------- COPY SOURCE CODE ----------
# copy source code ทั้งหมดของแอป (app.py, quotes.py) เข้าไปใน image
# ทำหลัง install dependencies เพื่อให้ cache layer ด้านบนยังใช้งานได้เวลาแก้แค่โค้ด
COPY . .

# ---------- CREATE NON-ROOT USER ----------
# สร้าง user ธรรมดาชื่อ appuser แทนการรันด้วย root
# เพื่อความปลอดภัย (security best practice) ลด privilege ของ process ภายใน container
RUN useradd --create-home appuser
USER appuser

# ---------- NETWORK PORT ----------
# ประกาศ (เอกสารประกอบ) ว่า container นี้เปิดใช้งาน port 5000 ภายใน
# EXPOSE ไม่ได้เปิด port จริง แค่เป็นการบอก intent ให้คนอ่าน Dockerfile เข้าใจ
EXPOSE 5000

# ---------- HEALTHCHECK ----------
# ให้ Docker คอยตรวจสอบสุขภาพของ container ทุก 30 วินาที
# โดยยิง request ไปที่ endpoint /health ที่เราสร้างไว้ใน app.py
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# ---------- START COMMAND ----------
# ใช้ gunicorn (production-grade WSGI server) แทนการรันด้วย python app.py ตรง ๆ
# -w 2         : จำนวน worker process 2 ตัว รองรับ concurrent request
# -b 0.0.0.0:5000 : bind ให้รับ request จากทุก network interface ที่ port 5000
# app:app      : ชี้ไปที่ตัวแปร "app" (Flask instance) ในไฟล์ app.py
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
