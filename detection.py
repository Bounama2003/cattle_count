from ultralytics import YOLO
import sys

def load_model(model_path="yolo11n.pt"):
    print("[INFO] Chargement du modèle YOLOv11...")
    model = YOLO(model_path)
    return model

def get_cow_class(model):
    names = model.names
    cow_class = None
    for key, value in names.items():
        if value.lower() == "cow":
            cow_class = key
            break
    if cow_class is None:
        print("[ERREUR] La classe 'cow' n'a pas été trouvée dans le modèle.")
        sys.exit(1)
    print(f"[INFO] Classe 'cow' détectée avec l'indice {cow_class}")
    return cow_class
