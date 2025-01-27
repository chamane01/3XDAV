import streamlit as st
import folium
from folium.plugins import Draw
import geopandas as gpd
import tempfile
import os
import uuid
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import rowcol
import numpy as np
import logging
from shapely.geometry import Polygon, Point, LineString, shape
from shapely.ops import transform
import pyproj
from functools import partial
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
from matplotlib import cm
from fpdf import FPDF

# Configuration du logging pour tracer les opérations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fonction pour créer une carte Folium centrée sur la Côte d'Ivoire
def create_map():
    """
    Crée une carte Folium centrée sur la Côte d'Ivoire avec un outil de dessin.
    Returns:
        folium.Map: Une carte Folium configurée.
    """
    m = folium.Map(location=[7.5399, -5.5471], zoom_start=7, crs='EPSG3857')
    Draw(export=True).add_to(m)  # Ajoute un outil de dessin à la carte
    return m

# Fonction pour reprojeter un fichier TIFF en EPSG:3857
def reproject_tiff_to_3857(input_path, output_path):
    """
    Reprojette un fichier TIFF en EPSG:3857 (Web Mercator).
    Args:
        input_path (str): Chemin du fichier TIFF source.
        output_path (str): Chemin du fichier TIFF reprojeté.
    """
    try:
        with rasterio.open(input_path) as src:
            # Calculer la transformation pour la reprojection
            transform, width, height = calculate_default_transform(
                src.crs, 'EPSG:3857', src.width, src.height, *src.bounds)
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': 'EPSG:3857',
                'transform': transform,
                'width': width,
                'height': height
            })

            # Reprojeter le fichier TIFF
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs='EPSG:3857',
                        resampling=Resampling.nearest)
        logger.info(f"Fichier TIFF reprojeté et sauvegardé : {output_path}")
    except Exception as e:
        logger.error(f"Erreur lors de la reprojection du fichier TIFF : {e}")
        raise

# Fonction pour vérifier si une géométrie est dans l'emprise du raster
def is_geometry_within_raster_extent(geometry, raster_path):
    """
    Vérifie si une géométrie est dans l'emprise du raster.
    Args:
        geometry (shapely.geometry): Géométrie à vérifier.
        raster_path (str): Chemin du fichier raster.
    Returns:
        bool: True si la géométrie est dans l'emprise, False sinon.
    """
    try:
        with rasterio.open(raster_path) as src:
            transform = src.transform
            for coord in geometry.coords:
                row, col = rowcol(transform, coord[0], coord[1])
                if row < 0 or row >= src.height or col < 0 or col >= src.width:
                    return False
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de l'emprise : {e}")
        return False

# Fonction pour convertir les coordonnées WGS84 (EPSG:4326) en EPSG:3857
def convert_wgs84_to_epsg3857(geometry):
    """
    Convertit une géométrie de WGS84 (EPSG:4326) en EPSG:3857 (Web Mercator).
    Args:
        geometry (shapely.geometry): Géométrie à convertir.
    Returns:
        shapely.geometry: Géométrie reprojetée.
    """
    try:
        project = partial(
            pyproj.transform,
            pyproj.Proj(init='epsg:4326'),  # WGS84
            pyproj.Proj(init='epsg:3857')   # Web Mercator
        )
        return transform(project, geometry)
    except Exception as e:
        logger.error(f"Erreur lors de la conversion des coordonnées : {e}")
        raise

