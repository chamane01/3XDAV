import streamlit as st
from streamlit_folium import st_folium, folium_static
import folium
from folium.plugins import Draw, MeasureControl
from folium import LayerControl
import rasterio
import rasterio.warp
from rasterio.plot import reshape_as_image
from PIL import Image
from rasterio.warp import transform_bounds
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, Point, LineString, shape
import json
from io import BytesIO
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
import matplotlib.pyplot as plt
import os
import uuid
import math

# Dictionnaire des couleurs pour les types de fichiers GeoJSON
geojson_colors = {
    "Routes": "orange",
    "Pistes": "brown",
    "Plantations": "green",
    "Bâtiments": "gray",
    "Électricité": "yellow",
    "Assainissements": "blue",
    "Villages": "purple",
    "Villes": "red",
    "Chemin de fer": "black",
    "Parc et réserves": "darkgreen",
    "Cours d'eau": "lightblue",
    "Polygonale": "pink"
}

# Fonctions UTM
def get_utm_zone(longitude):
    return int((longitude + 180) // 6) + 1

def get_utm_epsg(lon, lat):
    zone = get_utm_zone(lon)
    return 32600 + zone  # Zones nord seulement pour la Côte d'Ivoire

# Fonction de reprojection améliorée
def reproject_tiff(input_tiff, target_crs):
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

        unique_id = str(uuid.uuid4())[:8]
        reprojected_tiff = f"reprojected_{unique_id}.tiff"
        
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
        return reprojected_tiff, transform

# Fonctions d'affichage
def apply_color_gradient(tiff_path, output_path):
    with rasterio.open(tiff_path) as src:
        dem_data = src.read(1)
        cmap = plt.get_cmap("terrain")
        norm = plt.Normalize(vmin=dem_data.min(), vmax=dem_data.max())
        colored_image = cmap(norm(dem_data))
        plt.imsave(output_path, colored_image)
        plt.close()

def add_image_overlay(map_object, tiff_path, bounds, name):
    with rasterio.open(tiff_path) as src:
        image = reshape_as_image(src.read())
        folium.raster_layers.ImageOverlay(
            image=image,
            bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
            name=name,
            opacity=0.6,
        ).add_to(map_object)

# Fonctions de chargement
def load_tiff(tiff_path):
    try:
        with rasterio.open(tiff_path) as src:
            data = src.read(1)
            bounds = src.bounds
            transform = src.transform
            return data, bounds, transform
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return None, None, None

# Fonctions de calcul
def calculate_surface(polygon):
    try:
        geom = shape(polygon["geometry"])
        gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")
        gdf = gdf.to_crs("EPSG:3857")
        return gdf.geometry.area.values[0]
    except Exception as e:
        st.error(f"Erreur de calcul : {e}")
        return None

def calculate_volume_utm(mns_path, mnt_path, polygons, utm_crs):
    try:
        # Conversion des polygones en UTM
        gdf = gpd.GeoDataFrame(
            geometry=[shape(p["geometry"]) for p in polygons],
            crs="EPSG:4326"
        ).to_crs(utm_crs)

        with rasterio.open(mns_path) as src_mns, rasterio.open(mnt_path) as src_mnt:
            transform = src_mns.transform
            pixel_area = transform.a * -transform.e

            total_volume = 0.0
            for idx, polygon in gdf.iterrows():
                mask = polygon.geometry
                mns = np.where(mask, src_mns.read(1), np.nan)
                mnt = np.where(mask, src_mnt.read(1), np.nan)
                total_volume += np.nansum(mns - mnt) * pixel_area

            return total_volume

    except Exception as e:
        st.error(f"Erreur de calcul UTM : {e}")
        return None

# Interface Streamlit
st.title("Carte Topographique et Analyse Spatiale")
st.markdown("Affichage en EPSG:4326 | Calculs en UTM")

# Initialisation session
if "layers" not in st.session_state:
    st.session_state["layers"] = {}
if "uploaded_layers" not in st.session_state:
    st.session_state["uploaded_layers"] = []
if "new_features" not in st.session_state:
    st.session_state["new_features"] = []

# Sidebar
with st.sidebar:
    st.header("Gestion des Données")
    
    # Gestion UTM
    utm_choice = st.radio("Mode UTM", ["Auto", "Manuel (29N/30N)"])
    utm_zone = None
    if utm_choice == "Manuel (29N/30N)":
        utm_zone = st.selectbox("Zone UTM", ["32629", "32630"])
    
    # Téléversement TIFF
    tiff_type = st.selectbox("Type TIFF", ["MNT", "MNS", "Orthophoto"])
    uploaded_tiff = st.file_uploader("Téléverser TIFF", type=["tif", "tiff"])
    
    if uploaded_tiff and tiff_type:
        unique_id = str(uuid.uuid4())[:8]
        temp_path = f"temp_{unique_id}.tiff"
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_tiff.read())
        
        try:
            # Reprojection pour affichage
            tiff_4326, _ = reproject_tiff(temp_path, "EPSG:4326")
            
            # Détermination UTM
            if utm_zone:
                utm_crs = f"EPSG:{utm_zone}"
            else:
                with rasterio.open(tiff_4326) as src:
                    bounds = src.bounds
                    center_lon = (bounds.left + bounds.right) / 2
                    utm_crs = f"EPSG:{get_utm_epsg(center_lon, 0)}"
            
            # Reprojection pour calcul
            tiff_utm, _ = reproject_tiff(temp_path, utm_crs)
            
            st.session_state["uploaded_layers"].append({
                "type": "TIFF",
                "name": tiff_type,
                "path_4326": tiff_4326,
                "path_utm": tiff_utm,
                "utm_crs": utm_crs,
                "bounds": bounds
            })
            st.success(f"{tiff_type} ajouté!")
        
        except Exception as e:
            st.error(f"Erreur : {str(e)}")
        finally:
            os.remove(temp_path)

    # Gestion GeoJSON
    geojson_type = st.selectbox("Type GeoJSON", list(geojson_colors.keys()))
    uploaded_geojson = st.file_uploader("Téléverser GeoJSON", type=["geojson"])
    
    if uploaded_geojson and geojson_type:
        try:
            geojson_data = json.load(uploaded_geojson)
            st.session_state["uploaded_layers"].append({
                "type": "GeoJSON",
                "name": geojson_type,
                "data": geojson_data,
                "color": geojson_colors[geojson_type]
            })
            st.success(f"{geojson_type} ajouté!")
        except Exception as e:
            st.error(f"Erreur : {str(e)}")

