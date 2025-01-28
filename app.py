import streamlit as st
import geopandas as gpd

# Charger le fichier GeoJSON
geojson_file = 'routeJSON.geojson'
gdf = gpd.read_file(geojson_file)

# Afficher la carte
st.write("Carte des routes extraites d'OpenStreetMap")
st.map(gdf)
