import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw

# Stockage des couches dans la session Streamlit
if "drawn_features" not in st.session_state:
    st.session_state["drawn_features"] = []

# Titre de l'application
st.title("Carte Dynamique avec Dessin Interactif des Couches")

# Description
st.markdown("""
Cette application vous permet de dessiner directement sur une carte pour ajouter des couches de points, lignes ou polygones. Les couches ajoutées sont sauvegardées et affichées dynamiquement.
""")

# Création de la carte Folium
m = folium.Map(location=[5.5, -4.0], zoom_start=8)

# Ajout de l'outil de dessin
draw = Draw(
    draw_options={
        "polyline": True,
        "polygon": True,
        "circle": False,
        "rectangle": True,
        "marker": True,
        "circlemarker": False,
    },
    edit_options={"edit": True, "remove": True},
)
draw.add_to(m)

# Ajout des couches sauvegardées
for feature in st.session_state["drawn_features"]:
    feature_type = feature["geometry"]["type"]
    coordinates = feature["geometry"]["coordinates"]

    if feature_type == "Point":
        lat, lon = coordinates[1], coordinates[0]
        folium.Marker(location=[lat, lon], popup="Point").add_to(m)
    elif feature_type == "LineString":
        folium.PolyLine(locations=[(lat, lon) for lon, lat in coordinates], color="blue").add_to(m)
    elif feature_type == "Polygon":
        folium.Polygon(locations=[(lat, lon) for lon, lat in coordinates[0]], color="green", fill=True).add_to(m)

# Affichage de la carte avec interaction
output = st_folium(m, width=800, height=500, returned_objects=["last_active_drawing", "all_drawings"])

# Gestion des nouveaux dessins
if output and "last_active_drawing" in output and output["last_active_drawing"]:
    new_feature = output["last_active_drawing"]
    st.session_state["drawn_features"].append(new_feature)
    st.success("Nouvelle couche ajoutée avec succès !")

# Afficher les couches sauvegardées
st.subheader("Couches ajoutées :")
if st.session_state["drawn_features"]:
    for idx, feature in enumerate(st.session_state["drawn_features"], start=1):
        st.write(f"**Couche {idx}** : {feature['geometry']['type']} - {feature['geometry']['coordinates']}")
else:
    st.write("Aucune couche ajoutée pour le moment.")
