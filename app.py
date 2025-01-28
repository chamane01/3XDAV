import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import Point, shape
import pyproj
from pyproj import Transformer

# Fonction pour vérifier si le GeoJSON est en UTM (basé sur son CRS)
def is_geojson_utm(geojson_data):
    crs = geojson_data.get("crs", {}).get("properties", {}).get("name", "")
    return "UTM" in crs or "326" in crs or "327" in crs  # Vérifie si le CRS mentionne UTM ou EPSG 326/327

# Fonction pour convertir des coordonnées entre deux systèmes
def convert_coordinates(x, y, from_crs, to_crs):
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
    return transformer.transform(x, y)

# Fonction pour créer un tampon autour d'un point (en mètres)
def create_buffer(x, y, radius=20):
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

    # Vérifier si le GeoJSON est en UTM
    geojson_is_utm = is_geojson_utm(geojson_data)
    st.write(f"Le fichier GeoJSON est en UTM : {'Oui' if geojson_is_utm else 'Non'}")

    # Options de saisie des coordonnées
    st.subheader("Ajouter un point pour analyse")
    if geojson_is_utm:
        st.write("Saisie des coordonnées en UTM (x, y) :")
        x = st.number_input("Coordonnée X (UTM)", format="%.2f")
        y = st.number_input("Coordonnée Y (UTM)", format="%.2f")
    else:
        st.write("Saisie des coordonnées en latitude/longitude (WGS84) :")
        lat = st.number_input("Latitude (WGS84)", format="%.6f")
        lon = st.number_input("Longitude (WGS84)", format="%.6f")

    buffer_radius = st.slider("Rayon du tampon (mètres)", min_value=1, max_value=100, value=20)

    # Afficher le point et son tampon dès qu'il est saisi
    if st.button("Afficher le point"):
        try:
            # Convertir les coordonnées si nécessaire
            if geojson_is_utm:
                point_x, point_y = x, y
            else:
                point_x, point_y = convert_coordinates(
                    lon, lat, "EPSG:4326", "EPSG:32633"  # Vous pouvez adapter la zone EPSG ici
                )

            # Ajouter le point et le tampon à la carte
            folium.Marker(location=[lat, lon] if not geojson_is_utm else [point_y, point_x],
                          tooltip="Point ajouté").add_to(map_object)
            folium.Circle(
                location=[lat, lon] if not geojson_is_utm else [point_y, point_x],
                radius=buffer_radius,
                color="blue",
                fill=True,
                fill_opacity=0.3
            ).add_to(map_object)

            st.write("Point et tampon affichés sur la carte.")

            # Afficher la carte mise à jour
            st_folium(map_object, width=700, height=500)

        except Exception as e:
            st.error(f"Une erreur s'est produite : {e}")

    # Vérification des intersections
    st.subheader("Analyser les intersections")
    if st.button("Analyser"):
        try:
            buffer = create_buffer(point_x, point_y, radius=buffer_radius)
            intersections = check_intersections(buffer, geojson_data)

            if intersections:
                st.write(f"{len(intersections)} entité(s) intersectée(s) :")
                for feature in intersections:
                    st.json(feature)
            else:
                st.write("Aucune intersection trouvée.")

        except Exception as e:
            st.error(f"Une erreur s'est produite : {e}")
