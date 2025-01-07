import streamlit as st
import rasterio
import numpy as np
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
from shapely.geometry import shape
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling

# Fonction pour reprojeter un raster dans un nouveau système de coordonnées
def reproject_raster(src, dst_crs):
    transform, width, height = calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds
    )
    profile = src.profile.copy()
    profile.update({
        'crs': dst_crs,
        'transform': transform,
        'width': width,
        'height': height
    })

    data = np.empty((src.count, height, width), dtype=src.dtypes[0])

    for i in range(1, src.count + 1):
        reproject(
            source=rasterio.band(src, i),
            destination=data[i - 1],
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest
        )

    return data, profile

# Titre de l'application
st.title("Calculateur de volumes à partir d'un DEM avec emprises polygonales")

# Importer un fichier DEM
uploaded_file = st.file_uploader("Téléchargez un fichier DEM (GeoTIFF uniquement) :", type=["tif", "tiff"])

if uploaded_file:
    # Charger le DEM
    with rasterio.open(uploaded_file) as src:
        original_crs = src.crs
        dem_data, profile = reproject_raster(src, "EPSG:4326")
        dem_data[dem_data == src.nodata] = np.nan  # Gérer les valeurs no_data
        bounds = rasterio.transform.array_bounds(
            profile['height'], profile['width'], profile['transform']
        )

    st.success("Fichier DEM chargé et reprojeté en EPSG:4326 avec succès !")

    # Afficher les métadonnées
    st.write("**Dimensions du DEM :**", dem_data.shape)
    st.write("**Résolution :**", profile["transform"][0], "unités par pixel")
    st.write("**Bornes géographiques :**")
    st.write(f"  - Min Longitude : {bounds[0]}, Max Longitude : {bounds[2]}")
    st.write(f"  - Min Latitude : {bounds[1]}, Max Latitude : {bounds[3]}")

    # Affichage de la carte pour définir une emprise polygonale
    st.subheader("Définir une emprise polygonale")
    m = folium.Map(location=[(bounds[3] + bounds[1]) / 2, (bounds[2] + bounds[0]) / 2], zoom_start=10)

    # Ajouter l'outil de dessin pour les polygonales
    draw = Draw(export=True)
    draw.add_to(m)

    # Intégrer la carte dans Streamlit
    output = st_folium(m, width=700, height=500)

    # Vérifier si une géométrie a été dessinée
    if output["last_active_drawing"]:
        # Charger la géométrie dessinée
        geojson = output["last_active_drawing"]["geometry"]
        st.write("Emprise polygonale sélectionnée :")
        st.json(geojson)

        # Convertir GeoJSON en géométrie Shapely
        polygon = shape(geojson)

        # Masquer le DEM à l'aide de la géométrie
        with rasterio.open(uploaded_file) as src:
            out_image, out_transform = mask(src, [polygon], crop=True)
            out_image[out_image == src.nodata] = np.nan

        # Afficher la zone découpée
        st.subheader("Zone découpée")
        fig, ax = plt.subplots()
        ax.imshow(out_image[0], cmap="terrain")
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
                (out_image[0] - reference_altitude)[out_image[0] > reference_altitude]
            ) * cell_area
            below_reference = np.nansum(
                (reference_altitude - out_image[0])[out_image[0] < reference_altitude]
            ) * cell_area

            # Résultats
            st.write(f"**Volume au-dessus de l'altitude de référence :** {above_reference:.2f} m³")
            st.write(f"**Volume en dessous de l'altitude de référence :** {below_reference:.2f} m³")
            st.write(
                f"**Volume net (différence) :** {above_reference - below_reference:.2f} m³"
            )
