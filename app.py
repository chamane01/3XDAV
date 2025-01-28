import streamlit as st
import overpy
import geojson
import pandas as pd
import folium
from streamlit_folium import folium_static
import json

# Fonction pour récupérer les routes nationales via l'API Overpass
def download_national_roads(south_lat, west_lon, north_lat, east_lon):
    # Connexion à l'API Overpass
    api = overpy.Overpass()

    # Requête Overpass pour récupérer les routes principales, secondaires et tertiaires
    query = f"""
    way["highway"="primary"]({south_lat}, {west_lon}, {north_lat}, {east_lon});
    way["highway"="secondary"]({south_lat}, {west_lon}, {north_lat}, {east_lon});
    way["highway"="tertiary"]({south_lat}, {west_lon}, {north_lat}, {east_lon});
    node(w);
    out ids qt;
    """

    # Carte pour afficher l'emprise
    map_center = [(south_lat + north_lat) / 2, (west_lon + east_lon) / 2]  # Calcul du centre de la zone
    m = folium.Map(location=map_center, zoom_start=13)

    # Ajouter un rectangle pour visualiser l'emprise
    folium.Rectangle(
        bounds=[(south_lat, west_lon), (north_lat, east_lon)],
        color='blue',
        weight=2,
        opacity=0.5
    ).add_to(m)

    # Affichage de la carte avec Streamlit
    st.write("Visualisation de l'emprise de la zone géographique.")
    folium_static(m)  # Utilisation de folium_static pour afficher la carte

    # Essayer de récupérer les données avec Overpass
    try:
        # Exécuter la requête
        result = api.query(query)
        
        # Vérifier si des données ont été récupérées
        if len(result.ways) == 0:
            st.write("Aucune route nationale trouvée dans cette zone.")
            return

        st.write(f"Données récupérées: {len(result.ways)} routes trouvées.")
        
        # Créer un tableau avec les données des routes
        routes_data = []
        for way in result.ways:
            # Ajouter le nom de la route si disponible
            name = way.tags.get('name', 'Inconnu')
            routes_data.append({
                'ID': way.id,
                'Nom': name,
                'Nœuds': len(way.nodes)  # Nombre de nœuds (points) dans la route
            })

        # Convertir les données en DataFrame pandas
        df = pd.DataFrame(routes_data)
        st.write(df)  # Afficher le tableau des routes

        # Estimation de la taille du fichier (en octets)
        estimated_size = len(json.dumps(result))  # Estimation de la taille en octets (version JSON de la réponse)
        estimated_size_kb = estimated_size / 1024  # Convertir en Ko
        st.write(f"Estimation de la taille du fichier: {estimated_size_kb:.2f} Ko")

        # Demander confirmation avant téléchargement
        if st.button("Télécharger les données"):
            # Exporter les données au format CSV
            csv_file = df.to_csv(index=False)
            st.download_button(
                label="Télécharger les données CSV",
                data=csv_file,
                file_name="national_roads.csv",
                mime="text/csv"
            )

            # Convertir en GeoJSON
            features = []
            for way in result.ways:
                coordinates = [(node.lon, node.lat) for node in way.nodes]
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates
                    },
                    "properties": {
                        "ID": way.id,
                        "Nom": way.tags.get('name', 'Inconnu')
                    }
                })

            geojson_data = geojson.FeatureCollection(features)

            # Exporter les données GeoJSON
            geojson_file = geojson.dumps(geojson_data)
            st.download_button(
                label="Télécharger les données GeoJSON",
                data=geojson_file,
                file_name="national_roads.geojson",
                mime="application/geo+json"
            )

    except Exception as e:
        st.error(f"Une erreur est survenue : {e}")

# Interface Streamlit pour entrer les coordonnées de la zone
st.title("Télécharger les routes nationales")

# Formulaire pour définir l'emprise de la zone (latitude et longitude)
south_lat = st.number_input("Latitude Sud", value=5.25, step=0.01)
west_lon = st.number_input("Longitude Ouest", value=-4.05, step=0.01)
north_lat = st.number_input("Latitude Nord", value=5.30, step=0.01)
east_lon = st.number_input("Longitude Est", value=-3.95, step=0.01)

# Bouton pour télécharger les données avec la zone définie
if st.button("Télécharger les routes nationales"):
    download_national_roads(south_lat, west_lon, north_lat, east_lon)
