import cv2
import numpy as np
import argparse
import imutils
import time
from scipy.spatial import distance as dist
import datetime
from detection import load_model, get_cow_class
from tracking import update_tracks
from alert import init_engine, say_alert, log_alert

# Facteur de conversion des pixels en mètres
PIXEL_TO_METER = 0.00026458  # Exemple : 1px = 0.00026458 m

# Parser des arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", type=str, default="vid.mp4",
                help="Chemin vers le fichier vidéo (optionnel)")
ap.add_argument("-o", "--output", type=str, default="",
                help="Chemin vers le fichier vidéo de sortie (optionnel)")
ap.add_argument("-d", "--display", type=int, default=1,
                help="Afficher ou non les frames de sortie")
ap.add_argument("-t", "--threshold", type=float, default=0.1,
                help="Seuil de distance (en mètres) pour déclencher l'alerte d'isolement")
args = vars(ap.parse_args())

# Chargement du modèle YOLO et récupération de la classe "cow"
model = load_model("yolo11n.pt")
cow_class = get_cow_class(model)

# Initialisation du moteur d'alerte vocale
engine = init_engine()

# Accès à la vidéo ou à la webcam
print("[INFO] Accès à la vidéo/caméra...")
vs = cv2.VideoCapture(args["video"] if args["video"] != "" else 0)
time.sleep(2.0)

writer = None

while True:
    ret, frame = vs.read()
    if not ret:
        break

    frame = imutils.resize(frame, width=700)

    # Détection avec YOLO
    results = model(frame)
    detections = []
    for r in results:
        for box in r.boxes.data:
            x1, y1, x2, y2, conf, cls = box.tolist()
            # Filtrer pour la classe "cow"
            if int(cls) == cow_class:
                detections.append([x1, y1, x2, y2, conf])
    
    # Mise à jour du tracker personnalisé
    tracks_out = update_tracks(detections)

    # Listes pour stocker les centroïdes et IDs des vaches
    cow_centroids = []
    cow_ids = []
    
    # Affichage des bounding boxes et des IDs sur le frame
    for track in tracks_out:
        x1, y1, x2, y2, track_id = track
        cX = int((x1 + x2) / 2)
        cY = int((y1 + y2) / 2)
        cow_centroids.append((cX, cY))
        cow_ids.append(int(track_id))
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(frame, f"ID {int(track_id)}", (int(x1), int(y1)-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Conversion en array pour faciliter les calculs
    cow_centroids = np.array(cow_centroids)
    isolated_ids = []
    if len(cow_centroids) >= 2:
        # Calcul du centroïde du troupeau (moyenne des positions)
        group_centroid = np.mean(cow_centroids, axis=0)
        cv2.circle(frame, (int(group_centroid[0]), int(group_centroid[1])), 5, (255, 255, 0), -1)
        for i in range(len(cow_centroids)):
            d_pixels = np.linalg.norm(cow_centroids[i] - group_centroid)
            d_meters = d_pixels * PIXEL_TO_METER
            cv2.putText(frame, f"{d_meters:.2f} m", (cow_centroids[i][0] + 5, cow_centroids[i][1] + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            # Si la distance dépasse le seuil, la vache est considérée isolée
            if d_meters > args["threshold"]:
                isolated_ids.append(cow_ids[i])
                cv2.circle(frame, (cow_centroids[i][0], cow_centroids[i][1]), 8, (0, 0, 255), -1)
    
    # Déclenchement de l'alerte en cas de vaches isolées
    if len(isolated_ids) > 0:
        alert_msg = "Alerte! Vaches isolées ID: " + ", ".join(map(str, isolated_ids))
        print("[ALERTE]", alert_msg)
        log_alert(alert_msg)
        say_alert(engine, alert_msg)
    
    # Optionnel : Afficher les distances entre chaque paire de vaches
    if len(cow_centroids) >= 2:
        D_pixels = dist.cdist(cow_centroids, cow_centroids, metric="euclidean")
        for i in range(len(cow_centroids)):
            for j in range(i+1, len(cow_centroids)):
                mid_point = (int((cow_centroids[i][0] + cow_centroids[j][0]) / 2),
                             int((cow_centroids[i][1] + cow_centroids[j][1]) / 2))
                d_meters = D_pixels[i, j] * PIXEL_TO_METER
                cv2.putText(frame, f"{d_meters:.2f} m", mid_point,
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
    
    # Affichage du frame final
    cv2.imshow("Surveillance des vaches", frame)
    
    # Sauvegarde dans une vidéo si le paramètre de sortie est défini
    if args["output"] != "" and writer is None:
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        writer = cv2.VideoWriter(args["output"], fourcc, 15,
                                 (frame.shape[1], frame.shape[0]), True)
    if writer is not None:
        writer.write(frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

vs.release()
if writer is not None:
    writer.release()
cv2.destroyAllWindows()
