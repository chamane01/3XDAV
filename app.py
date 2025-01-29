import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point, mapping
from shapely.ops import transform
import pyproj

# Fonction pour charger et afficher un GeoJSON
def display_geojson(file):
    geojson_data = json.load(file)
    
    # Créer une carte centrée
    m = folium.Map(location=[0, 0], zoom_start=2)
    folium.GeoJson(
        geojson_data,
        name="GeoJSON",
        tooltip=folium.GeoJsonTooltip(fields=list(geojson_data['features'][0]['properties'].keys()), aliases=list(geojson_data['features'][0]['properties'].keys())),
        popup=folium.GeoJsonPopup(fields=list(geojson_data['features'][0]['properties'].keys()))
    ).add_to(m)

    return geojson_data, m

# Initialisation de Streamlit
st.title("Analyse de proximité avec des routes (avec projections UTM)")
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON des routes", type="geojson")

# Entrée utilisateur pour les coordonnées UTM
st.subheader("Saisissez les coordonnées UTM (Zone 30N)")
easting = st.number_input("Easting (X)", value=500000, step=1)
northing = st.number_input("Northing (Y)", value=4500000, step=1)

# Définition des systèmes de coordonnées
utm_zone = 32630  # EPSG:32630 (Zone UTM 30N)
utm_crs = pyproj.CRS(f"EPSG:{utm_zone}")
wgs84_crs = pyproj.CRS("EPSG:4326")

# Transformer les coordonnées UTM vers WGS84
transformer_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)
longitude, latitude = transformer_to_wgs84.transform(easting, northing)

# Afficher les coordonnées transformées
st.write(f"Coordonnées UTM : ({easting}, {northing})")
st.write(f"Coordonnées WGS84 : ({longitude}, {latitude})")

# Création du point en UTM
point_utm = Point(easting, northing)

if uploaded_file:
    geojson_data, map_object = display_geojson(uploaded_file)
    folium.Marker([latitude, longitude], popup=f"Point Saisi: {longitude}, {latitude}").add_to(map_object)
    map_object.location = [latitude, longitude]
    map_object.zoom_start = 15

    # Création d'un tampon de 20m en UTM
    buffer_utm = point_utm.buffer(20)
    st.write("Tampon (20m) créé autour du point (en UTM).")

    # Transformer le tampon en WGS84
    buffer_wgs84 = transform(transformer_to_wgs84.transform, buffer_utm)
    folium.GeoJson(mapping(buffer_wgs84), name="Tampon 20m").add_to(map_object)

    # Analyse d'intersection
    st.subheader("Analyse d'intersection")
    point_within_buffer = False
    route_name = "Nom inconnu"

    transformer_to_utm = pyproj.Transformer.from_crs(wgs84_crs, utm_crs, always_xy=True)

    for feature in geojson_data['features']:
        geom_wgs84 = shape(feature['geometry'])
        geom_utm = transform(transformer_to_utm.transform, geom_wgs84)
        
        if geom_utm.intersects(buffer_utm):
            point_within_buffer = True
            route_name = feature['properties'].get('name') or feature['properties'].get('id', 'Nom inconnu')
            break

    if point_within_buffer:
        st.write(f"Le point est proche de la route : {route_name}")
    else:
        st.write("Le point n'est pas proche d'une route.")

    st_folium(map_object, width=800, height=600)
else:
    st.write("Veuillez téléverser un fichier GeoJSON pour analyser.")
