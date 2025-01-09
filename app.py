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

    # Section 1: Carte Interactive des Routes
    st.header("Carte Interactive de Toutes les Routes")
    m = folium.Map(location=[7.5399, -5.5471], zoom_start=7)  # Centré sur la Côte d'Ivoire

    # Récupérer les défauts et les afficher sur la carte
    cur = conn.cursor()
    cur.execute('SELECT * FROM Defauts')
    defauts = cur.fetchall()
    for defaut in defauts:
        folium.Marker(
            location=[defaut[3], defaut[4]],
            popup=f"Défaut: {defaut[2]}",
            icon=folium.Icon(color='red')
        ).add_to(m)
    folium_static(m)

    # Section 2: Statistiques des Défauts
    st.header("Statistiques des Défauts")
    selected_month = st.selectbox("Sélectionner un mois", ["Jan", "Fév", "Mar", "Avr"])
    if selected_month:
        st.write(f"Statistiques pour {selected_month}:")
        st.write("- Fissures: En cours de développement")
        st.write("- Nids-de-poule: En cours de développement")
        st.write("- Usures: En cours de développement")

    # Section 3: Voir Toutes les Routes
    st.header("Voir Toutes les Routes")
    if st.button("Afficher toutes les routes"):
        cur.execute('SELECT * FROM Routes')
        routes = cur.fetchall()
        st.write("Liste des routes:")
        for route in routes:
            st.write(f"- {route[1]} ({route[2]})")

    # Section 4: Inspections Réalisées
    st.header("Inspections Réalisées")
    st.write("Statistiques des 5 derniers mois: En cours de développement")

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

    # Section 8: Analyse par Route
    st.header("Analyse par Route")
    cur.execute('SELECT id, nom FROM Routes')
    routes = cur.fetchall()
    route_options = {route[1]: route[0] for route in routes}
    selected_route_name = st.selectbox("Sélectionner une route", list(route_options.keys()))
    
    if st.button("Analyser la route sélectionnée"):
        selected_route_id = route_options[selected_route_name]
        cur.execute('''
            SELECT Defauts.type_defaut, Defauts.latitude, Defauts.longitude 
            FROM Defauts 
            JOIN Missions ON Defauts.mission_id = Missions.id 
            WHERE Missions.route_id = ?
        ''', (selected_route_id,))
        defauts_route = cur.fetchall()
        
        if defauts_route:
            st.write(f"Résultats de l'analyse pour la route {selected_route_name}:")
            for defaut in defauts_route:
                st.write(f"- Type de défaut: {defaut[0]}, Latitude: {defaut[1]}, Longitude: {defaut[2]}")
        else:
            st.write("Aucun défaut trouvé pour cette route.")

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
