import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, MeasureControl
from folium import LayerControl
import rasterio
from rasterio.plot import reshape_as_image
import numpy as np
import matplotlib.pyplot as plt
import os
import uuid
from rasterio.mask import mask
from shapely.geometry import shape
import geopandas as gpd
from shapely.geometry import LineString
from skimage import measure

# Fonction pour reprojeter un fichier TIFF avec un nom unique
def reproject_tiff(input_tiff, target_crs):
    """Reproject a TIFF file to a target CRS."""
    with rasterio.open(input_tiff) as src:
        transform, width, height = rasterio.warp.calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds
        )
        kwargs = src.meta.copy()
        kwargs.update({
            "crs": target_crs,
            "transform": transform,
            "width": width,
            "height": height,
        })

        # Générer un nom de fichier unique
        unique_id = str(uuid.uuid4())[:8]  # Utilisation des 8 premiers caractères d'un UUID
        reprojected_tiff = f"reprojected_{unique_id}.tiff"
        with rasterio.open(reprojected_tiff, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                rasterio.warp.reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=rasterio.warp.Resampling.nearest,
                )
    return reprojected_tiff

# Fonction pour générer les contours à partir d'un fichier TIFF
def generate_contours(tiff_path, interval=10):
    """Generate contours from a TIFF file."""
    with rasterio.open(tiff_path) as src:
        data = src.read(1)
        transform = src.transform

        # Générer les contours
        contours = measure.find_contours(data, level=interval)

        # Convertir les contours en polylignes
        contour_lines = []
        for contour in contours:
            coords = []
            for row, col in contour:
                x, y = rasterio.transform.xy(transform, row, col)
                coords.append((y, x))  # Folium utilise (lat, lon)
            contour_lines.append(LineString(coords))

        return contour_lines

# Initialisation des couches dans la session Streamlit
if "uploaded_layers" not in st.session_state:
    st.session_state["uploaded_layers"] = []  # Couches téléversées (TIFF et GeoJSON)

# Titre de l'application
st.title("Carte de Contours")

# Description
st.markdown("""
Générez des courbes de niveau à partir d'un fichier TIFF (MNT ou MNS) et affichez-les sur la carte.
""")

# Sidebar pour la gestion des couches
with st.sidebar:
    st.header("Gestion des Couches")

    # Section 1: Téléversement de fichiers
    st.markdown("### Téléverser un fichier TIFF")
    uploaded_tiff = st.file_uploader("Téléverser un fichier TIFF (MNT ou MNS)", type=["tif", "tiff"])

    if uploaded_tiff:
        # Générer un nom de fichier unique pour le fichier téléversé
        unique_id = str(uuid.uuid4())[:8]
        tiff_path = f"uploaded_{unique_id}.tiff"
        with open(tiff_path, "wb") as f:
            f.write(uploaded_tiff.read())

        st.write(f"Reprojection du fichier TIFF...")
        try:
            reprojected_tiff = reproject_tiff(tiff_path, "EPSG:4326")
            with rasterio.open(reprojected_tiff) as src:
                bounds = src.bounds
                # Vérifier si la couche existe déjà
                if not any(layer["name"] == "MNT/MNS" and layer["type"] == "TIFF" for layer in st.session_state["uploaded_layers"]):
                    st.session_state["uploaded_layers"].append({"type": "TIFF", "name": "MNT/MNS", "path": reprojected_tiff, "bounds": bounds})
                    st.success(f"Couche MNT/MNS ajoutée à la liste des couches.")
                else:
                    st.warning(f"La couche MNT/MNS existe déjà.")
        except Exception as e:
            st.error(f"Erreur lors de la reprojection : {e}")
        finally:
            # Supprimer le fichier temporaire après utilisation
            os.remove(tiff_path)

    # Liste des couches téléversées
    st.markdown("### Liste des couches téléversées")
    if st.session_state["uploaded_layers"]:
        for i, layer in enumerate(st.session_state["uploaded_layers"]):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{i + 1}. {layer['name']} ({layer['type']})")
            with col2:
                if st.button("🗑️", key=f"delete_{i}_{layer['name']}", help="Supprimer cette couche", type="secondary"):
                    st.session_state["uploaded_layers"].pop(i)
                    st.success(f"Couche {layer['name']} supprimée.")
    else:
        st.write("Aucune couche téléversée pour le moment.")

# Carte de base
m = folium.Map(location=[7.5399, -5.5471], zoom_start=6)  # Centré sur la Côte d'Ivoire avec un zoom adapté

# Ajout des fonds de carte
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Satellite",
).add_to(m)

folium.TileLayer(
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="OpenTopoMap",
    name="Topographique",
).add_to(m)  # Carte topographique ajoutée en dernier pour être la carte par défaut

# Ajout des couches téléversées à la carte
for layer in st.session_state["uploaded_layers"]:
    if layer["type"] == "TIFF":
        bounds = [[layer["bounds"].bottom, layer["bounds"].left], [layer["bounds"].top, layer["bounds"].right]]
        m.fit_bounds(bounds)

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

# Ajout du contrôle des couches pour basculer entre les fonds de carte
LayerControl(position="topleft", collapsed=True).add_to(m)

# Affichage interactif de la carte
output = st_folium(m, width=800, height=600, returned_objects=["last_active_drawing", "all_drawings"])

# Bouton pour générer les contours
if st.button("Générer la carte de contours"):
    tiff_layer = next((layer for layer in st.session_state["uploaded_layers"] if layer["name"] == "MNT/MNS"), None)
    if tiff_layer:
        contours = generate_contours(tiff_layer["path"], interval=10)
        contour_group = folium.FeatureGroup(name="Contours", show=True)
        for contour in contours:
            folium.PolyLine(
                locations=[(lat, lon) for lon, lat in contour.coords],
                color="blue",
                weight=1,
                opacity=0.7
            ).add_to(contour_group)
        contour_group.add_to(m)
        st.success("Les contours ont été générés et ajoutés à la carte.")
    else:
        st.error("Aucun fichier TIFF (MNT/MNS) n'a été téléversé.")
