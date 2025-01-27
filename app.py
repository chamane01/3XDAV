# Partie 1 : Initialisation et importation des bibliothèques
import streamlit as st
import folium
from folium.plugins import Draw
import rasterio
import geopandas as gpd
from shapely.geometry import shape, Polygon
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import tempfile
import uuid
import os
import json

# Configuration de l'application Streamlit
st.set_page_config(
    page_title="Application de cartographie et d'analyse spatiale",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialisation de l'état de la session
if "uploaded_layers" not in st.session_state:
    st.session_state["uploaded_layers"] = []  # Stockage des couches téléversées
if "new_features" not in st.session_state:
    st.session_state["new_features"] = []  # Entités dessinées non encore enregistrées
if "contour_map" not in st.session_state:
    st.session_state["contour_map"] = None  # Carte des contours

# Partie 2 : Création de la carte interactive Folium
def create_map():
    """
    Crée une carte Folium centrée sur la Côte d'Ivoire avec des fonds de carte optionnels.
    """
    center_coords = [7.539989, -5.54708]  # Latitude, Longitude

    folium_map = folium.Map(
        location=center_coords,
        zoom_start=7,  # Zoom initial
        tiles=None  # Désactiver le fond de carte par défaut
    )

    folium.TileLayer(
        tiles="OpenStreetMap", 
        name="Carte topographique", 
        control=True
    ).add_to(folium_map)

    folium.TileLayer(
        tiles="Stamen Terrain",
        name="Carte terrain",
        control=True
    ).add_to(folium_map)

    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
        name="Carte Humanitaire",
        attr="Humanitarian OSM",
        control=True
    ).add_to(folium_map)

    folium.TileLayer(
        tiles="CartoDB positron",
        name="Carte lumineuse",
        control=True
    ).add_to(folium_map)

    folium.TileLayer(
        tiles="CartoDB dark_matter",
        name="Carte sombre",
        control=True
    ).add_to(folium_map)

    folium.LayerControl(collapsed=False).add_to(folium_map)

    return folium_map

