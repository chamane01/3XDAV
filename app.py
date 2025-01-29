import streamlit as st
import folium
from streamlit_folium import st_folium
import random

# Liste des catégories de dégradations routières et niveaux de gravité
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

# Routes de Côte d'Ivoire concernées
routes_ci = [
    {"route": "Autoroute du Nord", "lat": 6.871, "lon": -5.276},
    {"route": "Route de Dabou", "lat": 5.325, "lon": -4.105},
    {"route": "Route d'Aboisso", "lat": 5.728, "lon": -3.207},
    {"route": "A1", "lat": 6.877, "lon": -5.233},
    {"route": "A2", "lat": 6.745, "lon": -4.842},
    {"route": "A3", "lat": 6.134, "lon": -5.365}
]

# Génération de 100 dégradations aléatoires
data = []
for _ in range(100):
    route = random.choice(routes_ci)
    categorie = random.choice(list(degradations.keys()))
    gravite = random.randint(1, 3)
    data.append({
        "route": route["route"],
        "categorie": categorie,
        "gravite": gravite,
        "lat": route["lat"] + random.uniform(-0.05, 0.05),
        "lon": route["lon"] + random.uniform(-0.05, 0.05)
    })

# Configuration de l'application Streamlit
st.title("Carte des dégradations routières en Côte d'Ivoire")
st.write("Cliquez sur un marqueur pour voir les détails de la dégradation.")

# Initialisation de la carte Folium
m = folium.Map(location=[6.5, -5], zoom_start=7)

# Ajout des marqueurs sur la carte
for d in data:
    couleur_base = degradations[d["categorie"]]
    couleur = {
        1: couleur_base + "33",  # Teinte claire pour gravité 1
        2: couleur_base + "66",  # Teinte intermédiaire pour gravité 2
        3: couleur_base           # Teinte forte pour gravité 3
    }[d["gravite"]]
    tooltip = f"{d['categorie']} (Gravité {d['gravite']})"
    popup_content = f"""
    <b>Catégorie :</b> {d['categorie']}<br>
    <b>Route :</b> {d['route']}<br>
    <b>Gravité :</b> {d['gravite']}
    """
    folium.CircleMarker(
        location=[d["lat"], d["lon"]],
        radius=5 + d["gravite"],
        color=couleur,
        fill=True,
        fill_color=couleur,
        popup=popup_content,
        tooltip=tooltip
    ).add_to(m)

# Affichage de la carte dans Streamlit
st_folium(m, width=800, height=600)
