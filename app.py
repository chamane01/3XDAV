import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point, Polygon
from shapely.ops import transform
import pyproj
import hashlib

# Fonction pour générer une couleur unique à partir d'un ID
def generate_color_from_id(id):
    # Utiliser un hash pour générer une couleur unique
    hash_object = hashlib.md5(str(id).encode())
    hex_color = '#' + hash_object.hexdigest()[:6]
    return hex_color

# Fonction pour afficher GeoJSON et afficher la carte
def display_geojson(file):
    geojson_data = json.load(file)
    
    # Créer une carte Folium centrée sur les coordonnées du fichier GeoJSON
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Ajouter chaque entité avec une couleur unique basée sur son ID
    for feature in geojson_data['features']:
        feature_id = feature['properties'].get('id', 'default_id')  # Remplacer 'id' par la clé appropriée
        color = generate_color_from_id(feature_id)
        
        folium.GeoJson(
            feature,
            name=f"Feature {feature_id}",
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': color,
                'weight': 2,
                'fillOpacity': 0.5
            },
            tooltip=folium.GeoJsonTooltip(fields=list(feature['properties'].keys()), aliases=list(feature['properties'].keys())),
            popup=folium.GeoJsonPopup(fields=list(feature['properties'].keys()))
        ).add_to(m)

    return geojson_data, m

# Interface Streamlit
st.title("Visualiseur de fichiers GeoJSON")

# Téléversement du fichier GeoJSON
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON", type="geojson")

# Saisie des coordonnées UTM
st.subheader("Saisissez les coordonnées UTM (Zone 30N)")
easting = st.number_input("Easting (X)", value=500000, step=1)
northing = st.number_input("Northing (Y)", value=4500000, step=1)

# Transformer les coordonnées UTM en WGS84 (longitude, latitude)
utm_zone = 32630
utm_proj = pyproj.CRS(f"EPSG:{utm_zone}").to_proj4()
utm_to_wgs84 = pyproj.CRS("EPSG:4326").to_proj4()

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

    # Centrer la carte sur le point saisi
    map_object.location = [latitude, longitude]
    map_object.zoom_start = 15

    # Calcul du tampon de 20m autour du point (en UTM 32630)
    buffer = point_utm.buffer(20)  # 20m autour du point
    
    # Transformer le tampon en WGS84 pour l'affichage
    transformer_for_display = pyproj.Transformer.from_proj(utm_proj, utm_to_wgs84)
    buffer_wgs84 = transform(transformer_for_display.transform, buffer)  # Transformer en WGS84 pour affichage
    geo_buffer = Polygon(buffer_wgs84)
    
    # Convertir la géométrie en GeoJSON
    geojson_buffer = geo_buffer.__geo_interface__
    
    # Ajouter le tampon à la carte
    folium.GeoJson(geojson_buffer, name="Tampon 20m").add_to(map_object)

    # Analyser l'intersection du point et des routes
    st.subheader("Vérification de la proximité avec une route")
    point_within_buffer = False
    route_name = None

    # Analyser les caractéristiques du fichier GeoJSON
    for feature in geojson_data['features']:
        geom = shape(feature['geometry'])

        # Reprojection de la géométrie du GeoJSON en WGS84
        geom_wgs84 = transform(transformer_for_display.transform, geom)

        # Vérification de l'intersection avec le tampon
        if geom_wgs84.intersects(buffer):  # Le point est proche d'une route si une intersection est détectée
            point_within_buffer = True
            if 'name' in feature['properties']:
                route_name = feature['properties']['name']
            break

    # Afficher la carte dans Streamlit
    st_folium(map_object, width=800, height=600)

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
