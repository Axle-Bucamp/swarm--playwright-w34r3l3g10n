FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système pour Playwright
RUN apt-get update && \
    apt-get install -y \
        curl \
        wget \
        gnupg \
        xvfb \
        libgtk-3-0 \
        libxss1 \
        libasound2 \
        libnss3 \
        libx11-xcb1 \
        libdbus-glib-1-2 \
        libxtst6 \
        libxrandr2 \
        libasound2 \
        libpangocairo-1.0-0 \
        libatk1.0-0 \
        libcairo-gobject2 \
        libgtk-3-0 \
        libgdk-pixbuf2.0-0 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxi6 \
        libxext6 \
        libxfixes3 \
        libxrender1 \
        libcairo2 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libatspi2.0-0 \
        libxss1 \
        libgconf-2-4 \
        && rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Installer les navigateurs Playwright
RUN playwright install firefox
RUN playwright install-deps firefox

# Copier le code source
COPY . .

# Créer un utilisateur non-root
RUN useradd -m -u 1000 agent && \
    chown -R agent:agent /app

# Créer les répertoires nécessaires
RUN mkdir -p /tmp/screenshots /tmp/downloads && \
    chown -R agent:agent /tmp/screenshots /tmp/downloads

USER agent

# Exposer le port
EXPOSE 8000

# Variables d'environnement
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Script de démarrage
COPY entrypoint.sh /entrypoint.sh
USER root
RUN chmod +x /entrypoint.sh
USER agent

# Point d'entrée
ENTRYPOINT ["/entrypoint.sh"]

