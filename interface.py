import json
import os
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="InstaTrace - POC",
    page_icon="🔍",
    layout="wide"
)

st.title("InstaTrace - Proof of Concept")
st.markdown("""
Cette démonstration présente les capacités de détection d'anomalies d'InstaTrace. 
Le système analyse les comportements des utilisateurs et identifie les activités suspectes
en se basant sur des modèles d'apprentissage automatique.
""")

# Définir les utilisateurs
users = [
    {"name": "neila.mansouri@outlook.com", "usual_countries": ["FR", "GB"], "usual_hours": range(8, 22)},
    {"name": "rania.bordjiba@outlook.com", "usual_countries": ["FR", "DZ"], "usual_hours": range(9, 23)},
    {"name": "destiny.hanna@outlook.com", "usual_countries": ["FR", "US"], "usual_hours": range(7, 21)}
]

# Charger les données
@st.cache_data
def load_data():
    if os.path.exists("output/results.csv") and os.path.exists("output/suspicious_cases.csv"):
        results = pd.read_csv("output/results.csv")
        suspicious = pd.read_csv("output/suspicious_cases.csv")
        

        if 'timestamp' in results.columns:
            results['timestamp'] = pd.to_datetime(results['timestamp'])
        if 'timestamp' in suspicious.columns:
            suspicious['timestamp'] = pd.to_datetime(suspicious['timestamp'])
        
        return results, suspicious
    else:
        st.error("Les fichiers de données n'ont pas été trouvés. Veuillez exécuter le script d'analyse au préalable.")
        return pd.DataFrame(), pd.DataFrame()

results_df, suspicious_df = load_data()

