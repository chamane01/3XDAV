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
import uuid  # Pour générer des identifiants uniques
from rasterio.mask import mask
from shapely.geometry import LineString as ShapelyLineString

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

# Fonction pour charger les fichiers TIFF depuis le dossier
def load_raster_files_from_folder(folder_path, map_object):
    """Charge tous les fichiers TIFF du dossier dans une couche 'elevation'."""
    if not os.path.exists(folder_path):
        st.warning(f"Le dossier {folder_path} n'existe pas.")
        return None

    global_bounds = None
    for filename in os.listdir(folder_path):
        if filename.endswith(".tif") or filename.endswith(".tiff"):
            tiff_path = os.path.join(folder_path, filename)
            try:
                with rasterio.open(tiff_path) as src:
                    bounds = src.bounds
                    image = reshape_as_image(src.read())
                    folium.raster_layers.ImageOverlay(
                        image=image,
                        bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
                        name="elevation",
                        opacity=0.6,
                    ).add_to(map_object)
                    st.success(f"Fichier {filename} chargé dans la couche 'elevation'.")

                    # Calcul des limites globales
                    if global_bounds is None:
                        global_bounds = bounds
                    else:
                        global_bounds = (
                            min(global_bounds.left, bounds.left),
                            min(global_bounds.bottom, bounds.bottom),
                            max(global_bounds.right, bounds.right),
                            max(global_bounds.top, bounds.top),
                        )
            except Exception as e:
                st.error(f"Erreur lors du chargement du fichier {filename}: {e}")

    return global_bounds

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

# Fonction pour appliquer un gradient de couleur à un MNT/MNS
def apply_color_gradient(tiff_path, output_path):
    """Apply a color gradient to the DEM TIFF and save it as a PNG."""
    with rasterio.open(tiff_path) as src:
        # Read the DEM data
        dem_data = src.read(1)
        
        # Create a color map using matplotlib
        cmap = plt.get_cmap("terrain")
        norm = plt.Normalize(vmin=dem_data.min(), vmax=dem_data.max())
        
        # Apply the colormap
        colored_image = cmap(norm(dem_data))
        
        # Save the colored image as PNG
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

# Fonction pour calculer les limites d'un GeoJSON
def calculate_geojson_bounds(geojson_data):
    """Calculate bounds from a GeoJSON object."""
    geometries = [feature["geometry"] for feature in geojson_data["features"]]
    gdf = gpd.GeoDataFrame.from_features(geojson_data)
    return gdf.total_bounds  # Returns [minx, miny, maxx, maxy]

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
        return data, bounds, transform
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier TIFF : {e}")
        return None, None, None

# Fonction de validation de projection et d'emprise
def validate_projection_and_extent(raster_path, polygons_gdf, target_crs):
    """Vérifie la projection et l'emprise des polygones par rapport au raster."""
    with rasterio.open(raster_path) as src:
        # Vérification CRS
        if src.crs != target_crs:
            raise ValueError(f"Le raster {raster_path} n'est pas dans la projection {target_crs}")

        # Conversion des polygones vers le CRS du raster
        polygons_gdf = polygons_gdf.to_crs(src.crs)
        
        # Vérification de l'emprise
        raster_bounds = src.bounds
        for idx, row in polygons_gdf.iterrows():
            if not row.geometry.intersects(Polygon.from_bounds(*raster_bounds)):
                st.warning(f"Le polygone {idx} est en dehors de l'emprise du raster")

    return polygons_gdf

# Fonction pour calculer le volume et la surface pour chaque polygone (MNS - MNT)
def calculate_volume_and_area_for_each_polygon(mns_path, mnt_path, polygons_gdf):
    """Calcule le volume pour chaque polygone avec découpage précis."""
    volumes = []
    areas = []
    
    # Reprojection des polygones en UTM
    with rasterio.open(mns_path) as src:
        polygons_gdf = polygons_gdf.to_crs(src.crs)
    
    for idx, polygon in polygons_gdf.iterrows():
        try:
            # Découpage du MNS
            with rasterio.open(mns_path) as src:
                mns_clipped, mns_transform = mask(src, [polygon.geometry], crop=True, nodata=np.nan)
                mns_data = mns_clipped[0]
                cell_area = abs(mns_transform.a * mns_transform.e)  # Surface par cellule

            # Découpage du MNT
            with rasterio.open(mnt_path) as src:
                mnt_clipped, _ = mask(src, [polygon.geometry], crop=True, nodata=np.nan)
                mnt_data = mnt_clipped[0]

            # Calcul différentiel
            valid_mask = (~np.isnan(mns_data)) & (~np.isnan(mnt_data))
            diff = np.where(valid_mask, mns_data - mnt_data, 0)
            
            # Calculs finaux
            volume = np.sum(diff) * cell_area
            area = np.count_nonzero(valid_mask) * cell_area
            
            volumes.append(volume)
            areas.append(area)
            
            # Récupérer le nom de la polygonale
            polygon_name = polygon.get("properties", {}).get("name", f"Polygone {idx + 1}")
            st.write(f"{polygon_name} - Volume: {volume:.2f} m³, Surface: {area:.2f} m²")

        except Exception as e:
            st.error(f"Erreur sur le polygone {idx + 1}: {str(e)}")
    
    return volumes, areas

