import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, mapping
from shapely.ops import transform
import pyproj

# Fonction pour charger un GeoJSON
def load_geojson(file):
    try:
        return json.load(file)
    except json.JSONDecodeError:
        st.error("Erreur : Le fichier téléversé n'est pas un GeoJSON valide.")
        return None

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
        # Chargement des routes en UTM
        routes_utm = []
        for feature in routes_geojson["features"]:
            geom_wgs84 = shape(feature["geometry"])
            geom_utm = transform(transformer_to_utm.transform, geom_wgs84)
            route_name = feature["properties"].get("name", "Inconnue")  # Assurez-vous que 'name' est bien la clé du nom de route
            routes_utm.append((geom_utm, route_name))
        
        # Création du nouveau GeoJSON modifié
        new_sections_geojson = {"type": "FeatureCollection", "features": []}
        
        # Analyse des sections et attribution du nom de la route
        for section in sections_geojson["features"]:
            section_geom_wgs84 = shape(section["geometry"])
            section_geom_utm = transform(transformer_to_utm.transform, section_geom_wgs84)
            
            # Création d'un tampon de 20m
            buffer_utm = section_geom_utm.buffer(20)
            
            # Recherche de la route la plus proche
            closest_route_name = "Inconnue"
            for route_geom, route_name in routes_utm:
                if route_geom.intersects(buffer_utm):
                    closest_route_name = route_name
                    break
            
            # Modification de l'ID avec le nom de la route
            section["properties"]["ID"] = closest_route_name
            new_sections_geojson["features"].append(section)
        
        # Téléchargement du nouveau fichier GeoJSON
        st.subheader("Télécharger le GeoJSON modifié")
        new_geojson_str = json.dumps(new_sections_geojson, indent=2)
        st.download_button(
            label="Télécharger le fichier modifié",
            data=new_geojson_str,
            file_name="sections_modifiees.geojson",
            mime="application/json"
        )
        
        # Affichage de la carte
        m = folium.Map(location=[0, 0], zoom_start=2)
        folium.GeoJson(new_sections_geojson, name="Sections Modifiées").add_to(m)
        st_folium(m, width=800, height=600)
else:
    st.write("Veuillez téléverser les fichiers GeoJSON des routes et sections.")
