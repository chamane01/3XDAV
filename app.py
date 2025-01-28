import streamlit as st
import folium
from streamlit_folium import st_folium
import json

def display_geojson(file):
    # Charger le fichier GeoJSON
    geojson_data = json.load(file)

    # Créer une carte Folium centrée sur les coordonnées du fichier GeoJSON
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Ajouter le GeoJSON à la carte avec une fonction de popup pour afficher les informations
    folium.GeoJson(
        geojson_data,
        name="GeoJSON",
        tooltip=folium.GeoJsonTooltip(fields=list(geojson_data['features'][0]['properties'].keys()), aliases=list(geojson_data['features'][0]['properties'].keys())),
        popup=folium.GeoJsonPopup(fields=list(geojson_data['features'][0]['properties'].keys()))
    ).add_to(m)

    return m

# Interface Streamlit
st.title("Visualiseur de fichiers GeoJSON")

# Téléversement du fichier GeoJSON
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON", type="geojson")

if uploaded_file:
    st.write("Fichier chargé avec succès !")

    # Afficher la carte interactive
    st.subheader("Carte dynamique")
    map_object = display_geojson(uploaded_file)
    st_data = st_folium(map_object, width=700, height=500)

    # Afficher les propriétés lorsque l'utilisateur clique sur une entité
    st.subheader("Informations sur l'entité sélectionnée")
    if st_data and st_data['last_active_drawing']:  # Vérifier si une entité a été cliquée
        st.json(st_data['last_active_drawing'])
    else:
        st.write("Cliquez sur une entité pour afficher ses informations.")
