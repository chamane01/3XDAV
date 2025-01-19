import streamlit as st
import folium
from folium.plugins import Draw, MeasureControl
from streamlit_folium import st_folium
import rasterio
from rasterio.plot import reshape_as_image
import matplotlib.pyplot as plt
from io import BytesIO
import geopandas as gpd
from shapely.geometry import shape

# Initialisation des couches et paramètres globaux
if "layers" not in st.session_state:
    st.session_state["layers"] = {
        "Routes": [],
        "Bâtiments": [],
        "Polygonale": [],
        "MNT": [],
        "MNS": [],
        "Orthophotos": [],
    }

if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = {}

if "new_features" not in st.session_state:
    st.session_state["new_features"] = []

# Titre de l'application
st.title("Application de Cartographie Avancée")

# Description
st.markdown("**Choisissez une option pour interagir avec la carte**.")

# Menu principal
menu = st.sidebar.radio("Options principales", ["Téléverser des fichiers", "Dessiner sur la carte"])

# Téléversement de fichiers
if menu == "Téléverser des fichiers":
    st.subheader("Téléversez vos fichiers géographiques")
    uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON ou TIFF", type=["geojson", "tiff"])

    if uploaded_file:
        file_type = uploaded_file.name.split(".")[-1].lower()

        if file_type == "geojson":
            geojson_data = gpd.read_file(uploaded_file)
            st.session_state["uploaded_files"][uploaded_file.name] = geojson_data
            st.success(f"Fichier GeoJSON '{uploaded_file.name}' téléversé avec succès.")

        elif file_type == "tiff":
            with rasterio.open(uploaded_file) as src:
                bounds = src.bounds
                st.session_state["uploaded_files"][uploaded_file.name] = {
                    "bounds": bounds,
                    "file": uploaded_file.getvalue(),
                }
                st.success(f"Fichier TIFF '{uploaded_file.name}' téléversé avec succès.")
    
    if st.session_state["uploaded_files"]:
        st.write("**Fichiers téléversés :**")
        for file_name in st.session_state["uploaded_files"].keys():
            st.write(f"- {file_name}")

# Dessiner sur la carte
elif menu == "Dessiner sur la carte":
    st.subheader("Carte Interactive avec Dessin")

    # Carte de base
    m = folium.Map(location=[5.5, -4.0], zoom_start=8)

    # Ajout des couches existantes à la carte
    for layer, features in st.session_state["layers"].items():
        layer_group = folium.FeatureGroup(name=layer)
        for feature in features:
            feature_shape = shape(feature["geometry"])
            if feature_shape.geom_type == "Point":
                folium.Marker(
                    location=[feature_shape.y, feature_shape.x],
                    popup=layer,
                ).add_to(layer_group)
            elif feature_shape.geom_type in ["Polygon", "MultiPolygon"]:
                folium.GeoJson(data=feature, style_function=lambda x: {"fillColor": "blue"}).add_to(layer_group)
        layer_group.add_to(m)

    # Gestionnaire de dessin
    draw = Draw(
        draw_options={
            "polyline": True,
            "polygon": True,
            "rectangle": True,
            "circle": False,
            "marker": True,
        },
        edit_options={"edit": True, "remove": True},
    )
    draw.add_to(m)

    # Ajout du gestionnaire de mesures
    MeasureControl(primary_length_unit="kilometers").add_to(m)

    # Gestionnaire de couches
    folium.LayerControl().add_to(m)

    # Affichage interactif de la carte
    output = st_folium(m, width=800, height=600, returned_objects=["last_active_drawing", "all_drawings"])

    # Enregistrement des nouvelles entités
    if output and "last_active_drawing" in output and output["last_active_drawing"]:
        new_feature = output["last_active_drawing"]
        st.session_state["new_features"].append(new_feature)
        st.success("Nouvelle entité ajoutée temporairement.")

    # Ajout des entités dans les couches
    if st.session_state["new_features"]:
        st.write("**Entités dessinées temporairement :**")
        for idx, feature in enumerate(st.session_state["new_features"]):
            st.write(f"- Entité {idx + 1}: {feature['geometry']['type']}")

        layer_name = st.selectbox("Choisissez une couche pour enregistrer les entités", st.session_state["layers"].keys())
        if st.button("Enregistrer dans la couche"):
            st.session_state["layers"][layer_name].extend(st.session_state["new_features"])
            st.session_state["new_features"] = []
            st.success(f"Entités enregistrées dans la couche '{layer_name}'.")
