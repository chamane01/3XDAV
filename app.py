import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from folium import LayerControl

# Initialisation des couches et des entités dans la session Streamlit
if "layers" not in st.session_state:
    st.session_state["layers"] = {"Plantations": [], "Polygonales": [], "Points": []}

# Titre de l'application
st.title("Carte Dynamique avec Gestion Avancée des Couches")

# Description
st.markdown("""
Créez des entités géographiques (points, lignes, polygones) en les dessinant sur la carte et ajoutez-les à des couches spécifiques. 
Vous pouvez également activer ou désactiver des couches grâce au gestionnaire de couches.
""")

# Sélection de la couche active pour ajouter les nouvelles entités
layer_name = st.selectbox(
    "Choisissez la couche à laquelle ajouter les entités",
    list(st.session_state["layers"].keys())
)

# Carte de base
m = folium.Map(location=[5.5, -4.0], zoom_start=8)

# Ajout des couches existantes à la carte
layer_groups = {}
for layer, features in st.session_state["layers"].items():
    layer_groups[layer] = folium.FeatureGroup(name=layer, show=True)
    for feature in features:
        feature_type = feature["geometry"]["type"]
        coordinates = feature["geometry"]["coordinates"]

        if feature_type == "Point":
            lat, lon = coordinates[1], coordinates[0]
            folium.Marker(location=[lat, lon], popup=f"{layer} - Point").add_to(layer_groups[layer])
        elif feature_type == "LineString":
            folium.PolyLine(locations=[(lat, lon) for lon, lat in coordinates], color="blue").add_to(layer_groups[layer])
        elif feature_type == "Polygon":
            folium.Polygon(locations=[(lat, lon) for lon, lat in coordinates[0]], color="green", fill=True).add_to(layer_groups[layer])

    # Ajout du groupe à la carte
    layer_groups[layer].add_to(m)

# Gestionnaire de dessin
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

# Ajout du gestionnaire de couches
LayerControl(collapsed=False).add_to(m)  # collapsed=False permet de l'afficher par défaut

# Affichage interactif de la carte
output = st_folium(m, width=800, height=500, returned_objects=["last_active_drawing", "all_drawings"])

# Gestion des nouveaux dessins
if output and "last_active_drawing" in output and output["last_active_drawing"]:
    new_feature = output["last_active_drawing"]
    st.session_state["layers"][layer_name].append(new_feature)
    st.success(f"Nouvelle entité ajoutée à la couche '{layer_name}'.")
    if st.button("Recharger la carte"):  # Bouton pour recharger la carte
        st.experimental_rerun()  # Recharger la carte pour afficher la nouvelle entité

# Suppression d'une entité d'une couche
st.header("Gestion des entités dans les couches")
selected_layer = st.selectbox("Choisissez une couche pour voir ses entités", list(st.session_state["layers"].keys()))
if st.session_state["layers"][selected_layer]:
    entity_idx = st.selectbox(
        "Sélectionnez une entité à supprimer",
        range(len(st.session_state["layers"][selected_layer])),
        format_func=lambda idx: f"Entité {idx + 1}: {st.session_state['layers'][selected_layer][idx]['geometry']['type']}"
    )
    if st.button("Supprimer l'entité sélectionnée"):
        st.session_state["layers"][selected_layer].pop(entity_idx)
        st.success(f"L'entité sélectionnée a été supprimée de la couche '{selected_layer}'.")
        if st.button("Recharger la carte après suppression"):  # Bouton pour recharger la carte
            st.experimental_rerun()  # Recharger la carte pour refléter la suppression
else:
    st.write("Aucune entité dans cette couche pour le moment.")
