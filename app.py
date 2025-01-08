import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
import os

# Titre de l'application
st.title("Téléversement et visualisation de Shapefiles sur une carte dynamique")

# Fonction pour charger un Shapefile
def load_shapefile(file):
    try:
        # Essayer d'abord avec pyogrio, puis avec fiona en cas d'échec
        try:
            gdf = gpd.read_file(file, engine="pyogrio")
        except Exception as e:
            st.warning(f"pyogrio a échoué, utilisation de fiona : {e}")
            gdf = gpd.read_file(file, engine="fiona")
        return gdf
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier {file} : {e}")
        return None

# Fonction pour afficher les Shapefiles sur une carte Folium
def display_shapefiles_on_map(shapefiles):
    # Créer une carte Folium centrée sur une position par défaut (ex: France)
    m = folium.Map(location=[46.603354, 1.888334], zoom_start=6, crs="EPSG4326")
    
    # Ajouter chaque Shapefile à la carte avec le nom du fichier comme libellé
    for name, gdf in shapefiles.items():
        if gdf is not None:
            folium.GeoJson(
                gdf.__geo_interface__,
                name=name  # Utiliser le nom du fichier comme libellé de la couche
            ).add_to(m)
    
    # Activer le contrôle des couches pour permettre à l'utilisateur de les activer/désactiver
    folium.LayerControl().add_to(m)
    
    # Afficher la carte dans Streamlit
    folium_static(m)

# Téléversement de fichiers Shapefile
uploaded_files = st.file_uploader(
    "Téléversez vos fichiers Shapefile ( .shp, .shx, .dbf, etc.)",
    type=["shp", "shx", "dbf", "prj"],
    accept_multiple_files=True
)

# Dictionnaire pour stocker les Shapefiles chargés
shapefiles = {}

if uploaded_files:
    # Vérifier que tous les fichiers nécessaires sont présents
    required_extensions = [".shp", ".shx", ".dbf"]
    uploaded_file_names = [file.name for file in uploaded_files]
    for ext in required_extensions:
        if not any(name.endswith(ext) for name in uploaded_file_names):
            st.error(f"Fichier {ext} manquant pour le Shapefile.")
            st.stop()
    
    # Créer un dossier temporaire pour stocker les fichiers téléversés
    temp_dir = "temp_shapefiles"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Enregistrer les fichiers téléversés dans le dossier temporaire
    for uploaded_file in uploaded_files:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    
    # Charger les Shapefiles à partir des fichiers .shp
    for file in os.listdir(temp_dir):
        if file.endswith(".shp"):
            shapefile_path = os.path.join(temp_dir, file)
            st.write(f"Tentative de lecture du fichier : {file}")
            gdf = load_shapefile(shapefile_path)
            if gdf is not None:
                # Vérifier si le système de coordonnées est EPSG:4326, sinon le reprojeter
                if gdf.crs != "EPSG:4326":
                    gdf = gdf.to_crs("EPSG:4326")
                # Ajouter le Shapefile au dictionnaire avec le nom du fichier comme clé
                shapefiles[file] = gdf
    
    # Afficher les Shapefiles sur la carte
    if shapefiles:
        display_shapefiles_on_map(shapefiles)
    else:
        st.warning("Aucun fichier Shapefile valide trouvé.")
    
    # Nettoyer le dossier temporaire
    for file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file))
    os.rmdir(temp_dir)
else:
    st.info("Veuillez téléverser des fichiers Shapefile pour les visualiser sur la carte.")
