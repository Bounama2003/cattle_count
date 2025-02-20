from ultralytics.solutions.solutions import BaseSolution
from ultralytics.utils.plotting import Annotator, colors
import csv
from datetime import datetime
import os
import pyttsx3


class ObjectCounter(BaseSolution):
    """
    Une classe pour gérer le comptage d'objets dans un flux vidéo en temps réel basé sur leur suivi.
    
    La classe permet de compter les objets entrant et sortant d'une région définie. 
    Une méthode finalize() permet de déclencher une alerte vocale à la fin du flux si le nombre de vaches entrantes est insuffisant.
    """

    def __init__(self, **kwargs):
        """Initialise la classe ObjectCounter pour le comptage en temps réel."""
        super().__init__(**kwargs)

        self.in_count = 0  # Compteur pour les objets se dirigeant vers l'intérieur
        self.out_count = 0  # Compteur pour les objets se dirigeant vers l'extérieur
        self.counted_ids = []  # Liste des IDs déjà comptés
        self.saved_ids = []  # Liste des IDs déjà enregistrés dans le CSV
        self.classwise_counts = {}  # Dictionnaire de comptages par classe
        self.region_initialized = False  # Indique si la région de comptage est initialisée
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.expected_count = 10  # Seuil attendu pour le nombre de vaches entrantes

        self.show_in = self.CFG.get("show_in", True)
        self.show_out = self.CFG.get("show_out", True)

    def save_label_to_csv(self, track_id, label):
        """Enregistre le label, track_id et l'heure actuelle dans un fichier CSV dont le nom est basé sur la date."""
        if track_id in self.saved_ids:
            return  # On ne sauvegarde pas plusieurs fois le même ID

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")  # Date du jour

        filename = f'tracked_objects_{current_date}.csv'
        file_exists = os.path.isfile(filename)

        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['track_id', 'label', 'date', 'time'])
            writer.writerow([track_id, label, current_time.split()[0], current_time.split()[1]])
            self.saved_ids.append(track_id)

    def count_objects(self, current_centroid, track_id, prev_position, cls):
        """
        Compte les objets dans une région polygonale ou linéaire basée sur leur trajectoire.
        
        Args:
            current_centroid (Tuple[float, float]): Coordonnées actuelles du centroïde.
            track_id (int): Identifiant unique de l'objet suivi.
            prev_position (Tuple[float, float]): Position précédente de l'objet.
            cls (int): Index de la classe de l'objet.
        """
        if prev_position is None or track_id in self.counted_ids:
            return

        if len(self.region) == 2:  # Région linéaire
            line = self.LineString(self.region)
            if line.intersects(self.LineString([prev_position, current_centroid])):
                if abs(self.region[0][0] - self.region[1][0]) < abs(self.region[0][1] - self.region[1][1]):
                    if current_centroid[0] > prev_position[0]:
                        self.in_count += 1
                        self.classwise_counts[self.names[cls]]["IN"] += 1
                    else:
                        self.out_count += 1
                        self.classwise_counts[self.names[cls]]["OUT"] += 1
                else:
                    if current_centroid[1] > prev_position[1]:
                        self.in_count += 1
                        self.classwise_counts[self.names[cls]]["IN"] += 1
                    else:
                        self.out_count += 1
                        self.classwise_counts[self.names[cls]]["OUT"] += 1
                self.counted_ids.append(track_id)

        elif len(self.region) > 2:  # Région polygonale
            polygon = self.Polygon(self.region)
            if polygon.contains(self.Point(current_centroid)):
                region_width = max([p[0] for p in self.region]) - min([p[0] for p in self.region])
                region_height = max([p[1] for p in self.region]) - min([p[1] for p in self.region])

                if region_width < region_height:
                    if current_centroid[0] > prev_position[0]:
                        self.in_count += 1
                        self.classwise_counts[self.names[cls]]["IN"] += 1
                    else:
                        self.out_count += 1
                        self.classwise_counts[self.names[cls]]["OUT"] += 1
                else:
                    if current_centroid[1] > prev_position[1]:
                        self.in_count += 1
                        self.classwise_counts[self.names[cls]]["IN"] += 1
                    else:
                        self.out_count += 1
                        self.classwise_counts[self.names[cls]]["OUT"] += 1
                self.counted_ids.append(track_id)

    def store_classwise_counts(self, cls):
        """Initialise le comptage par classe si nécessaire."""
        if self.names[cls] not in self.classwise_counts:
            self.classwise_counts[self.names[cls]] = {"IN": 0, "OUT": 0}

    def display_counts(self, im0):
        """Affiche les comptages sur l'image d'entrée."""
        labels_dict = {
            str.capitalize(key): f"{'IN ' + str(value['IN']) if self.show_in else ''} "
            f"{'OUT ' + str(value['OUT']) if self.show_out else ''}".strip()
            for key, value in self.classwise_counts.items()
            if value["IN"] != 0 or value["OUT"] != 0
        }

        if labels_dict:
            self.annotator.display_analytics(im0, labels_dict, (104, 31, 17), (255, 255, 255), 10)

        for track_id in self.track_ids:
            if track_id in self.counted_ids:
                in_count = self.in_count
                label = f"cow ID:{track_id} count at number {in_count}"
                self.annotator.box_label(self.boxes[self.track_ids.index(track_id)], label=label, color=(255, 255, 0))
                self.save_label_to_csv(track_id, label)
    
    def count(self, im0):
        """Traite les images et met à jour les comptages."""
        if not self.region_initialized:
            self.initialize_region()
            self.region_initialized = True

        self.annotator = Annotator(im0, line_width=self.line_width)
        self.extract_tracks(im0)
        self.annotator.draw_region(reg_pts=self.region, color=(104, 0, 123), thickness=self.line_width * 2)

        for box, track_id, cls in zip(self.boxes, self.track_ids, self.clss):
            self.store_tracking_history(track_id, box)
            self.store_classwise_counts(cls)

            label = f"{self.names[cls]} ID: {track_id}"
            self.annotator.box_label(box, label=label, color=colors(cls, True))

            current_centroid = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            prev_position = self.track_history[track_id][-2] if len(self.track_history[track_id]) > 1 else None
            self.count_objects(current_centroid, track_id, prev_position, cls)

        self.display_counts(im0)
        self.display_output(im0)
        return im0

    def finalize(self):
        """
        Méthode à appeler en fin de flux pour vérifier le nombre de vaches entrantes et déclencher l'alerte si nécessaire.
        """
        cow_count = None
        for key, value in self.classwise_counts.items():
            if key.lower() == "cow":
                cow_count = value["IN"]
                break
        if cow_count is not None and cow_count < self.expected_count:
            missing_count=self.expected_count - cow_count
            alert_message = f"Alerte : il manque {missing_count} vaches."
            self.engine.say(alert_message)
            self.engine.runAndWait()
        else:
            print('Ok c\'est super')
