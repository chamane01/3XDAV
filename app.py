import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import json

# Fonction pour créer une carte Folium avec l'outil de dessin
def create_map():
    m = folium.Map(location=[46.603354, 1.888334], zoom_start=6)  # Centré sur la France
    Draw(export=True, draw_options={"polyline": True, "polygon": True, "circle": False, "marker": True}).add_to(m)
    return m

# Fonction pour convertir les dessins en GeoDataFrame
def convert_drawings_to_gdf(drawings):
    features = []
    for feature in drawings['features']:
        geometry = feature['geometry']
        if geometry['type'] == 'Point':
            geom = Point(geometry['coordinates'])
        elif geometry['type'] == 'LineString':
            geom = LineString(geometry['coordinates'])
        elif geometry['type'] == 'Polygon':
            geom = Polygon(geometry['coordinates'][0])  # Polygon a une structure imbriquée
        else:
            continue
        features.append({'geometry': geom, 'properties': {}})
    
    if features:
        return gpd.GeoDataFrame(features, crs="EPSG:4326")
    return None

# Interface Streamlit
st.title("Carte Dynamique avec Dessin et Gestion de Couches")

# Initialisation de la session state pour stocker les couches
if 'layers' not in st.session_state:
    st.session_state.layers = []

# Création de la carte
m = create_map()

# Utilisation de st_folium pour afficher la carte et récupérer les interactions
output = st_folium(m, width=1200, height=600, key="map")

# Récupération des dessins
if output and 'last_active_drawing' in output:
    drawings = output['last_active_drawing']
    if drawings:
        gdf = convert_drawings_to_gdf(drawings)
        if gdf is not None:
            st.session_state.layers.append(gdf)

# Affichage des couches
if st.session_state.layers:
    st.subheader("Couches disponibles")
    for i, layer in enumerate(st.session_state.layers):
        st.write(f"Couche {i+1}")
        st.write(layer)

# Option pour supprimer une couche
if st.session_state.layers:
    layer_to_remove = st.selectbox("Sélectionnez une couche à supprimer", options=list(range(len(st.session_state.layers))))
    if st.button("Supprimer la couche sélectionnée"):
        st.session_state.layers.pop(layer_to_remove)
        st.experimental_rerun()

# Option pour exporter les couches
if st.session_state.layers:
    if st.button("Exporter toutes les couches en GeoJSON"):
        combined_gdf = gpd.GeoDataFrame(gpd.pd.concat(st.session_state.layers, ignore_index=True))
        st.download_button(
            label="Télécharger GeoJSON",
            data=combined_gdf.to_json(),
            file_name="layers.geojson",
            mime="application/json"
        )
