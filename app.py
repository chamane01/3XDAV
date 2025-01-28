import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import Point, Polygon
import pyproj
import json

def reproject_to_utm(gdf):
    # Reprojetter le GeoDataFrame en UTM (zone automatique basée sur les données)
    centroid = gdf.geometry.unary_union.centroid
    utm_zone = int((centroid.x + 180) // 6) + 1
    utm_crs = f"EPSG:{326 if centroid.y >= 0 else 327}{utm_zone}"
    return gdf.to_crs(utm_crs)

def create_buffer(gdf, distance):
    # Créer une zone tampon autour des géométries
    return gdf.buffer(distance)

def check_point_proximity(point, gdf, buffer_gdf):
    # Vérifier si le point est proche des routes
    result = []
    for idx, row in gdf.iterrows():
        if point.within(row.geometry):
            result.append((row['ID'], row.get('name', 'N/A'), row.get('classe', 'N/A')))
        elif point.within(buffer_gdf.iloc[idx]):
            result.append((row['ID'], row.get('name', 'N/A'), row.get('classe', 'N/A')))
    return result

def display_geojson(file):
    # Charger le fichier GeoJSON
    geojson_data = json.load(file)

    # Créer un GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])

    # Reprojeter en UTM
    gdf = reproject_to_utm(gdf)

    # Créer une zone tampon de 10m
    buffer_gdf = create_buffer(gdf, 10)

    # Créer une carte Folium centrée sur les coordonnées du fichier GeoJSON
    m = folium.Map(location=[gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()], zoom_start=12)

    # Ajouter le GeoJSON original à la carte
    folium.GeoJson(
        gdf.to_crs("EPSG:4326").to_json(),
        name="Routes",
        tooltip=folium.GeoJsonTooltip(fields=['ID', 'name', 'classe'], aliases=['ID', 'Nom', 'Classe']),
    ).add_to(m)

    # Ajouter les tampons à la carte
    folium.GeoJson(
        gpd.GeoDataFrame(geometry=buffer_gdf).to_crs("EPSG:4326").to_json(),
        name="Zones Tampons",
        style_function=lambda x: {
            "fillColor": "blue",
            "color": "blue",
            "weight": 1,
            "fillOpacity": 0.2,
        },
    ).add_to(m)

    return m, gdf, buffer_gdf

# Interface Streamlit
st.title("Analyse GeoJSON avec Tampon et Recherche de Proximité")

# Téléversement du fichier GeoJSON
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON", type="geojson")

if uploaded_file:
    st.write("Fichier chargé avec succès !")

    # Afficher la carte interactive avec tampons
    st.subheader("Carte dynamique")
    map_object, gdf, buffer_gdf = display_geojson(uploaded_file)
    st_data = st_folium(map_object, width=700, height=500)

    # Saisie manuelle des coordonnées
    st.subheader("Vérification de la proximité")
    col1, col2 = st.columns(2)
    with col1:
        latitude = st.number_input("Latitude", format="%.6f")
    with col2:
        longitude = st.number_input("Longitude", format="%.6f")

    if latitude and longitude:
        point = Point(longitude, latitude)
        point_gdf = gpd.GeoSeries([point], crs="EPSG:4326").to_crs(gdf.crs)
        proximity_results = check_point_proximity(point_gdf.iloc[0], gdf, buffer_gdf)

        if proximity_results:
            st.write("Le point est proche des routes suivantes :")
            for res in proximity_results:
                st.write(f"- ID: {res[0]}, Nom: {res[1]}, Classe: {res[2]}")
        else:
            st.write("Le point n'est proche d'aucune route.")
