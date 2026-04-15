FROM python:3.12-slim

# Install Chrome + dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg2 \
    unzip \
    curl \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (required by HF Spaces)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py server.py extract_urls.py extract_event_details.py ./
COPY src/ ./src/
COPY templates/ ./templates/

# Create city data directories with correct permissions
RUN mkdir -p Charleroi La_Louvière Liège Mons Namur static \
    && chown -R appuser:appuser /app

# Copy existing data if present
COPY --chown=appuser:appuser Charleroi/ ./Charleroi/
COPY --chown=appuser:appuser La_Louvière/ ./La_Louvière/
COPY --chown=appuser:appuser Liège/ ./Liège/
COPY --chown=appuser:appuser Mons/ ./Mons/
COPY --chown=appuser:appuser Namur/ ./Namur/

USER appuser

# HF Spaces uses port 7860
ENV PORT=7860
EXPOSE 7860

CMD ["python", "server.py"]
