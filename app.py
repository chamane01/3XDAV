import streamlit as st
import sqlite3
import pandas as pd
import folium
import json
import plotly.express as px
from streamlit_folium import st_folium

# Connexion à la base de données SQLite
def connect_db():
    conn = sqlite3.connect('missions_drone.db')
    return conn

# Fonction pour récupérer les données de la table Missions
def get_missions():
    conn = connect_db()
    query = "SELECT * FROM Missions"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Fonction pour ajouter une nouvelle mission à la base de données
def add_mission(id_mission, type_mission, latitude, longitude, date, heure, statut, drone_id, operateur, observations):
    conn = connect_db()
    query = '''INSERT INTO Missions (id_mission, type_mission, latitude, longitude, date, heure, statut, drone_id, operateur, observations)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    conn.execute(query, (id_mission, type_mission, latitude, longitude, date, heure, statut, drone_id, operateur, observations))
    conn.commit()
    conn.close()

# Fonction pour supprimer une mission par son ID
def delete_mission(id_mission):
    conn = connect_db()
    query = "DELETE FROM Missions WHERE id_mission = ?"
    conn.execute(query, (id_mission,))
    conn.commit()
    conn.close()

# Charger les données des routes à partir du fichier JSON
with open("routeQSD.txt", "r") as f:
    routes_data = json.load(f)

# Extraire les coordonnées et noms des routes sous forme de LineStrings
routes_ci = []
for feature in routes_data["features"]:
    if feature["geometry"]["type"] == "LineString":
        routes_ci.append({
            "coords": feature["geometry"]["coordinates"],
            "nom": feature["properties"].get("ID", "Route inconnue")
        })

# Initialisation de l'application Streamlit
st.title("Interface de Gestion des Missions et Dégradations Routières")

# Sidebar pour la navigation
st.sidebar.title("Navigation")
selection = st.sidebar.radio("Choisir une section", ["Gestion des Missions", "Tableau de Bord des Dégradations"])

# Si l'utilisateur choisit "Gestion des Missions"
if selection == "Gestion des Missions":
    st.subheader("Gestion des Missions")
    missions_df = get_missions()
    st.write(missions_df)

    # Ajouter une nouvelle mission
    with st.form(key='add_mission_form'):
        id_mission = st.text_input("ID Mission")
        type_mission = st.selectbox("Type de Mission", ["drone", "voiture", "manuelle", "mixte"])
        latitude = st.number_input("Latitude", format="%.6f")
        longitude = st.number_input("Longitude", format="%.6f")
        date = st.date_input("Date")
        heure = st.time_input("Heure")
        statut = st.selectbox("Statut", ["terminée", "en cours", "planifiée", "annulée"])
        drone_id = st.text_input("ID Drone")
        operateur = st.text_input("Opérateur")
        observations = st.text_area("Observations")
        submit_button = st.form_submit_button(label='Ajouter Mission')
        if submit_button:
            add_mission(id_mission, type_mission, latitude, longitude, date, heure, statut, drone_id, operateur, observations)
            st.success("Mission ajoutée avec succès!")

    # Supprimer une mission
    mission_to_delete = st.text_input("Entrez l'ID de la mission à supprimer")
    delete_button = st.button("Supprimer Mission")
    if delete_button:
        delete_mission(mission_to_delete)
        st.success(f"Mission {mission_to_delete} supprimée avec succès!")

# Si l'utilisateur choisit "Tableau de Bord des Dégradations"
elif selection == "Tableau de Bord des Dégradations":
    st.header("Dégradations Routières : Carte des Inspections Réelles")
    m = folium.Map(location=[6.5, -5], zoom_start=7)
    for route in routes_ci:
        folium.PolyLine(
            locations=[(lat, lon) for lon, lat in route["coords"]],
            color="blue",
            weight=3,
            opacity=0.7,
            tooltip=route["nom"]
        ).add_to(m)
    st_folium(m, width=800, height=600)
