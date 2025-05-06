import paho.mqtt.client as mqtt
import ssl
import json
import random
import time

# === CONFIGURATION TLS ===
MQTT_BROKER    = "localhost"
MQTT_PORT      = 8883               # port TLS exposé par le proxy OpenRemote
REALM          = "master"
SERVICE_USER   = "usermqtt"
SERVICE_SECRET = "rrm7eSkDf0nP6Oxd7oIzQDagGiwatiBV"
CLIENT_ID      = "loraherd_sim1"
ASSET_ID       = "6BzWmbabR4gC0OEFARNHB3"

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
client.tls_set(
    ca_certs=None,            # CA système par défaut
    certfile=None,
    keyfile=None,
    cert_reqs=ssl.CERT_NONE,  # ne vérifie pas le certificat (self‑signed)
    tls_version=ssl.PROTOCOL_TLS,
    ciphers=None
)
client.tls_insecure_set(True)  # autorise les certificats invalides

# Authentification
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect

# Connexion au broker TLS
client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
client.loop_start()

# Simulation des données terrain
cities = {
    "Dakar":        {"lat": 14.693425, "lon": -17.447938},
    "Bamako":       {"lat": 12.6392, "lon":  -8.0029},
    "Yamoussoukro": {"lat":  6.8276, "lon":  -5.2893},
    "Paris":        {"lat": 48.8566, "lon":   2.3522}
}

try:
    while True:
        # Génération de valeurs aléatoires
        telemetry = {
            "temperature": round(random.uniform(20.0, 30.0), 1),
            "age":         random.randint(1, 10),
            "poids":       round(random.uniform(40.0, 400.0), 1),
            "active":      random.choice([True, False]),
            "time":        int(time.time()),
        }
        city, coords = random.choice(list(cities.items()))
        telemetry["gps_city"] = city
        telemetry["gps_lat"]  = coords["lat"]
        telemetry["gps_lon"]  = coords["lon"]

        # Publication des attributs classiques
        for attr, value in telemetry.items():
            topic = f"{REALM}/{CLIENT_ID}/writeattributevalue/{attr}/{ASSET_ID}"
            payload = json.dumps(value) if isinstance(value, str) else value
            client.publish(topic, payload)
            print(f"Publié {attr}={value} sur {topic}")

        # Publication GeoJSON pour la carte
        geojson_point = {
            "type": "Point",
            "coordinates": [telemetry["gps_lon"], telemetry["gps_lat"]]
        }
        location_topic = f"{REALM}/{CLIENT_ID}/writeattributevalue/location/{ASSET_ID}"
        client.publish(location_topic, json.dumps(geojson_point))
        print(f"Publié location={geojson_point} sur {location_topic}")

        time.sleep(10)

except KeyboardInterrupt:
    print("Arrêt de la simulation...")
    client.loop_stop()
    client.disconnect()
