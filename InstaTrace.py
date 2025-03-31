import ipaddress
import json
import os
import re
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Configuration
LOGS_DIR = "TrainData/"
CONTAMINATION = 0.05  # % d'anomalies attendues
OUTPUT_DIR = "output"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Fonction pour extraire le pays à partir de l'adresse IP ou de la chaîne de localisation
def extract_country(row):
    if pd.notna(row.get('Activity Country')) and row['Activity Country'] != "":
        return row['Activity Country']
    
    if pd.notna(row.get('Device Last Location')) and isinstance(row['Device Last Location'], str):
        match = re.search(r'Country ISO: (\w+)', row['Device Last Location'])
        if match:
            return match.group(1)
    
    return "Unknown"

# Fonction pour extraire l'heure de la journée (pour détecter les accès inhabituels)
def extract_hour(timestamp):
    if pd.isna(timestamp):
        return -1
    try:
        if isinstance(timestamp, str):
            # Essayer différents formats de date
            for fmt in ["%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%dT%H:%M:%S.%fZ"]:
                try:
                    dt = datetime.strptime(timestamp, fmt)
                    return dt.hour
                except ValueError:
                    continue
        return timestamp.hour if hasattr(timestamp, 'hour') else -1
    except:
        return -1

# Fonction pour normaliser les logs provenant de différentes sources
def normalize_logs(logs):
    normalized = []
    
    for log in logs:
        # Déterminer la source du log et normaliser en conséquence
        if 'google_takeout' in log:
            # Traiter les logs Google
            if 'Activités _ liste des services Google auxquels vos' in log['google_takeout']:
                for activity in log['google_takeout']['Activités _ liste des services Google auxquels vos']:
                    if not isinstance(activity, dict):
                        continue
                    
                    normalized_log = {
                        'user': str(activity.get('Gaia ID', 'unknown')),
                        'timestamp': activity.get('Activity Timestamp'),
                        'ipAddress': activity.get('IP Address', 'unknown'),
                        'action': 'google_activity',
                        'appDisplayName': activity.get('Product Name', 'Google'),
                        'deviceType': 'unknown',
                        'location': {'countryOrRegion': extract_country(activity)}
                    }
                    
                    # Extraire le type d'appareil à partir du User Agent
                    if pd.notna(activity.get('User Agent String')):
                        if 'MOBILE' in activity['User Agent String']:
                            normalized_log['deviceType'] = 'MOBILE'
                        else:
                            normalized_log['deviceType'] = 'PC'
                    
                    normalized.append(normalized_log)
            
            # Traiter les appareils
            if 'Appareils _ liste des appareils (par exemple, Nest' in log['google_takeout']:
                for device in log['google_takeout']['Appareils _ liste des appareils (par exemple, Nest']:
                    if not isinstance(device, dict):
                        continue
                    
                    # Extraire l'heure de dernière activité
                    last_activity_time = None
                    if pd.notna(device.get('Device Last Location')) and isinstance(device['Device Last Location'], str):
                        match = re.search(r'Last Activity Time: ([\d-]+ [\d:]+) UTC', device['Device Last Location'])
                        if match:
                            last_activity_time = match.group(1)
                    
                    normalized_log = {
                        'user': str(device.get('Gaia ID', 'unknown')),
                        'timestamp': last_activity_time,
                        'ipAddress': 'unknown',
                        'action': 'device_login',
                        'appDisplayName': device.get('OS', 'Unknown'),
                        'deviceType': device.get('Device Type', 'Unknown'),
                        'location': {'countryOrRegion': extract_country(device)}
                    }
                    normalized.append(normalized_log)
        
        # Microsoft logs
        elif 'id' in log and 'activity' in log and 'time' in log:
            normalized_log = {
                'user': log.get('targetUser', 'unknown'),
                'timestamp': log.get('time'),
                'ipAddress': 'unknown',
                'action': log.get('activity'),
                'appDisplayName': 'Microsoft',
                'deviceType': 'Unknown',
                'location': {'countryOrRegion': 'Unknown'}
            }
            
            # Si l'initiateur est présent
            if 'initiatedBy' in log and 'user' in log['initiatedBy']:
                normalized_log['initiator'] = log['initiatedBy']['user']
                normalized_log['initiatorRole'] = log['initiatedBy'].get('role', 'Unknown')
            
            normalized.append(normalized_log)
        
        # Si c'est déjà dans un format similaire à celui que nous attendons
        elif isinstance(log, dict) and 'user' in log:
            normalized.append(log)
    
    return normalized

# Charger tous les fichiers JSON du dossier
all_logs = []

