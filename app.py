import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from folium import LayerControl
import rasterio
from rasterio.plot import reshape_as_image
from rasterio.warp import calculate_default_transform, reproject
from rasterio.enums import Resampling
import geopandas as gpd
from shapely.geometry import shape
from io import BytesIO
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# Initialisation des couches et des entités
if "layers" not in st.session_state:
    st.session_state["layers"] = {"Routes": [], "Bâtiments": [], "Polygonale": []}

if "new_features" not in st.session_state:
    st.session_state["new_features"] = []

# Titre
st.title("Carte Dynamique avec Gestion des Couches")

# Sidebar pour la gestion des couches
with st.sidebar:
    st.header("Gestion des Couches")

    # Ajouter une couche
    new_layer_name = st.text_input("Nom de la nouvelle couche", "")
    if st.button("Ajouter une couche") and new_layer_name:
        if new_layer_name not in st.session_state["layers"]:
            st.session_state["layers"][new_layer_name] = []
            st.success(f"Couche '{new_layer_name}' ajoutée.")
        else:
            st.warning(f"La couche '{new_layer_name}' existe déjà.")

    # Sélectionner une couche
    selected_layer = st.selectbox("Sélectionner une couche", list(st.session_state["layers"].keys()))

    # Enregistrer les entités temporaires
    if st.button("Enregistrer les entités"):
        for feature in st.session_state["new_features"]:
            if feature not in st.session_state["layers"][selected_layer]:
                st.session_state["layers"][selected_layer].append(feature)
        st.session_state["new_features"] = []
        st.success(f"Entités enregistrées dans la couche '{selected_layer}'.")

# Carte de base
m = folium.Map(location=[5.5, -4.0], zoom_start=8)

# Ajouter les couches existantes
for layer_name, features in st.session_state["layers"].items():
    feature_group = folium.FeatureGroup(name=layer_name)
    for feature in features:
        geom_type = feature["geometry"]["type"]
        coords = feature["geometry"]["coordinates"]
        if geom_type == "Point":
            folium.Marker(location=[coords[1], coords[0]]).add_to(feature_group)
        elif geom_type == "LineString":
            folium.PolyLine([(lat, lon) for lon, lat in coords], color="blue").add_to(feature_group)
        elif geom_type == "Polygon":
            folium.Polygon([(lat, lon) for lon, lat in coords[0]], color="green", fill=True).add_to(feature_group)
    feature_group.add_to(m)

# Ajouter outils de dessin et contrôle
draw = Draw(
    draw_options={
        "polyline": True,
        "polygon": True,
        "rectangle": True,
        "circle": False,
        "marker": True,
        "circlemarker": False,
    },
    edit_options={"edit": True, "remove": True},
)
draw.add_to(m)
LayerControl().add_to(m)

# Carte interactive
output = st_folium(m, width=800, height=600, returned_objects=["last_active_drawing"])

# Enregistrer le dernier dessin
if output and "last_active_drawing" in output and output["last_active_drawing"]:
    new_feature = output["last_active_drawing"]
    if new_feature not in st.session_state["new_features"]:
        st.session_state["new_features"].append(new_feature)
        st.info("Nouvelle entité ajoutée temporairement.")

# Fonctions utilitaires
def reproject_tiff(input_tiff, target_crs):
    with rasterio.open(input_tiff) as src:
        transform, width, height = calculate_default_transform(src.crs, target_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({"crs": target_crs, "transform": transform, "width": width, "height": height})
        output_tiff = f"{input_tiff.stem}_reprojected.tiff"
        with rasterio.open(output_tiff, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.nearest,
                )
    return output_tiff

def apply_color_gradient(tiff_path, output_path):
    with rasterio.open(tiff_path) as src:
        dem_data = src.read(1)
        cmap = plt.get_cmap("terrain")
        norm = plt.Normalize(vmin=np.nanmin(dem_data), vmax=np.nanmax(dem_data))
        colored_image = cmap(norm(dem_data))
        plt.imsave(output_path, colored_image)

st.sidebar.header("Téléversement de fichiers")
uploaded_file = st.sidebar.file_uploader("Téléverser un fichier TIFF", type=["tif", "tiff"])
if uploaded_file:
    output_path = "colored_image.png"
    apply_color_gradient(uploaded_file, output_path)
    st.sidebar.image(output_path, caption="Aperçu du fichier traité")