# Fonction pour gérer les fichiers téléversés
def handle_uploaded_file(uploaded_file):
    """
    Gère les fichiers téléversés (TIFF ou GeoJSON) et les reprojette si nécessaire.
    Args:
        uploaded_file (UploadedFile): Fichier téléversé via Streamlit.
    Returns:
        tuple: (Chemin du fichier, bornes du fichier) ou (None, None) en cas d'erreur.
    """
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    unique_id = str(uuid.uuid4())
    temp_file_path = os.path.join(tempfile.gettempdir(), f"{unique_id}{file_ext}")
    reprojected_file_path = os.path.join(tempfile.gettempdir(), f"{unique_id}_reprojected{file_ext}")

    try:
        # Sauvegarder le fichier téléversé temporairement
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        if file_ext == '.tif' or file_ext == '.tiff':
            # Vérifier le CRS du fichier TIFF
            with rasterio.open(temp_file_path) as src:
                if src.crs is None:
                    st.warning("Le fichier TIFF n'a pas de CRS défini.")
                    os.unlink(temp_file_path)
                    return None, None
                if src.crs.to_epsg() != 3857:
                    st.info(f"Reprojection du fichier TIFF de {src.crs} vers EPSG:3857.")
                    reproject_tiff_to_3857(temp_file_path, reprojected_file_path)
                    bounds = rasterio.open(reprojected_file_path).bounds
                    st.session_state.temp_files.append(reprojected_file_path)
                    st.session_state.raster_path = reprojected_file_path
                    return reprojected_file_path, bounds
                else:
                    bounds = src.bounds
                    st.session_state.temp_files.append(temp_file_path)
                    st.session_state.raster_path = temp_file_path
                    return temp_file_path, bounds

        elif file_ext == '.geojson':
            # Vérifier le CRS du fichier GeoJSON
            gdf = gpd.read_file(temp_file_path)
            if gdf.crs is None:
                st.warning("Le fichier GeoJSON n'a pas de CRS défini.")
                os.unlink(temp_file_path)
                return None, None
            if gdf.crs.to_epsg() != 3857:
                st.info(f"Conversion du fichier GeoJSON de {gdf.crs} vers EPSG:3857.")
                gdf = gdf.to_crs('EPSG:3857')
                gdf.to_file(reprojected_file_path, driver='GeoJSON')
                bounds = gdf.total_bounds
                st.session_state.temp_files.append(reprojected_file_path)
                return reprojected_file_path, bounds
            else:
                bounds = gdf.total_bounds
                st.session_state.temp_files.append(temp_file_path)
                return temp_file_path, bounds

        else:
            st.error("Format de fichier non supporté. Veuillez téléverser un fichier TIFF ou GeoJSON.")
            os.unlink(temp_file_path)
            return None, None

    except Exception as e:
        logger.error(f"Erreur lors du traitement du fichier téléversé : {e}")
        return None, None

# Fonction pour nettoyer les fichiers temporaires
def clean_temp_files():
    """
    Supprime les fichiers temporaires stockés dans `st.session_state.temp_files`.
    """
    if 'temp_files' in st.session_state:
        for file_path in st.session_state.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Fichier temporaire supprimé : {file_path}")
            except Exception as e:
                logger.error(f"Erreur lors de la suppression du fichier {file_path}: {e}")
        st.session_state.temp_files = []
        st.success("Tous les fichiers temporaires ont été supprimés.")

# Fonction pour calculer le volume entre un MNS et un MNT
def calculate_volume(mns_path, mnt_path, polygon):
    """
    Calcule le volume entre un MNS et un MNT pour un polygone donné.
    Args:
        mns_path (str): Chemin du fichier MNS.
        mnt_path (str): Chemin du fichier MNT.
        polygon (shapely.geometry.Polygon): Polygone pour lequel calculer le volume.
    Returns:
        float: Volume calculé.
    """
    try:
        with rasterio.open(mns_path) as mns, rasterio.open(mnt_path) as mnt:
            mns_data, _ = mask(mns, [polygon], crop=True, nodata=np.nan)
            mnt_data, _ = mask(mnt, [polygon], crop=True, nodata=np.nan)
            diff = mns_data - mnt_data
            resolution = mns.res[0] * mns.res[1]  # Résolution en m²
            volume = np.nansum(diff) * resolution
            return volume
    except Exception as e:
        logger.error(f"Erreur lors du calcul du volume : {e}")
        raise

# Fonction pour générer des contours
def generate_contours(tiff_path, output_path, interval=10):
    """
    Génère une carte de contours à partir d'un fichier TIFF.
    Args:
        tiff_path (str): Chemin du fichier TIFF.
        output_path (str): Chemin de sortie pour l'image des contours.
        interval (int): Intervalle entre les contours.
    """
    try:
        with rasterio.open(tiff_path) as src:
            elevation = src.read(1)
            transform = src.transform
            x = np.arange(0, src.width)
            y = np.arange(0, src.height)
            x, y = np.meshgrid(x, y)
            x = transform[2] + x * transform[0]
            y = transform[5] + y * transform[4]
            fig, ax = plt.subplots()
            contours = ax.contour(x, y, elevation, levels=np.arange(elevation.min(), elevation.max(), interval), cmap=cm.terrain)
            ax.clabel(contours, inline=True, fontsize=8)
            plt.savefig(output_path, dpi=300)
            plt.close()
            logger.info(f"Carte de contours générée : {output_path}")
    except Exception as e:
        logger.error(f"Erreur lors de la génération des contours : {e}")
        raise

