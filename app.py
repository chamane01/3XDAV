import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import hashlib
from shapely.geometry import shape, Point, Polygon, mapping
from shapely.ops import transform
import pyproj
import copy

def generate_color_from_id(id_value):
    """Génère une couleur hexadécimale unique basée sur le hash de l'ID"""
    hash_str = hashlib.md5(str(id_value).encode()).hexdigest()[:6]
    return f'#{hash_str}'

def display_geojson(file):
    geojson_data = json.load(file)
    
    # Créer une carte centrée
    m = folium.Map(location=[0, 0], zoom_start=2)
    
    # Créer une copie profonde des features originales
    original_features = geojson_data['features'].copy()
    
    # Créer des doublons avec de nouvelles propriétés
    duplicated_features = []
    target_id = 'way/68486464354'  # ID spécifique à traiter
    
    for feature in original_features:
        # Vérifier si c'est l'ID cible
        if feature['properties'].get('ID') == target_id:
            # Créer un doublon
            duplicated_feature = copy.deepcopy(feature)
            duplicated_feature['properties']['is_duplicate'] = True
            duplicated_features.append(duplicated_feature)
    
    # Fusionner les features originales et doublons
    all_features = original_features + duplicated_features
    
    # Créer un nouveau GeoJSON avec toutes les features
    modified_geojson = {
        'type': 'FeatureCollection',
        'features': all_features
    }
    
    # Style function pour les doublons
    def style_function(feature):
        if feature['properties'].get('is_duplicate'):
            return {
                'color': generate_color_from_id(feature['properties']['ID']),
                'weight': 4,
                'opacity': 0.7
            }
        return {'color': '#3388ff'}  # Couleur bleue originale
    
    folium.GeoJson(
        modified_geojson,
        name="GeoJSON",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=['ID', 'highway', 'lanes', 'surface', 'is_duplicate']),
        popup=folium.GeoJsonPopup(fields=['ID', 'highway', 'lanes', 'surface', 'is_duplicate'])
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

# Transformer les coordonnées UTM vers WGS84 pour l'affichage
transformer_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)
longitude, latitude = transformer_to_wgs84.transform(easting, northing)

# Afficher les coordonnées transformées
st.write(f"Coordonnées UTM : ({easting}, {northing})")
st.write(f"Coordonnées WGS84 : ({longitude}, {latitude})")

# Création d'un point à partir des coordonnées UTM
point_utm = Point(easting, northing)

if uploaded_file:
    # Charger le fichier GeoJSON modifié
    geojson_data, map_object = display_geojson(uploaded_file)

    # Ajouter le point sur la carte pour l'affichage
    folium.Marker([latitude, longitude], popup=f"Point Saisi: {longitude}, {latitude}").add_to(map_object)
    map_object.location = [latitude, longitude]
    map_object.zoom_start = 15

    # Création d'un tampon de 20m en UTM
    buffer_utm = point_utm.buffer(20)  # Rayon de 20m
    st.write("Tampon (20m) créé autour du point (en UTM).")

    # Transformer le tampon en WGS84 pour l'affichage
    transformer_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)
    buffer_wgs84 = transform(transformer_to_wgs84.transform, buffer_utm)

    # Ajouter le tampon à la carte
    folium.GeoJson(mapping(buffer_wgs84), name="Tampon 20m").add_to(map_object)

    # Initialisation de l'analyse
    st.subheader("Analyse d'intersection")
    point_within_buffer = False
    route_name = None

    # Préparer la transformation WGS84 -> UTM pour les géométries des routes
    transformer_to_utm = pyproj.Transformer.from_crs(wgs84_crs, utm_crs, always_xy=True)

    # Analyse des intersections avec les routes
    for feature in geojson_data['features']:
        geom_wgs84 = shape(feature['geometry'])  # Géométrie en WGS84
        geom_utm = transform(transformer_to_utm.transform, geom_wgs84)  # Reprojection en UTM

        # Vérification de l'intersection avec le tampon
        if geom_utm.intersects(buffer_utm):
            point_within_buffer = True
            route_name = feature['properties'].get('name', 'Nom inconnu')
            break

    # Afficher les résultats
    if point_within_buffer:
        st.write(f"Le point est proche de la route : {route_name}")
    else:
        st.write("Le point n'est pas proche d'une route.")

    # Afficher la carte dans Streamlit
    st_folium(map_object, width=800, height=600)
else:
    st.write("Veuillez téléverser un fichier GeoJSON pour analyser.")
