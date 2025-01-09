import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# Fonction pour se connecter à la base de données PostgreSQL
def connect_to_db():
    conn = psycopg2.connect(
        dbname="votre_nom_db",
        user="votre_utilisateur",
        password="votre_mot_de_passe",
        host="votre_host",
        port="votre_port"
    )
    return conn

# Fonction pour ajouter une mission dans la base de données
def add_mission_to_db(conn, date, images):
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO Missions (date, images)
        VALUES (%s, %s)
        RETURNING id
    ''', (date, images))
    mission_id = cur.fetchone()[0]
    conn.commit()
    return mission_id

# Fonction pour ajouter un défaut dans la base de données
def add_defaut_to_db(conn, mission_id, type_defaut, latitude, longitude):
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO Defauts (mission_id, type_defaut, latitude, longitude)
        VALUES (%s, %s, %s, %s)
    ''', (mission_id, type_defaut, latitude, longitude))
    conn.commit()

# Fonction pour récupérer les missions
def get_missions(conn):
    cur = conn.cursor()
    cur.execute('SELECT * FROM Missions')
    return cur.fetchall()

# Fonction pour récupérer les défauts d'une mission
def get_defauts(conn, mission_id):
    cur = conn.cursor()
    cur.execute('SELECT * FROM Defauts WHERE mission_id = %s', (mission_id,))
    return cur.fetchall()

# Interface Streamlit
def main():
    st.title("Tableau de Bord Ageroute Côte d'Ivoire")

    # Connexion à la base de données
    conn = connect_to_db()

    # Navigation
    choice = st.sidebar.radio("Choisir une option", ["Tableau de Bord", "Ajouter une Mission"])

    if choice == "Tableau de Bord":
        st.header("Tableau de Bord")
        missions = get_missions(conn)
        st.write(f"Nombre total de missions: {len(missions)}")

        # Afficher les défauts sur une carte
        st.header("Carte Interactive des Défauts")
        defauts = conn.cursor().execute('SELECT * FROM Defauts').fetchall()
        if defauts:
            m = folium.Map(location=[7.5399, -5.5471], zoom_start=7)
            for defaut in defauts:
                folium.Marker(
                    location=[defaut[3], defaut[4]],
                    popup=f"Défaut: {defaut[2]}",
                    icon=folium.Icon(color='red')
                ).add_to(m)
            folium_static(m)
        else:
            st.write("Aucun défaut détecté.")

    elif choice == "Ajouter une Mission":
        st.header("Ajouter une Mission")
        uploaded_files = st.file_uploader("Charger les images de la mission drone", type=["jpg", "png"], accept_multiple_files=True)
        if uploaded_files:
            st.write(f"{len(uploaded_files)} images chargées.")
            if st.button("Lancer l'analyse par IA"):
                # Simuler l'analyse IA
                mission_id = add_mission_to_db(conn, datetime.now(), str(uploaded_files))
                # Ajouter des défauts fictifs
                add_defaut_to_db(conn, mission_id, "Fissure", 7.5399, -5.5471)
                add_defaut_to_db(conn, mission_id, "Nid-de-poule", 7.5499, -5.5571)
                st.success("Mission ajoutée et analyse terminée !")

    # Fermer la connexion à la base de données
    conn.close()

if __name__ == "__main__":
    main()