# Fonction pour générer un rapport PDF
def generate_report(volumes, areas, output_path):
    """
    Génère un rapport PDF avec les volumes et surfaces calculés.
    Args:
        volumes (list): Liste des volumes calculés.
        areas (list): Liste des surfaces calculées.
        output_path (str): Chemin de sortie pour le rapport PDF.
    """
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Rapport d'Analyse Spatiale", ln=True, align="C")
        pdf.cell(200, 10, txt="Volumes et Surfaces Calculés", ln=True, align="C")
        for i, (volume, area) in enumerate(zip(volumes, areas)):
            pdf.cell(200, 10, txt=f"Polygone {i+1}: Volume = {volume:.2f} m³, Surface = {area:.2f} m²", ln=True)
        pdf.output(output_path)
        logger.info(f"Rapport généré : {output_path}")
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport : {e}")
        raise

# Initialisation de la session pour stocker les fichiers temporaires
if 'temp_files' not in st.session_state:
    st.session_state.temp_files = []

# Interface Streamlit
st.title("Carte Folium avec outil de dessin et gestion de fichiers")

# Création de la carte
m = create_map()

# Affichage de la carte dans Streamlit
folium_static = st_folium(m, width=700, height=500)

# Gestion des fichiers téléversés
uploaded_file = st.file_uploader("Téléversez un fichier TIFF ou GeoJSON", type=['tif', 'tiff', 'geojson'])
if uploaded_file is not None:
    file_path, bounds = handle_uploaded_file(uploaded_file)
    if file_path is not None and bounds is not None:
        st.success("Fichier téléversé et reprojeté avec succès.")
        st.write(f"Bornes du fichier reprojeté : {bounds}")

        # Centrer la carte sur les bornes du fichier reprojeté
        if uploaded_file.name.endswith('.geojson'):
            gdf = gpd.read_file(file_path)
            centroid = gdf.geometry.centroid
            m.location = [centroid.y.mean(), centroid.x.mean()]
        else:
            m.location = [(bounds.bottom + bounds.top) / 2, (bounds.left + bounds.right) / 2]

        # Rafraîchir la carte
        folium_static = st_folium(m, width=700, height=500)

# Gestion des entités dessinées par l'utilisateur
if folium_static.get('last_active_drawing'):
    drawing = folium_static['last_active_drawing']
    geometry = shape(drawing['geometry'])  # Convertir en objet Shapely

    try:
        # Convertir les coordonnées WGS84 (EPSG:4326) en EPSG:3857
        geometry_3857 = convert_wgs84_to_epsg3857(geometry)

        # Stocker les géométries reprojetées dans un GeoDataFrame
        if 'drawn_features' not in st.session_state:
            st.session_state.drawn_features = gpd.GeoDataFrame(geometry=[], crs='EPSG:3857')
        st.session_state.drawn_features = st.session_state.drawn_features.append(
            {'geometry': geometry_3857}, ignore_index=True
        )

        # Vérifier si la géométrie est dans l'emprise du raster
        if 'raster_path' in st.session_state:
            if is_geometry_within_raster_extent(geometry_3857, st.session_state.raster_path):
                st.success("La géométrie est dans l'emprise du raster.")
            else:
                st.error("La géométrie est hors de l'emprise du raster.")
        else:
            st.warning("Aucun raster n'a été téléversé pour vérifier l'emprise.")

        # Afficher les géométries dessinées
        st.write("Géométries dessinées (EPSG:3857):")
        st.write(st.session_state.drawn_features)

    except Exception as e:
        logger.error(f"Erreur lors du traitement de la géométrie dessinée : {e}")
        st.error("Une erreur est survenue lors du traitement de la géométrie dessinée.")

# Bouton pour nettoyer les fichiers temporaires
if st.button("Nettoyer les fichiers temporaires"):
    clean_temp_files()

# Nettoyage des fichiers temporaires à la fermeture de l'application
import atexit
atexit.register(clean_temp_files)