# Carte Folium
m = folium.Map(location=[7.5399, -5.5471], zoom_start=6)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Satellite"
).add_to(m)

# Ajout des couches
for layer in st.session_state["uploaded_layers"]:
    if layer["type"] == "TIFF":
        if layer["name"] in ["MNT", "MNS"]:
            unique_id = str(uuid.uuid4())[:8]
            temp_png = f"temp_{unique_id}.png"
            apply_color_gradient(layer["path_4326"], temp_png)
            add_image_overlay(m, temp_png, layer["bounds"], layer["name"])
            os.remove(temp_png)
        else:
            add_image_overlay(m, layer["path_4326"], layer["bounds"], layer["name"])
    elif layer["type"] == "GeoJSON":
        folium.GeoJson(
            layer["data"],
            name=layer["name"],
            style_function=lambda x, color=layer["color"]: {
                "color": color,
                "weight": 4,
                "opacity": 0.7
            }
        ).add_to(m)

# Contrôles carte
Draw().add_to(m)
MeasureControl().add_to(m)
LayerControl().add_to(m)
output = st_folium(m, width=800, height=600)

# Calcul des volumes
if st.button("Calculer les volumes"):
    mns_layers = [l for l in st.session_state["uploaded_layers"] if l["name"] == "MNS"]
    mnt_layers = [l for l in st.session_state["uploaded_layers"] if l["name"] == "MNT"]
    
    if not mns_layers or not mnt_layers:
        st.error("MNS et MNT requis pour le calcul")
    else:
        mns = mns_layers[0]
        mnt = mnt_layers[0]
        
        if mns["utm_crs"] != mnt["utm_crs"]:
            st.error("Les couches doivent être dans la même zone UTM")
        else:
            polygons = [
                f for f in output["all_drawings"] 
                if f["geometry"]["type"] == "Polygon"
            ]
            
            if not polygons:
                st.error("Dessinez au moins un polygone")
            else:
                volume = calculate_volume_utm(
                    mns["path_utm"],
                    mnt["path_utm"],
                    polygons,
                    mns["utm_crs"]
                )
                
                if volume is not None:
                    st.success(f"Volume total : {volume:.2f} m³")
