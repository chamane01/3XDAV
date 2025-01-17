import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw

# Titre de l'application
st.title("Carte Dynamique avec Gestion de Couches")

# Initialisation de la carte
m = folium.Map(location=[46.603354, 1.888334], zoom_start=6)

# Ajout du plugin Draw pour dessiner des points, lignes et polylignes
draw = Draw(
    draw_options={
        "polyline": True,
        "polygon": True,
        "circle": False,
        "marker": True,
        "circlemarker": False,
        "rectangle": True,
    },
    export=True,
)
draw.add_to(m)

# Affichage de la carte dans Streamlit
output = st_folium(m, width=700, height=500)

# Gestion des couches
if output["last_active_drawing"]:
    drawing = output["last_active_drawing"]
    st.write("Dernier élément dessiné :")
    st.json(drawing)

    # Ajout de l'élément dessiné à une couche spécifique
    if drawing["geometry"]["type"] == "Point":
        folium.Marker(
            location=[drawing["geometry"]["coordinates"][1], drawing["geometry"]["coordinates"][0]],
            popup="Point",
        ).add_to(m)
    elif drawing["geometry"]["type"] == "LineString":
        folium.PolyLine(
            locations=[(lat, lon) for lon, lat in drawing["geometry"]["coordinates"]],
            popup="Ligne",
        ).add_to(m)
    elif drawing["geometry"]["type"] == "Polygon":
        folium.Polygon(
            locations=[(lat, lon) for lon, lat in drawing["geometry"]["coordinates"][0]],
            popup="Polygone",
        ).add_to(m)

# Affichage de la carte mise à jour
st_folium(m, width=700, height=500)
