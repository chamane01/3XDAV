import streamlit as st
import geopandas as gpd
from shapely.geometry import Polygon, LineString
import matplotlib.pyplot as plt
import numpy as np


def generate_lots(polygon, lot_size, road_width, buffer_distance, lot_shape="rectangle"):
    """
    Génère des lots dans une polygonale en tenant compte des servitudes et des routes.
    polygon : Shapely Polygon
    lot_size : Surface d'un lot en m²
    road_width : Largeur des routes entre les lots
    buffer_distance : Servitude à appliquer en bordure
    lot_shape : Forme préférée des lots ("rectangle" ou "carré")
    """
    # Appliquer la servitude en bordure
    buffered_polygon = polygon.buffer(-buffer_distance)

    # Calculer les dimensions des lots (approximatif)
    lot_side = (lot_size ** 0.5) if lot_shape == "carré" else (lot_size / 20)
    lots = []
    minx, miny, maxx, maxy = buffered_polygon.bounds

    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            # Créer un lot
            lot = Polygon([
                (x, y),
                (x + lot_side, y),
                (x + lot_side, y + lot_side),
                (x, y + lot_side),
                (x, y)
            ])

            # Ajouter le lot s'il est dans la zone
            if buffered_polygon.contains(lot):
                lots.append(lot)

            # Avancer dans la grille
            y += lot_side + road_width
        x += lot_side + road_width

    return lots


# Interface Streamlit
st.title("Application de morcellement pour lotissement")

# Chargement de la polygonale
uploaded_file = st.file_uploader("Téléchargez un fichier GeoJSON ou Shapefile", type=["geojson", "shp"])

if uploaded_file:
    # Charger le fichier avec GeoPandas
    try:
        gdf = gpd.read_file(uploaded_file)
        st.success("Fichier chargé avec succès.")
        st.write(gdf)
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier : {e}")
        st.stop()

    # Sélection des paramètres
    lot_size = st.number_input("Superficie d'un lot (m²)", min_value=1.0, value=500.0)
    road_width = st.number_input("Largeur des voies (m)", min_value=0.0, value=8.0)
    buffer_distance = st.number_input("Servitude aux bordures (m)", min_value=0.0, value=5.0)
    lot_shape = st.selectbox("Forme des lots", ["rectangle", "carré"])

    # Sélectionner un polygone
    selected_polygon_index = st.selectbox("Sélectionnez un polygone à morceler", gdf.index)
    polygon = gdf.iloc[selected_polygon_index].geometry

    # Générer les lots
    if st.button("Lancer le morcellement"):
        lots = generate_lots(polygon, lot_size, road_width, buffer_distance, lot_shape)
        lots_gdf = gpd.GeoDataFrame(geometry=lots)

        # Visualiser les résultats
        st.subheader("Résultats du morcellement")
        fig, ax = plt.subplots(figsize=(10, 10))
        lots_gdf.plot(ax=ax, edgecolor="black", facecolor="cyan", alpha=0.5)
        gpd.GeoSeries([polygon]).plot(ax=ax, edgecolor="red", facecolor="none")
        st.pyplot(fig)

        # Export des résultats
        lots_gdf.to_file("morcellement.geojson", driver="GeoJSON")
        st.download_button("Télécharger le fichier morcelé (GeoJSON)",
                           data=open("morcellement.geojson", "rb"),
                           file_name="morcellement.geojson",
                           mime="application/json")
