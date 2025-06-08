FROM python:3.11-slim

# Install basic system deps + Chromium-compatible shared libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl unzip gnupg xvfb \
    libnss3 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libasound2 libpangocairo-1.0-0 libpango-1.0-0 libgtk-3-0 \
    libx11-xcb1 libsecret-1-0 libgles2 \
    ca-certificates fonts-liberation libappindicator3-1 lsb-release \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Pre-install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and download Chromium
RUN pip install playwright && playwright install chromium

# Copy source code into container
COPY . /app
WORKDIR /app

EXPOSE 8000

# Start server
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
