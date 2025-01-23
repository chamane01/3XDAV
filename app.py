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
    """Détermine la zone UTM à partir de la longitude (en degrés)"""
    return int((longitude + 180) // 6) + 1

def get_utm_epsg(lon, lat):
    """Retourne le code EPSG UTM approprié (hémisphère Nord pour la Côte d'Ivoire)"""
    zone = get_utm_zone(lon)
    return 32600 + zone  # 326XX pour les zones Nord

# Fonction pour reprojeter un fichier TIFF avec un nom unique
def reproject_tiff(input_tiff, target_crs=None):
    """Reprojette automatiquement le TIFF en UTM local ou selon le CRS spécifié"""
    with rasterio.open(input_tiff) as src:
        if target_crs is None:
            # Calcul automatique de la zone UTM
            bounds = src.bounds
            center_lon = (bounds.left + bounds.right) / 2
            center_lat = (bounds.bottom + bounds.top) / 2
            utm_epsg = get_utm_epsg(center_lon, center_lat)
            target_crs = f"EPSG:{utm_epsg}"
        
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
        return reprojected_tiff

# Fonction pour appliquer un gradient de couleur à un MNT/MNS
def apply_color_gradient(tiff_path, output_path):
    """Apply a color gradient to the DEM TIFF and save it as a PNG."""
    with rasterio.open(tiff_path) as src:
        dem_data = src.read(1)
        cmap = plt.get_cmap("terrain")
        norm = plt.Normalize(vmin=dem_data.min(), vmax=dem_data.max())
        colored_image = cmap(norm(dem_data))
        plt.imsave(output_path, colored_image)
        plt.close()

# Fonction pour ajouter une image TIFF à la carte
def add_image_overlay(map_object, tiff_path, bounds, name):
    """Add a TIFF image overlay to a Folium map."""
    with rasterio.open(tiff_path) as src:
        image = reshape_as_image(src.read())
        folium.raster_layers.ImageOverlay(
            image=image,
            bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
            name=name,
            opacity=0.6,
        ).add_to(map_object)

# Fonction pour charger un fichier TIFF
def load_tiff(tiff_path):
    """Charge un fichier TIFF et retourne les données, bornes et transform"""
    try:
        with rasterio.open(tiff_path) as src:
            data = src.read(1)
            bounds = src.bounds
            transform = src.transform
            if transform.is_identity:
                st.warning("La transformation est invalide. Génération d'une transformation par défaut.")
                transform, width, height = calculate_default_transform(src.crs, src.crs, src.width, src.height, *src.bounds)
            st.write(f"CRS: {src.crs}")
            st.write(f"Résolution spatiale: {transform.a:.2f} m x {-transform.e:.2f} m")
            return data, bounds, transform
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier TIFF : {e}")
        return None, None, None

# Fonction pour calculer la surface d'un polygone
def calculate_surface(polygon, crs="EPSG:4326"):
    """Calcule la surface d'un polygone en mètres carrés (m²)."""
    try:
        geom = shape(polygon["geometry"])
        gdf = gpd.GeoDataFrame(geometry=[geom], crs=crs)
        gdf = gdf.to_crs("EPSG:3857")
        surface = gdf.geometry.area.values[0]
        return surface
    except Exception as e:
        st.error(f"Erreur lors du calcul de la surface : {e}")
        return None

# Fonctions de calcul de volume modifiées
def calculate_volume_for_each_polygon(mns, mnt, transform, polygons_gdf):
    """Calcule le volume pour chaque polygone avec la bonne résolution"""
    volumes = []
    pixel_area = transform.a * -transform.e  # Surface d'un pixel en m²
    
    for idx, polygon in polygons_gdf.iterrows():
        try:
            mask = polygon.geometry
            mns_masked = np.where(mask, mns, np.nan)
            mnt_masked = np.where(mask, mnt, np.nan)
            
            volume = np.nansum(mns_masked - mnt_masked) * pixel_area
            volumes.append(volume)
            st.write(f"Volume pour le polygone {idx + 1} : {volume:.2f} m³")
        except Exception as e:
            st.error(f"Erreur lors du calcul du volume pour le polygone {idx + 1} : {e}")
    return volumes

def calculate_volume_without_mnt(mns, transform, polygons_gdf, reference_altitude):
    """Calcule le volume sans MNT avec la bonne résolution"""
    positive_volume = 0.0
    negative_volume = 0.0
    pixel_area = transform.a * -transform.e
    
    for idx, polygon in polygons_gdf.iterrows():
        try:
            mask = polygon.geometry
            mns_masked = np.where(mask, mns, np.nan)
            diff = mns_masked - reference_altitude
            
            positive_volume += np.nansum(np.where(diff > 0, diff, 0)) * pixel_area
            negative_volume += np.nansum(np.where(diff < 0, diff, 0)) * pixel_area
        except Exception as e:
            st.error(f"Erreur lors du calcul du volume pour le polygone {idx + 1} : {e}")
    
    return positive_volume, negative_volume, (positive_volume + negative_volume)

# Le reste du code reste inchangé jusqu'à la section de téléversement...

# Initialisation des couches et des entités dans la session Streamlit
if "layers" not in st.session_state:
    st.session_state["layers"] = {}

if "uploaded_layers" not in st.session_state:
    st.session_state["uploaded_layers"] = []

if "new_features" not in st.session_state:
    st.session_state["new_features"] = []

# Interface utilisateur
st.title("Carte Topographique et Analyse Spatiale")
st.markdown("""Créez des entités géographiques et analysez les données spatiales.""")

# Sidebar pour la gestion des couches
with st.sidebar:
    st.header("Gestion des Couches")

    # Section 1: Ajout d'une nouvelle couche
    st.markdown("### 1- Ajouter une nouvelle couche")
    new_layer_name = st.text_input("Nom de la nouvelle couche à ajouter", "")
    if st.button("Ajouter la couche", key="add_layer_button") and new_layer_name:
        if new_layer_name not in st.session_state["layers"]:
            st.session_state["layers"][new_layer_name] = []
            st.success(f"La couche '{new_layer_name}' a été ajoutée.")
        else:
            st.warning(f"La couche '{new_layer_name}' existe déjà.")

    # Sélection de la couche active
    if st.session_state["layers"]:
        layer_name = st.selectbox(
            "Choisissez la couche active",
            list(st.session_state["layers"].keys())
        )
    else:
        st.write("Aucune couche disponible.")

    # Gestion des entités temporaires
    if st.session_state["new_features"]:
        st.write(f"**Entités temporaires ({len(st.session_state['new_features'])}) :**")
        for idx, feature in enumerate(st.session_state["new_features"]):
            st.write(f"- Entité {idx + 1}: {feature['geometry']['type']}")

    if st.button("Enregistrer les entités", key="save_features_button") and st.session_state["layers"]:
        current_layer = st.session_state["layers"][layer_name]
        for feature in st.session_state["new_features"]:
            if feature not in current_layer:
                current_layer.append(feature)
        st.session_state["new_features"] = []
        st.success(f"Entités enregistrées dans '{layer_name}'.")

    # Gestion des entités existantes
    if st.session_state["layers"]:
        selected_layer = st.selectbox("Choisissez une couche", list(st.session_state["layers"].keys()))
        if st.session_state["layers"][selected_layer]:
            entity_idx = st.selectbox(
                "Sélectionnez une entité",
                range(len(st.session_state["layers"][selected_layer])),
                format_func=lambda idx: f"Entité {idx + 1}: {st.session_state['layers'][selected_layer][idx]['geometry']['type']}"
            )
            selected_entity = st.session_state["layers"][selected_layer][entity_idx]
            new_name = st.text_input("Nom de l'entité", selected_entity.get("properties", {}).get("name", ""))
            
            if st.button("Modifier le nom", key=f"edit_{entity_idx}"):
                selected_entity["properties"]["name"] = new_name
                st.success("Nom mis à jour.")
            
            if st.button("Supprimer", key=f"delete_{entity_idx}"):
                st.session_state["layers"][selected_layer].pop(entity_idx)
                st.success("Entité supprimée.")

    st.markdown("---")
    st.markdown("### 2- Téléverser des fichiers")

    # Section de téléversement TIFF avec sélection UTM
    tiff_type = st.selectbox(
        "Type de fichier TIFF",
        ["MNT", "MNS", "Orthophoto"],
        index=None
    )

    if tiff_type:
        utm_choice = st.radio(
            "Projection UTM",
            ["Détection automatique", "Manuelle (29N/30N)"],
            help="Choisir la projection pour la Côte d'Ivoire"
        )
        
        target_crs = None
        if utm_choice == "Manuelle (29N/30N)":
            utm_zone = st.selectbox("Zone UTM", ["29N (EPSG:32629)", "30N (EPSG:32630)"])
            target_crs = "EPSG:32629" if "29" in utm_zone else "EPSG:32630"

        uploaded_tiff = st.file_uploader(f"Téléverser {tiff_type}", type=["tif", "tiff"])
        
        if uploaded_tiff:
            unique_id = str(uuid.uuid4())[:8]
            tiff_path = f"uploaded_{unique_id}.tiff"
            with open(tiff_path, "wb") as f:
                f.write(uploaded_tiff.read())

            try:
                reprojected_tiff = reproject_tiff(tiff_path, target_crs)
                with rasterio.open(reprojected_tiff) as src:
                    bounds = src.bounds
                    if not any(layer["name"] == tiff_type for layer in st.session_state["uploaded_layers"]):
                        st.session_state["uploaded_layers"].append({
                            "type": "TIFF",
                            "name": tiff_type,
                            "path": reprojected_tiff,
                            "bounds": bounds
                        })
                        st.success(f"{tiff_type} ajouté!")
                    else:
                        st.warning(f"{tiff_type} existe déjà.")
            except Exception as e:
                st.error(f"Erreur: {str(e)}")
            finally:
                os.remove(tiff_path)

    # Section de téléversement GeoJSON
    geojson_type = st.selectbox(
        "Type de fichier GeoJSON",
        ["Polygonale", "Routes", "Cours d'eau", "Bâtiments", "Pistes", "Plantations",
         "Électricité", "Assainissements", "Villages", "Villes", "Chemin de fer", "Parc et réserves"],
        index=None
    )

    if geojson_type:
        uploaded_geojson = st.file_uploader(f"Téléverser {geojson_type}", type=["geojson"])
        if uploaded_geojson:
            try:
                geojson_data = json.load(uploaded_geojson)
                if not any(layer["name"] == geojson_type for layer in st.session_state["uploaded_layers"]):
                    st.session_state["uploaded_layers"].append({
                        "type": "GeoJSON",
                        "name": geojson_type,
                        "data": geojson_data
                    })
                    st.success(f"{geojson_type} ajouté!")
                else:
                    st.warning(f"{geojson_type} existe déjà.")
            except Exception as e:
                st.error(f"Erreur: {str(e)}")

    # Liste des couches téléversées
    st.markdown("### Couches téléversées")
    if st.session_state["uploaded_layers"]:
        for i, layer in enumerate(st.session_state["uploaded_layers"]):
            col1, col2 = st.columns([4,1])
            with col1:
                st.write(f"{i+1}. {layer['name']} ({layer['type']})")
            with col2:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state["uploaded_layers"].pop(i)
                    st.success("Couche supprimée")
    else:
        st.write("Aucune couche téléversée")

# Carte Folium
m = folium.Map(location=[7.5399, -5.5471], zoom_start=6)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Satellite"
).add_to(m)

