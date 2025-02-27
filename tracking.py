import numpy as np
from scipy.spatial import distance as dist

# Paramètres du tracking
TRACKING_MAX_DISTANCE = 50   # Distance maximale (en pixels) pour associer une détection à un track existant
TRACKING_MAX_LOST = 5        # Nombre maximal de frames sans association avant de supprimer un track

# Variables globales pour le tracking personnalisé
next_track_id = 0
tracks = []  # Chaque track est un dictionnaire : {"id": id, "bbox": [x1,y1,x2,y2], "centroid": (cx,cy), "lost": n_frames}

def update_tracks(detections):
    """
    Fonction de tracking personnalisée.
    Entrée : 
      - detections : liste de détections au format [x1, y1, x2, y2, conf]
    Retourne une liste de tracks au format [x1, y1, x2, y2, id]
    """
    global next_track_id, tracks, TRACKING_MAX_DISTANCE, TRACKING_MAX_LOST

    # Calcul des centroïdes pour chaque détection
    detection_centroids = []
    for det in detections:
        x1, y1, x2, y2, conf = det
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        detection_centroids.append((cx, cy))
    detection_centroids = np.array(detection_centroids) if detection_centroids else np.empty((0, 2))

    # Si aucun track n'existe, créer un nouveau track pour chaque détection
    if len(tracks) == 0:
        for det in detections:
            new_track = {
                "id": next_track_id,
                "bbox": det[:4],
                "centroid": (int((det[0] + det[2]) / 2), int((det[1] + det[3]) / 2)),
                "lost": 0
            }
            next_track_id += 1
            tracks.append(new_track)
        return [[t["bbox"][0], t["bbox"][1], t["bbox"][2], t["bbox"][3], t["id"]] for t in tracks]

    # Association des détections aux tracks existants
    assigned_detections = set()
    for track in tracks:
        track_centroid = np.array(track["centroid"])
        best_detection_index = None
        best_distance = TRACKING_MAX_DISTANCE  # distance maximale autorisée pour une association
        for i, det_centroid in enumerate(detection_centroids):
            if i in assigned_detections:
                continue
            d = np.linalg.norm(track_centroid - np.array(det_centroid))
            if d < best_distance:
                best_distance = d
                best_detection_index = i
        if best_detection_index is not None:
            # Mise à jour du track avec la détection associée
            det = detections[best_detection_index]
            track["bbox"] = det[:4]
            track["centroid"] = (int((det[0] + det[2]) / 2), int((det[1] + det[3]) / 2))
            track["lost"] = 0
            assigned_detections.add(best_detection_index)
        else:
            # Aucun match trouvé, incrémenter le compteur "lost"
            track["lost"] += 1

    # Suppression des tracks trop "perdus"
    tracks[:] = [track for track in tracks if track["lost"] <= TRACKING_MAX_LOST]

    # Création de nouveaux tracks pour les détections non associées
    for i, det in enumerate(detections):
        if i not in assigned_detections:
            new_track = {
                "id": next_track_id,
                "bbox": det[:4],
                "centroid": (int((det[0] + det[2]) / 2), int((det[1] + det[3]) / 2)),
                "lost": 0
            }
            next_track_id += 1
            tracks.append(new_track)

    # Retourner les tracks au format [x1, y1, x2, y2, id]
    return [[track["bbox"][0], track["bbox"][1], track["bbox"][2], track["bbox"][3], track["id"]] for track in tracks]