# Parcourir tous les fichiers du répertoire
for filename in os.listdir(LOGS_DIR):
    if filename.endswith('.json'):
        with open(os.path.join(LOGS_DIR, filename), 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
                if isinstance(data, list):
                    all_logs.extend(data)
                else:
                    all_logs.append(data)
            except json.JSONDecodeError:
                print(f"Erreur lors du décodage de {filename}. Fichier ignoré.")

# Normaliser les logs
normalized_logs = normalize_logs(all_logs)

# Convertir en DataFrame
df = pd.json_normalize(normalized_logs)

# Assurons-nous que les colonnes essentielles existent
required_columns = ['user', 'timestamp', 'action', 'deviceType', 'location.countryOrRegion']
for col in required_columns:
    if col not in df.columns:
        df[col] = 'Unknown'

# Nettoyage des données
df.fillna('Unknown', inplace=True)

# Conversion des timestamps en datetime
if 'timestamp' in df.columns:
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    # Pour les timestamps non valides, utiliser une date par défaut
    default_date = pd.to_datetime('2024-01-01')
    df.loc[df['timestamp'].isna(), 'timestamp'] = pd.to_datetime('2024-01-01', utc=True)  
      
    # Créer des caractéristiques temporelles
    df['hour_of_day'] = df['timestamp'].apply(lambda x: x.hour)
    df['day_of_week'] = df['timestamp'].apply(lambda x: x.dayofweek)
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    df['is_night'] = df['hour_of_day'].apply(lambda x: 1 if (x < 6 or x >= 22) else 0)

# Création de caractéristiques supplémentaires
df['action_category'] = df['action'].apply(lambda x: x.split('_')[0] if '_' in x else x)

# Regroupement par utilisateur et calcul des statistiques
user_stats = df.groupby('user').agg({
    'timestamp': ['count'],
    'is_night': ['mean'],
    'is_weekend': ['mean'],
    'location.countryOrRegion': lambda x: len(set(x))  # Nombre unique de pays
}).reset_index()

user_stats.columns = ['user', 'activity_count', 'night_activity_ratio', 'weekend_activity_ratio', 'unique_countries']

# Fusion avec le DataFrame principal
df = pd.merge(df, user_stats, on='user', how='left')

# Préparation des données pour le modèle
# Sélection des fonctionnalités pertinentes pour la détection d'anomalies
features = [
    'hour_of_day', 'day_of_week', 'is_weekend', 'is_night', 
    'activity_count', 'night_activity_ratio', 'weekend_activity_ratio', 'unique_countries'
]

# S'assurer que toutes les caractéristiques sont numériques
for feature in features:
    if feature in df.columns:
        df[feature] = pd.to_numeric(df[feature], errors='coerce')
    else:
        print(f"Avertissement: Caractéristique '{feature}' non trouvée dans les données.")
        df[feature] = 0

# Remplacer les valeurs NaN par 0
df[features] = df[features].fillna(0)

# Normalisation des données
scaler = StandardScaler()
df_scaled = scaler.fit_transform(df[features])

# Entraînement du modèle de détection d'anomalies
model = IsolationForest(
    n_estimators=100,
    contamination=CONTAMINATION,
    random_state=42,
    n_jobs=-1
)

# Prédiction des anomalies
df['anomaly_score'] = model.fit_predict(df_scaled)
df['anomaly'] = df['anomaly_score'].apply(lambda x: 'Anomalie' if x == -1 else 'Normal')
df['anomaly_probability'] = model.decision_function(df_scaled)
df['anomaly_probability'] = 1 - (df['anomaly_probability'] - df['anomaly_probability'].min()) / (df['anomaly_probability'].max() - df['anomaly_probability'].min())

# Définition des seuils d'anomalie
df['anomaly_level'] = pd.cut(
    df['anomaly_probability'], 
    bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0], 
    labels=['Très faible', 'Faible', 'Moyen', 'Élevé', 'Très élevé']
)

# Identifier les cas très suspects (haut niveau d'anomalie)
suspicious_cases = df[df['anomaly_probability'] > 0.8].sort_values('anomaly_probability', ascending=False)

print(f"Analyse complète. {len(suspicious_cases)} cas suspects identifiés sur {len(df)} événements.")

# Génération de visualisations
plt.figure(figsize=(10, 6))
plt.hist(df['anomaly_probability'], bins=30, color='skyblue', edgecolor='black')
plt.title("Distribution des probabilités d'anomalie")
plt.xlabel("Probabilité d'anomalie")
plt.ylabel("Nombre d'événements")
plt.savefig(os.path.join(OUTPUT_DIR, "anomaly_distribution.png"))
plt.close()

# Visualisation par heure de la journée
plt.figure(figsize=(12, 6))
normal_by_hour = df[df['anomaly'] == 'Normal'].groupby('hour_of_day').size()
anomaly_by_hour = df[df['anomaly'] == 'Anomalie'].groupby('hour_of_day').size()

