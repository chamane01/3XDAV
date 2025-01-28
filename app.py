import streamlit as st
import geopandas as gpd
import json
from io import StringIO
import os

# Titre de l'application
st.title("Convertisseur de fichiers JSON vers GeoJSON/Shapefile")

# Téléverser un fichier JSON
uploaded_file = st.file_uploader("Téléversez votre fichier JSON", type=["json"])

if uploaded_file is not None:
    # Lire le fichier JSON comme texte
    json_data = uploaded_file.read().decode("utf-8")

    try:
        # Essayer de charger le JSON
        data = json.loads(json_data)

        # Vérifier si c'est un GeoJSON valide
        if data.get("type") == "FeatureCollection" and "features" in data:
            st.success("Le fichier JSON est un GeoJSON valide.")

            # Convertir en GeoDataFrame
            gdf = gpd.GeoDataFrame.from_features(data["features"])

            # Afficher un aperçu des données
            st.write("Aperçu des données :")
            st.write(gdf.head())

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
        else:
            st.error("Le fichier JSON n'est pas un GeoJSON valide. Assurez-vous qu'il contient une 'FeatureCollection'.")

    except json.JSONDecodeError:
        st.error("Le fichier n'est pas un JSON valide.")
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier JSON : {e}")
