import paho.mqtt.client as mqtt
import ssl
import time

# === CONFIGURATION TLS ===
MQTT_BROKER    = "localhost"
MQTT_PORT      = 8883               # port TLS exposé par le proxy
REALM          = "master"
SERVICE_USER   = "usermqtt"
SERVICE_SECRET = "1aw9FBSoHPYyuiQL9EsVWt0pYWpem31w"
CLIENT_ID      = "loraherd_temp_sim"
ASSET_ID       = "2AMcEvCgIAahRe835h31dZ"  # récupéré dans l'URL de l'asset

USERNAME = f"{REALM}:{SERVICE_USER}"
PASSWORD = SERVICE_SECRET

# Callback connexion
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connecté avec succès au broker MQTT TLS")
    else:
        print("❌ Erreur de connexion TLS, code:", rc)

# Initialisation du client MQTT
client = mqtt.Client(client_id=CLIENT_ID)

# --- Activation de TLS ---
client.tls_set(         # passe le client en mode TLS :contentReference[oaicite:0]{index=0}
    ca_certs=None,       # utilise les CA racines système
    certfile=None,
    keyfile=None,
    cert_reqs=ssl.CERT_NONE,       # ne vérifie pas le certificat (self‑signed)
    tls_version=ssl.PROTOCOL_TLS,  # version TLS par défaut
    ciphers=None
)
client.tls_insecure_set(True)  # autorise les certificats invalides :contentReference[oaicite:1]{index=1}

# Authentification
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect

# Connexion au broker TLS
client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
client.loop_start()

# Publication d’une mesure unique de température
temperature = 25.3
topic = f"{REALM}/{CLIENT_ID}/writeattributevalue/temperature/{ASSET_ID}"
client.publish(topic, temperature)
print(f"Publié temperature={temperature} sur {topic}")

time.sleep(2)
client.loop_stop()
client.disconnect()
