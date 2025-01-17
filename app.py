import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from folium import LayerControl

# Initialisation des couches et des entités dans la session Streamlit
if "layers" not in st.session_state:
    st.session_state["layers"] = {"Routes": [], "Bâtiments": [], "Polygonale": []}
if "styles" not in st.session_state:
    st.session_state["styles"] = {
        "Routes": {"points": {"color": "red", "size": 10},
                   "lines": {"color": "blue", "weight": 2},
                   "polygons": {"color": "green", "fill": True, "fillOpacity": 0.5}},
        "Bâtiments": {"points": {"color": "black", "size": 8},
                      "lines": {"color": "gray", "weight": 2},
                      "polygons": {"color": "brown", "fill": True, "fillOpacity": 0.6}},
        "Polygonale": {"points": {"color": "purple", "size": 6},
                       "lines": {"color": "orange", "weight": 3},
                       "polygons": {"color": "yellow", "fill": True, "fillOpacity": 0.4}},
    }

# Titre de l'application
st.title("Carte Dynamique avec Gestion Avancée des Couches et Styles")

# Ajout d'une nouvelle couche par nom
st.header("Ajouter une nouvelle couche")
new_layer_name = st.text_input("Nom de la nouvelle couche à ajouter", "")
if st.button("Ajouter la couche") and new_layer_name:
    if new_layer_name not in st.session_state["layers"]:
        st.session_state["layers"][new_layer_name] = []
        st.session_state["styles"][new_layer_name] = {
            "points": {"color": "red", "size": 10},
            "lines": {"color": "blue", "weight": 2},
            "polygons": {"color": "green", "fill": True, "fillOpacity": 0.5},
        }
        st.success(f"La couche '{new_layer_name}' a été ajoutée.")
    else:
        st.warning(f"La couche '{new_layer_name}' existe déjà.")

# Gestionnaire de styles
st.header("Gestionnaire de styles")
selected_style_layer = st.selectbox("Choisissez une couche pour configurer son style", list(st.session_state["styles"].keys()))
if selected_style_layer:
    with st.expander("Configurer le style des points"):
        point_color = st.color_picker("Couleur des points", st.session_state["styles"][selected_style_layer]["points"]["color"])
        point_size = st.slider("Taille des points", 1, 20, st.session_state["styles"][selected_style_layer]["points"]["size"])
        st.session_state["styles"][selected_style_layer]["points"].update({"color": point_color, "size": point_size})

    with st.expander("Configurer le style des lignes"):
        line_color = st.color_picker("Couleur des lignes", st.session_state["styles"][selected_style_layer]["lines"]["color"])
        line_weight = st.slider("Épaisseur des lignes", 1, 10, st.session_state["styles"][selected_style_layer]["lines"]["weight"])
        st.session_state["styles"][selected_style_layer]["lines"].update({"color": line_color, "weight": line_weight})

    with st.expander("Configurer le style des polygones"):
        poly_color = st.color_picker("Couleur des polygones", st.session_state["styles"][selected_style_layer]["polygons"]["color"])
        poly_fill_opacity = st.slider("Opacité du remplissage", 0.1, 1.0, st.session_state["styles"][selected_style_layer]["polygons"]["fillOpacity"])
        st.session_state["styles"][selected_style_layer]["polygons"].update({"color": poly_color, "fillOpacity": poly_fill_opacity})

# Sélection de la couche active pour ajouter les nouvelles entités
st.header("Sélectionner une couche active")
layer_name = st.selectbox("Choisissez la couche à laquelle ajouter les entités", list(st.session_state["layers"].keys()))

# Carte de base
m = folium.Map(location=[5.5, -4.0], zoom_start=8)

# Ajout des couches existantes à la carte
for layer, features in st.session_state["layers"].items():
    feature_group = folium.FeatureGroup(name=layer, show=True)
    for idx, feature in enumerate(features):
        feature_type = feature["geometry"]["type"]
        coordinates = feature["geometry"]["coordinates"]
        style = st.session_state["styles"][layer]

        popup_html = f"""
        <b>Nom:</b> <input type="text" id="entity-{idx}" value="{feature.get('properties', {}).get('name', f'{layer} - Entité')}" 
        onchange="updateName('{layer}', {idx}, this.value)">
        """
        popup = folium.Popup(popup_html, max_width=300)

        if feature_type == "Point":
            lat, lon = coordinates[1], coordinates[0]
            folium.CircleMarker(location=[lat, lon], color=style["points"]["color"], radius=style["points"]["size"], popup=popup).add_to(feature_group)
        elif feature_type == "LineString":
            folium.PolyLine(locations=[(lat, lon) for lon, lat in coordinates], color=style["lines"]["color"], weight=style["lines"]["weight"], popup=popup).add_to(feature_group)
        elif feature_type == "Polygon":
            folium.Polygon(locations=[(lat, lon) for lon, lat in coordinates[0]], color=style["polygons"]["color"], fill=True, fillOpacity=style["polygons"]["fillOpacity"], popup=popup).add_to(feature_group)

    feature_group.add_to(m)

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
    if new_feature not in st.session_state["layers"][layer_name]:
        st.session_state["layers"][layer_name].append(new_feature)
