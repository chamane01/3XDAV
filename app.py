import streamlit as st
import folium
import random
import json
from streamlit_folium import st_folium

# Charger les données des routes à partir du fichier JSON
with open("routeQSD.txt", "r") as f:
    routes_data = json.load(f)

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

# Extraire les coordonnées des routes sous forme de LineStrings
routes_ci = []
for feature in routes_data["features"]:
    if feature["geometry"]["type"] == "LineString":
        routes_ci.append({
            "coords": feature["geometry"]["coordinates"]
        })

# Fonction pour générer des dégradations aléatoires sur les routes
def generer_degradations():
    data = []
    for _ in range(100):
        route = random.choice(routes_ci)
        categorie = random.choice(list(degradations.keys()))
        gravite = random.randint(1, 3)
        coord = random.choice(route["coords"])
        lon, lat = coord[0] + random.uniform(-0.0005, 0.0005), coord[1] + random.uniform(-0.0005, 0.0005)
        data.append({
            "categorie": categorie,
            "gravite": gravite,
            "lat": lat,
            "lon": lon
        })
    return data

# Initialisation de l'application Streamlit
st.title("Dégradations Routières : Carte des Inspections Virtuelles")
st.write("Cliquez sur un marqueur pour voir les détails de la dégradation.")

# Bouton pour rafraîchir les données
if st.button("Rafraîchir les dégradations"):
    st.session_state.degradations = generer_degradations()

# Générer les données si elles n'existent pas déjà
if "degradations" not in st.session_state:
    st.session_state.degradations = generer_degradations()

data = st.session_state.degradations

# Initialisation de la carte Folium
m = folium.Map(location=[6.5, -5], zoom_start=7)

# Ajouter les routes sous forme de lignes
for route in routes_ci:
    folium.PolyLine(
        locations=[(lat, lon) for lon, lat in route["coords"]],
        color="blue",
        weight=3,
        opacity=0.7
    ).add_to(m)

# Ajout des marqueurs sous forme de petits cercles pleins
for d in data:
    couleur = degradations[d["categorie"]]
    folium.CircleMarker(
        location=[d["lat"], d["lon"]],
        radius=4 + d["gravite"],
        color=couleur,
        fill=True,
        fill_color=couleur,
        popup=f"Catégorie: {d['categorie']}\nGravité: {d['gravite']}",
        tooltip=f"{d['categorie']} (Gravité {d['gravite']})"
    ).add_to(m)

# Affichage de la carte dans Streamlit
st_folium(m, width=800, height=600)

# Fonction pour télécharger les données en JSON
def telecharger_json():
    return json.dumps(data, indent=4)

# Fonction pour télécharger les données en GeoJSON
def telecharger_geojson():
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [d["lon"], d["lat"]]
                },
                "properties": {
                    "categorie": d["categorie"],
                    "gravite": d["gravite"]
                }
            } for d in data
        ]
    }
    return json.dumps(geojson_data, indent=4)

# Boutons de téléchargement
st.download_button("Télécharger JSON", telecharger_json(), "degradations.json", "application/json")
st.download_button("Télécharger GeoJSON", telecharger_geojson(), "degradations.geojson", "application/geo+json")
