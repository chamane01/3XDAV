import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from folium import LayerControl

# Initialisation des couches et des entités dans la session Streamlit
if "layers" not in st.session_state:
    st.session_state["layers"] = {"Routes": [], "Bâtiments": [], "Polygonale": []}
if "refresh_flag" not in st.session_state:
    st.session_state["refresh_flag"] = False

# Titre de l'application
st.title("Carte Dynamique avec Gestion Avancée des Couches")

# Description
st.markdown("""
Créez des entités géographiques (points, lignes, polygones) en les dessinant sur la carte et ajoutez-les à des couches spécifiques. 
Vous pouvez également activer ou désactiver des couches grâce au gestionnaire de couches.
""")

# Ajout d'une nouvelle couche par nom
st.header("Ajouter une nouvelle couche")
new_layer_name = st.text_input("Nom de la nouvelle couche à ajouter", "")
if st.button("Ajouter la couche") and new_layer_name:
    if new_layer_name not in st.session_state["layers"]:
        st.session_state["layers"][new_layer_name] = []
        st.success(f"La couche '{new_layer_name}' a été ajoutée.")
    else:
        st.warning(f"La couche '{new_layer_name}' existe déjà.")

# Sélection de la couche active pour ajouter les nouvelles entités
st.header("Sélectionner une couche active")
layer_name = st.selectbox(
    "Choisissez la couche à laquelle ajouter les entités",
    list(st.session_state["layers"].keys())
)

# Gestionnaire de styles
styles = {
    "Routes": {"color": "red"},
    "Bâtiments": {"color": "blue"},
    "Polygonale": {"color": "green"},
}

# Carte de base
m = folium.Map(location=[5.5, -4.0], zoom_start=8)

# Ajout des couches existantes à la carte
layer_groups = {}
for layer, features in st.session_state["layers"].items():
    layer_groups[layer] = folium.FeatureGroup(name=layer, show=True)
    style = styles.get(layer, {"color": "black"})
    for feature in features:
        feature_type = feature["geometry"]["type"]
        coordinates = feature["geometry"]["coordinates"]
        popup = feature.get("properties", {}).get("name", f"{layer} - Entité")

        if feature_type == "Point":
            lat, lon = coordinates[1], coordinates[0]
            folium.Marker(location=[lat, lon], popup=popup, icon=folium.Icon(color=style["color"])).add_to(layer_groups[layer])
        elif feature_type == "LineString":
            folium.PolyLine(locations=[(lat, lon) for lon, lat in coordinates], color=style["color"], popup=popup).add_to(layer_groups[layer])
        elif feature_type == "Polygon":
            folium.Polygon(locations=[(lat, lon) for lon, lat in coordinates[0]], color=style["color"], fill=True, popup=popup).add_to(layer_groups[layer])

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

# Ajout du gestionnaire de couches en mode plié
LayerControl(position="topleft", collapsed=True).add_to(m)

# Affichage interactif de la carte
output = st_folium(m, width=800, height=600, returned_objects=["last_active_drawing", "all_drawings"])

# Gestion des nouveaux dessins
if output and "last_active_drawing" in output and output["last_active_drawing"]:
    new_feature = output["last_active_drawing"]
    if new_feature not in st.session_state["layers"][layer_name]:  # Évite les doublons
        st.session_state["layers"][layer_name].append(new_feature)
        st.success("Nouvelle entité ajoutée.")

# Rafraîchissement manuel
st.header("Rafraîchissement manuel")
if st.button("Rafraîchir les listes et cartes"):
    st.session_state["refresh_flag"] = not st.session_state["refresh_flag"]
    st.experimental_rerun()

# Gestion des entités
st.header("Gestion des entités dans les couches")
selected_layer = st.selectbox("Choisissez une couche pour voir ses entités", list(st.session_state["layers"].keys()))
if st.session_state["layers"][selected_layer]:
    entity_idx = st.selectbox(
        "Sélectionnez une entité à gérer",
        range(len(st.session_state["layers"][selected_layer])),
        format_func=lambda idx: f"Entité {idx + 1}: {st.session_state['layers'][selected_layer][idx]['geometry']['type']}"
    )
    selected_entity = st.session_state["layers"][selected_layer][entity_idx]
    current_name = selected_entity.get("properties", {}).get("name", "")
    new_name = st.text_input("Nom de l'entité", current_name)

    if st.button("Modifier le nom", key=f"edit_{entity_idx}"):
        if "properties" not in selected_entity:
            selected_entity["properties"] = {}
        selected_entity["properties"]["name"] = new_name
        st.success(f"Le nom de l'entité a été mis à jour en '{new_name}'.")

    if st.button("Supprimer l'entité sélectionnée", key=f"delete_{entity_idx}"):
        st.session_state["layers"][selected_layer].pop(entity_idx)
        st.success(f"L'entité sélectionnée a été supprimée de la couche '{selected_layer}'.")
else:
    st.write("Aucune entité dans cette couche pour le moment.")
