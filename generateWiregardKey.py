import base64
from nacl.public import PrivateKey
import os

# === 1. Générer les clés ===
private_key = PrivateKey.generate()
private_key_bytes = bytes(private_key)
public_key_bytes = private_key.public_key.encode()

private_key_b64 = base64.b64encode(private_key_bytes).decode()
public_key_b64 = base64.b64encode(public_key_bytes).decode()

# === 2. Adresses IP (Cloudflare doit te les attribuer via wgcf normalement) ===
ipv4_address = "10.0.0.2/32"  # temporaire/test uniquement
ipv6_address = "2606:4700:110:8b07::2/128"  # placeholder

# === 3. Lire le template (ou le définir ici directement) ===
template = """
[Interface]
PrivateKey = WARP_PRIVATE_KEY_PLACEHOLDER
Address = WARP_ADDRESS_PLACEHOLDER
DNS = 1.1.1.1, 1.0.0.1
MTU = 1280

[Peer]
PublicKey = bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=
AllowedIPs = 0.0.0.0/0
Endpoint = engage.cloudflareclient.com:2408
"""

# === 4. Remplacer les placeholders ===
config = template \
    .replace("WARP_PRIVATE_KEY_PLACEHOLDER", private_key_b64) \
    .replace("WARP_ADDRESS_PLACEHOLDER", f"{ipv4_address}, {ipv6_address}")

# === 5. Sauver dans un fichier .conf ===
output_path = "wgcf.conf"
with open(output_path, "w") as f:
    f.write(config)

# === 6. Afficher le résultat ===
print("✅ Configuration WARP générée :")
print(f"- Clé privée : {private_key_b64}")
print(f"- Clé publique : {public_key_b64}")
print(f"- Fichier généré : {output_path}")
