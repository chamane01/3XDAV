import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point, Polygon
from shapely.ops import transform
import pyproj
import hashlib

# Fonction pour générer une couleur unique à partir d'un ID
def generate_color(id_value):
    id_str = str(id_value)
    hash_hex = hashlib.md5(id_str.encode()).hexdigest()[:6]
    return f'#{hash_hex}'

# Fonction pour afficher GeoJSON avec les deux couches
def display_geojson(file):
    geojson_data = json.load(file)
    
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Couche originale
    folium.GeoJson(
        geojson_data,
        name="GeoJSON Original",
        tooltip=folium.GeoJsonTooltip(fields=list(geojson_data['features'][0]['properties'].keys())),
        popup=folium.GeoJsonPopup(fields=list(geojson_data['features'][0]['properties'].keys()))
    ).add_to(m)

    # Couche colorée par ID
    def style_function(feature):
        feature_id = feature.get('id') or feature['properties'].get('id', 'N/A')
        color = generate_color(feature_id)
        return {
            'fillColor': color,
            'color': color,
            'weight': 2,
            'fillOpacity': 0.5
        }

    folium.GeoJson(
        geojson_data,
        name="Coloré par ID",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=['id'] + list(geojson_data['features'][0]['properties'].keys())),
        popup=folium.GeoJsonPopup(fields=['id'] + list(geojson_data['features'][0]['properties'].keys()))
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return geojson_data, m

# Interface Streamlit
st.title("Visualiseur de fichiers GeoJSON")

# Téléversement du fichier GeoJSON
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON", type="geojson")

# ... (le reste du code reste inchangé jusqu'à la partie d'affichage de la carte)

if uploaded_file:
    st.write("Fichier chargé avec succès!")
    
    # Charger et afficher le fichier GeoJSON avec les deux couches
    geojson_data, map_object = display_geojson(uploaded_file)

    # Ajouter le point sur la carte
    folium.Marker([latitude, longitude], popup=f"Point Saisi: {longitude}, {latitude}").add_to(map_object)
    
    # ... (le reste du code reste inchangé)

# ... (la fin du code reste inchangée)
