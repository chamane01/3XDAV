import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, LineString

# Fonction pour charger et afficher un GeoJSON
def display_geojson(file, color):
    geojson_data = json.load(file)
    m = folium.Map(location=[0, 0], zoom_start=2)
    
    for feature in geojson_data["features"]:
        folium.GeoJson(
            feature,
            style_function=lambda x, color=color: {"color": color},
            tooltip=feature["properties"].get("name", "Sans nom")
        ).add_to(m)
    
    return geojson_data, m

# Fonction pour analyser l'appartenance des sections aux routes
def analyze_sections(routes_geojson, sections_geojson):
    results = []
    
    for section in sections_geojson["features"]:
        section_geom = shape(section["geometry"])
        section_name = section["properties"].get("name", "Section inconnue")
        
        for route in routes_geojson["features"]:
            route_geom = shape(route["geometry"])
            route_name = route["properties"].get("name", "Route inconnue")
            
            if section_geom.intersects(route_geom):
                results.append(f"La section '{section_name}' appartient à la route '{route_name}'.")
                break
        else:
            results.append(f"La section '{section_name}' n'appartient à aucune route connue.")
    
    return results

# Interface Streamlit
st.title("Analyse d'appartenance des sections de route")
route_file = st.file_uploader("Téléverser un fichier GeoJSON des routes", type="geojson")
section_file = st.file_uploader("Téléverser un fichier GeoJSON des sections de route", type="geojson")

if route_file and section_file:
    routes_geojson, map_object = display_geojson(route_file, "blue")
    sections_geojson, _ = display_geojson(section_file, "red")
    
    # Afficher les sections sur la carte
    for feature in sections_geojson["features"]:
        folium.GeoJson(
            feature,
            style_function=lambda x: {"color": "red"},
            tooltip=feature["properties"].get("name", "Sans nom")
        ).add_to(map_object)
    
    # Analyse d'appartenance
    results = analyze_sections(routes_geojson, sections_geojson)
    
    # Affichage des résultats
    st.subheader("Résultats de l'analyse")
    for result in results:
        st.write(result)
    
    # Affichage de la carte
    st_folium(map_object, width=800, height=600)
else:
    st.write("Veuillez téléverser les deux fichiers GeoJSON pour analyser.")
