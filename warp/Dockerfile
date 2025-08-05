FROM alpine:latest

# Installer les dépendances
RUN apk add --no-cache \
    wireguard-tools \
    iproute2 \
    iptables \
    curl \
    bash \
    openssl \
    jq \
    && rm -rf /var/cache/apk/* 

# Télécharger wgcf (Cloudflare WARP configurator)
RUN wget -O /usr/local/bin/wgcf https://github.com/ViRb3/wgcf/releases/download/v2.2.16/wgcf_2.2.16_linux_amd64 \
    && chmod +x /usr/local/bin/wgcf

# Créer l'utilisateur warp
RUN adduser -D -s /bin/bash warp

# Créer les répertoires nécessaires
RUN mkdir -p /etc/wireguard /var/log/warp /opt/warp \
    && chown -R warp:warp /etc/wireguard /var/log/warp /opt/warp

# Copier les scripts et configurations
COPY entrypoint.sh /entrypoint.sh
COPY warp-manager.sh /opt/warp/warp-manager.sh
COPY wgcf-profile.conf.template /etc/wireguard/wgcf.conf.template
COPY wgcf-profile.conf.template /etc/wireguard/wgcf.conf 
# ensure different ips ?
RUN head -n1 /opt/warp/warp-manager.sh

# Rendre les scripts exécutables
RUN chmod +x /entrypoint.sh /opt/warp/warp-manager.sh

# Exposer les ports pour les proxies
EXPOSE 1080 3128 8080

# Variables d'environnement
ENV WARP_INTERFACE=wgcf
ENV WARP_CONFIG=/etc/wireguard/wgcf.conf
ENV ENABLE_SOCKS_PROXY=true
ENV ENABLE_HTTP_PROXY=true
# ENV SOCKS_PORT=1080
ENV HTTP_PORT=3128

# Point d'entrée
ENTRYPOINT ["/entrypoint.sh"]

