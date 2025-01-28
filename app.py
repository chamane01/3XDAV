import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, mapping, Point
import pyproj
from shapely.ops import transform
from shapely.geometry import Polygon

def display_geojson(file):
    # Charger le fichier GeoJSON en EPSG:4326 pour l'affichage
    geojson_data = json.load(file)
    
    # Créer une carte Folium centrée sur les coordonnées du fichier GeoJSON
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Ajouter le GeoJSON à la carte avec une fonction de popup pour afficher les informations
    folium.GeoJson(
        geojson_data,
        name="GeoJSON",
        tooltip=folium.GeoJsonTooltip(fields=list(geojson_data['features'][0]['properties'].keys()), aliases=list(geojson_data['features'][0]['properties'].keys())),
        popup=folium.GeoJsonPopup(fields=list(geojson_data['features'][0]['properties'].keys()))
    ).add_to(m)

    return geojson_data, m  # Retourner aussi les données GeoJSON pour les calculs

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
    st.write("Fichier chargé avec succès!")
    
    # Charger et afficher le fichier GeoJSON
    geojson_data, map_object = display_geojson(uploaded_file)

    # Ajouter le point sur la carte
    folium.Marker([latitude, longitude], popup=f"Point Saisi: {longitude}, {latitude}").add_to(map_object)

    # Afficher la carte
    st.subheader("Carte dynamique")
    st_data = st_folium(map_object, width=700, height=500)

    # Calcul du tampon de 20m autour du point (en UTM 32630)
    buffer = point_utm.buffer(20)  # 20m autour du point
    # Transformer le tampon en WGS84 pour l'affichage
    transformer_for_display = pyproj.Transformer.from_proj(utm_proj, utm_to_wgs84)
    buffer_wgs84 = transform(transformer_for_display.transform, buffer)  # Transformer en WGS84 pour affichage
    geo_buffer = Polygon(buffer_wgs84)
    geojson_buffer = geo_buffer.__geo_interface__
    
    # Afficher le tampon sur la carte
    folium.GeoJson(geojson_buffer).add_to(map_object)

    # Analyse spatiale : Vérification de la proximité avec une route
    st.subheader("Vérification de la proximité avec une route")
    point_within_buffer = False
    route_name = None

    # Analyser les caractéristiques du fichier GeoJSON
    for feature in geojson_data['features']:
        geom = shape(feature['geometry'])
        
        # Debug : Affichage des coordonnées de la géométrie et du point
        st.write(f"Point de l'analyse : {longitude}, {latitude}")
        st.write(f"Géométrie du GeoJSON (avant projection) : {geom.wkt}")

        # Reprojection de la géométrie du GeoJSON en WGS84 si nécessaire
        if geom.crs != "EPSG:4326":
            geom = transform(transformer_for_display.transform, geom)
            st.write(f"Géométrie après reprojection : {geom.wkt}")

        # Vérification de l'intersection avec le tampon
        if geom.intersects(buffer):  # Le point est proche d'une route si une intersection est détectée
            point_within_buffer = True
            if 'name' in feature['properties']:
                route_name = feature['properties']['name']
            break

    # Afficher les résultats de l'analyse
    if point_within_buffer:
        if route_name:
            st.write(f"Le point est proche de la route : {route_name}")
        else:
            st.write("Le point est proche d'une route, mais son nom est inconnu.")
    else:
        st.write("Le point n'est pas proche d'une route.")
else:
    st.write("Téléversez un fichier GeoJSON pour continuer.")
