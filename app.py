import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
import os

# Titre de l'application
st.title("Visualisation de Shapefiles extraits d'OSM")

# Fonction pour charger les Shapefiles
def load_shapefiles(directory):
    shapefiles = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".shp"):
                shapefile_path = os.path.join(root, file)
                gdf = gpd.read_file(shapefile_path)
                shapefiles.append(gdf)
    return shapefiles

# Upload du dossier contenant les Shapefiles
uploaded_dir = st.file_uploader("Téléchargez un dossier contenant des Shapefiles", type=None, accept_multiple_files=True)

if uploaded_dir is not None:
    # Créer un dossier temporaire pour stocker les fichiers téléchargés
    temp_dir = "temp_shapefiles"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Enregistrer les fichiers téléchargés dans le dossier temporaire
    for uploaded_file in uploaded_dir:
        with open(os.path.join(temp_dir, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
    
    # Charger les Shapefiles
    shapefiles = load_shapefiles(temp_dir)
    
    # Afficher les Shapefiles sur une carte Folium
    if shapefiles:
        m = folium.Map(location=[46.603354, 1.888334], zoom_start=6)  # Centré sur la France
        
        for gdf in shapefiles:
            for _, row in gdf.iterrows():
                folium.GeoJson(row['geometry']).add_to(m)
        
        folium_static(m)
    else:
        st.warning("Aucun fichier Shapefile trouvé dans le dossier.")
    
    # Nettoyer le dossier temporaire
    for file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file))
    os.rmdir(temp_dir)
else:
    st.info("Veuillez télécharger un dossier contenant des Shapefiles.")
