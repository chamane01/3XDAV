import streamlit as st
import folium
from streamlit_folium import folium_static
import geopandas as gpd

# Charger le fichier GeoJSON contenant les routes extraites d'OpenStreetMap
geojson_file = 'routeJSON.geojson'  # Remplacez par le chemin de votre fichier GeoJSON
gdf = gpd.read_file(geojson_file)

# Obtenir les coordonnées du centre de la ville (par exemple, Botro, Côte d'Ivoire)
center = [gdf['geometry'].y.mean(), gdf['geometry'].x.mean()]

# Créer une carte centrée sur la ville
m = folium.Map(location=center, zoom_start=12)

# Ajouter les routes à la carte
folium.GeoJson(gdf).add_to(m)

# Afficher la carte dans l'application Streamlit
folium_static(m)
