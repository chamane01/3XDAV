import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, MeasureControl
from folium import LayerControl
import rasterio
from rasterio.plot import reshape_as_image
from rasterio.merge import merge
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import LineString
import geopandas as gpd
import os
import uuid

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

# Fonction pour charger les rasters en mémoire
def load_rasters(raster_files):
    """Charge plusieurs rasters et les fusionne en mémoire."""
    src_files_to_mosaic = []
    for file in raster_files:
        src = rasterio.open(file)
        src_files_to_mosaic.append(src)
    mosaic, out_transform = merge(src_files_to_mosaic)
    return mosaic, out_transform, src_files_to_mosaic[0].meta

# Fonction pour tracer un profil en long
def plot_profile(elevation, x1, y1, x2, y2):
    """Trace un profil en long à partir des données d'élévation."""
    num_points = 100
    x_values = np.linspace(x1, x2, num_points)
    y_values = np.linspace(y1, y2, num_points)
    profile = [elevation[int(y), int(x)] for x, y in zip(x_values, y_values)]
    plt.plot(profile)
    plt.xlabel("Distance")
    plt.ylabel("Élévation")
    plt.title("Profil en long")
    st.pyplot(plt.gcf())

# Fonction pour générer une carte d'inondation
def generate_flood_map(elevation, flood_threshold):
    """Génère une carte d'inondation à partir des données d'élévation."""
    flood_map = elevation < flood_threshold
    plt.imshow(flood_map, cmap="Blues")
    plt.colorbar(label="Inondation (1 = inondé, 0 = sec)")
    plt.title("Carte d'inondation")
    st.pyplot(plt.gcf())

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
    if st.button("Enregistrer les entités", type="primary") and st.session_state["layers"]:
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

# Charger les rasters en mémoire (exemple)
raster_files = ["raster1.tif", "raster2.tif", "raster3.tif"]  # Remplacez par vos fichiers
if "elevation_data" not in st.session_state:
    st.session_state["elevation_data"], st.session_state["transform"], st.session_state["meta"] = load_rasters(raster_files)

# Section pour les analyses spatiales
st.sidebar.markdown("---")
st.sidebar.header("Analyses Spatiales")

# Exemple : Tracer un profil en long
if st.sidebar.button("Tracer un profil en long"):
    x1, y1 = 100, 200  # Coordonnées de départ
    x2, y2 = 300, 400  # Coordonnées d'arrivée
    plot_profile(st.session_state["elevation_data"], x1, y1, x2, y2)

# Exemple : Générer une carte d'inondation
if st.sidebar.button("Générer une carte d'inondation"):
    flood_threshold = st.sidebar.slider("Seuil d'inondation (m)", 0, 100, 10)
    generate_flood_map(st.session_state["elevation_data"], flood_threshold)
