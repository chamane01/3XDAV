import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import zipfile
import tempfile

# Fonction pour charger et afficher les fichiers Shapefile
@st.cache_data
def load_shapefiles(directory):
    shapefiles = {}
    for file in os.listdir(directory):
        if file.endswith(".shp"):
            filepath = os.path.join(directory, file)
            shapefiles[file] = gpd.read_file(filepath)
    return shapefiles

def create_map(shapefiles):
    base_map = folium.Map(location=[0, 0], zoom_start=2)
    for name, gdf in shapefiles.items():
        if not gdf.empty:
            folium.GeoJson(
                gdf,
                name=name,
                tooltip=folium.GeoJsonTooltip(fields=list(gdf.columns)),
            ).add_to(base_map)
    folium.LayerControl().add_to(base_map)
    return base_map

# Interface utilisateur Streamlit
st.title("Affichage des couches Shapefile téléversées")

uploaded_file = st.file_uploader(
    "Téléversez un fichier ZIP contenant vos fichiers Shapefile", type=["zip"]
)

if uploaded_file:
    # Créer un dossier temporaire pour extraire les fichiers
    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = os.path.join(tmp_dir, "uploaded_zip.zip")
        
        # Sauvegarder le fichier ZIP téléversé
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Extraire le fichier ZIP
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmp_dir)

        # Charger les fichiers Shapefile
        shapefiles = load_shapefiles(tmp_dir)

        if shapefiles:
            st.write(f"{len(shapefiles)} couches trouvées :")
            for name in shapefiles.keys():
                st.write(f"- {name}")

            # Créer une carte et l'afficher
            map_ = create_map(shapefiles)
            st_folium(map_, width=800, height=600)
        else:
            st.warning("Aucun fichier Shapefile valide trouvé dans le ZIP.")
