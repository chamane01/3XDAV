import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os

# Fonction pour charger et afficher un Shapefile sur une carte
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
st.title("Affichage des couches Shapefile")

directory = st.text_input("Entrez le chemin du dossier contenant les fichiers Shapefile :")

if directory:
    if os.path.exists(directory):
        shapefiles = load_shapefiles(directory)

        if shapefiles:
            st.write(f"{len(shapefiles)} couches trouvées :")
            for name in shapefiles.keys():
                st.write(f"- {name}")

            # Créer une carte et l'afficher
            map_ = create_map(shapefiles)
            st_folium(map_, width=800, height=600)
        else:
            st.warning("Aucun fichier Shapefile trouvé dans le dossier.")
    else:
        st.error("Le chemin spécifié n'existe pas.")
