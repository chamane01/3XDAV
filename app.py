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

# Fonction pour calculer la surface d'un polygone
def calculate_area(polygon):
    """Calcule la surface d'un polygone en mètres carrés."""
    geom = shape(polygon)
    return geom.area

# Fonction pour calculer le volume sans MNT
def calculate_volume_without_mnt(mns, mns_bounds, polygons_gdf, reference_altitude, resolution_x, resolution_y):
    """
    Calcule le volume sans utiliser de MNT en utilisant une altitude de référence.
    
    :param mns: Données MNS (Modèle Numérique de Surface)
    :param mns_bounds: Bornes géographiques du MNS
    :param polygons_gdf: GeoDataFrame contenant les polygones
    :param reference_altitude: Altitude de référence pour le calcul du volume
    :param resolution_x: Résolution spatiale en X (mètres par pixel)
    :param resolution_y: Résolution spatiale en Y (mètres par pixel)
    :return: Volume positif, volume négatif, volume réel, surface
    """
    positive_volume = 0.0
    negative_volume = 0.0
    total_area = 0.0  # Surface totale des polygones
    
    for idx, polygon in polygons_gdf.iterrows():
        try:
            # Masquer les données en dehors du polygone courant
            mask = polygon.geometry
            mns_masked = np.where(mask, mns, np.nan)
            
            # Calculer la différence entre le MNS et l'altitude de référence
            diff = mns_masked - reference_altitude
            
            # Calculer les volumes positif et négatif
            positive_volume += np.nansum(np.where(diff > 0, diff, 0)) * resolution_x * resolution_y
            negative_volume += np.nansum(np.where(diff < 0, diff, 0)) * resolution_x * resolution_y
            
            # Calculer la surface du polygone
            total_area += calculate_area(polygon.geometry)
        except Exception as e:
            st.error(f"Erreur lors du calcul du volume pour le polygone {idx + 1} : {e}")
    
    # Calculer le volume réel (différence entre positif et négatif)
    real_volume = positive_volume + negative_volume
    
    return positive_volume, negative_volume, real_volume, total_area

# Fonction pour charger un fichier TIFF
def load_tiff(tiff_path):
    """Charge un fichier TIFF et retourne les données, les bornes et la résolution spatiale."""
    try:
        with rasterio.open(tiff_path) as src:
            data = src.read(1)
            bounds = src.bounds
            transform = src.transform
            if transform.is_identity:
                st.warning("La transformation est invalide. Génération d'une transformation par défaut.")
                transform, width, height = calculate_default_transform(src.crs, src.crs, src.width, src.height, *src.bounds)
            
            # Extraire la résolution spatiale
            resolution_x = transform.a  # Résolution en X (largeur)
            resolution_y = -transform.e  # Résolution en Y (hauteur, valeur absolue)
            
            st.write(f"Transform: {transform}")
            st.write(f"Résolution spatiale: {resolution_x} m (largeur) x {resolution_y} m (hauteur)")
        return data, bounds, resolution_x, resolution_y
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier TIFF : {e}")
        return None, None, None, None

# Titre de l'application
st.title("Carte Topographique et Analyse Spatiale")

# Description
st.markdown("""
Créez des entités géographiques (points, lignes, polygones) en les dessinant sur la carte et ajoutez-les à des couches spécifiques. 
Vous pouvez également téléverser des fichiers TIFF ou GeoJSON pour les superposer à la carte.
""")

