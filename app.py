import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point, mapping
from shapely.ops import transform
import pyproj
import tempfile
import os

# Fonction pour charger et afficher un GeoJSON
def display_geojson(file, color):
    geojson_data = json.load(file)
    m = folium.Map(location=[0, 0], zoom_start=2)
    folium.GeoJson(
        geojson_data,
        name="GeoJSON",
        style_function=lambda x: {"color": color},
        tooltip=folium.GeoJsonTooltip(fields=list(geojson_data['features'][0]['properties'].keys()),
                                      aliases=list(geojson_data['features'][0]['properties'].keys())),
    ).add_to(m)
    return geojson_data, m

# Initialisation de Streamlit
st.title("Analyse de proximité des sections de routes")
route_file = st.file_uploader("Téléverser un fichier GeoJSON des routes", type="geojson")
section_file = st.file_uploader("Téléverser un fichier GeoJSON des sections de route", type="geojson")

# Définition des systèmes de coordonnées
utm_zone = 32630  # EPSG:32630 (Zone UTM 30N)
utm_crs = pyproj.CRS(f"EPSG:{utm_zone}")
wgs84_crs = pyproj.CRS("EPSG:4326")
transformer_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)
transformer_to_utm = pyproj.Transformer.from_crs(wgs84_crs, utm_crs, always_xy=True)

if route_file and section_file:
    routes_geojson, map_object = display_geojson(route_file, "blue")
    sections_geojson, _ = display_geojson(section_file, "red")
    
    updated_features = []
    for section in sections_geojson['features']:
        section_geom_wgs84 = shape(section['geometry'])
        section_geom_utm = transform(transformer_to_utm.transform, section_geom_wgs84)
        closest_route = None
        min_distance = float('inf')
        
        for route in routes_geojson['features']:
            route_geom_wgs84 = shape(route['geometry'])
            route_geom_utm = transform(transformer_to_utm.transform, route_geom_wgs84)
            
            distance = section_geom_utm.distance(route_geom_utm)
            if distance < min_distance:
                min_distance = distance
                closest_route = route['properties'].get(list(route['properties'].keys())[1], 'Nom inconnu')
        
        section['properties'] = {"ID": closest_route}
        updated_features.append(section)
    
    new_geojson = {"type": "FeatureCollection", "features": updated_features}
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson") as tmp_file:
        json.dump(new_geojson, tmp_file)
        tmp_file_path = tmp_file.name
    
    st.download_button(
        label="Télécharger le nouveau fichier GeoJSON",
        data=open(tmp_file_path, "rb").read(),
        file_name="updated_sections.geojson",
        mime="application/json"
    )
    
    st_folium(map_object, width=800, height=600)
else:
    st.write("Veuillez téléverser les fichiers GeoJSON des routes et des sections de route.")
