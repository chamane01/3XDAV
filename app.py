import streamlit as st
import folium
from folium.plugins import Draw
import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import shape
import tempfile
import uuid
import os
from PIL import Image
from streamlit_folium import st_folium

# Fonction pour reprojeter un fichier TIFF en EPSG:4326
def reproject_tiff(input_path, output_path, dst_crs='EPSG:4326'):
    with rasterio.open(input_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(output_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest)

# Fonction pour calculer les volumes et surfaces
def calculate_volume_and_area(mns_path, mnt_path, polygon):
    try:
        with rasterio.open(mns_path) as mns:
            mns_data = mns.read(1)
            mns_transform = mns.transform

        with rasterio.open(mnt_path) as mnt:
            mnt_data = mnt.read(1)
            mnt_transform = mnt.transform

        # Convertir le polygone en masque raster
        from rasterio.features import geometry_mask
        mask = geometry_mask([polygon], transform=mns_transform, out_shape=mns_data.shape, invert=True)

        # Calculer la différence entre MNS et MNT
        diff = mns_data - mnt_data
        diff = np.where(mask, diff, 0)

        # Calculer le volume et la surface
        volume = np.sum(diff) * abs(mns_transform.a * mns_transform.e)
        area = np.sum(mask) * abs(mns_transform.a * mns_transform.e)

        return volume, area
    except Exception as e:
        st.error(f"Erreur lors du calcul des volumes et surfaces : {e}")
        return None, None

# Fonction pour générer des contours
def generate_contours(mnt_path, interval=10):
    with rasterio.open(mnt_path) as src:
        elevation = src.read(1)
        transform = src.transform

        # Générer les contours
        fig, ax = plt.subplots()
        contours = ax.contour(elevation, levels=np.arange(0, np.max(elevation), interval), colors='black')
        plt.close(fig)

        # Convertir les contours en géométries GeoJSON
        contour_geometries = []
        for contour_level in contours.allsegs:
            for contour in contour_level:
                if len(contour) > 0:
                    contour_geometries.append({
                        "type": "LineString",
                        "coordinates": [transform * (x, y) for x, y in contour]
                    })

        return contour_geometries

# Initialisation de la session Streamlit
if 'new_features' not in st.session_state:
    st.session_state['new_features'] = []

# Interface utilisateur
st.title("Application de Cartographie et d'Analyse Spatiale")

# Sidebar pour la gestion des couches et le téléversement de fichiers
with st.sidebar:
    st.header("Gestion des Couches")
    layer_name = st.text_input("Nom de la nouvelle couche")
    if st.button("Ajouter une couche"):
        if layer_name:
            st.session_state[layer_name] = []
            st.success(f"Couche '{layer_name}' ajoutée.")
        else:
            st.error("Veuillez entrer un nom de couche.")

    st.header("Téléversement de fichiers")
    uploaded_tiff = st.file_uploader("Téléverser un fichier TIFF", type=['tif', 'tiff'])
    uploaded_geojson = st.file_uploader("Téléverser un fichier GeoJSON", type=['geojson'])

    if uploaded_tiff:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp_file:
            tmp_file.write(uploaded_tiff.read())
            reprojected_path = f"{uuid.uuid4()}.tif"
            reproject_tiff(tmp_file.name, reprojected_path)
            st.session_state['uploaded_tiff'] = reprojected_path
            st.success("Fichier TIFF téléversé et reprojeté avec succès.")

    if uploaded_geojson:
        gdf = gpd.read_file(uploaded_geojson)
        st.session_state['uploaded_geojson'] = gdf
        st.success("Fichier GeoJSON téléversé avec succès.")

# Carte Folium
m = folium.Map(location=[7.5399, -5.5471], zoom_start=7)

# Ajout des fonds de carte
folium.TileLayer('openstreetmap', name='Carte Topographique').add_to(m)
folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                 name='Carte Satellite', attr='Esri').add_to(m)

# Ajout des couches téléversées
if 'uploaded_tiff' in st.session_state:
    folium.raster_layers.ImageOverlay(
        image=st.session_state['uploaded_tiff'],
        bounds=[[7.5399, -5.5471], [8.5399, -4.5471]],  # Ajuster les limites selon le fichier
        opacity=0.6,
        name='TIFF Téléversé'
    ).add_to(m)

if 'uploaded_geojson' in st.session_state:
    for idx, row in st.session_state['uploaded_geojson'].iterrows():
        folium.GeoJson(
            row['geometry'],
            style_function=lambda x: {'color': 'orange' if x['geometry']['type'] == 'LineString' else 'green'}
        ).add_to(m)

# Ajout du plugin Draw pour dessiner des entités
Draw(export=True).add_to(m)

# Affichage de la carte
folium_static = st_folium(m, width=700, height=500)

# Gestion des entités dessinées
if folium_static.get('last_active_drawing'):
    new_feature = folium_static['last_active_drawing']
    st.session_state['new_features'].append(new_feature)
    st.success("Nouvelle entité dessinée ajoutée.")

# Affichage des entités temporairement dessinées
if st.session_state['new_features']:
    st.header("Entités Dessinées")
    for feature in st.session_state['new_features']:
        st.write(feature)

# Analyse spatiale
if st.button("Calculer les volumes et surfaces"):
    if 'uploaded_tiff' in st.session_state and st.session_state['new_features']:
        mns_path = st.session_state['uploaded_tiff']
        mnt_path = "path_to_mnt.tif"  # Remplacez par le chemin réel du MNT ou téléversez un fichier MNT
        if not os.path.exists(mnt_path):
            st.error("Veuillez téléverser un fichier MNT.")
        else:
            polygon = shape(st.session_state['new_features'][0]['geometry'])
            volume, area = calculate_volume_and_area(mns_path, mnt_path, polygon)
            if volume is not None and area is not None:
                st.success(f"Volume: {volume:.2f} m³, Surface: {area:.2f} m²")
    else:
        st.error("Veuillez téléverser un fichier TIFF et dessiner un polygone.")

if st.button("Générer des contours"):
    if 'uploaded_tiff' in st.session_state:
        contours = generate_contours(st.session_state['uploaded_tiff'])
        st.session_state['contours'] = contours
        st.success("Contours générés avec succès.")
    else:
        st.error("Veuillez téléverser un fichier TIFF.")

# Affichage des contours générés
if 'contours' in st.session_state:
    st.header("Contours Générés")
    for contour in st.session_state['contours']:
        st.write(contour)

# Nettoyage des fichiers temporaires
if 'uploaded_tiff' in st.session_state:
    os.remove(st.session_state['uploaded_tiff'])
    del st.session_state['uploaded_tiff']