folium.TileLayer(
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="OpenTopoMap",
    name="Topographique"
).add_to(m)

# Ajout des couches
for layer, features in st.session_state["layers"].items():
    layer_group = folium.FeatureGroup(name=layer)
    for feature in features:
        geom_type = feature["geometry"]["type"]
        coords = feature["geometry"]["coordinates"]
        popup = feature.get("properties", {}).get("name", "")
        
        if geom_type == "Point":
            folium.Marker([coords[1], coords[0]], popup=popup).add_to(layer_group)
        elif geom_type == "LineString":
            folium.PolyLine(
                locations=[[lat, lon] for lon, lat in coords],
                color="blue",
                popup=popup
            ).add_to(layer_group)
        elif geom_type == "Polygon":
            folium.Polygon(
                locations=[[lat, lon] for lon, lat in coords[0]],
                color="green",
                popup=popup
            ).add_to(layer_group)
    layer_group.add_to(m)

# Ajout des couches téléversées
for layer in st.session_state["uploaded_layers"]:
    if layer["type"] == "TIFF":
        if layer["name"] in ["MNT", "MNS"]:
            unique_id = str(uuid.uuid4())[:8]
            temp_png = f"temp_{unique_id}.png"
            apply_color_gradient(layer["path"], temp_png)
            add_image_overlay(m, temp_png, layer["bounds"], layer["name"])
            os.remove(temp_png)
        else:
            add_image_overlay(m, layer["path"], layer["bounds"], layer["name"])
    elif layer["type"] == "GeoJSON":
        color = geojson_colors.get(layer["name"], "blue")
        folium.GeoJson(
            layer["data"],
            name=layer["name"],
            style_function=lambda x, color=color: {
                "color": color,
                "weight": 4,
                "opacity": 0.7
            }
        ).add_to(m)

