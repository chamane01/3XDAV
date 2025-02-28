import streamlit as st
import sqlite3
import pandas as pd
import folium
import plotly.express as px
from streamlit_folium import st_folium
import json
from datetime import datetime

# =============================================================================
# Fonctions de connexion et de gestion de la base de données
# =============================================================================

def connect_db():
    conn = sqlite3.connect('base_donnees_missions.db')
    return conn

def get_missions():
    conn = connect_db()
    query = "SELECT * FROM missions"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_defects():
    conn = connect_db()
    query = "SELECT * FROM defects"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def add_mission(id_mission, operator, appareil_type, nom_appareil, date_mission, troncon):
    conn = connect_db()
    query = '''INSERT INTO missions (id, operator, appareil_type, nom_appareil, date, troncon)
               VALUES (?, ?, ?, ?, ?, ?)'''
    conn.execute(query, (id_mission, operator, appareil_type, nom_appareil, date_mission, troncon))
    conn.commit()
    conn.close()

def delete_mission(id_mission):
    conn = connect_db()
    query = "DELETE FROM missions WHERE id = ?"
    conn.execute(query, (id_mission,))
    conn.commit()
    conn.close()

# =============================================================================
# Chargement des données géographiques (routes) depuis un fichier JSON
# =============================================================================

try:
    with open("routeQSD.txt", "r") as f:
        routes_data = json.load(f)
except Exception as e:
    st.error("Erreur lors du chargement des données de routes : " + str(e))
    routes_data = {"features": []}

routes_list = []
for feature in routes_data.get("features", []):
    if feature["geometry"]["type"] == "LineString":
        routes_list.append({
            "coords": feature["geometry"]["coordinates"],
            "nom": feature["properties"].get("ID", "Route inconnue")
        })

# Mapping pour attribuer des couleurs aux classes de défauts (optionnel)
classe_colors = {
    "deformations ornierage": "red",
    "fissurations": "blue",
    "faiençage": "green",
    "fissure de retrait": "purple",
    "fissure anarchique": "orange",
    "reparations": "pink",
    "nid de poule": "brown",
    "fluage": "yellow",
    "arrachements": "gray",
    "depot de terre": "cyan",
    "assainissements": "magenta",
    "envahissement vegetations": "teal",
    "chaussée detruite": "black",
    "denivellement accotement": "darkblue"
}

# =============================================================================
# Initialisation de l'application Streamlit
# =============================================================================

st.title("🛣️ Dashboard – Missions & Défauts Routiers")

# Navigation via la sidebar
st.sidebar.title("Navigation")
section = st.sidebar.radio("Choisir une section", ["Tableau de Bord des Défauts", "Gestion des Missions"])

# =============================================================================
# Section 1 : Gestion des Missions
# =============================================================================
if section == "Gestion des Missions":
    st.header("Gestion des Missions")
    
    # Afficher la liste des missions
    st.subheader("Liste des Missions")
    missions_df = get_missions()
    st.dataframe(missions_df)
    
    # Formulaire pour ajouter une nouvelle mission
    st.subheader("Ajouter une Mission")
    with st.form(key='add_mission_form'):
        id_mission = st.text_input("ID Mission")
        operator = st.text_input("Opérateur")
        appareil_type = st.selectbox("Type d'appareil", ["Drone", "Voiture", "Manuelle", "Mixte"])
        nom_appareil = st.text_input("Nom de l'appareil")
        date_mission = st.date_input("Date de la mission", datetime.today())
        troncon = st.text_input("Tronçon")
        
        submit_add = st.form_submit_button("Ajouter la Mission")
        if submit_add:
            add_mission(id_mission, operator, appareil_type, nom_appareil, str(date_mission), troncon)
            st.success("Mission ajoutée avec succès!")
    
    # Formulaire pour supprimer une mission
    st.subheader("Supprimer une Mission")
    mission_id_to_delete = st.text_input("Entrer l'ID de la mission à supprimer")
    if st.button("Supprimer la Mission"):
        delete_mission(mission_id_to_delete)
        st.success(f"Mission {mission_id_to_delete} supprimée avec succès!")
    
    # Option pour télécharger la base de données
    st.subheader("Télécharger la Base de Données")
    if st.button("Télécharger la base de données"):
        with open('base_donnees_missions.db', 'rb') as f:
            st.download_button('Télécharger base_donnees_missions.db', f, file_name='base_donnees_missions.db')

# =============================================================================
# Section 2 : Tableau de Bord des Défauts
# =============================================================================
elif section == "Tableau de Bord des Défauts":
    st.header("Tableau de Bord des Défauts")
    
    defects_df = get_defects()
    
    # Conversion de la colonne date en datetime
    defects_df['date'] = pd.to_datetime(defects_df['date'], errors='coerce')
    
    # Filtres dans la sidebar pour les défauts
    st.sidebar.subheader("Filtres pour Défauts")
    unique_routes = defects_df['routes'].dropna().unique().tolist()
    selected_routes = st.sidebar.multiselect("Sélectionner les routes", unique_routes, default=unique_routes)
    
    if not defects_df.empty:
        min_date = defects_df['date'].min().date()
        max_date = defects_df['date'].max().date()
    else:
        min_date = max_date = datetime.today().date()
    
    date_range = st.sidebar.date_input("Plage de dates", [min_date, max_date])
    
    # Filtrer les défauts selon les critères
    filtered_defects = defects_df[
        (defects_df['routes'].isin(selected_routes)) &
        (defects_df['date'] >= pd.to_datetime(date_range[0])) &
        (defects_df['date'] <= pd.to_datetime(date_range[1]))
    ]
    
    # Affichage des indicateurs clés
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Défauts", defects_df.shape[0])
    with col2:
        st.metric("Défauts filtrés", filtered_defects.shape[0])
    with col3:
        st.metric("Nombre de Missions", get_missions().shape[0])
    
    # Carte interactive avec Folium
    st.subheader("Carte Interactive des Défauts")
    # Centrer la carte sur la moyenne des coordonnées filtrées
    if not filtered_defects.empty:
        avg_lat = filtered_defects['lat'].mean()
        avg_lon = filtered_defects['longitude'].mean()
    else:
        avg_lat, avg_lon = 5.237, -3.6349
        
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)
    
    # Afficher les routes (issue du fichier JSON)
    for route in routes_list:
        # Conversion des coordonnées : on suppose qu'elles sont en [lon, lat]
        line_coords = [(coord[1], coord[0]) for coord in route["coords"]]
        folium.PolyLine(
            locations=line_coords,
            color="blue",
            weight=3,
            opacity=0.7,
            tooltip=route["nom"]
        ).add_to(m)
    
    # Ajouter les défauts sur la carte
    for idx, row in filtered_defects.iterrows():
        # Utiliser la couleur enregistrée, ou la couleur associée à la classe
        color = row['couleur'] if pd.notnull(row['couleur']) else classe_colors.get(row['classe'].lower(), "gray")
        folium.CircleMarker(
            location=[row['lat'], row['longitude']],
            radius=3 + row['gravite'] * 2,
            color=color,
            fill=True,
            fill_color=color,
            popup=(
                f"ID : {row['id']}<br>"
                f"Classe : {row['classe']}<br>"
                f"Gravité : {row['gravite']}<br>"
                f"Route : {row['routes']}<br>"
                f"Date : {row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else 'N/A'}"
            ),
            tooltip=f"{row['classe']} (Gravité {row['gravite']})"
        ).add_to(m)
    
    st_folium(m, width=700, height=500)
    
    # Visualisations avec Plotly
    st.sub