# Fonction pour extraire les points sur les bords d'une polygonale
def extract_boundary_points(polygon):
    """Extrait les points situés sur les bords d'une polygonale."""
    boundary = polygon.boundary
    if isinstance(boundary, ShapelyLineString):
        return list(boundary.coords)
    else:
        # Si la polygonale a des trous, on prend uniquement le contour extérieur
        return list(polygon.exterior.coords)

# Fonction pour calculer la cote moyenne des élévations sur les bords de la polygonale
def calculate_average_elevation_on_boundary(mns_path, polygon):
    """Calcule la cote moyenne des élévations sur les bords de la polygonale."""
    with rasterio.open(mns_path) as src:
        # Extraire les points sur les bords de la polygonale
        boundary_points = extract_boundary_points(polygon)
        
        # Convertir les points en coordonnées raster
        boundary_coords = [src.index(x, y) for (x, y) in boundary_points]
        
        # Extraire les élévations sur les bords
        elevations = [src.read(1)[int(row), int(col)] for (row, col) in boundary_coords]
        
        # Calculer la cote moyenne
        average_elevation = np.mean(elevations)
    return average_elevation

# Fonction pour calculer le volume et la surface pour chaque polygone (MNS seul)
def calculate_volume_and_area_with_mns_only(mns_path, polygons_gdf, use_average_elevation=True, reference_altitude=None):
    """Calcule le volume et la surface pour chaque polygone en utilisant uniquement le MNS."""
    volumes = []
    areas = []
    
    # Reprojection des polygones en UTM
    with rasterio.open(mns_path) as src:
        polygons_gdf = polygons_gdf.to_crs(src.crs)
    
    for idx, polygon in polygons_gdf.iterrows():
        try:
            # Découpage du MNS
            with rasterio.open(mns_path) as src:
                mns_clipped, mns_transform = mask(src, [polygon.geometry], crop=True, nodata=np.nan)
                mns_data = mns_clipped[0]
                cell_area = abs(mns_transform.a * mns_transform.e)  # Surface par cellule

            # Calcul de la cote de référence
            if use_average_elevation:
                reference_altitude = calculate_average_elevation_on_boundary(mns_path, polygon.geometry)
            elif reference_altitude is None:
                st.error("Veuillez fournir une altitude de référence.")
                return [], []

            # Calcul différentiel par rapport à la cote de référence
            valid_mask = ~np.isnan(mns_data)
            diff = np.where(valid_mask, mns_data - reference_altitude, 0)
            
            # Calculs finaux
            volume = np.sum(diff) * cell_area
            area = np.count_nonzero(valid_mask) * cell_area
            
            volumes.append(volume)
            areas.append(area)
            
            # Récupérer le nom de la polygonale
            polygon_name = polygon.get("properties", {}).get("name", f"Polygone {idx + 1}")
            st.write(f"{polygon_name} - Volume: {volume:.2f} m³, Surface: {area:.2f} m², Cote de référence: {reference_altitude:.2f} m")

        except Exception as e:
            st.error(f"Erreur sur le polygone {idx + 1}: {str(e)}")
    
    return volumes, areas

# Fonction pour calculer le volume global
def calculate_global_volume(volumes):
    """Calcule le volume global en additionnant les volumes individuels."""
    return sum(volumes)

# Fonction pour calculer la surface globale
def calculate_global_area(areas):
    """Calcule la surface globale en additionnant les surfaces individuelles."""
    return sum(areas)

# Fonction pour rechercher des polygones dans les couches téléversées
def find_polygons_in_layers(layers):
    """Recherche des polygones dans les couches téléversées."""
    polygons = []
    for layer in layers:
        if layer["type"] == "GeoJSON":
            geojson_data = layer["data"]
            for feature in geojson_data["features"]:
                if feature["geometry"]["type"] == "Polygon":
                    polygons.append(feature)
    return polygons

# Fonction pour rechercher des polygones dans les couches créées par l'utilisateur
def find_polygons_in_user_layers(layers):
    """Recherche des polygones dans les couches créées par l'utilisateur."""
    polygons = []
    for layer_name, features in layers.items():
        for feature in features:
            if feature["geometry"]["type"] == "Polygon":
                polygons.append(feature)
    return polygons

