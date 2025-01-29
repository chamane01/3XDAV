import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point, mapping
from shapely.ops import transform
import pyproj

# Fonction pour charger et afficher un GeoJSON
def load_geojson(file):
    try:
        return json.load(file)
    except json.JSONDecodeError:
        st.error("Erreur : Le fichier téléversé n'est pas un GeoJSON valide.")
        return None

# Fonction pour convertir les géométries en UTM
def convert_to_utm(geometry, transformer):
    return transform(transformer.transform, geometry)

# Définition des systèmes de coordonnées
utm_zone = 32630  # EPSG:32630 (Zone UTM 30N)
utm_crs = pyproj.CRS(f"EPSG:{utm_zone}")
wgs84_crs = pyproj.CRS("EPSG:4326")
transformer_to_utm = pyproj.Transformer.from_crs(wgs84_crs, utm_crs, always_xy=True)
transformer_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)

# Interface Streamlit
st.title("Analyse de proximité des sections de route")

# Téléversement des fichiers GeoJSON
route_file = st.file_uploader("Téléverser le fichier GeoJSON des routes", type="geojson")
section_file = st.file_uploader("Téléverser le fichier GeoJSON des sections de route", type="geojson")

if route_file and section_file:
    routes_geojson = load_geojson(route_file)
    sections_geojson = load_geojson(section_file)
    
    if routes_geojson and sections_geojson:
        # Création de la carte
        m = folium.Map(location=[0, 0], zoom_start=2)
        
        # Chargement des routes en UTM
        routes_utm = []
        for feature in routes_geojson["features"]:
            geom_wgs84 = shape(feature["geometry"])
            geom_utm = convert_to_utm(geom_wgs84, transformer_to_utm)
            route_name = list(feature["properties"].values())[1]  # Colonne du milieu
            routes_utm.append((geom_utm, route_name))
            folium.GeoJson(feature["geometry"], tooltip=route_name).add_to(m)
        
        # Analyse des sections
        st.subheader("Résultats de l'analyse")
        results = []
        for section in sections_geojson["features"]:
            section_geom_wgs84 = shape(section["geometry"])
            section_geom_utm = convert_to_utm(section_geom_wgs84, transformer_to_utm)
            
            # Recherche de la route la plus proche avec un rayon progressif
            found = False
            for radius in [10, 50, 100, 200, 500, 1000]:
                buffer_utm = section_geom_utm.buffer(radius)
                
                for route_geom, route_name in routes_utm:
                    if route_geom.intersects(buffer_utm):
                        results.append(f"Section trouvée à {radius}m de la route : {route_name}")
                        found = True
                        break
                if found:
                    break
            
            if not found:
                results.append("Aucune route trouvée dans un rayon de 1km")
        
        # Affichage des résultats
        for res in results:
            st.write(res)
        
        # Affichage de la carte
        st_folium(m, width=800, height=600)
else:
    st.write("Veuillez téléverser les fichiers GeoJSON des routes et sections.")
