import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import Point, shape
from shapely.ops import transform
import pyproj
import geopandas as gpd

# Fonction pour convertir les coordonnées en UTM
def convert_to_utm(lat, lon):
    utm_zone = int((lon + 180) // 6) + 1
    utm_proj = pyproj.CRS(f"EPSG:326{utm_zone}")
    wgs84_proj = pyproj.CRS("EPSG:4326")
    project = pyproj.Transformer.from_crs(wgs84_proj, utm_proj, always_xy=True).transform
    x, y = transform(project, Point(lon, lat))
    return x, y

# Fonction pour créer un tampon autour d'un point
def create_buffer(lat, lon, radius=20):
    x, y = convert_to_utm(lat, lon)
    buffer = Point(x, y).buffer(radius)  # Rayon en mètres
    return buffer

# Fonction pour vérifier les intersections
def check_intersections(buffer, geojson_data):
    intersecting_features = []
    for feature in geojson_data['features']:
        geom = shape(feature['geometry'])
        if buffer.intersects(geom):
            intersecting_features.append(feature['properties'])
    return intersecting_features

# Fonction pour afficher le GeoJSON
def display_geojson(file):
    geojson_data = json.load(file)
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Ajouter le GeoJSON à la carte avec une info-bulle
    folium.GeoJson(
        geojson_data,
        name="GeoJSON",
        tooltip=folium.GeoJsonTooltip(
            fields=list(geojson_data['features'][0]['properties'].keys()),
            aliases=list(geojson_data['features'][0]['properties'].keys())
        )
    ).add_to(m)

    return m, geojson_data

# Interface Streamlit
st.title("Analyse spatiale avec tampon")

# Téléversement du fichier GeoJSON
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON", type="geojson")

if uploaded_file:
    st.write("Fichier chargé avec succès !")

    # Afficher la carte interactive
    st.subheader("Carte dynamique")
    map_object, geojson_data = display_geojson(uploaded_file)
    st_data = st_folium(map_object, width=700, height=500)

    # Ajouter un point manuel
    st.subheader("Ajouter un point pour analyse")
    lat = st.number_input("Latitude", format="%.6f")
    lon = st.number_input("Longitude", format="%.6f")
    buffer_radius = st.slider("Rayon du tampon (mètres)", min_value=1, max_value=100, value=20)

    if st.button("Analyser"):
        # Créer un tampon autour du point ajouté
        buffer = create_buffer(lat, lon, radius=buffer_radius)

        # Vérifier les intersections avec les entités du GeoJSON
        intersections = check_intersections(buffer, geojson_data)

        if intersections:
            st.write(f"{len(intersections)} entité(s) intersectée(s) :")
            for feature in intersections:
                st.json(feature)
        else:
            st.write("Aucune intersection trouvée.")

        # Ajouter le point et le tampon sur la carte
        folium.Marker(location=[lat, lon], tooltip="Point ajouté").add_to(map_object)
        folium.Circle(
            location=[lat, lon],
            radius=buffer_radius,
            color="red",
            fill=True,
            fill_opacity=0.3
        ).add_to(map_object)
        st_folium(map_object, width=700, height=500)
