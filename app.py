import streamlit as st
import folium
import sqlite3
from streamlit_folium import st_folium

# Connexion à la base de données SQLite
conn = sqlite3.connect('routes_defauts.db')
cur = conn.cursor()

# Récupérer les données des dégradations depuis la base de données
cur.execute("SELECT route, categorie, gravite, latitude, longitude FROM Defauts")
defauts_data = cur.fetchall()

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

# Ajouter les dégradations à la carte
for defaut in defauts_data:
    route, categorie, gravite, lat, lon = defaut
    couleur = degradations.get(categorie, "gray")
    folium.Circle(
        location=[lat, lon],
        radius=3 + gravite * 2,
        color=couleur,
        fill=True,
        fill_color=couleur,
        popup=f"Route: {route}<br>Catégorie: {categorie}<br>Gravité: {gravite}",
        tooltip=f"{categorie} (Gravité {gravite})"
    ).add_to(m)

# Affichage de la carte dans Streamlit
st_folium(m, width=800, height=600)

# Fermer la connexion à la base de données
conn.close()