# Contrôles de la carte
Draw(export=True).add_to(m)
MeasureControl().add_to(m)
LayerControl().add_to(m)

# Affichage de la carte
output = st_folium(m, width=800, height=600)

# Gestion des nouvelles entités dessinées
if output.get("last_active_drawing"):
    new_feature = output["last_active_drawing"]
    if new_feature not in st.session_state["new_features"]:
        st.session_state["new_features"].append(new_feature)
        st.rerun()

# Section d'analyse spatiale
st.markdown("## Analyse Spatiale")
if st.button("Surfaces et volumes"):
    st.session_state['active_button'] = "volumes"
if st.button("Carte de contours"):
    st.session_state['active_button'] = "contours"

if st.session_state.get('active_button') == "volumes":
    st.markdown("### Calcul des volumes")
    
    polygons = []
    for layer in st.session_state["uploaded_layers"] + list(st.session_state["layers"].values()):
        if isinstance(layer, dict) and layer["type"] == "GeoJSON":
            polygons.extend([f for f in layer["data"]["features"] if f["geometry"]["type"] == "Polygon"])
        elif isinstance(layer, list):
            polygons.extend([f for f in layer if f["geometry"]["type"] == "Polygon"])
    
    if not polygons:
        st.warning("Aucun polygone trouvé!")
    else:
        method = st.radio("Méthode", ["MNS - MNT", "MNS seul"])
        
        mns_layer = next((l for l in st.session_state["uploaded_layers"] if l["name"] == "MNS"), None)
        mnt_layer = next((l for l in st.session_state["uploaded_layers"] if l["name"] == "MNT"), None)
        
        if method == "MNS - MNT" and not mnt_layer:
            st.error("MNT requis pour cette méthode")
        else:
            if mns_layer:
                mns, _, mns_transform = load_tiff(mns_layer["path"])
                polygons_gdf = convert_polygons_to_gdf(polygons)
                
                if method == "MNS - MNT" and mnt_layer:
                    mnt, _, mnt_transform = load_tiff(mnt_layer["path"])
                    if mns_transform != mnt_transform:
                        st.error("Les rasters doivent avoir la même résolution")
                    else:
                        volumes = calculate_volume_for_each_polygon(mns, mnt, mns_transform, polygons_gdf)
                        st.write(f"Volume total: {sum(volumes):.2f} m³")
                else:
                    ref_alt = st.number_input("Altitude de référence (m)", value=0.0)
                    pos, neg, total = calculate_volume_without_mnt(mns, mns_transform, polygons_gdf, ref_alt)
                    st.write(f"Volume positif: {pos:.2f} m³")
                    st.write(f"Volume négatif: {neg:.2f} m³")
                    st.write(f"Volume net: {total:.2f} m³")