# Assurez-vous que toutes les heures sont présentes
all_hours = range(24)
normal_values = [normal_by_hour.get(hour, 0) for hour in all_hours]
anomaly_values = [anomaly_by_hour.get(hour, 0) for hour in all_hours]

plt.bar(all_hours, normal_values, label='Normal', color='blue', alpha=0.6)
plt.bar(all_hours, anomaly_values, bottom=normal_values, label='Anomalie', color='red', alpha=0.6)
plt.title("Répartition des activités normales et anormales par heure de la journée")
plt.xlabel("Heure de la journée")
plt.ylabel("Nombre d'événements")
plt.xticks(all_hours)
plt.legend()
plt.savefig(os.path.join(OUTPUT_DIR, "anomaly_by_hour.png"))
plt.close()

# Cas suspects en tableau
if not suspicious_cases.empty:
    plt.figure(figsize=(14, len(suspicious_cases.head(10)) * 0.5 + 2))
    
    # top10 des cas dans le tableau
    top_10_suspicious = suspicious_cases.head(10).reset_index(drop=True)
    
    table_data = []
    for i, row in top_10_suspicious.iterrows():
        table_data.append([
            i+1,
            row['user'],
            row['action'],
            row['location.countryOrRegion'],
            f"{row['anomaly_probability']:.2f}"
        ])

    # Créer un tableau
    plt.axis('off')
    table = plt.table(
        cellText=table_data,
        colLabels=['#', 'Utilisateur', 'Action', 'Pays', 'Probabilité'],
        loc='center',
        cellLoc='center'
    )

    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 1.5)

    for i in range(len(table_data)):
        prob = float(table_data[i][4])
        color = (1, 1 - prob, 1 - prob)
        
        for j in range(5):
            table[i+1, j].set_facecolor(color)
    
    plt.title("Top 10 des événements suspects", fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "top_suspicious.png"))
    plt.close()

# Exportation des résultats
df.to_csv(os.path.join(OUTPUT_DIR, "results.csv"), index=False)
suspicious_cases.to_csv(os.path.join(OUTPUT_DIR, "suspicious_cases.csv"), index=False)

# rapport textuel des cas suspects
with open(os.path.join(OUTPUT_DIR, "anomaly_report.txt"), "w") as f:
    f.write("RAPPORT DE DÉTECTION D'ANOMALIES INSTA'TRACE\n")
    f.write("==========================================\n\n")
    f.write(f"Date de l'analyse: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Nombre total d'événements analysés: {len(df)}\n")
    f.write(f"Nombre d'anomalies détectées: {len(df[df['anomaly'] == 'Anomalie'])}\n\n")
    
    f.write("ALERTES DE HAUTE PRIORITÉ\n")
    f.write("------------------------\n\n")
    
    if not suspicious_cases.empty:
        for idx, row in suspicious_cases.iterrows():
            f.write(f"ALERTE #{idx+1} (Niveau de risque: {row['anomaly_level']})\n")
            f.write(f"  Utilisateur: {row['user']}\n")
            f.write(f"  Action: {row['action']}\n")
            f.write(f"  Timestamp: {row['timestamp']}\n")
            f.write(f"  Pays: {row['location.countryOrRegion']}\n")
            f.write(f"  Appareil: {row['deviceType']}\n")
            f.write(f"  Probabilité d'anomalie: {row['anomaly_probability']:.2f}\n")
            
            # recommandations basées sur le type d'alerte
            if row['is_night'] == 1:
                f.write("  Raison potentielle: Activité inhabituelle pendant la nuit\n")
            if row['location.countryOrRegion'] != 'FR' and row['location.countryOrRegion'] != 'Unknown':
                f.write("  Raison potentielle: Connexion depuis un pays inhabituel\n")
            
            f.write("\n")
    else:
        f.write("Aucune alerte de haute priorité détectée.\n\n")
    
    # Statistiques par utilisateur
    f.write("STATISTIQUES PAR UTILISATEUR\n")
    f.write("--------------------------\n\n")
    
    for user, data in df.groupby('user'):
        anomaly_count = len(data[data['anomaly'] == 'Anomalie'])
        total_count = len(data)
        f.write(f"Utilisateur: {user}\n")
        f.write(f"  Nombre total d'activités: {total_count}\n")
        f.write(f"  Nombre d'anomalies: {anomaly_count} ({anomaly_count/total_count*100:.1f}%)\n")
        f.write(f"  Pays d'accès: {', '.join(data['location.countryOrRegion'].unique())}\n")
        f.write(f"  Types d'appareils: {', '.join(data['deviceType'].unique())}\n")
        f.write("\n")

print(f"Rapport généré avec succès dans le dossier: {OUTPUT_DIR}")