import streamlit as st
import folium
import json
from streamlit_folium import st_folium

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

# Charger les données des dégradations depuis un fichier utilisateur
uploaded_file = st.file_uploader("Choisissez un fichier GEOJSON ou TXT", type=["geojson", "txt"])

data = []
if uploaded_file is not None:
    file_content = uploaded_file.read().decode("utf-8")
    try:
        geojson_data = json.loads(file_content)
        for feature in geojson_data["features"]:
            if feature["geometry"]["type"] == "Point":
                coords = feature["geometry"]["coordinates"]
                props = feature["properties"]
                data.append({
                    "categorie": props.get("categorie", "Inconnu"),
                    "gravite": props.get("gravite", 1),
                    "lat": coords[1],
                    "lon": coords[0]
                })
    except json.JSONDecodeError:
        st.error("Erreur de lecture du fichier. Assurez-vous qu'il est bien formaté.")

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

# Ajout des points de dégradations si les données sont valides
if data:
    for d in data:
        couleur = degradations.get(d["categorie"], "gray")
        folium.Circle(
            location=[d["lat"], d["lon"]],
            radius=3 + d["gravite"] * 2,
            color=couleur,
            fill=True,
            fill_color=couleur,
            popup=f"Catégorie: {d['categorie']}<br>Gravité: {d['gravite']}",
            tooltip=f"{d['categorie']} (Gravité {d['gravite']})"
        ).add_to(m)
else:
    st.write("Aucune donnée de dégradation chargée.")

# Affichage de la carte dans Streamlit
st_folium(m, width=800, height=600)
