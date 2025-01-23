import streamlit as st
import numpy as np
import geopandas as gpd
from shapely.geometry import shape
import rasterio
from rasterio.plot import reshape_as_image
from rasterio.warp import transform_bounds
import matplotlib.pyplot as plt
import os
import uuid

# Fonction pour calculer la surface d'un polygone
def calculate_area(polygon):
    """Calcule la surface d'un polygone en mètres carrés."""
    geom = shape(polygon)
    return geom.area

# Fonction pour calculer le volume sans MNT
def calculate_volume_without_mnt(mns, mns_bounds, polygons_gdf, reference_altitude):
    """
    Calcule le volume sans utiliser de MNT en utilisant une altitude de référence.
    
    :param mns: Données MNS (Modèle Numérique de Surface)
    :param mns_bounds: Bornes géographiques du MNS
    :param polygons_gdf: GeoDataFrame contenant les polygones
    :param reference_altitude: Altitude de référence pour le calcul du volume
    :return: Volume positif, volume négatif, volume réel
    """
    positive_volume = 0.0
    negative_volume = 0.0
    
    for idx, polygon in polygons_gdf.iterrows():
        try:
            # Masquer les données en dehors du polygone courant
            mask = polygon.geometry
            mns_masked = np.where(mask, mns, np.nan)
            
            # Calculer la différence entre le MNS et l'altitude de référence
            diff = mns_masked - reference_altitude
            
            # Calculer les volumes positif et négatif
            positive_volume += np.nansum(np.where(diff > 0, diff, 0)) * (mns_bounds[2] - mns_bounds[0]) * (mns_bounds[3] - mns_bounds[1]) / (mns.shape[0] * mns.shape[1])
            negative_volume += np.nansum(np.where(diff < 0, diff, 0)) * (mns_bounds[2] - mns_bounds[0]) * (mns_bounds[3] - mns_bounds[1]) / (mns.shape[0] * mns.shape[1])
        except Exception as e:
            st.error(f"Erreur lors du calcul du volume pour le polygone {idx + 1} : {e}")
    
    # Calculer le volume réel (différence entre positif et négatif)
    real_volume = positive_volume + negative_volume
    
    return positive_volume, negative_volume, real_volume

# Fonction pour charger un fichier TIFF
def load_tiff(tiff_path):
    """Charge un fichier TIFF et retourne les données et les bornes."""
    try:
        with rasterio.open(tiff_path) as src:
            data = src.read(1)
            bounds = src.bounds
            transform = src.transform
            if transform.is_identity:
                st.warning("La transformation est invalide. Génération d'une transformation par défaut.")
                transform, width, height = calculate_default_transform(src.crs, src.crs, src.width, src.height, *src.bounds)
            st.write(f"Transform: {transform}")
            st.write(f"Résolution spatiale: {transform.a} m (largeur) x {-transform.e} m (hauteur)")
        return data, bounds
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier TIFF : {e}")
        return None, None

# Titre de l'application
st.title("Calcul des Surfaces et Volumes")

# Téléversement du fichier MNS
uploaded_mns = st.file_uploader("Téléverser un fichier MNS (TIFF)", type=["tif", "tiff"])

if uploaded_mns:
    # Sauvegarder le fichier téléversé
    unique_id = str(uuid.uuid4())[:8]
    mns_path = f"uploaded_mns_{unique_id}.tiff"
    with open(mns_path, "wb") as f:
        f.write(uploaded_mns.read())

    # Charger les données MNS
    mns, mns_bounds = load_tiff(mns_path)

    if mns is not None:
        # Téléversement du fichier GeoJSON contenant les polygones
        uploaded_geojson = st.file_uploader("Téléverser un fichier GeoJSON contenant les polygones", type=["geojson"])

        if uploaded_geojson:
            # Charger les données GeoJSON
            geojson_data = gpd.read_file(uploaded_geojson)

            # Convertir les polygones en GeoDataFrame
            polygons_gdf = gpd.GeoDataFrame(geojson_data, geometry='geometry')

            # Calculer la surface des polygones
            for idx, polygon in polygons_gdf.iterrows():
                area = calculate_area(polygon.geometry)
                st.write(f"Surface du polygone {idx + 1} : {area:.2f} m²")

            # Saisie de l'altitude de référence
            reference_altitude = st.number_input(
                "Entrez l'altitude de référence (en mètres) :",
                value=0.0,
                step=0.1,
                key="reference_altitude"
            )

            # Calcul du volume
            if st.button("Calculer le volume"):
                positive_volume, negative_volume, real_volume = calculate_volume_without_mnt(
                    mns, mns_bounds, polygons_gdf, reference_altitude
                )
                st.write(f"Volume positif (au-dessus de la référence) : {positive_volume:.2f} m³")
                st.write(f"Volume négatif (en dessous de la référence) : {negative_volume:.2f} m³")
                st.write(f"Volume réel (différence) : {real_volume:.2f} m³")

    # Supprimer le fichier temporaire après utilisation
    os.remove(mns_path)
