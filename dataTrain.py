import ipaddress
import json
import os
import random
from datetime import datetime, timedelta

# Dossier de destination
OUTPUT_DIR = "TrainData"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Fonction pour générer une adresse IP aléatoire
def random_ip():
    return str(ipaddress.IPv4Address(random.randint(0, 2**32-1)))

# Fonction pour générer un timestamp dans un intervalle de temps
def random_timestamp(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86399)  # secondes dans une journée
    return (start_date + timedelta(days=random_days, seconds=random_seconds)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

# Définition des utilisateurs
users = [
    {"name": "neila.mansouri@outlook.com", "usual_countries": ["FR", "GB"], "usual_hours": range(8, 22)},
    {"name": "rania.bordjiba@outlook.com", "usual_countries": ["FR", "DZ"], "usual_hours": range(9, 23)},
    {"name": "destiny.hanna@outlook.com", "usual_countries": ["FR", "US"], "usual_hours": range(7, 21)}
]

# Définition des applications habituelles
common_apps = ["Microsoft Office", "Microsoft Teams", "Outlook", "Chrome", "Edge", "Google Drive"]

# Générer des activités normales
def generate_normal_activities(user, num_activities=50):
    activities = []
    start_date = datetime(2024, 12, 1)
    end_date = datetime(2025, 2, 1)
    
    for _ in range(num_activities):
        # Choisir des valeurs habituelles
        country = random.choice(user["usual_countries"])
        timestamp = random_timestamp(start_date, end_date)
        dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        
        # Veiller à ce que l'heure soit dans la plage habituelle de l'utilisateur
        while dt.hour not in user["usual_hours"]:
            timestamp = random_timestamp(start_date, end_date)
            dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        
        activity = {
            "id": f"{random.randint(10000, 99999)}",
            "user": user["name"],
            "timestamp": timestamp,
            "ipAddress": random_ip(),
            "action": random.choice(["login", "view_file", "edit_document", "share_file", "send_email"]),
            "appDisplayName": random.choice(common_apps),
            "deviceType": random.choice(["PC", "MOBILE"]),
            "location": {
                "countryOrRegion": country,
            }
        }
        activities.append(activity)
    
    return activities

# Générer des activités anormales
def generate_abnormal_activities(user, num_activities=5):
    activities = []
    start_date = datetime(2025, 2, 1)
    end_date = datetime(2025, 2, 15)
    
    # Pays inhabituels
    unusual_countries = ["RU", "CN", "BR", "IN", "ZA"]
    unusual_countries = [c for c in unusual_countries if c not in user["usual_countries"]]
    
    for _ in range(num_activities):
        # Choisir des valeurs inhabituelles
        country = random.choice(unusual_countries)
        timestamp = random_timestamp(start_date, end_date)
        dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        
        # Veiller à ce que l'heure soit en dehors de la plage habituelle de l'utilisateur
        all_hours = list(range(24))
        unusual_hours = [h for h in all_hours if h not in user["usual_hours"]]
        
        # Remplacer l'heure par une heure inhabituelle
        dt = dt.replace(hour=random.choice(unusual_hours))
        timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        activity = {
            "id": f"{random.randint(10000, 99999)}",
            "user": user["name"],
            "timestamp": timestamp,
            "ipAddress": random_ip(),
            "action": random.choice(["login", "download_all_files", "change_permissions", "reset_password"]),
            "appDisplayName": random.choice(common_apps),
            "deviceType": random.choice(["PC", "MOBILE"]),
            "location": {
                "countryOrRegion": country,
            }
        }
        activities.append(activity)
    
    return activities

# Générer les données pour chaque utilisateur
all_activities = []

for user in users:
    normal_activities = generate_normal_activities(user, 100)
    abnormal_activities = generate_abnormal_activities(user, 5)
    
    all_activities.extend(normal_activities)
    all_activities.extend(abnormal_activities)

# Mélanger les activités pour qu'elles ne soient pas regroupées par type
random.shuffle(all_activities)

# Enregistrer les données générées
with open(os.path.join(OUTPUT_DIR, "simulated_activities.json"), "w") as f:
    json.dump(all_activities, f, indent=2)

print(f"Données générées et enregistrées dans {OUTPUT_DIR}/simulated_activities.json")