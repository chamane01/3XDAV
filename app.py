import streamlit as st
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
import folium
from streamlit_folium import st_folium
from shapely.geometry import shape
from rasterio.mask import mask
import geopandas as gpd
import matplotlib.pyplot as plt

# Titre de l'application
st.title("Calculateur de volumes à partir d'un DEM et d'une emprise polygonale")

# Téléchargement du fichier DEM
uploaded_dem = st.file_uploader("Téléchargez un fichier DEM (GeoTIFF uniquement) :", type=["tif", "tiff"])

# Téléchargement d'une emprise polygonale (GeoJSON, Shapefile, etc.)
uploaded_polygon = st.file_uploader("Téléchargez une emprise polygonale (GeoJSON ou Shapefile) :", type=["geojson", "zip"])

if uploaded_dem and uploaded_polygon:
    # Charger le DEM et reprojeter en EPSG:4326
    with rasterio.open(uploaded_dem) as src:
        profile = src.profile
        dst_crs = "EPSG:4326"  # Système de coordonnées cible
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        profile.update({
            "crs": dst_crs,
            "transform": transform,
            "width": width,
            "height": height
        })
        
        with rasterio.MemoryFile() as memfile:
            with memfile.open(**profile) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=dst_crs,
                        resampling=Resampling.nearest
                    )
                dem_data = dst.read(1)
                dem_data[dem_data == src.nodata] = np.nan

    # Charger la polygonale
    if uploaded_polygon.name.endswith(".zip"):
        gdf = gpd.read_file(f"zip://{uploaded_polygon}")
    else:
        gdf = gpd.read_file(uploaded_polygon)

    if gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")

    st.success("Fichiers chargés et reprojetés avec succès !")

    # Masquer le DEM en fonction de l'emprise
    polygons = [shape(geom) for geom in gdf.geometry]
    with rasterio.open(uploaded_dem) as src:
        out_image, out_transform = mask(src, polygons, crop=True)
        out_image[out_image == src.nodata] = np.nan

    # Afficher la zone découpée
    st.subheader("Zone découpée")
    fig, ax = plt.subplots()
    ax.imshow(out_image[0], cmap="terrain")
    st.pyplot(fig)

    # Entrée de l'altitude de référence
    reference_altitude = st.number_input("Altitude de référence (mètres) :", value=0.0, step=0.1)

    if st.button("Calculer le volume"):
        # Calcul des volumes
        cell_area = abs(profile["transform"][0]) * abs(profile["transform"][4])
        above_reference = np.nansum((out_image[0] - reference_altitude)[out_image[0] > reference_altitude]) * cell_area
        below_reference = np.nansum((reference_altitude - out_image[0])[out_image[0] < reference_altitude]) * cell_area

        # Résultats
        st.write(f"**Volume au-dessus de l'altitude de référence :** {above_reference:.2f} m³")
        st.write(f"**Volume en dessous de l'altitude de référence :** {below_reference:.2f} m³")
        st.write(f"**Volume net (différence) :** {above_reference - below_reference:.2f} m³")