# Partie 3 : Téléversement et gestion des fichiers GeoJSON et TIFF
def upload_and_process_files():
    """
    Gère le téléversement de fichiers GeoJSON et TIFF.
    Les fichiers GeoJSON sont affichés avec des couleurs spécifiques.
    Les fichiers TIFF sont reprojetés et affichés sur la carte.
    """
    uploaded_files = st.sidebar.file_uploader(
        "Téléversez vos fichiers (GeoJSON, TIFF)", 
        type=["geojson", "tiff"], 
        accept_multiple_files=True
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_type = uploaded_file.name.split('.')[-1].lower()

            if file_type == "geojson":
                # Charger le fichier GeoJSON
                gdf = gpd.read_file(uploaded_file)
                color = "orange"  # Exemple de couleur

                # Ajouter les entités GeoJSON sur la carte
                for _, row in gdf.iterrows():
                    folium.GeoJson(
                        row.geometry, 
                        style_function=lambda x, color=color: {
                            "color": color, 
                            "weight": 2
                        }
                    ).add_to(st_map)

                st.session_state["geojson_layers"].append(uploaded_file.name)
                st.success(f"Fichier GeoJSON {uploaded_file.name} ajouté avec succès !")

            elif file_type == "tiff":
                # Reprojection et ajout à la carte (fonction déjà définie)
                temp_file = f"/tmp/{uuid.uuid4()}.tiff"
                with open(temp_file, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                reprojected_file = reproject_tiff(temp_file)
                add_image_overlay(reprojected_file, uploaded_file.name)

                st.session_state["tiff_layers"].append(uploaded_file.name)
                st.success(f"Fichier TIFF {uploaded_file.name} ajouté avec succès !")

def reproject_tiff(input_file):
    """
    Reprojette un fichier TIFF en EPSG:4326 et renvoie le chemin du fichier reprojeté.
    """
    output_file = f"/tmp/{uuid.uuid4()}_reprojected.tiff"
    with rio_open(input_file) as src:
        transform, width, height = calculate_default_transform(
            src.crs, "EPSG:4326", src.width, src.height, *src.bounds
        )
        kwargs = src.meta.copy()
        kwargs.update({
            "crs": "EPSG:4326",
            "transform": transform,
            "width": width,
            "height": height
        })

        with rio_open(output_file, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs="EPSG:4326",
                    resampling=Resampling.nearest
                )
    return output_file

# Partie 4 : Ajout des entités dessinées
def add_draw_tool(map_object):
    """
    Ajoute un outil de dessin à la carte pour permettre à l'utilisateur 
    de dessiner des points, lignes et polygones.
    """
    draw = Draw(
        draw_options={
            "polyline": True,
            "polygon": True,
            "circle": False,
            "rectangle": True,
            "marker": True,
        },
        edit_options={"edit": True, "remove": True}
    )
    draw.add_to(map_object)

def handle_drawn_features():
    """
    Gère les entités dessinées par l'utilisateur et les exporte en GeoJSON.
    """
    st.subheader("Entités dessinées")

    if "drawn_features" not in st.session_state:
        st.session_state["drawn_features"] = []

    if st.session_state["drawn_features"]:
        export_geojson = st.button("Exporter les entités en GeoJSON")
        if export_geojson:
            geojson_data = {
                "type": "FeatureCollection",
                "features": st.session_state["drawn_features"]
            }
            geojson_file = json.dumps(geojson_data, indent=2)
            st.download_button(
                label="Télécharger le fichier GeoJSON",
                data=geojson_file,
                file_name="drawn_features.geojson",
                mime="application/json"
            )

    for feature in st.session_state["drawn_features"]:
        geometry = feature["geometry"]
        st.write(f"Type : {geometry['type']}")
        st.write(f"Coordonnées : {geometry['coordinates']}")

# Génération de la carte dans Streamlit
st.title("Application de cartographie et d'analyse spatiale")
st.sidebar.header("Options de la carte")

# Création de la carte et ajout du plugin de dessin
st_map = create_map()
add_draw_tool(st_map)
st_data = st._folium_static(st_map, width=800, height=500)

# Appel de la fonction pour gérer le téléversement des fichiers
upload_and_process_files()
handle_drawn_features()

import numpy as np
import rasterio
from shapely.geometry import Polygon
from rasterio.mask import mask

def calculate_volume_and_area(mnt_path, mns_path, polygons, method=1, altitude_ref=None):
    """
    Calcule les volumes et surfaces pour des polygones donnés.
    
    Args:
        mnt_path (str): Chemin du fichier MNT.
        mns_path (str): Chemin du fichier MNS.
        polygons (list): Liste de polygones (format GeoJSON).
        method (int): Méthode de calcul (1 ou 2).
        altitude_ref (float): Altitude de référence pour la méthode 2.
    
    Returns:
        dict: Dictionnaire contenant les résultats des analyses.
    """
    results = []

    # Charger les MNT et MNS
    with rasterio.open(mnt_path) as mnt, rasterio.open(mns_path) as mns:
        for polygon in polygons:
            # Convertir le polygone en masque
            geom = [polygon]
            mnt_masked, mnt_transform = mask(mnt, geom, crop=True)
            mns_masked, mns_transform = mask(mns, geom, crop=True)

            # Extraire les données valides
            mnt_data = mnt_masked[mnt_masked != mnt.nodata]
            mns_data = mns_masked[mns_masked != mns.nodata]

            if method == 1:
                # Différence MNS - MNT
                volume = np.sum(mns_data - mnt_data)
            elif method == 2 and altitude_ref is not None:
                # Différence MNS - altitude de référence
                volume = np.sum(mns_data - altitude_ref)
            else:
                volume = 0

            # Surface (nombre de pixels * surface par pixel)
            pixel_area = mnt.res[0] * mnt.res[1]
            surface = len(mnt_data) * pixel_area

            # Résultats pour le polygone
            results.append({
                "polygon": polygon,
                "volume": volume,
                "surface": surface
            })

    return results
def handle_spatial_analysis():
    """
    Gère les analyses spatiales (volumes et surfaces) depuis l'interface utilisateur.
    """
    st.subheader("Analyse spatiale : Volumes et Surfaces")

    # Sélection des fichiers MNT et MNS
    mnt_file = st.file_uploader("Téléverser le MNT (fichier TIFF)", type=["tif"])
    mns_file = st.file_uploader("Téléverser le MNS (fichier TIFF)", type=["tif"])

    # Sélection de la méthode de calcul
    method = st.radio("Choisir la méthode de calcul", [1, 2])
    altitude_ref = None
    if method == 2:
        altitude_ref = st.number_input("Altitude de référence (mètres)", value=0.0)

    # Sélection des polygones pour l'analyse
    if "drawn_features" in st.session_state and st.session_state["drawn_features"]:
        polygons = [shape(feature["geometry"]) for feature in st.session_state["drawn_features"]]
    else:
        polygons = []

    if mnt_file and mns_file and polygons:
        # Bouton pour lancer l'analyse
        if st.button("Lancer l'analyse"):
            try:
                # Sauvegarder les fichiers téléversés temporairement
                mnt_path = f"mnt_{uuid.uuid4()}.tif"
                mns_path = f"mns_{uuid.uuid4()}.tif"
                with open(mnt_path, "wb") as f:
                    f.write(mnt_file.read())
                with open(mns_path, "wb") as f:
                    f.write(mns_file.read())

                # Calculer les volumes et surfaces
                results = calculate_volume_and_area(mnt_path, mns_path, polygons, method, altitude_ref)

                # Afficher les résultats
                st.write("Résultats de l'analyse :")
                for i, res in enumerate(results):
                    st.write(f"Polygone {i+1} : Surface = {res['surface']:.2f} m², Volume = {res['volume']:.2f} m³")

                # Nettoyer les fichiers temporaires
                os.remove(mnt_path)
                os.remove(mns_path)

            except Exception as e:
                st.error(f"Erreur lors de l'analyse spatiale : {e}")
    else:
        st.info("Veuillez téléverser les fichiers nécessaires et dessiner des polygones pour commencer l'analyse.")

# Ajouter l'analyse spatiale à l'application
handle_spatial_analysis()
import matplotlib.pyplot as plt

def generate_contours(mnt_path, output_path, interval=10):
    """
    Génère des courbes de niveau à partir d'un MNT.
    
    Args:
        mnt_path (str): Chemin du fichier MNT.
        output_path (str): Chemin de sauvegarde de l'image des contours.
        interval (int): Intervalle entre les courbes de niveau (en mètres).
    """
    with rasterio.open(mnt_path) as mnt:
        # Charger les données du MNT
        data = mnt.read(1)
        transform = mnt.transform

        # Masquer les valeurs invalides
        data = np.ma.masked_equal(data, mnt.nodata)

        # Créer les axes en fonction des dimensions du MNT
        x = np.arange(data.shape[1]) * transform[0] + transform[2]
        y = np.arange(data.shape[0]) * transform[4] + transform[5]
        X, Y = np.meshgrid(x, y)

        # Tracer les courbes de niveau
        plt.figure(figsize=(10, 8))
        plt.contour(X, Y, data, levels=np.arange(data.min(), data.max(), interval), cmap="terrain")
        plt.colorbar(label="Altitude (m)")
        plt.xlabel("Longitude")
        plt.ylabel("Latitude")
        plt.title("Courbes de Niveau")
        plt.savefig(output_path)
        plt.close()
def generate_profile(mnt_path, line_coords, output_path):
    """
    Génère un profil topographique à partir d'un MNT et d'une ligne.
    
    Args:
        mnt_path (str): Chemin du fichier MNT.
        line_coords (list): Liste de coordonnées [(x1, y1), (x2, y2), ...].
        output_path (str): Chemin de sauvegarde de l'image du profil.
    """
    with rasterio.open(mnt_path) as mnt:
        # Convertir les coordonnées en indices de pixels
        row_col_coords = [mnt.index(x, y) for x, y in line_coords]

        # Extraire les valeurs d'altitude le long de la ligne
        altitudes = [mnt.read(1)[row, col] for row, col in row_col_coords]

        # Calculer la distance cumulée le long de la ligne
        distances = [0]
        for i in range(1, len(line_coords)):
            dx = line_coords[i][0] - line_coords[i-1][0]
            dy = line_coords[i][1] - line_coords[i-1][1]
            distances.append(distances[-1] + np.sqrt(dx**2 + dy**2))

        # Tracer le profil topographique
        plt.figure(figsize=(10, 6))
        plt.plot(distances, altitudes, label="Profil topographique")
        plt.fill_between(distances, altitudes, alpha=0.3, color="green")
        plt.xlabel("Distance (m)")
        plt.ylabel("Altitude (m)")
        plt.title("Profil Topographique")
        plt.legend()
        plt.grid(True)
        plt.savefig(output_path)
        plt.close()
def handle_contours_and_profiles():
    """
    Gère la génération des courbes de niveau et des profils topographiques.
    """
    st.subheader("Génération de courbes de niveau et profils topographiques")

    mnt_file = st.file_uploader("Téléverser le MNT (fichier TIFF)", type=["tif"])

    if mnt_file:
        # Sauvegarder temporairement le fichier MNT
        mnt_path = f"mnt_{uuid.uuid4()}.tif"
        with open(mnt_path, "wb") as f:
            f.write(mnt_file.read())

        # Section pour les courbes de niveau
        st.markdown("### Courbes de Niveau")
        interval = st.number_input("Intervalle entre les courbes de niveau (m)", value=10, step=1)
        if st.button("Générer les courbes de niveau"):
            try:
                output_path = f"contours_{uuid.uuid4()}.png"
                generate_contours(mnt_path, output_path, interval)
                st.image(output_path, caption="Courbes de niveau")
                os.remove(output_path)
            except Exception as e:
                st.error(f"Erreur lors de la génération des courbes de niveau : {e}")

        # Section pour les profils topographiques
        st.markdown("### Profil Topographique")
        st.info("Dessinez une ligne sur la carte pour générer un profil.")
        if "drawn_features" in st.session_state and st.session_state["drawn_features"]:
            drawn_line = st.session_state["drawn_features"][0]["geometry"]["coordinates"]
            if st.button("Générer le profil topographique"):
                try:
                    output_path = f"profile_{uuid.uuid4()}.png"
                    generate_profile(mnt_path, drawn_line, output_path)
                    st.image(output_path, caption="Profil topographique")
                    os.remove(output_path)
                except Exception as e:
                    st.error(f"Erreur lors de la génération du profil : {e}")

        os.remove(mnt_path)

# Ajouter la gestion des courbes de niveau et profils à l'application
handle_contours_and_profiles()
import ezdxf

def export_contours_to_dxf(mnt_path, output_path, interval=10):
    """
    Exporte les courbes de niveau à partir d'un MNT dans un fichier DXF.

    Args:
        mnt_path (str): Chemin du fichier MNT.
        output_path (str): Chemin de sauvegarde du fichier DXF.
        interval (int): Intervalle entre les courbes de niveau (en mètres).
    """
    with rasterio.open(mnt_path) as mnt:
        # Charger les données du MNT
        data = mnt.read(1)
        transform = mnt.transform

        # Masquer les valeurs invalides
        data = np.ma.masked_equal(data, mnt.nodata)

        # Créer les axes en fonction des dimensions du MNT
        x = np.arange(data.shape[1]) * transform[0] + transform[2]
        y = np.arange(data.shape[0]) * transform[4] + transform[5]
        X, Y = np.meshgrid(x, y)

        # Créer le document DXF
        doc = ezdxf.new()
        msp = doc.modelspace()

        # Ajouter des polylignes pour chaque courbe de niveau
        levels = np.arange(data.min(), data.max(), interval)
        for level in levels:
            contours = plt.contour(X, Y, data, levels=[level])
            for path in contours.collections[0].get_paths():
                vertices = path.vertices
                if len(vertices) > 1:
                    # Ajouter une polyligne pour chaque segment
                    polyline = msp.add_lwpolyline(vertices, close=False)
                    polyline.dxf.elevation = level  # Ajouter l'altitude de la courbe

        # Sauvegarder le fichier DXF
        doc.saveas(output_path)
def export_profile_to_dxf(line_coords, altitudes, output_path):
    """
    Exporte un profil topographique dans un fichier DXF.

    Args:
        line_coords (list): Liste des coordonnées [(x1, y1), (x2, y2), ...].
        altitudes (list): Liste des altitudes correspondantes.
        output_path (str): Chemin de sauvegarde du fichier DXF.
    """
    # Créer le document DXF
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Ajouter une polyligne 3D représentant le profil topographique
    profile_coords = [(x, y, z) for (x, y), z in zip(line_coords, altitudes)]
    msp.add_polyline3d(profile_coords)

    # Sauvegarder le fichier DXF
    doc.saveas(output_path)
def handle_dxf_export():
    """
    Gère l'exportation des données en DXF.
    """
    st.subheader("Exportation des données en format DXF")

    mnt_file = st.file_uploader("Téléverser le MNT (fichier TIFF)", type=["tif"])

    if mnt_file:
        # Sauvegarder temporairement le fichier MNT
        mnt_path = f"mnt_{uuid.uuid4()}.tif"
        with open(mnt_path, "wb") as f:
            f.write(mnt_file.read())

        # Exporter les courbes de niveau
        st.markdown("### Export des courbes de niveau")
        interval = st.number_input("Intervalle entre les courbes de niveau (m)", value=10, step=1)
        if st.button("Exporter les courbes de niveau en DXF"):
            try:
                output_path = f"contours_{uuid.uuid4()}.dxf"
                export_contours_to_dxf(mnt_path, output_path, interval)
                st.success("Exportation réussie !")
                with open(output_path, "rb") as f:
                    st.download_button("Télécharger le fichier DXF", f, file_name="contours.dxf")
                os.remove(output_path)
            except Exception as e:
                st.error(f"Erreur lors de l'exportation : {e}")

        # Exporter le profil topographique
        st.markdown("### Export du profil topographique")
        if "drawn_features" in st.session_state and st.session_state["drawn_features"]:
            drawn_line = st.session_state["drawn_features"][0]["geometry"]["coordinates"]
            try:
                with rasterio.open(mnt_path) as mnt:
                    # Convertir les coordonnées en indices de pixels
                    row_col_coords = [mnt.index(x, y) for x, y in drawn_line]

                    # Extraire les altitudes
                    altitudes = [mnt.read(1)[row, col] for row, col in row_col_coords]

                    # Exporter en DXF
                    output_path = f"profile_{uuid.uuid4()}.dxf"
                    export_profile_to_dxf(drawn_line, altitudes, output_path)
                    st.success("Exportation réussie !")
                    with open(output_path, "rb") as f:
                        st.download_button("Télécharger le fichier DXF", f, file_name="profile.dxf")
                    os.remove(output_path)
            except Exception as e:
                st.error(f"Erreur lors de l'exportation du profil : {e}")

        os.remove(mnt_path)

# Ajouter la gestion des exportations DXF à l'application
handle_dxf_export()

