import streamlit as st
import rasterio
import geopandas as gpd
import numpy as np
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
from shapely.geometry import shape, box
from rasterio.mask import mask

# Titre de l'application
st.title("Calculateur de volumes à partir d'un DEM avec emprises polygonales")

# Importer un fichier DEM
uploaded_dem = st.file_uploader("Téléchargez un fichier DEM (GeoTIFF uniquement) :", type=["tif", "tiff"])

# Importer une polygonale
uploaded_polygon = st.file_uploader("Téléchargez une polygonale (GeoJSON uniquement) :", type=["geojson"])

if uploaded_dem:
    # Charger le DEM
    with rasterio.open(uploaded_dem) as src:
        dem_data = src.read(1)
        dem_data[dem_data == src.nodata] = np.nan
        profile = src.profile
        bounds = src.bounds

    st.success("Fichier DEM chargé avec succès !")

    # Afficher les métadonnées
    st.write("**Dimensions du DEM :**", dem_data.shape)
    st.write("**Résolution :**", profile["transform"][0], "unités par pixel")
    st.write("**Bornes géographiques du DEM :**")
    st.write(f"  - Min Longitude : {bounds.left}, Max Longitude : {bounds.right}")
    st.write(f"  - Min Latitude : {bounds.bottom}, Max Latitude : {bounds.top}")

    # Charger la polygonale si disponible
    if uploaded_polygon:
        gdf = gpd.read_file(uploaded_polygon)

        # Reprojection si nécessaire
        if gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        st.success("Polygonale chargée avec succès !")

        # Vérifier le chevauchement
        raster_bounds = box(bounds.left, bounds.bottom, bounds.right, bounds.top)
        polygons = [shape(geom) for geom in gdf.geometry]
        if not any(raster_bounds.intersects(polygon) for polygon in polygons):
            st.error("Les polygonales ne chevauchent pas le DEM. Vérifiez les fichiers ou les coordonnées.")
        else:
            # Masquer le DEM avec les polygonales
            with rasterio.open(uploaded_dem) as src:
                out_image, out_transform = mask(src, polygons, crop=True)
                out_image[out_image == src.nodata] = np.nan

            # Afficher la zone découpée
            st.subheader("Zone découpée")
            fig, ax = plt.subplots()
            ax.imshow(out_image[0], cmap="terrain")
            st.pyplot(fig)

            # Calcul du volume
            st.subheader("Calcul du volume")
            reference_altitude = st.number_input(
                "Altitude de référence (mètres) :", value=0.0, step=0.1, format="%.1f"
            )

            if st.button("Calculer le volume"):
                cell_area = profile["transform"][0] * abs(profile["transform"][4])
                above_reference = np.nansum(
                    (out_image[0] - reference_altitude)[out_image[0] > reference_altitude]
                ) * cell_area
                below_reference = np.nansum(
                    (reference_altitude - out_image[0])[out_image[0] < reference_altitude]
                ) * cell_area

                # Résultats
                st.write(f"**Volume au-dessus de l'altitude de référence :** {above_reference:.2f} m³")
                st.write(f"**Volume en dessous de l'altitude de référence :** {below_reference:.2f} m³")
                st.write(f"**Volume net (différence) :** {above_reference - below_reference:.2f} m³")

    else:
        # Carte pour définir une emprise si aucune polygonale n'est téléchargée
        st.subheader("Définir une emprise polygonale")
        m = folium.Map(location=[(bounds.top + bounds.bottom) / 2, (bounds.left + bounds.right) / 2], zoom_start=10)

        draw = Draw(export=True)
        draw.add_to(m)

        output = st_folium(m, width=700, height=500)

        if output["last_active_drawing"]:
            geojson = output["last_active_drawing"]["geometry"]
            st.write("Emprise polygonale sélectionnée :")
            st.json(geojson)

            polygon = shape(geojson)

            with rasterio.open(uploaded_dem) as src:
                out_image, out_transform = mask(src, [polygon], crop=True)
                out_image[out_image == src.nodata] = np.nan

            st.subheader("Zone découpée")
            fig, ax = plt.subplots()
            ax.imshow(out_image[0], cmap="terrain")
            st.pyplot(fig)

            st.subheader("Calcul du volume")
            reference_altitude = st.number_input(
                "Altitude de référence (mètres) :", value=0.0, step=0.1, format="%.1f"
            )

            if st.button("Calculer le volume"):
                cell_area = profile["transform"][0] * abs(profile["transform"][4])
                above_reference = np.nansum(
                    (out_image[0] - reference_altitude)[out_image[0] > reference_altitude]
                ) * cell_area
                below_reference = np.nansum(
                    (reference_altitude - out_image[0])[out_image[0] < reference_altitude]
                ) * cell_area

                st.write(f"**Volume au-dessus de l'altitude de référence :** {above_reference:.2f} m³")
                st.write(f"**Volume en dessous de l'altitude de référence :** {below_reference:.2f} m³")
                st.write(f"**Volume net (différence) :** {above_reference - below_reference:.2f} m³")