# Fonction pour convertir les polygones en GeoDataFrame
def convert_polygons_to_gdf(polygons):
    """Convertit une liste de polygones en GeoDataFrame."""
    geometries = [shape(polygon["geometry"]) for polygon in polygons]
    properties = [polygon.get("properties", {}) for polygon in polygons]
    gdf = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326")
    gdf["properties"] = properties
    return gdf

# Fonction pour convertir les entités dessinées en GeoDataFrame
def convert_drawn_features_to_gdf(features):
    """Convertit les entités dessinées en GeoDataFrame."""
    geometries = []
    properties = []
    for feature in features:
        geom = shape(feature["geometry"])
        geometries.append(geom)
        properties.append(feature.get("properties", {}))
    gdf = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326")
    gdf["properties"] = properties
    return gdf

# Initialisation des couches et des entités dans la session Streamlit
if "layers" not in st.session_state:
    st.session_state["layers"] = {}  # Couches créées par l'utilisateur

if "uploaded_layers" not in st.session_state:
    st.session_state["uploaded_layers"] = []  # Couches téléversées (TIFF et GeoJSON)

if "new_features" not in st.session_state:
    st.session_state["new_features"] = []  # Entités temporairement dessinées

# Titre de l'application
st.title("Carte Topographique et Analyse Spatiale")

# Description
st.markdown("""
Créez des entités géographiques (points, lignes, polygones) en les dessinant sur la carte et ajoutez-les à des couches spécifiques. 
Vous pouvez également téléverser des fichiers TIFF ou GeoJSON pour les superposer à la carte.
""")

# Initialisation de la carte
m = folium.Map(location=[7.5399, -5.5471], zoom_start=6)  # Centré sur la Côte d'Ivoire avec un zoom adapté

# Charger les fichiers TIFF du dossier 'raster-files' dans la couche 'elevation'
global_bounds = load_raster_files_from_folder("raster_files", m)

# Ajuster la vue de la carte pour inclure tous les fichiers TIFF
if global_bounds:
    m.fit_bounds([[global_bounds.bottom, global_bounds.left], [global_bounds.top, global_bounds.right]])

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

# Ajout des couches créées à la carte
for layer, features in st.session_state["layers"].items():
    layer_group = folium.FeatureGroup(name=layer, show=True)
    for feature in features:
        feature_type = feature["geometry"]["type"]
        coordinates = feature["geometry"]["coordinates"]
        popup = feature.get("properties", {}).get("name", f"{layer} - Entité")

        if feature_type == "Point":
            lat, lon = coordinates[1], coordinates[0]
            folium.Marker(location=[lat, lon], popup=popup).add_to(layer_group)
        elif feature_type == "LineString":
            folium.PolyLine(locations=[(lat, lon) for lon, lat in coordinates], color="blue", popup=popup).add_to(layer_group)
        elif feature_type == "Polygon":
            folium.Polygon(locations=[(lat, lon) for lon, lat in coordinates[0]], color="green", fill=True, popup=popup).add_to(layer_group)
    layer_group.add_to(m)

# Ajout des couches téléversées à la carte
for layer in st.session_state["uploaded_layers"]:
    if layer["type"] == "TIFF":
        if layer["name"] in ["MNT", "MNS"]:
            # Générer un nom de fichier unique pour l'image colorée
            unique_id = str(uuid.uuid4())[:8]
            temp_png_path = f"{layer['name'].lower()}_colored_{unique_id}.png"
            apply_color_gradient(layer["path"], temp_png_path)
            add_image_overlay(m, temp_png_path, layer["bounds"], layer["name"])
            os.remove(temp_png_path)  # Supprimer le fichier PNG temporaire
        else:
            add_image_overlay(m, layer["path"], layer["bounds"], layer["name"])
        
        # Ajuster la vue de la carte pour inclure l'image TIFF
        bounds = [[layer["bounds"].bottom, layer["bounds"].left], [layer["bounds"].top, layer["bounds"].right]]
        m.fit_bounds(bounds)
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

# Gestion des nouveaux dessins
if output and "last_active_drawing" in output and output["last_active_drawing"]:
    new_feature = output["last_active_drawing"]
    if new_feature not in st.session_state["new_features"]:
        st.session_state["new_features"].append(new_feature)
        st.info("Nouvelle entité ajoutée temporairement. Cliquez sur 'Enregistrer les entités' pour les ajouter à la couche.")

# Initialisation de l'état de session pour le bouton actif
if 'active_button' not in st.session_state:
    st.session_state['active_button'] = None

