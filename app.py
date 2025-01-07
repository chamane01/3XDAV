import streamlit as st
import rasterio
import geopandas as gpd
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import shape, box
from rasterio.mask import mask
import matplotlib.pyplot as plt
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw

# Titre de l'application
st.title("Calculateur de volumes à partir d'un DEM avec emprises polygonales")

# Fonction pour reprojeter un raster
def reproject_raster_to_epsg4326(src_path, dst_path):
    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, 'EPSG:4326', src.width, src.height, *src.bounds
        )
        profile = src.profile
        profile.update({
            'crs': 'EPSG:4326',
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(dst_path, 'w', **profile) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs='EPSG:4326',
                    resampling=Resampling.nearest
                )

# Téléversement des fichiers
uploaded_dem = st.file_uploader("Téléchargez un fichier DEM (GeoTIFF uniquement) :", type=["tif", "tiff"])
uploaded_polygon = st.file_uploader("Téléchargez une polygonale (GeoJSON uniquement) :", type=["geojson"])

if uploaded_dem:
    st.success("Fichier DEM chargé avec succès !")

    # Reprojection du DEM vers EPSG:4326
    reprojected_dem_path = "reprojected_dem.tif"
    reproject_raster_to_epsg4326(uploaded_dem, reprojected_dem_path)
    
    with rasterio.open(reprojected_dem_path) as src:
        dem_data = src.read(1)
        dem_data[dem_data == src.nodata] = np.nan
        profile = src.profile
        bounds = src.bounds

    st.write("**Dimensions du DEM reprojeté :**", dem_data.shape)
    st.write("**Résolution :**", profile["transform"][0], "unités par pixel")

if uploaded_polygon:
    st.success("Polygonale chargée avec succès !")

    # Charger et reprojeter la polygonale vers EPSG:4326
    gdf = gpd.read_file(uploaded_polygon)
    if gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    
    st.write("**Polygonale reprojetée vers EPSG:4326**")
    st.write(gdf)

    # Vérification du chevauchement
    raster_bounds = box(bounds.left, bounds.bottom, bounds.right, bounds.top)
    polygons = [shape(geom) for geom in gdf.geometry]
    if not any(raster_bounds.intersects(polygon) for polygon in polygons):
        st.error("Les polygonales ne chevauchent pas le DEM. Vérifiez les fichiers ou les coordonnées.")
    else:
        # Masquer le DEM avec les polygonales
        with rasterio.open(reprojected_dem_path) as src:
            out_image, out_transform = mask(src, polygons, crop=True)
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
