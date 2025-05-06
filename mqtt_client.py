import requests
import time
import json
from fastapi import FastAPI, HTTPException
import psycopg2
import pandas as pd  # Utilisé pour le prétraitement et la normalisation
import uvicorn
app = FastAPI(title="Data Collection Service")

# === Configuration de l'API REST ThingsBoard ===
THINGSBOARD_API_URL = "https://demo.thingsboard.io/api/plugins/telemetry/DEVICE"
DEVICE_ID = "7c33fa90-dfe9-11ef-9dbc-834dadad7dd9"  # Remplacez par l'ID réel de votre device
JWT_TOKEN = ("Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJmb2ZhbmFib3VuYW"
             "1hNzZAZ21haWwuY29tIiwidXNlcklkIjoiNzUyYWQ0ZDAtZGZlOS0xMWVmLTlk"
             "YmMtODM0ZGFkYWQ3ZGQ5Iiwic2NvcGVzIjpbIlRFTkFOVF9BRE1JTiJdLCJzZX"
             "NzaW9uSWQiOiIxNDZlZjFjZi05NDBmLTQ5NzAtYjZlNy1iY2Q1NWFiNTdkYzEi"
             "LCJleHAiOjE3NDQwMTkzOTcsImlzcyI6InRoaW5nc2JvYXJkLmlvIiwiaWF0Ijox"
             "NzQyMjE5Mzk3LCJmaXJzdE5hbWUiOiJCT1VOQU1BIiwibGFzdE5hbWUiOiJGb2Zh"
             "bmEiLCJlbmFibGVkIjp0cnVlLCJwcml2YWN5UG9saWN5QWNjZXB0ZWQiOnRydWUs"
             "ImlzUHVibGljIjpmYWxzZSwidGVuYW50SWQiOiI3NDFhNzY0MC1kZmU5LTExZWYt"
             "OWRiYy04MzRkYWRhZDdkZDkiLCJjdXN0b21lcklkIjoiMTM4MTQwMDAtMWRkMi0x"
             "MWIyLTgwODAtODA4MDgwODA4MDgwIn0.93Q3me8u3yB1llDUi3tH3qKENbqM7Tvriu6lnEYcmjbIDTv1ufhhx-qS5KlnptK89lkidLjiUv2-aEJtlmVn2A")

def get_telemetry(device_id: str, start_ts: int, end_ts: int, jwt_token: str):
    """
    Interroge l'API REST de ThingsBoard pour récupérer la télémétrie.
    La réponse est attendue sous forme d'un dictionnaire où chaque clé correspond à un champ 
    (par ex. "temperature", "humidity", etc.) et la valeur est une liste de dictionnaires 
    contenant "ts" (timestamp) et "value".
    """
    url = f"{THINGSBOARD_API_URL}/{device_id}/values/timeseries"
    params = {
        "keys": "id,temperature,age,poids,active",  # Les champs attendus
        "startTs": start_ts,
        "endTs": end_ts
    }
    headers = {
        "Content-Type": "application/json",
        "X-Authorization": jwt_token
    }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Erreur lors de la récupération des données de ThingsBoard")
    return response.json()

def process_telemetry_data(data: dict):
    """
    Transforme la réponse de ThingsBoard (où chaque clé est associée à une liste de dicts avec "ts" et "value")
    en une liste de dictionnaires contenant les champs normalisés :
      - time (timestamp en millisecondes)
      - temperature (float)
      - id (string)
      - age (int)
      - poids (float)
      - active (bool)
    Utilise pandas pour réaliser le prétraitement, la normalisation et la fusion sur le timestamp.
    """
    keys = ["temperature", "id", "age", "poids", "active"]
    
    # Créer un DataFrame pour chaque clé, si les données existent
    dfs = {}
    for key in keys:
        if key in data and data[key]:
            df = pd.DataFrame(data[key])
            # On s'assure que les colonnes 'ts' et 'value' sont présentes
            if 'ts' not in df.columns or 'value' not in df.columns:
                continue
            # Convertir ts en chaîne pour faciliter la fusion
            df['ts'] = df['ts'].astype(str)
            # Renommer la colonne value en le nom du champ
            df = df.rename(columns={"value": key})
            # Ne conserver que 'ts' et le champ
            df = df[['ts', key]]
            dfs[key] = df
        else:
            # Si aucune donnée n'existe pour le champ, créer un DataFrame vide
            dfs[key] = pd.DataFrame(columns=["ts", key])
    
    # Fusionner tous les DataFrames sur la colonne 'ts' en effectuant une jointure interne (intersection des timestamps)
    df_merged = None
    for key in keys:
        if df_merged is None:
            df_merged = dfs[key]
        else:
            df_merged = pd.merge(df_merged, dfs[key], on='ts', how='inner')
    
    if df_merged is None or df_merged.empty:
        return []
    
    # Conversion des types de données
    df_merged['time'] = df_merged['ts'].astype(int)
    df_merged['temperature'] = df_merged['temperature'].astype(float)
    df_merged['poids'] = df_merged['poids'].astype(float)
    df_merged['age'] = df_merged['age'].astype(int)
    # Convertir active en bool (on considère "true", "True", "1" comme True)
    df_merged['active'] = df_merged['active'].apply(lambda x: True if str(x).lower() in ["true", "1"] else False)
    df_merged['id'] = df_merged['id'].astype(str)
    
    # Sélectionner les colonnes finales et convertir en liste de dictionnaires
    df_final = df_merged[['time', 'temperature', 'id', 'age', 'poids', 'active']]
    records = df_final.to_dict(orient='records')
    return records

# --- Connexion à PostgreSQL pour le stockage ---
PG_CONN = psycopg2.connect(
    dbname="loradb",
    user="postgres",
    password="passer",
    host="localhost",
    port="5432"
)

def create_table_if_not_exists():
    """Crée la table 'telemetry_data' si elle n'existe pas déjà."""
    with PG_CONN.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_data (
                time BIGINT PRIMARY KEY,
                temperature REAL,
                id TEXT,
                age INTEGER,
                poids REAL,
                active BOOLEAN
            );
        """)
        PG_CONN.commit()

def store_telemetry_data(records: list[dict]):
    """Insère ou met à jour les enregistrements de télémétrie dans PostgreSQL."""
    with PG_CONN.cursor() as cur:
        for record in records:
            cur.execute("""
                INSERT INTO telemetry_data (time, temperature, id, age, poids, active)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (time) DO UPDATE SET
                    temperature = EXCLUDED.temperature,
                    id = EXCLUDED.id,
                    age = EXCLUDED.age,
                    poids = EXCLUDED.poids,
                    active = EXCLUDED.active;
            """, (
                record["time"],
                record["temperature"],
                record["id"],
                record["age"],
                record["poids"],
                record["active"]
            ))
        PG_CONN.commit()

# --- Endpoint FastAPI pour lancer la récupération, le traitement et le stockage des données ---
@app.get("/fetch_and_store")
def fetch_and_store():
    """
    Interroge l'API de ThingsBoard pour récupérer la télémétrie sur la dernière heure,
    nettoie et normalise les données à l'aide de pandas, puis les stocke dans PostgreSQL.
    Renvoie les enregistrements traités.
    """
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - (60 * 60 * 1000)  # Dernière heure en millisecondes
    raw_data = get_telemetry(DEVICE_ID, start_ts, end_ts, JWT_TOKEN)
    processed_records = process_telemetry_data(raw_data)
    create_table_if_not_exists()
    store_telemetry_data(processed_records)
    return {"status": "success", "stored_records": len(processed_records), "data": processed_records}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