if not results_df.empty:
    # Afficher les statistiques générales
    st.header("Tableau de bord")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_events = len(results_df)
        st.metric("Total des événements analysés", total_events)
    
    with col2:
        anomaly_count = len(results_df[results_df['anomaly'] == 'Anomalie'])
        st.metric("Anomalies détectées", anomaly_count, f"{anomaly_count/total_events*100:.1f}%")
    
    with col3:
        high_risk = len(results_df[results_df['anomaly_probability'] > 0.8])
        st.metric("Alertes haute priorité", high_risk)
    
    # Graphique de distribution des probabilités d'anomalie
    st.subheader("Distribution des probabilités d'anomalie")
    
    fig = px.histogram(
        results_df,
        x='anomaly_probability',
        nbins=30,
        color_discrete_sequence=['#3366CC'],
        opacity=0.7
    )
    fig.update_layout(
        xaxis_title="Probabilité d'anomalie",
        yaxis_title="Nombre d'événements"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Graphiques par heure et jour de la semaine
    st.subheader("Répartition des activités")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Graphique par heure
        hour_data = results_df.groupby(['hour_of_day', 'anomaly']).size().reset_index(name='count')
        
        fig = px.bar(
            hour_data, 
            x='hour_of_day', 
            y='count', 
            color='anomaly',
            labels={'hour_of_day': 'Heure de la journée', 'count': 'Nombre d\'événements'},
            title="Activités par heure",
            color_discrete_map={'Normal': '#3366CC', 'Anomalie': '#DC3912'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Graphique par jour de la semaine
        day_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        results_df['day_name'] = results_df['day_of_week'].apply(lambda x: day_names[int(x)] if pd.notna(x) and 0 <= x < 7 else 'Inconnu')
        
        day_data = results_df.groupby(['day_name', 'anomaly']).size().reset_index(name='count')
        
        fig = px.bar(
            day_data, 
            x='day_name', 
            y='count', 
            color='anomaly',
            labels={'day_name': 'Jour de la semaine', 'count': 'Nombre d\'événements'},
            title="Activités par jour",
            color_discrete_map={'Normal': '#3366CC', 'Anomalie': '#DC3912'},
            category_orders={"day_name": day_names}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Activités par pays
    st.subheader("Activités par pays")
    
    country_data = results_df.groupby(['location.countryOrRegion', 'anomaly']).size().reset_index(name='count')
    
    fig = px.bar(
        country_data, 
        x='location.countryOrRegion', 
        y='count', 
        color='anomaly',
        labels={'location.countryOrRegion': 'Pays', 'count': 'Nombre d\'événements'},
        color_discrete_map={'Normal': '#3366CC', 'Anomalie': '#DC3912'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Alertes de haute priorité
    st.header("Alertes de haute priorité")
    
    if not suspicious_df.empty:
        for idx, row in suspicious_df.head(5).iterrows():
            with st.expander(f"Alerte #{idx+1}: {row['user']} - {row['action']} ({row['timestamp']})"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown(f"**Utilisateur:** {row['user']}")
                    st.markdown(f"**Action:** {row['action']}")
                    st.markdown(f"**Date/Heure:** {row['timestamp']}")
                    st.markdown(f"**Pays:** {row.get('location.countryOrRegion', 'Inconnu')}")
                    st.markdown(f"**Appareil:** {row.get('deviceType', 'Inconnu')}")
                    st.markdown(f"**Probabilité d'anomalie:** {row['anomaly_probability']:.2f}")
                
                with col2:
                    # Afficher les raisons de l'alerte
                    st.markdown("### Raisons de l'alerte")
                    
                    reasons = []
                    
                    if 'is_night' in row and row['is_night'] == 1:
                        reasons.append("🕓 Activité en dehors des heures habituelles")
                    
                    normal_countries = []
                    for user_info in [u for u in users if u['name'] in str(row['user'])]:
                        normal_countries = user_info.get('usual_countries', [])
                    
                    if 'location.countryOrRegion' in row and row['location.countryOrRegion'] not in normal_countries and row['location.countryOrRegion'] != 'Unknown':
                        reasons.append(f"🌍 Connexion depuis un pays inhabituel ({row['location.countryOrRegion']})")
                    
                    if 'action' in row and row['action'] in ['download_all_files', 'change_permissions', 'reset_password', 'Modify permissions']:
                        reasons.append(f"⚠️ Action sensible ({row['action']})")
                    
                    if not reasons:
                        reasons.append("🔍 Combinaison inhabituelle de facteurs")
                    
                    for reason in reasons:
                        st.markdown(f"- {reason}")
                    
                    st.markdown("### Recommandations")
                    st.markdown("- Vérifier l'identité de l'utilisateur")
                    st.markdown("- Examiner le contexte de l'activité")
                    st.markdown("- Envisager de bloquer temporairement l'accès si nécessaire")
                    st.markdown("- Renforcer l'authentification pour cet utilisateur")
    
    # Statistiques par utilisateur
    st.header("Statistiques par utilisateur")
    
    # Sélectionner l'utilisateur
    users_list = results_df['user'].unique().tolist()
    selected_user = st.selectbox("Sélectionner un utilisateur", users_list)
    
    # Filtrer les données pour l'utilisateur sélectionné
    user_data = results_df[results_df['user'] == selected_user]
    
    if not user_data.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_user_events = len(user_data)
            st.metric("Total des activités", total_user_events)
        
        with col2:
            user_anomaly_count = len(user_data[user_data['anomaly'] == 'Anomalie'])
            st.metric("Anomalies", user_anomaly_count, f"{user_anomaly_count/total_user_events*100:.1f}%")
        
        with col3:
            countries = user_data['location.countryOrRegion'].nunique()
            st.metric("Pays d'accès uniques", countries)
        
        # Chronologie des activités
        st.subheader("Chronologie des activités")
        
        # S'assurer que timestamp est une colonne datetime
        if 'timestamp' in user_data.columns and not pd.api.types.is_datetime64_any_dtype(user_data['timestamp']):
            user_data['timestamp'] = pd.to_datetime(user_data['timestamp'])
        
        # Trier par timestamp
        user_data_sorted = user_data.sort_values('timestamp')
        
        fig = px.scatter(
            user_data_sorted,
            x='timestamp',
            y='anomaly_probability',
            color='anomaly',
            size='anomaly_probability',
            hover_data=['action', 'location.countryOrRegion', 'hour_of_day'],
            labels={
                'timestamp': 'Date et heure', 
                'anomaly_probability': 'Probabilité d\'anomalie',
                'action': 'Action',
                'location.countryOrRegion': 'Pays',
                'hour_of_day': 'Heure'
            },
            title=f"Chronologie des activités pour {selected_user}",
            color_discrete_map={'Normal': '#3366CC', 'Anomalie': '#DC3912'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Répartition des actions
        st.subheader("Répartition des actions")
        
        action_counts = user_data['action'].value_counts().reset_index()
        action_counts.columns = ['action', 'count']
        
        fig = px.pie(
            action_counts,
            values='count',
            names='action',
            title=f"Actions effectuées par {selected_user}"
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Veuillez charger et analyser des données pour visualiser les résultats.")

# Pied de page
st.markdown("---")
st.markdown("""
<div style="text-align: center">
    <h3>InstaTrace</h3>
    <p>Protéger vos habitudes numériques, anticiper les cybermenaces.</p>
    <p>© 2025 Rania BORDJIBA, Destiny HANNA, Neila Camélia MANSOURI</p>
</div>
""", unsafe_allow_html=True)