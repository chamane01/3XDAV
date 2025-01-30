import streamlit as st
import folium
import sqlite3
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

# Ajouter les routes sous forme de lignes avec tooltip
for route in routes_ci:
    folium.PolyLine(
        locations=[(lat, lon) for lon, lat in route["coords"]],
        color="blue",
        weight=3,
        opacity=0.7,
        tooltip=route["nom"]  # Affichage du vrai nom de la route
    ).add_to(m)

# Affichage de la carte dans Streamlit
st_folium(m, width=800, height=600)

# Fermer la connexion à la base de données
conn.close()
