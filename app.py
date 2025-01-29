import streamlit as st
import folium
import random
import time
from streamlit_folium import st_folium

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

# Coordonnées des routes adaptées en Côte d'Ivoire
routes_ci = [
    {"route": "BVD lagunaire", "coords": [[-4.0113663, 5.3187904], [-4.0127054, 5.3179905]]},
    {"route": "A100(port-bouet, bassam)", "coords": [[-3.9009539, 5.2400795], [-3.9440652, 5.2469259]]},
    {"route": "BVD de la paix", "coords": [[-4.0192387, 5.3095622], [-4.0192237, 5.3092212]]},
    {"route": "A3(abidjan-yamoussoukro)", "coords": [[-4.0016795, 5.3555151], [-4.0047339, 5.3550991]]},
]

# Fonction pour générer des dégradations aléatoires
def generer_degradations():
    data = []
    for _ in range(100):
        route = random.choice(routes_ci)
        categorie = random.choice(list(degradations.keys()))
        gravite = random.randint(1, 3)
        coord = random.choice(route["coords"])
        lat, lon = coord[1] + random.uniform(-0.001, 0.001), coord[0] + random.uniform(-0.001, 0.001)
        data.append({
            "route": route["route"],
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
    time.sleep(1)

# Générer les données si elles n'existent pas déjà
if "degradations" not in st.session_state:
    st.session_state.degradations = generer_degradations()

data = st.session_state.degradations

# Initialisation de la carte Folium
m = folium.Map(location=[6.5, -5], zoom_start=7)

# Ajout des marqueurs sous forme de petits cercles pleins
for d in data:
    couleur = degradations[d["categorie"]]
    folium.CircleMarker(
        location=[d["lat"], d["lon"]],
        radius=4 + d["gravite"],
        color=couleur,
        fill=True,
        fill_color=couleur,
        popup=f"Catégorie: {d['categorie']}\nGravité: {d['gravite']}\nRoute: {d['route']}",
        tooltip=f"{d['categorie']} (Gravité {d['gravite']})"
    ).add_to(m)

# Affichage de la carte dans Streamlit
st_folium(m, width=800, height=600)
