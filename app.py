import streamlit as st
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
import numpy as np
import matplotlib.pyplot as plt
from pyproj import Proj, transform

# Titre de l'application
st.title("Calculateur de volumes à partir d'un DEM avec emprise polygonale (EPSG:4326)")

# Importer un fichier DEM
uploaded_file = st.file_uploader("Téléchargez un fichier DEM (GeoTIFF uniquement) :", type=["tif", "tiff"])

if uploaded_file:
    # Charger le DEM
    with rasterio.open(uploaded_file) as src:
        dem_data = src.read(1)  # Lire la première bande
        dem_data[dem_data == src.nodata] = np.nan  # Gérer les valeurs no_data
        profile = src.profile

        # Reprojeter le DEM vers EPSG:4326
        dst_crs = "EPSG:4326"
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        profile.update({
            "crs": dst_crs,
            "transform": transform,
            "width": width,
            "height": height
        })
        
        reprojected_dem = np.empty((height, width), dtype=dem_data.dtype)
        reproject(
            source=dem_data,
            destination=reprojected_dem,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear
        )

    st.success("Fichier DEM chargé et reprojeté en EPSG:4326 avec succès !")

    # Afficher les métadonnées reprojetées
    st.write("**Système de coordonnées :** EPSG:4326")
    st.write("**Dimensions du DEM reprojeté :**", reprojected_dem.shape)
    st.write("**Transformation :**", transform)

    # Afficher le DEM reprojeté sous forme d'image
    st.subheader("Aperçu du DEM (EPSG:4326)")
    fig, ax = plt.subplots()
    bounds = rasterio.transform.array_bounds(height, width, transform)
    cax = ax.imshow(
        reprojected_dem,
        cmap="terrain",
        extent=(bounds[0], bounds[2], bounds[1], bounds[3])
    )
    fig.colorbar(cax, ax=ax, label="Altitude (mètres)")
    st.pyplot(fig)

    # Définir une emprise polygonale
    st.subheader("Définir l'emprise polygonale pour le calcul")
    st.markdown("**Entrez les coordonnées d'un polygone (en WGS 84 - EPSG:4326)**")

    # Entrée des coordonnées du polygone
    coordinates = st.text_area(
        "Entrez les sommets du polygone (format : 'lon1,lat1; lon2,lat2; ...') :",
        placeholder="Exemple : -3.5,5.3; -3.4,5.4; -3.5,5.5; ..."
    )

    if coordinates:
        try:
            # Parsing des coordonnées
            polygon_coords = [
                tuple(map(float, coord.strip().split(",")))
                for coord in coordinates.split(";")
            ]

            # Calcul de l'emprise raster pour le polygone
            from shapely.geometry import Polygon
            from rasterio.features import geometry_window

            polygon_geom = Polygon(polygon_coords)
            window = geometry_window(reprojected_dem, [polygon_geom], transform=transform)
            windowed_dem = reprojected_dem[window.row_off:window.row_off+window.height, 
                                           window.col_off:window.col_off+window.width]

            # Affichage de la zone sélectionnée
            st.subheader("Zone découpée")
            fig, ax = plt.subplots()
            ax.imshow(
                windowed_dem,
                cmap="terrain",
                extent=(polygon_geom.bounds[0], polygon_geom.bounds[2], polygon_geom.bounds[1], polygon_geom.bounds[3])
            )
            st.pyplot(fig)

            # Choisir une altitude de référence
            st.subheader("Calcul du volume")
            reference_altitude = st.number_input(
                "Altitude de référence (mètres) :", value=0.0, step=0.1, format="%.1f"
            )

            if st.button("Calculer le volume"):
                # Calculer les volumes pour la zone sélectionnée
                cell_area = profile["transform"][0] * abs(profile["transform"][4])  # Surface d'une cellule
                above_reference = np.nansum(
                    (windowed_dem - reference_altitude)[windowed_dem > reference_altitude]
                ) * cell_area
                below_reference = np.nansum(
                    (reference_altitude - windowed_dem)[windowed_dem < reference_altitude]
                ) * cell_area

                # Résultats
                st.write(f"**Volume au-dessus de l'altitude de référence :** {above_reference:.2f} m³")
                st.write(f"**Volume en dessous de l'altitude de référence :** {below_reference:.2f} m³")
                st.write(
                    f"**Volume net (différence) :** {above_reference - below_reference:.2f} m³"
                )
        except Exception as e:
            st.error(f"Erreur dans le traitement des coordonnées : {e}")
