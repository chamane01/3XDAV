import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, MeasureControl
from folium import LayerControl
import rasterio
from rasterio.plot import reshape_as_image
from PIL import Image
from rasterio.warp import transform_bounds, calculate_default_transform, reproject
from rasterio.enums import Resampling
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, Point, LineString
import json
import os
import matplotlib.pyplot as plt

# Fonction pour reprojeter un fichier TIFF
def reproject_tiff(input_tiff, target_crs):
    """Reproject a TIFF file to a target CRS."""
    try:
        with rasterio.open(input_tiff) as src:
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )
            kwargs = src.meta.copy()
            kwargs.update({
                "crs": target_crs,
                "transform": transform,
                "width": width,
                "height": height,
            })

            reprojected_tiff = f"reprojected_{os.path.basename(input_tiff)}"
            with rasterio.open(reprojected_tiff, "w", **kwargs) as dst:
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
        return reprojected_tiff
    except Exception as e:
        st.error(f"Erreur lors de la reprojection : {e}")
        return None

# Fonction pour appliquer un gradient de couleur à un MNT/MNS
def apply_color_gradient(tiff_path, output_path):
    """Apply a color gradient to the DEM TIFF and save it as a PNG."""
    try:
        with rasterio.open(tiff_path) as src:
            dem_data = src.read(1)
            cmap = plt.get_cmap("terrain")
            norm = plt.Normalize(vmin=np.nanmin(dem_data), vmax=np.nanmax(dem_data))
            colored_image = cmap(norm(dem_data))
            plt.imsave(output_path, colored_image)
            plt.close()
    except Exception as e:
        st.error(f"Erreur lors de l'application du gradient de couleur : {e}")

# Fonction pour ajouter une image TIFF en tant qu'overlay sur une carte Folium
def add_image_overlay(map_object, tiff_path, bounds, name):
    """Add a TIFF image overlay to a Folium map."""
    try:
        with rasterio.open(tiff_path) as src:
            image = reshape_as_image(src.read())
            folium.raster_layers.ImageOverlay(
                image=image,
                bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
                name=name,
                opacity=0.6,
            ).add_to(map_object)
    except Exception as e:
        st.error(f"Erreur lors de l'ajout de l'overlay : {e}")

# Fonction pour calculer les limites d'un GeoJSON
def calculate_geojson_bounds(geojson_data):
    """Calculate bounds from a GeoJSON object."""
    try:
        gdf = gpd.GeoDataFrame.from_features(geojson_data)
        return gdf.total_bounds  # Returns [minx, miny, maxx, maxy]
    except Exception as e:
        st.error(f"Erreur lors du calcul des limites GeoJSON : {e}")
        return None

# Initialisation des états de session
if "layers" not in st.session_state:
    st.session_state["layers"] = {"Routes": [], "Bâtiments": [], "Polygonale": [], "MNT": [], "MNS": [], "Orthophotos": []}

if "new_features" not in st.session_state:
    st.session_state["new_features"] = []

if "uploaded_layers" not in st.session_state:
    st.session_state["uploaded_layers"] = []

# Titre de l'application
st.title("Carte Dynamique avec Gestion Avancée des Couches")

# Description
st.markdown("""
Créez des entités géographiques (points, lignes, polygones) en les dessinant sur la carte et ajoutez-les à des couches spécifiques. 
Vous pouvez également activer ou désactiver des couches grâce au gestionnaire de couches.
""")

# Sidebar pour la gestion des couches
with st.sidebar:
    st.header("Gestion des Couches")

    # Téléversement de fichiers TIFF
    st.subheader("Téléverser un fichier TIFF")
    tiff_type = st.selectbox("Sélectionnez le type de TIFF", ["MNT", "MNS", "Orthophoto"])
    uploaded_tiff = st.file_uploader(f"Téléverser un fichier TIFF ({tiff_type})", type=["tif", "tiff"])

    if uploaded_tiff:
        try:
            tiff_path = uploaded_tiff.name
            with open(tiff_path, "wb") as f:
                f.write(uploaded_tiff.read())
            reprojected_tiff = reproject_tiff(tiff_path, "EPSG:4326")
            if reprojected_tiff:
                st.success(f"Fichier TIFF ({tiff_type}) reprojecté et prêt à l'emploi.")
                # Ajout à la carte et couches
        except Exception as e:
            st.error(f"Erreur : {e}")

    # Téléversement de fichiers GeoJSON
    st.subheader("Téléverser un fichier GeoJSON")
    geojson_type = st.selectbox("Type de fichier GeoJSON", ["Polygonale", "Routes", "Bâtiments"])
    uploaded_geojson = st.file_uploader(f"Téléverser un fichier GeoJSON ({geojson_type})", type=["geojson"])

    if uploaded_geojson:
        try:
            geojson_data = json.load(uploaded_geojson)
            st.success(f"Fichier GeoJSON ({geojson_type}) chargé avec succès.")
        except Exception as e:
            st.error(f"Erreur : {e}")

# Carte principale
m = folium.Map(location=[5.0, -3.0], zoom_start=5)
folium.LayerControl().add_to(m)
st_folium(m, width=700, height=500)
