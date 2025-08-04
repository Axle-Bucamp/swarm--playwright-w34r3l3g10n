FROM alpine:latest

# Installer Tor et les dépendances
RUN apk add --no-cache \
    tor \
    curl \
    bash \
    && rm -rf /var/cache/apk/*

# Créer l'utilisateur tor
#RUN adduser -D -s /bin/bash tor

# Créer les répertoires nécessaires
RUN mkdir -p /var/lib/tor /var/log/tor /etc/tor \
    && chown -R tor:tor /var/lib/tor /var/log/tor /etc/tor

# Copier la configuration Tor
COPY torrc /etc/tor/torrc
COPY entrypoint.sh /entrypoint.sh

# Rendre le script exécutable
RUN chmod +x /entrypoint.sh

# Exposer le port SOCKS
EXPOSE 9050

# Changer vers l'utilisateur tor
USER tor

# Point d'entrée
ENTRYPOINT ["/entrypoint.sh"]

