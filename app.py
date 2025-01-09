import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import folium_static

# Fonction pour se connecter à la base de données SQLite
def connect_to_db():
    conn = sqlite3.connect('ageroute.db')
    return conn

# Fonction pour afficher le tableau de bord
def dashboard():
    st.title("Tableau de Bord Ageroute Côte d'Ivoire")

    # Connexion à la base de données
    conn = connect_to_db()
    cur = conn.cursor()

    # Section 1: Carte Interactive des Routes
    st.header("Carte Interactive de Toutes les Routes")
    m = folium.Map(location=[7.5399, -5.5471], zoom_start=7)  # Centré sur la Côte d'Ivoire

    # Récupérer les défauts et les afficher sur la carte
    cur.execute('SELECT * FROM Defauts')
    defauts = cur.fetchall()
    for defaut in defauts:
        folium.Marker(
            location=[defaut[3], defaut[4]],
            popup=f"Défaut: {defaut[2]}",
            icon=folium.Icon(color='red')
        ).add_to(m)
    folium_static(m)

    # Section 2: Statistiques des Défauts par Mois
    st.header("Statistiques des Défauts par Mois")

    # Liste des mois de l'année
    months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Jul", "Août", "Sep", "Oct", "Nov", "Déc"]
    selected_month = st.selectbox("Sélectionner un mois", months)

    # Récupérer les données pour le mois sélectionné
    month_number = months.index(selected_month) + 1  # Convertir le mois en numéro
    cur.execute('''
        SELECT COUNT(Missions.id) AS nb_missions, 
               SUM(CASE WHEN Defauts.type_defaut = "Fissure" THEN 1 ELSE 0 END) AS nb_fissures,
               SUM(CASE WHEN Defauts.type_defaut = "Nid-de-poule" THEN 1 ELSE 0 END) AS nb_nids,
               SUM(CASE WHEN Defauts.type_defaut = "Usure" THEN 1 ELSE 0 END) AS nb_usures
        FROM Missions
        LEFT JOIN Defauts ON Missions.id = Defauts.mission_id
        WHERE strftime("%m", Missions.date) = ?
    ''', (f"{month_number:02}",))  # Format MM

    result = cur.fetchone()

    if result:
        nb_missions, nb_fissures, nb_nids, nb_usures = result
        # Gérer les valeurs None
        nb_fissures = nb_fissures if nb_fissures is not None else 0
        nb_nids = nb_nids if nb_nids is not None else 0
        nb_usures = nb_usures if nb_usures is not None else 0

        st.write(f"Statistiques pour {selected_month}:")
        st.write(f"- Nombre de missions réalisées: {nb_missions}")
        st.write(f"- Fissures: {nb_fissures}")
        st.write(f"- Nids-de-poule: {nb_nids}")
        st.write(f"- Usures: {nb_usures}")

        # Afficher les détails des défauts si disponibles
        if nb_fissures > 0 or nb_nids > 0 or nb_usures > 0:
            st.write("### Détails des Défauts")
            cur.execute('''
                SELECT Defauts.type_defaut, Defauts.latitude, Defauts.longitude
                FROM Defauts
                JOIN Missions ON Defauts.mission_id = Missions.id
                WHERE strftime("%m", Missions.date) = ?
            ''', (f"{month_number:02}",))
            defauts_details = cur.fetchall()
            for defaut in defauts_details:
                st.write(f"- **Type:** {defaut[0]}, **Latitude:** {defaut[1]}, **Longitude:** {defaut[2]}")
        else:
            st.write("Aucun défaut identifié pour ce mois.")
    else:
        st.write(f"Aucune donnée disponible pour {selected_month}.")

    # Section 3: Inspections Réalisées
    st.header("Inspections Réalisées")
    cur.execute('SELECT COUNT(*) FROM Missions')
    total_missions = cur.fetchone()[0]
    st.write(f"Nombre total de missions réalisées: {total_missions}")

    # Section 4: Analyse par Route
    st.header("Analyse par Route")
    cur.execute('SELECT * FROM Routes')
    routes = cur.fetchall()
    route_options = {route[0]: route[1] for route in routes}
    selected_route_id = st.selectbox("Sélectionner une route", options=route_options.keys(), format_func=lambda x: route_options[x])

    if selected_route_id:
        # Récupérer les missions et les défauts pour la route sélectionnée
        cur.execute('''
            SELECT Missions.id, Missions.date, Defauts.type_defaut, Defauts.latitude, Defauts.longitude
            FROM Missions
            LEFT JOIN Defauts ON Missions.id = Defauts.mission_id
            WHERE Missions.route_id = ?
        ''', (selected_route_id,))
        missions_defauts = cur.fetchall()

        if missions_defauts:
            st.write(f"### Missions et Défauts sur la route {route_options[selected_route_id]}:")
            missions_dict = {}
            for mission in missions_defauts:
                mission_id, mission_date, type_defaut, latitude, longitude = mission
                if mission_id not in missions_dict:
                    missions_dict[mission_id] = {
                        "date": mission_date,
                        "defauts": []
                    }
                if type_defaut:  # Si un défaut est associé à la mission
                    missions_dict[mission_id]["defauts"].append({
                        "type": type_defaut,
                        "latitude": latitude,
                        "longitude": longitude
                    })

            for mission_id, mission_data in missions_dict.items():
                st.write(f"**Mission du {mission_data['date']}**")
                if mission_data["defauts"]:
                    for defaut in mission_data["defauts"]:
                        st.write(f"- **Type:** {defaut['type']}, **Latitude:** {defaut['latitude']}, **Longitude:** {defaut['longitude']}")
                else:
                    st.write("Aucun défaut identifié pour cette mission.")
        else:
            st.write(f"Aucune mission ou défaut identifié sur la route {route_options[selected_route_id]}.")

    # Section 5: Génération de Rapports
    st.header("Générer des Rapports")
    report_type = st.radio("Type de rapport", ["Journalier", "Mensuel", "Annuel"])
    if st.button("Générer le rapport"):
        st.write(f"Génération du rapport {report_type.lower()} en cours de développement")

    # Section 6: Alertes
    st.header("Alertes")
    st.write("Nid-de-poule dangereux détecté sur l’Autoroute du Nord (Section Yamoussoukro-Bouaké)")
    st.write("Fissures multiples sur le Pont HKB à Abidjan")
    st.write("Usures importantes sur la Nationale A3 (Abidjan-Adzopé)")

    # Section 7: Inspections par Date
    st.header("Inspections par Date")
    selected_date = st.date_input("Sélectionner une date")
    if st.button("Voir les inspections pour cette date"):
        st.write(f"Inspections pour {selected_date}: En cours de développement")

    # Fermer la connexion
    conn.close()

# Fonction pour ajouter une mission
def add_mission():
    st.title("Ajouter une Mission")
    uploaded_files = st.file_uploader("Charger les images de la mission drone", type=["jpg", "png"], accept_multiple_files=True)
    if uploaded_files:
        st.write(f"{len(uploaded_files)} images chargées.")
        if st.button("Lancer l'analyse par IA"):
            st.write("Analyse en cours...")
            # Ici, vous pouvez ajouter le code pour l'analyse IA
            st.write("Résultats de l'analyse: En cours de développement")

# Page d'Accueil
st.sidebar.title("Navigation")
choice = st.sidebar.radio("Choisir une option", ["Tableau de Bord", "Ajouter une Mission"])

if choice == "Tableau de Bord":
    dashboard()
elif choice == "Ajouter une Mission":
    add_mission()
