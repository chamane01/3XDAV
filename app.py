import streamlit as st
import rasterio
import numpy as np
import matplotlib.pyplot as plt

# Titre de l'application
st.title("Calculateur de volumes à partir d'un DEM avec emprise personnalisée")

# Importer un fichier DEM
uploaded_file = st.file_uploader("Téléchargez un fichier DEM (GeoTIFF uniquement) :", type=["tif", "tiff"])

if uploaded_file:
    # Charger le DEM
    with rasterio.open(uploaded_file) as src:
        dem_data = src.read(1)  # Lire la première bande
        dem_data[dem_data == src.nodata] = np.nan  # Gérer les valeurs no_data
        profile = src.profile
        bounds = src.bounds  # Bornes géographiques
        transform = src.transform  # Transformation affine

    st.success("Fichier DEM chargé avec succès !")

    # Affichage des métadonnées
    st.write("**Dimensions du DEM :**", dem_data.shape)
    st.write("**Résolution :**", profile["transform"][0], "unités par pixel")
    st.write("**Bornes géographiques :**")
    st.write(f"  - Min Longitude : {bounds.left}, Max Longitude : {bounds.right}")
    st.write(f"  - Min Latitude : {bounds.bottom}, Max Latitude : {bounds.top}")

    # Afficher le DEM sous forme d'image
    st.subheader("Aperçu du DEM")
    fig, ax = plt.subplots()
    cax = ax.imshow(dem_data, cmap="terrain", extent=(bounds.left, bounds.right, bounds.bottom, bounds.top))
    fig.colorbar(cax, ax=ax, label="Altitude (mètres)")
    st.pyplot(fig)

    # Définir une emprise pour la zone d'intérêt
    st.subheader("Définir l'emprise pour le calcul du volume")
    col1, col2 = st.columns(2)

    with col1:
        min_long = st.number_input("Longitude minimale :", value=bounds.left)
        max_long = st.number_input("Longitude maximale :", value=bounds.right)

    with col2:
        min_lat = st.number_input("Latitude minimale :", value=bounds.bottom)
        max_lat = st.number_input("Latitude maximale :", value=bounds.top)

    # Vérification de la validité de l'emprise
    if min_long >= max_long or min_lat >= max_lat:
        st.error("L'emprise n'est pas valide. Vérifiez les coordonnées.")
    else:
        # Découper le DEM pour la zone d'emprise
        row_start, col_start = ~transform * (min_long, max_lat)  # Indices pour la coordonnée supérieure gauche
        row_end, col_end = ~transform * (max_long, min_lat)  # Indices pour la coordonnée inférieure droite

        row_start, col_start = int(row_start), int(col_start)
        row_end, col_end = int(row_end), int(col_end)

        cropped_dem = dem_data[row_start:row_end, col_start:col_end]

        # Afficher la zone découpée
        st.subheader("Zone découpée")
        fig, ax = plt.subplots()
        ax.imshow(cropped_dem, cmap="terrain", extent=(min_long, max_long, min_lat, max_lat))
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
                (cropped_dem - reference_altitude)[cropped_dem > reference_altitude]
            ) * cell_area
            below_reference = np.nansum(
                (reference_altitude - cropped_dem)[cropped_dem < reference_altitude]
            ) * cell_area

            # Résultats
            st.write(f"**Volume au-dessus de l'altitude de référence :** {above_reference:.2f} m³")
            st.write(f"**Volume en dessous de l'altitude de référence :** {below_reference:.2f} m³")
            st.write(
                f"**Volume net (différence) :** {above_reference - below_reference:.2f} m³"
            )
