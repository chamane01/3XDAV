import streamlit as st
import osmnx as ox
import folium
from streamlit_folium import folium_static

# Définir le nom de la ville ou les coordonnées de la zone d'intérêt
place_name = "Botro, Côte d'Ivoire"

# Télécharger le graphe routier de la zone spécifiée
graph = ox.graph_from_place(place_name, network_type='all')

# Convertir le graphe en GeoDataFrame
gdf_nodes, gdf_edges = ox.graph_to_gdfs(graph)

# Obtenir les coordonnées du centre de la ville
center = [gdf_nodes['y'].mean(), gdf_nodes['x'].mean()]

# Créer une carte centrée sur la ville
m = folium.Map(location=center, zoom_start=12)

# Ajouter les routes à la carte
folium.GeoJson(gdf_edges).add_to(m)

# Afficher la carte dans Streamlit
folium_static(m)
