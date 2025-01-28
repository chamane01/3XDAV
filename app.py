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

def safe_property_access(properties, key):
    """Accès sécurisé aux propriétés avec valeur par défaut"""
    return properties.get(key, 'N/A')

def display_geojson(file):
    geojson_data = json.load(file)
    
    # Créer une carte centrée
    m = folium.Map(location=[0, 0], zoom_start=2)
    
    # Préparation des features avec propriétés sécurisées
    processed_features = []
    target_id = 'way/68486464354'

    for feature in geojson_data['features']:
        # Copie profonde avec propriétés sécurisées
        new_feature = copy.deepcopy(feature)
        props = new_feature['properties']
        
        # Ajout des propriétés manquantes avec valeurs par défaut
        props.setdefault('is_duplicate', False)
        props.setdefault('ID', 'N/A')
        props.setdefault('highway', 'Inconnu')
        props.setdefault('lanes', 'N/A')
        props.setdefault('surface', 'N/A')
        
        processed_features.append(new_feature)

        # Création du doublon si ID correspond
        if props.get('ID') == target_id:
            duplicated = copy.deepcopy(new_feature)
            duplicated['properties']['is_duplicate'] = True
            processed_features.append(duplicated)

    # Fonction de style sécurisée
    def style_function(feature):
        if feature['properties'].get('is_duplicate', False):
            return {
                'color': generate_color_from_id(feature['properties']['ID']),
                'weight': 4,
                'opacity': 0.7
            }
        return {'color': '#3388ff', 'weight': 2, 'opacity': 0.5}

    # Tooltip personnalisé avec gestion des valeurs manquantes
    class SafeTooltip(folium.GeoJsonTooltip):
        def render(self, **kwargs):
            for field in self.fields:
                self.labels.append(field if field != 'is_duplicate' else 'Duplicate')
            super().render(**kwargs)

    # Affichage du GeoJSON
    folium.GeoJson(
        {'type': 'FeatureCollection', 'features': processed_features},
        name="Routes",
        style_function=style_function,
        tooltip=SafeTooltip(
            fields=['ID', 'highway', 'lanes', 'surface', 'is_duplicate'],
            aliases=['ID', 'Type', 'Voies', 'Surface', 'Doublon'],
            localize=True
        ),
        popup=folium.GeoJsonPopup(
            fields=['ID', 'highway', 'lanes', 'surface'],
            aliases=['ID', 'Type', 'Voies', 'Surface'],
            localize=True
        )
    ).add_to(m)

    return geojson_data, m

# Configuration de la page Streamlit
st.title("Analyse de proximité avec des routes (avec projections UTM)")
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON des routes", type="geojson")

# Section de saisie des coordonnées UTM
st.subheader("Saisissez les coordonnées UTM (Zone 30N)")
easting = st.number_input("Easting (X)", value=500000, step=1)
northing = st.number_input("Northing (Y)", value=4500000, step=1)

# Systèmes de coordonnées
utm_crs = pyproj.CRS("EPSG:32630")
wgs84_crs = pyproj.CRS("EPSG:4326")
transformer_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)
transformer_to_utm = pyproj.Transformer.from_crs(wgs84_crs, utm_crs, always_xy=True)

# Conversion des coordonnées
longitude, latitude = transformer_to_wgs84.transform(easting, northing)
point_utm = Point(easting, northing)

if uploaded_file:
    geojson_data, map_object = display_geojson(uploaded_file)
    
    # Ajout des éléments cartographiques
    folium.Marker([latitude, longitude], popup=f"Point saisi: {longitude:.6f}, {latitude:.6f}").add_to(map_object)
    map_object.location = [latitude, longitude]
    map_object.zoom_start = 15

    # Création et affichage du tampon
    buffer_utm = point_utm.buffer(20)
    buffer_wgs84 = transform(transformer_to_wgs84.transform, buffer_utm)
    folium.GeoJson(mapping(buffer_wgs84), name="Tampon 20m").add_to(map_object)

    # Analyse d'intersection
    intersection_trouvee = False
    for feature in geojson_data['features']:
        geom = transform(transformer_to_utm.transform, shape(feature['geometry']))
        if geom.intersects(buffer_utm):
            intersection_trouvee = True
            break

    st.subheader("Résultats de l'analyse")
    if intersection_trouvee:
        st.success("✅ Le point est à proximité d'une route")
    else:
        st.error("❌ Aucune route à proximité immédiate")

    st_folium(map_object, width=800, height=600)
else:
    st.info("Veuillez téléverser un fichier GeoJSON pour commencer l'analyse.")
