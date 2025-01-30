import sqlite3
import streamlit as st
import pandas as pd

# Fonction pour se connecter à la base de données SQLite
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

# Interface Streamlit
st.title("Interface de Gestion des Missions")

# Afficher les missions
st.subheader("Liste des Missions")
missions_df = get_missions()
st.write(missions_df)

# Ajouter une nouvelle mission
st.subheader("Ajouter une Mission")
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
st.subheader("Supprimer une Mission")
mission_to_delete = st.text_input("Entrez l'ID de la mission à supprimer")
delete_button = st.button("Supprimer Mission")
if delete_button:
    delete_mission(mission_to_delete)
    st.success(f"Mission {mission_to_delete} supprimée avec succès!")

# Option pour télécharger la base de données
st.subheader("Télécharger la Base de Données")
if st.button("Télécharger la base de données"):
    with open('missions_drone.db', 'rb') as f:
        st.download_button('Télécharger missions_drone.db', f, file_name='missions_drone.db')
