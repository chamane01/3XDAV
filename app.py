import streamlit as st
import xmltodict
import folium
from io import StringIO

# Titre de l'application
st.title("Affichage d'un fichier XML sur une carte dynamique")

# Téléversement du fichier XML
uploaded_file = st.file_uploader("Téléversez votre fichier XML", type=["xml"])

if uploaded_file is not None:
    # Lecture du contenu du fichier XML
    file_content = uploaded_file.getvalue().decode("utf-8")
    data_dict = xmltodict.parse(file_content)

    # Extraction des coordonnées (exemple : latitude et longitude)
    # Adaptez cette partie en fonction de la structure de votre fichier XML
    try:
        latitude = float(data_dict['root']['location']['latitude'])
        longitude = float(data_dict['root']['location']['longitude'])
    except KeyError:
        st.error("Le fichier XML ne contient pas les informations de latitude et de longitude.")
        st.stop()

    # Création de la carte centrée sur les coordonnées extraites
    map_center = [latitude, longitude]
    m = folium.Map(location=map_center, zoom_start=12)

    # Ajout d'un marqueur sur la carte
    folium.Marker(location=map_center, popup="Emplacement").add_to(m)

    # Affichage de la carte dans Streamlit
    st.write("Carte générée à partir du fichier XML :")
    st.components.v1.html(m._repr_html_(), width=700, height=500)
else:
    st.info("Veuillez téléverser un fichier XML pour afficher la carte.")
