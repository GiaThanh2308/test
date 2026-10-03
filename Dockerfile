FROM python:3.11-slim

# build-essential: insightface biên dịch một phần từ mã nguồn khi cài
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Chỉ tạo admin khi bạn đặt ADMIN_PASSWORD (không còn mật khẩu mặc định ghi sẵn trong image)
CMD ["sh", "-c", "[ -z \"$ADMIN_PASSWORD\" ] || python create_admin.py --username \"${ADMIN_USERNAME:-admin}\" --role admin; exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
