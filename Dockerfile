# Use an official Python base image
FROM python:3.11-slim

# Install Chromium + dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg curl unzip xvfb \
    libnss3 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 \
    libpango-1.0-0 libgtk-3-0 libx11-xcb1 libgtk-4-1 libgraphene-1.0-0 \
    libgstgl-1.0-0 libgstcodecparsers-1.0-0 libavif15 libenchant-2-2 \
    libsecret-1-0 libmanette-0.2-0 libgles2 && \
    apt-get clean

# Install your Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browser binaries
RUN pip install playwright && \
    playwright install chromium

# Copy app code
COPY . /app
WORKDIR /app

# Expose the port and define the entrypoint
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