# Sidebar pour la gestion des couches
with st.sidebar:
    st.header("Gestion des Couches")

    # Section 1: Ajout d'une nouvelle couche
    st.markdown("### 1- Ajouter une nouvelle couche")
    new_layer_name = st.text_input("Nom de la nouvelle couche à ajouter", "")
    if st.button("Ajouter la couche", key="add_layer_button", help="Ajouter une nouvelle couche", type="primary") and new_layer_name:
        if new_layer_name not in st.session_state["layers"]:
            st.session_state["layers"][new_layer_name] = []
            st.success(f"La couche '{new_layer_name}' a été ajoutée.")
        else:
            st.warning(f"La couche '{new_layer_name}' existe déjà.")

    # Sélection de la couche active pour ajouter les nouvelles entités
    st.markdown("#### Sélectionner une couche active")
    if st.session_state["layers"]:
        layer_name = st.selectbox(
            "Choisissez la couche à laquelle ajouter les entités",
            list(st.session_state["layers"].keys())
        )
    else:
        st.write("Aucune couche disponible. Ajoutez une couche pour commencer.")

    # Affichage des entités temporairement dessinées
    if st.session_state["new_features"]:
        st.write(f"**Entités dessinées temporairement ({len(st.session_state['new_features'])}) :**")
        for idx, feature in enumerate(st.session_state["new_features"]):
            st.write(f"- Entité {idx + 1}: {feature['geometry']['type']}")

    # Bouton pour enregistrer les nouvelles entités dans la couche active
    if st.button("Enregistrer les entités", key="save_features_button", type="primary") and st.session_state["layers"]:
        # Ajouter les entités non dupliquées à la couche sélectionnée
        current_layer = st.session_state["layers"][layer_name]
        for feature in st.session_state["new_features"]:
            if feature not in current_layer:
                current_layer.append(feature)
        st.session_state["new_features"] = []  # Réinitialisation des entités temporaires
        st.success(f"Toutes les nouvelles entités ont été enregistrées dans la couche '{layer_name}'.")

    # Gestion des entités dans les couches
    st.markdown("#### Gestion des entités dans les couches")
    if st.session_state["layers"]:
        selected_layer = st.selectbox("Choisissez une couche pour voir ses entités", list(st.session_state["layers"].keys()))
        if st.session_state["layers"][selected_layer]:
            entity_idx = st.selectbox(
                "Sélectionnez une entité à gérer",
                range(len(st.session_state["layers"][selected_layer])),
                format_func=lambda idx: f"Entité {idx + 1}: {st.session_state['layers'][selected_layer][idx]['geometry']['type']}"
            )
            selected_entity = st.session_state["layers"][selected_layer][entity_idx]
            current_name = selected_entity.get("properties", {}).get("name", "")
            new_name = st.text_input("Nom de l'entité", current_name)

            if st.button("Modifier le nom", key=f"edit_{entity_idx}", type="primary"):
                if "properties" not in selected_entity:
                    selected_entity["properties"] = {}
                selected_entity["properties"]["name"] = new_name
                st.success(f"Le nom de l'entité a été mis à jour en '{new_name}'.")

            if st.button("Supprimer l'entité sélectionnée", key=f"delete_{entity_idx}", type="secondary"):
                st.session_state["layers"][selected_layer].pop(entity_idx)
                st.success(f"L'entité sélectionnée a été supprimée de la couche '{selected_layer}'.")
        else:
            st.write("Aucune entité dans cette couche pour le moment.")
    else:
        st.write("Aucune couche disponible pour gérer les entités.")

    # Démarcation claire entre 1- et 2-
    st.markdown("---")

    # Section 2: Téléversement de fichiers
    st.markdown("### 2- Téléverser des fichiers")
    tiff_type = st.selectbox(
        "Sélectionnez le type de fichier TIFF",
        options=["MNT", "MNS", "Orthophoto"],
        index=None,
        placeholder="Veuillez sélectionner",
        key="tiff_selectbox"
    )

    if tiff_type:
        uploaded_tiff = st.file_uploader(f"Téléverser un fichier TIFF ({tiff_type})", type=["tif", "tiff"], key="tiff_uploader")

        if uploaded_tiff:
            # Générer un nom de fichier unique pour le fichier téléversé
            unique_id = str(uuid.uuid4())[:8]
            tiff_path = f"uploaded_{unique_id}.tiff"
            with open(tiff_path, "wb") as f:
                f.write(uploaded_tiff.read())

            st.write(f"Reprojection du fichier TIFF ({tiff_type})...")
            try:
                reprojected_tiff = reproject_tiff(tiff_path, "EPSG:4326")
                with rasterio.open(reprojected_tiff) as src:
                    bounds = src.bounds
                    # Vérifier si la couche existe déjà
                    if not any(layer["name"] == tiff_type and layer["type"] == "TIFF" for layer in st.session_state["uploaded_layers"]):
                        st.session_state["uploaded_layers"].append({"type": "TIFF", "name": tiff_type, "path": reprojected_tiff, "bounds": bounds})
                        st.success(f"Couche {tiff_type} ajoutée à la liste des couches.")
                    else:
                        st.warning(f"La couche {tiff_type} existe déjà.")
            except Exception as e:
                st.error(f"Erreur lors de la reprojection : {e}")
            finally:
                # Supprimer le fichier temporaire après utilisation
                os.remove(tiff_path)

    geojson_type = st.selectbox(
        "Sélectionnez le type de fichier GeoJSON",
        options=[
            "Polygonale", "Routes", "Cours d'eau", "Bâtiments", "Pistes", "Plantations",
            "Électricité", "Assainissements", "Villages", "Villes", "Chemin de fer", "Parc et réserves"
        ],
        index=None,
        placeholder="Veuillez sélectionner",
        key="geojson_selectbox"
    )

    if geojson_type:
        uploaded_geojson = st.file_uploader(f"Téléverser un fichier GeoJSON ({geojson_type})", type=["geojson"], key="geojson_uploader")

        if uploaded_geojson:
            try:
                geojson_data = json.load(uploaded_geojson)
                # Vérifier si la couche existe déjà
                if not any(layer["name"] == geojson_type and layer["type"] == "GeoJSON" for layer in st.session_state["uploaded_layers"]):
                    st.session_state["uploaded_layers"].append({"type": "GeoJSON", "name": geojson_type, "data": geojson_data})
                    st.success(f"Couche {geojson_type} ajoutée à la liste des couches.")
                else:
                    st.warning(f"La couche {geojson_type} existe déjà.")
            except Exception as e:
                st.error(f"Erreur lors du chargement du GeoJSON : {e}")

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
        st.markdown("### Calcul des volumes")
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

        # Charger les données
        mns, mns_bounds, resolution_x, resolution_y = load_tiff(mns_layer["path"])
        if method == "Méthode 1 : MNS - MNT":
            mnt, mnt_bounds, _, _ = load_tiff(mnt_layer["path"])

        # Récupérer les polygones des couches téléversées, des couches créées par l'utilisateur et des dessins
        polygons_uploaded = find_polygons_in_layers(st.session_state["uploaded_layers"])
        polygons_user_layers = find_polygons_in_user_layers(st.session_state["layers"])
        polygons_drawn = st.session_state["new_features"]

        # Combiner tous les polygones
        all_polygons = polygons_uploaded + polygons_user_layers + polygons_drawn

        if not all_polygons:
            st.error("Aucune polygonale disponible. Veuillez dessiner ou téléverser une polygonale.")
            return

        # Convertir les polygones en GeoDataFrame
        polygons_gdf = convert_polygons_to_gdf(all_polygons)

        if mns is None or polygons_gdf is None:
            st.error("Erreur lors du chargement des fichiers.")
            return

        try:
            if method == "Méthode 1 : MNS - MNT":
                if mnt is None or mnt_bounds != mns_bounds:
                    st.error("Les fichiers doivent avoir les mêmes bornes géographiques.")
                else:
                    # Calculer le volume pour chaque polygone
                    volumes = calculate_volume_for_each_polygon(mns, mnt, mnt_bounds, polygons_gdf)
                    
                    # Calculer le volume global
                    global_volume = calculate_global_volume(volumes)
                    st.write(f"Volume global : {global_volume:.2f} m³")
            else:
                # Saisie de l'altitude de référence pour la méthode 2
                reference_altitude = st.number_input(
                    "Entrez l'altitude de référence (en mètres) :",
                    value=0.0,
                    step=0.1,
                    key="reference_altitude"
                )
                positive_volume, negative_volume, real_volume, total_area = calculate_volume_without_mnt(
                    mns, mns_bounds, polygons_gdf, reference_altitude, resolution_x, resolution_y
                )
                st.write(f"Volume positif (au-dessus de la référence) : {positive_volume:.2f} m³")
                st.write(f"Volume négatif (en dessous de la référence) : {negative_volume:.2f} m³")
                st.write(f"Volume réel (différence) : {real_volume:.2f} m³")
                st.write(f"Surface totale des polygones : {total_area:.2f} m²")

        except Exception as e:
            st.error(f"Erreur lors du calcul du volume : {e}")

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
