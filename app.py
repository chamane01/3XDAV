import streamlit as st
import folium
import sqlite3
import json
import pandas as pd
import plotly.express as px
from streamlit_folium import st_folium

# Connexion à la base de données SQLite
conn = sqlite3.connect('routes_defauts.db')
cur = conn.cursor()

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
st.title("Dégradations Routières : Carte des Inspections Réelles")
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
        popup=(
            f"Route: {route}<br>"
            f"Catégorie: {categorie}<br>"
            f"Gravité: {gravite}<br>"
            f"Date: {date}<br>"
            f"Heure: {heure}<br>"
            f"Ville: {ville}"
        ),
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
defauts_par_date = df_defauts.groupby(df_defauts["date"].dt.date).size().reset_index(name="nombre_de_degradations")
fig_date = px.line(defauts_par_date, x="date", y="nombre_de_degradations", title="Évolution du Nombre de Dégradations au Fil du Temps")
st.plotly_chart(fig_date)

# Fermer la connexion à la base de données
conn.close()
