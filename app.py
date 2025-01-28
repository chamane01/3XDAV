import streamlit as st
import geopandas as gpd
import os
from io import StringIO

# Titre de l'application
st.title("Convertisseur de fichiers JSON vers GeoJSON/Shapefile")

# Téléverser un fichier JSON
uploaded_file = st.file_uploader("Téléversez votre fichier JSON", type=["json"])

if uploaded_file is not None:
    # Lire le fichier JSON
    try:
        # Convertir le fichier téléversé en GeoDataFrame
        gdf = gpd.read_file(uploaded_file)

        # Afficher un aperçu des données
        st.write("Aperçu des données :")
        st.write(gdf.head())

        # Vérifier si le fichier contient des géométries
        if not isinstance(gdf, gpd.GeoDataFrame):
            st.error("Le fichier JSON ne contient pas de géométries valides.")
        else:
            st.success("Le fichier JSON est un GeoJSON valide.")

            # Options de conversion
            st.write("### Options de conversion")
            output_format = st.selectbox("Choisissez le format de sortie", ["GeoJSON", "Shapefile"])

            # Bouton pour lancer la conversion
            if st.button("Convertir"):
                if output_format == "GeoJSON":
                    # Exporter en GeoJSON
                    output_file = "output.geojson"
                    gdf.to_file(output_file, driver="GeoJSON")
                elif output_format == "Shapefile":
                    # Exporter en Shapefile
                    output_file = "output.shp"
                    gdf.to_file(output_file, driver="ESRI Shapefile")

                # Télécharger le fichier converti
                with open(output_file, "rb") as f:
                    st.download_button(
                        label="Télécharger le fichier converti",
                        data=f,
                        file_name=output_file,
                        mime="application/octet-stream"
                    )

                # Supprimer le fichier temporaire
                os.remove(output_file)

    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier JSON : {e}")
