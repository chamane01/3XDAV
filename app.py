import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Point

st.title("Visualiseur de routes avec analyse de proximité")

# Téléversement du fichier GeoJSON
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON de routes", type="geojson")

if uploaded_file:
    # Chargement et préparation des données
    try:
        # Lecture du GeoJSON
        gdf = gpd.read_file(uploaded_file)
        
        # Vérification du système de coordonnées
        if gdf.crs is None:
            gdf.set_crs(epsg=4326, inplace=True)
        else:
            gdf = gdf.to_crs(epsg=4326)
        
        # Reprojection en UTM 32630 pour les calculs
        gdf_utm = gdf.to_crs(epsg=32630)
        
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier: {e}")
        st.stop()

    st.success("Fichier chargé avec succès !")

    # Saisie des coordonnées UTM
    st.subheader("Saisie des coordonnées du point")
    col1, col2 = st.columns(2)
    with col1:
        easting = st.number_input("Easting (UTM 32630)", value=535157.0)
    with col2:
        northing = st.number_input("Northing (UTM 32630)", value=1556627.0)

    # Conversion des coordonnées et analyse
    if easting and northing:
        try:
            # Conversion UTM vers WGS84
            transformer = Transformer.from_crs("EPSG:32630", "EPSG:4326")
            lon, lat = transformer.transform(easting, northing)
            
            # Création des géométries pour analyse
            point_utm = Point(easting, northing)
            buffer_utm = point_utm.buffer(20)
            
            # Recherche des routes dans la zone tampon
            routes_proches = gdf_utm[gdf_utm.intersects(buffer_utm)]
            
        except Exception as e:
            st.error(f"Erreur de traitement: {e}")
            st.stop()

        # Affichage des résultats
        st.subheader("Résultats de l'analyse")
        if not routes_proches.empty:
            st.success("**Le point est à moins de 20 mètres d'une route !**")
            
            # Affichage des propriétés des routes concernées
            for idx, route in routes_proches.iterrows():
                proprietes = {k: v for k, v in route.items() if k != 'geometry'}
                st.write(f"**Route {idx + 1}:**")
                st.json(proprietes)
        else:
            st.error("Aucune route dans un rayon de 20 mètres")

    # Création de la carte
    m = folium.Map(location=[lat if 'lat' in locals() else 45, 
                            lon if 'lon' in locals() else 3], 
                  zoom_start=15)

    # Ajout des routes
    folium.GeoJson(
        gdf,
        name='Routes',
        tooltip=folium.GeoJsonTooltip(fields=list(gdf.columns)),
        style_function=lambda x: {'color': 'darkgreen', 'weight': 3}
    ).add_to(m)

    # Ajout du point et de la zone tampon
    if easting and northing and 'lat' in locals():
        # Marqueur du point
        folium.Marker(
            [lat, lon],
            popup="Point saisi",
            icon=folium.Icon(color='red', icon='map-marker')
        ).add_to(m)
        
        # Zone tampon
        folium.Circle(
            location=[lat, lon],
            radius=20,
            color='blue',
            fill=True,
            fill_opacity=0.2,
            popup="Zone tampon 20m"
        ).add_to(m)

        # Ajustement de la vue
        m.fit_bounds([[lat, lon], [lat, lon]])

    # Affichage de la carte
    st.subheader("Visualisation cartographique")
    st_folium(m, width=700, height=500)

else:
    st.info("Veuillez téléverser un fichier GeoJSON contenant des routes")
