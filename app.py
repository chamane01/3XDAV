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
            "nom": feature["properties"].get("ID", "Route inconnue")  # Récupération correcte du nom
        })

# Récupérer les données des dégradations depuis la base de données
conn = sqlite3.connect('routes_defauts.db')
cur = conn.cursor()
cur.execute("SELECT route, categorie, gravite, latitude, longitude, date, heure, ville FROM Defauts")
defauts_data = cur.fetchall()

# Convertir les données en DataFrame pour une analyse facile
df_defauts = pd.DataFrame(defauts_data, columns=["route", "categorie", "gravite", "latitude", "longitude", "date", "heure", "ville"])

# Définition des catégories de dégradations et niveaux de gravité
degradations = {
    "déformation orniérage": "red",
    "fissure de fatigue": "blue",
    "faïençage de fatigue": "green",
    "fissure de retrait": "purple",
    "fissure anarchique": "orange",
    "réparation": "pink",
    "nid de poule": "brown",
    "arrachements": "gray",
    "fluage": "yellow",
    "dénivellement accotement": "cyan",
    "chaussée détruite": "black",
    "envahissement végétation": "magenta",
    "assainissement": "teal"
}

# Initialisation de l'application Streamlit
st.title("Interface de Gestion des Missions et Dégradations Routières")

# Sidebar pour la navigation
st.sidebar.title("Navigation")
selection = st.sidebar.radio("Choisir une section", ["Gestion des Missions", "Tableau de Bord des Dégradations"])

# Si l'utilisateur choisit "Gestion des Missions"
if selection == "Gestion des Missions":
    st.subheader("Gestion des Missions")

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

# Si l'utilisateur choisit "Tableau de Bord des Dégradations"
elif selection == "Tableau de Bord des Dégradations":
    st.header("Dégradations Routières : Carte des Inspections Réelles")
    st.write("Survolez une route pour voir son nom et passez sur un marqueur pour voir les détails de la dégradation.")

    # Initialisation de la carte Folium
    m = folium.Map(location=[6.5, -5], zoom_start=7)

    # Ajouter les routes sous forme de lignes avec tooltip
    for route in routes_ci:
        folium.PolyLine(
            locations=[(lat, lon) for lon, lat in route["coords"]],
            color="blue",
            weight=3,
            opacity=0.7,
            tooltip=route["nom"]  # Affichage du vrai nom de la route
        ).add_to(m)

    # Ajouter les dégradations à la carte
    for defaut in defauts_data:
        route, categorie, gravite, lat, lon, date, heure, ville = defaut
        couleur = degradations.get(categorie, "gray")
        
        # Créer un cercle avec une taille en fonction de la gravité
        folium.Circle(
            location=[lat, lon],
            radius=3 + gravite * 2,
            color=couleur,
            fill=True,
            fill_color=couleur,
            popup=(f"Route: {route}<br>"
                   f"Catégorie: {categorie}<br>"
                   f"Gravité: {gravite}<br>"
                   f"Date: {date}<br>"
                   f"Heure: {heure}<br>"
                   f"Ville: {ville}"),
            tooltip=f"{categorie} (Gravité {gravite})"
        ).add_to(m)

    # Affichage de la carte dans Streamlit
    st_folium(m, width=800, height=600)

    # Tableau de bord sous la carte
    st.header("Tableau de Bord des Dégradations Routières")

    # Section 1 : Statistiques Globales
    st.subheader("Statistiques Globales")
    col1, col2, col3 = st.columns(3)
    col1.metric("Nombre Total de Dégradations", df_defauts.shape[0])
    col2.metric("Nombre de Routes Inspectées", df_defauts["route"].nunique())
    col3.metric("Nombre de Villes Touchées", df_defauts["ville"].nunique())

    # Section 2 : Répartition des Dégradations par Catégorie
    st.subheader("Répartition des Dégradations par Catégorie")
    fig_categories = px.pie(df_defauts, names="categorie", title="Répartition des Dégradations par Catégorie")
    st.plotly_chart(fig_categories)

    # Section 3 : Gravité des Dégradations
    st.subheader("Distribution des Niveaux de Gravité")
    fig_gravite = px.histogram(df_defauts, x="gravite", nbins=10, title="Distribution des Niveaux de Gravité")
    st.plotly_chart(fig_gravite)

    # Section 4 : Dégradations par Ville
    st.subheader("Dégradations par Ville")
    defauts_par_ville = df_defauts["ville"].value_counts().reset_index()
    defauts_par_ville.columns = ["ville", "nombre_de_degradations"]
    fig_ville = px.bar(defauts_par_ville, x="ville", y="nombre_de_degradations", title="Nombre de Dégradations par Ville")
    st.plotly_chart(fig_ville)

    # Section 5 : Évolution Temporelle des Dégradations
    st.subheader("Évolution Temporelle des Dégradations")
    df_defauts["date"] = pd.to_datetime(df_defauts["date"])  # Convertir la colonne date en datetime
    fig_temporal = px.line(df_defauts, x="date", title="Évolution Temporelle des Dégradations")
    st.plotly_chart(fig_temporal)
