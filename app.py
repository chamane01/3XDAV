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
st.title("Visualiseur de fichiers GeoJSON avec coloration par ID")

# Saisie des coordonnées UTM
st.subheader("Saisissez les coordonnées UTM (Zone 30N)")
easting = st.number_input("Easting (X)", value=500000, step=1)
northing = st.number_input("Northing (Y)", value=4500000, step=1)

# Conversion UTM vers WGS84
try:
    utm_zone = 32630
    utm_proj = pyproj.CRS(f"EPSG:{utm_zone}")
    wgs84_proj = pyproj.CRS("EPSG:4326")
    transformer = pyproj.Transformer.from_crs(utm_proj, wgs84_proj)
    longitude, latitude = transformer.transform(easting, northing)
except Exception as e:
    st.error(f"Erreur de conversion : {str(e)}")
    longitude, latitude = 0.0, 0.0

# Affichage des coordonnées
st.write(f"Coordonnées UTM : ({easting}, {northing})")
st.write(f"Coordonnées WGS84 : ({longitude:.6f}, {latitude:.6f})")

# Téléversement du fichier GeoJSON
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON", type="geojson")

if uploaded_file:
    geojson_data, map_object = display_geojson(uploaded_file)
    
    # Ajout du marqueur
    folium.Marker(
        [latitude, longitude],
        popup=f"Point saisi:<br>{longitude:.6f}, {latitude:.6f}",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(map_object)

    # Configuration de la carte
    map_object.location = [latitude, longitude]
    map_object.zoom_start = 15

    # Calcul du tampon
    try:
        point_utm = Point(easting, northing)
        buffer_utm = point_utm.buffer(20)
        transformer_buffer = pyproj.Transformer.from_crs(utm_proj, wgs84_proj)
        buffer_wgs84 = transform(transformer_buffer.transform, buffer_utm)
        folium.GeoJson(Polygon(buffer_wgs84), name="Tampon 20m").add_to(map_object)
    except Exception as e:
        st.error(f"Erreur dans le calcul du tampon : {str(e)}")

    # Vérification des intersections
    point_in_buffer = False
    route_name = None
    
    for feature in geojson_data['features']:
        geom = shape(feature['geometry'])
        geom_wgs84 = transform(transformer_buffer.transform, geom)
        if geom_wgs84.intersects(buffer_wgs84):
            point_in_buffer = True
            route_name = feature['properties'].get('name')
            break

    # Affichage final
    st_folium(map_object, width=800, height=600)
    
    if point_in_buffer:
        st.success(f"Point proche d'une route{f' : {route_name}' if route_name else ''}")
    else:
        st.warning("Le point n'est pas proche d'une route")

else:
    st.info("Veuillez téléverser un fichier GeoJSON pour commencer")