# Fonction pour afficher les paramètres en fonction du bouton cliqué
def display_parameters(button_name):
    if button_name == "Surfaces et volumes":
        st.markdown("### Calcul des volumes et des surfaces")
        method = st.radio(
            "Choisissez la méthode de calcul :",
            ("Méthode 1 : MNS - MNT", "Méthode 2 : MNS seul"),
            key="volume_method"
        )

        # Récupérer les couches nécessaires
        mns_layer = next((layer for layer in st.session_state["uploaded_layers"] if layer["name"] == "MNS"), None)
        mnt_layer = next((layer for layer in st.session_state["uploaded_layers"] if layer["name"] == "MNT"), None)

        if not mns_layer:
            st.error("La couche MNS est manquante. Veuillez téléverser un fichier MNS.")
            return
        if method == "Méthode 1 : MNS - MNT" and not mnt_layer:
            st.error("La couche MNT est manquante. Veuillez téléverser un fichier MNT.")
            return

        # Reprojection des fichiers en UTM
        try:
            mns_utm_path = reproject_tiff(mns_layer["path"], "EPSG:32630")
            if method == "Méthode 1 : MNS - MNT":
                mnt_utm_path = reproject_tiff(mnt_layer["path"], "EPSG:32630")
        except Exception as e:
            st.error(f"Échec de la reprojection : {e}")
            return

        # Récupération des polygones
        polygons_uploaded = find_polygons_in_layers(st.session_state["uploaded_layers"])
        polygons_user_layers = find_polygons_in_user_layers(st.session_state["layers"])
        polygons_drawn = st.session_state["new_features"]
        all_polygons = polygons_uploaded + polygons_user_layers + polygons_drawn

        if not all_polygons:
            st.error("Aucune polygonale disponible.")
            return

        # Conversion en GeoDataFrame
        polygons_gdf = convert_polygons_to_gdf(all_polygons)

        try:
            # Validation des données
            polygons_gdf_utm = validate_projection_and_extent(mns_utm_path, polygons_gdf, "EPSG:32630")
            
            if method == "Méthode 1 : MNS - MNT":
                # Calcul avec MNS et MNT
                volumes, areas = calculate_volume_and_area_for_each_polygon(
                    mns_utm_path, 
                    mnt_utm_path,
                    polygons_gdf_utm
                )
            else:
                # Choix de la méthode de calcul pour MNS seul
                use_average_elevation = st.checkbox(
                    "Utiliser la cote moyenne des élévations sur les bords de la polygonale comme référence",
                    value=True,
                    key="use_average_elevation"
                )
                reference_altitude = None
                if not use_average_elevation:
                    reference_altitude = st.number_input(
                        "Entrez l'altitude de référence (en mètres) :",
                        value=0.0,
                        step=0.1,
                        key="reference_altitude"
                    )
                
                # Calcul avec MNS seul
                volumes, areas = calculate_volume_and_area_with_mns_only(
                    mns_utm_path,
                    polygons_gdf_utm,
                    use_average_elevation=use_average_elevation,
                    reference_altitude=reference_altitude
                )
            
            # Calcul des volumes et surfaces globaux
            global_volume = calculate_global_volume(volumes)
            global_area = calculate_global_area(areas)
            st.write(f"Volume global : {global_volume:.2f} m³")
            st.write(f"Surface globale : {global_area:.2f} m²")
            
            # Nettoyage des fichiers temporaires
            os.remove(mns_utm_path)
            if method == "Méthode 1 : MNS - MNT":
                os.remove(mnt_utm_path)

        except Exception as e:
            st.error(f"Erreur lors du calcul : {e}")
            # Nettoyage en cas d'erreur
            if os.path.exists(mns_utm_path):
                os.remove(mns_utm_path)
            if method == "Méthode 1 : MNS - MNT" and os.path.exists(mnt_utm_path):
                os.remove(mnt_utm_path)

# Ajout des boutons pour les analyses spatiales
st.markdown("### Analyse Spatiale")
col1, col2, col3 = st.columns(3)

# Boutons principaux
with col1:
    if st.button("Surfaces et volumes", key="surfaces_volumes"):
        st.session_state['active_button'] = "Surfaces et volumes"
    if st.button("Carte de contours", key="contours"):
        st.session_state['active_button'] = "Carte de contours"

with col2:
    if st.button("Trouver un point", key="trouver_point"):
        st.session_state['active_button'] = "Trouver un point"
    if st.button("Générer un rapport", key="generer_rapport"):
        st.session_state['active_button'] = "Générer un rapport"

with col3:
    if st.button("Télécharger la carte", key="telecharger_carte"):
        st.session_state['active_button'] = "Télécharger la carte"
    if st.button("Dessin automatique", key="dessin_auto"):
        st.session_state['active_button'] = "Dessin automatique"

# Création d'un espace réservé pour les paramètres
parameters_placeholder = st.empty()

# Affichage des paramètres en fonction du bouton actif
if st.session_state['active_button']:
    with parameters_placeholder.container():
        display_parameters(st.session_state['active_button'])
