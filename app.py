import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import Point
from shapely.geometry import mapping
import geopandas as gpd
import pyproj
from shapely.ops import transform
from shapely.geometry import Polygon
from shapely.geometry import shape

def display_geojson(file, utm_proj=None):
    # Charger le fichier GeoJSON
    geojson_data = json.load(file)
    
    # Si une projection UTM est définie, reprojeter le GeoJSON en UTM
    if utm_proj:
        for feature in geojson_data['features']:
            # Transformer chaque géométrie en UTM 32630
            geom = shape(feature['geometry'])
            transformed_geom = transform(utm_proj, geom)
            feature['geometry'] = mapping(transformed_geom)

    # Créer une carte Folium centrée sur les coordonnées du fichier GeoJSON
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Ajouter le GeoJSON à la carte avec une fonction de popup pour afficher les informations
    folium.GeoJson(
        geojson_data,
        name="GeoJSON",
        tooltip=folium.GeoJsonTooltip(fields=list(geojson_data['features'][0]['properties'].keys()), aliases=list(geojson_data['features'][0]['properties'].keys())),
        popup=folium.GeoJsonPopup(fields=list(geojson_data['features'][0]['properties'].keys()))
    ).add_to(m)

    return m

# Interface Streamlit
st.title("Visualiseur de fichiers GeoJSON")

# Téléversement du fichier GeoJSON
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON", type="geojson")

# Saisie manuelle des coordonnées
utm_zone = 32630
utm_proj = pyproj.CRS(f"EPSG:{utm_zone}").to_proj4()
utm_to_wgs84 = pyproj.CRS("EPSG:4326").to_proj4()

# Saisie des coordonnées UTM
st.subheader("Saisissez les coordonnées UTM (Zone 30N)")
easting = st.number_input("Easting (X)", value=500000, step=1)
northing = st.number_input("Northing (Y)", value=4500000, step=1)

# Transformer les coordonnées UTM en WGS84 (longitude, latitude)
point_utm = Point(easting, northing)
transformer = pyproj.Transformer.from_proj(utm_proj, utm_to_wgs84)
longitude, latitude = transformer.transform(point_utm.x, point_utm.y)

# Afficher le point sur la carte
st.write(f"Coordonnées UTM : ({easting}, {northing})")
st.write(f"Coordonnées WGS84 : ({longitude}, {latitude})")

# Ajouter le point sur la carte
if uploaded_file:
    st.write("Fichier chargé avec succès !")
    map_object = display_geojson(uploaded_file, utm_proj=pyproj.CRS(utm_proj))
    folium.Marker([latitude, longitude], popup=f"Point Saisi: {longitude}, {latitude}").add_to(map_object)
    
    # Afficher la carte
    st.subheader("Carte dynamique")
    st_data = st_folium(map_object, width=700, height=500)

    # Calcul du tampon de 20m autour du point
    buffer = point_utm.buffer(20)  # 20m autour du point
    buffer_wgs84 = transform(transformer, buffer)  # Transformer en WGS84 pour affichage
    geo_buffer = Polygon(buffer_wgs84)
    geojson_buffer = geo_buffer.__geo_interface__
    
    # Afficher le tampon sur la carte
    folium.GeoJson(geojson_buffer).add_to(map_object)
    
    # Vérification si une route est à proximité
    st.subheader("Vérification de la proximité avec une route")
    # Vérifier la proximité avec une route
    # Cette logique dépend de l'analyse de la couche GeoJSON des routes
    if st_data and st_data['last_active_drawing']:  
        route_info = st_data['last_active_drawing']
        if route_info:
            st.write(f"Le point est sur une route: {route_info['properties']['name']}")
        else:
            st.write("Aucune route à proximité.")
else:
    st.write("Téléversez un fichier GeoJSON pour continuer.")
