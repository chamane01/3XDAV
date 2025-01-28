import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import Point, shape
import pyproj
from pyproj import Transformer

# Fonction pour convertir les coordonnées en UTM
def convert_to_utm(lat, lon):
    utm_zone = int((lon + 180) // 6) + 1
    utm_proj = pyproj.CRS(f"EPSG:326{utm_zone}")  # Zone UTM pour l'hémisphère nord
    wgs84_proj = pyproj.CRS("EPSG:4326")  # Coordonnées en WGS84 (lat/lon)
    transformer = Transformer.from_crs(wgs84_proj, utm_proj, always_xy=True)
    x, y = transformer.transform(lon, lat)  # pyproj demande (lon, lat) pour la transformation
    return x, y

# Fonction pour créer un tampon autour d'un point
def create_buffer(lat, lon, radius=20):
    x, y = convert_to_utm(lat, lon)
    buffer = Point(x, y).buffer(radius)  # Rayon en mètres
    return buffer

# Fonction pour vérifier les intersections avec les entités GeoJSON
def check_intersections(buffer, geojson_data):
    intersecting_features = []
    for feature in geojson_data['features']:
        geom = shape(feature['geometry'])  # Convertir en géométrie Shapely
        if buffer.intersects(geom):  # Vérifier si le tampon intersecte la géométrie
            intersecting_features.append(feature['properties'])
    return intersecting_features

# Fonction pour afficher le GeoJSON
def display_geojson(file):
    geojson_data = json.load(file)  # Charger le contenu GeoJSON
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Ajouter le GeoJSON à la carte
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

    # Afficher la carte et charger le fichier GeoJSON
    st.subheader("Carte dynamique")
    map_object, geojson_data = display_geojson(uploaded_file)
    st_data = st_folium(map_object, width=700, height=500)

    # Ajouter un point manuel
    st.subheader("Ajouter un point pour analyse")
    lat = st.number_input("Latitude (WGS84)", format="%.6f")
    lon = st.number_input("Longitude (WGS84)", format="%.6f")
    buffer_radius = st.slider("Rayon du tampon (mètres)", min_value=1, max_value=100, value=20)

    if st.button("Analyser"):
        try:
            # Créer un tampon autour du point ajouté
            buffer = create_buffer(lat, lon, radius=buffer_radius)

            # Vérifier les intersections avec les entités GeoJSON
            intersections = check_intersections(buffer, geojson_data)

            # Ajouter le point et le tampon à la carte
            folium.Marker(location=[lat, lon], tooltip="Point ajouté").add_to(map_object)
            folium.Circle(
                location=[lat, lon],
                radius=buffer_radius,
                color="red",
                fill=True,
                fill_opacity=0.3
            ).add_to(map_object)

            # Afficher les résultats d'intersections
            if intersections:
                st.write(f"{len(intersections)} entité(s) intersectée(s) :")
                for feature in intersections:
                    st.json(feature)
            else:
                st.write("Aucune intersection trouvée.")

            # Afficher la carte mise à jour
            st_folium(map_object, width=700, height=500)

        except Exception as e:
            st.error(f"Une erreur s'est produite : {e}")
