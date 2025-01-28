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
    
    # Copie des features originales
    original_features = geojson_data['features'].copy()
    
    # Création des doublons
    duplicated_features = []
    target_id = 'way/68486464354'  # ID spécifique à dupliquer
    
    for feature in original_features:
        if feature['properties'].get('ID') == target_id:
            # Création du doublon
            duplicated_feature = copy.deepcopy(feature)
            duplicated_feature['properties']['is_duplicate'] = True
            duplicated_features.append(duplicated_feature)
    
    # Fusion des features
    all_features = original_features + duplicated_features
    
    # Création du GeoJSON modifié
    modified_geojson = {
        'type': 'FeatureCollection',
        'features': all_features
    }
    
    # Fonction de style personnalisée
    def style_function(feature):
        if feature['properties'].get('is_duplicate'):
            return {
                'color': generate_color_from_id(feature['properties']['ID']),
                'weight': 4,
                'opacity': 0.7
            }
        return {'color': '#3388ff', 'weight': 2, 'opacity': 0.5}
    
    # Affichage du GeoJSON avec style personnalisé
    folium.GeoJson(
        modified_geojson,
        name="GeoJSON",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=['ID', 'highway', 'lanes', 'surface', 'is_duplicate']),
        popup=folium.GeoJsonPopup(fields=['ID', 'highway', 'lanes', 'surface', 'is_duplicate'])
    ).add_to(m)

    return geojson_data, m

# Configuration de la page Streamlit
st.title("Analyse de proximité avec des routes (avec projections UTM)")
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON des routes", type="geojson")

# Section de saisie des coordonnées UTM
st.subheader("Saisissez les coordonnées UTM (Zone 30N)")
easting = st.number_input("Easting (X)", value=500000, step=1)
northing = st.number_input("Northing (Y)", value=4500000, step=1)

# Définition des systèmes de coordonnées
utm_zone = 32630  # EPSG:32630 (Zone UTM 30N)
utm_crs = pyproj.CRS(f"EPSG:{utm_zone}")
wgs84_crs = pyproj.CRS("EPSG:4326")

# Transformation des coordonnées UTM vers WGS84
transformer_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)
longitude, latitude = transformer_to_wgs84.transform(easting, northing)

# Affichage des coordonnées transformées
st.write(f"Coordonnées UTM : ({easting}, {northing})")
st.write(f"Coordonnées WGS84 : ({longitude:.6f}, {latitude:.6f})")

# Création du point UTM
point_utm = Point(easting, northing)

if uploaded_file:
    # Chargement et affichage du GeoJSON
    geojson_data, map_object = display_geojson(uploaded_file)

    # Ajout du marqueur pour le point saisi
    folium.Marker([latitude, longitude], popup=f"Point Saisi: {longitude:.6f}, {latitude:.6f}").add_to(map_object)
    map_object.location = [latitude, longitude]
    map_object.zoom_start = 15

    # Création du tampon UTM
    buffer_utm = point_utm.buffer(20)
    st.write("Tampon (20m) créé autour du point (en UTM).")

    # Transformation du tampon en WGS84
    buffer_wgs84 = transform(transformer_to_wgs84.transform, buffer_utm)

    # Ajout du tampon à la carte
    folium.GeoJson(mapping(buffer_wgs84), name="Tampon 20m").add_to(map_object)

    # Analyse d'intersection
    st.subheader("Analyse d'intersection")
    point_within_buffer = False
    route_name = None

    # Préparation de la transformation WGS84 -> UTM
    transformer_to_utm = pyproj.Transformer.from_crs(wgs84_crs, utm_crs, always_xy=True)

    # Vérification des intersections
    for feature in geojson_data['features']:
        geom_wgs84 = shape(feature['geometry'])
        geom_utm = transform(transformer_to_utm.transform, geom_wgs84)

        if geom_utm.intersects(buffer_utm):
            point_within_buffer = True
            route_name = feature['properties'].get('name', 'Nom inconnu')
            break

    # Affichage des résultats
    if point_within_buffer:
        st.success(f"Le point est proche de la route : {route_name}")
    else:
        st.error("Le point n'est pas proche d'une route.")

    # Affichage final de la carte
    st_folium(map_object, width=800, height=600)
else:
    st.info("Veuillez téléverser un fichier GeoJSON pour commencer l'analyse.")
