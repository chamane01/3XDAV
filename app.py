import streamlit as st
from streamlit_folium import st_folium
import folium

# Stockage des couches dans la session Streamlit
if "layers" not in st.session_state:
    st.session_state["layers"] = {"points": [], "lines": [], "polylines": []}

# Titre de l'application
st.title("Carte Dynamique avec Gestion des Couches")

# Sélection de l'action
action = st.sidebar.radio(
    "Que souhaitez-vous faire ?",
    ("Ajouter un point", "Ajouter une ligne", "Ajouter une polyligne", "Afficher la carte")
)

# Gestion des actions
if action == "Ajouter un point":
    st.header("Ajouter un Point")
    lat = st.number_input("Latitude", format="%.6f")
    lon = st.number_input("Longitude", format="%.6f")
    nom = st.text_input("Nom du point")

    if st.button("Ajouter le point"):
        st.session_state["layers"]["points"].append({"lat": lat, "lon": lon, "nom": nom})
        st.success(f"Point '{nom}' ajouté avec succès.")

elif action == "Ajouter une ligne":
    st.header("Ajouter une Ligne")
    points = st.text_area(
        "Coordonnées des points (format : lat,lon ; lat,lon ...)",
        help="Exemple : 5.5,-4.1 ; 5.6,-4.2"
    )

    if st.button("Ajouter la ligne"):
        try:
            coords = [tuple(map(float, p.split(","))) for p in points.split(";")]
            st.session_state["layers"]["lines"].append({"coords": coords})
            st.success("Ligne ajoutée avec succès.")
        except Exception as e:
            st.error(f"Erreur dans le format des coordonnées : {e}")

elif action == "Ajouter une polyligne":
    st.header("Ajouter une Polyligne")
    points = st.text_area(
        "Coordonnées des points (format : lat,lon ; lat,lon ...)",
        help="Exemple : 5.5,-4.1 ; 5.6,-4.2 ; 5.7,-4.3"
    )

    if st.button("Ajouter la polyligne"):
        try:
            coords = [tuple(map(float, p.split(","))) for p in points.split(";")]
            st.session_state["layers"]["polylines"].append({"coords": coords})
            st.success("Polyligne ajoutée avec succès.")
        except Exception as e:
            st.error(f"Erreur dans le format des coordonnées : {e}")

# Affichage de la carte
if action == "Afficher la carte":
    st.header("Carte Dynamique")

    # Création de la carte Folium
    m = folium.Map(location=[5.5, -4.0], zoom_start=8)

    # Ajout des points
    for point in st.session_state["layers"]["points"]:
        folium.Marker(
            location=[point["lat"], point["lon"]],
            popup=point["nom"],
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    # Ajout des lignes
    for line in st.session_state["layers"]["lines"]:
        folium.PolyLine(
            locations=line["coords"],
            color="green",
            weight=2.5,
            opacity=1
        ).add_to(m)

    # Ajout des polylignes
    for polyline in st.session_state["layers"]["polylines"]:
        folium.PolyLine(
            locations=polyline["coords"],
            color="red",
            weight=2.5,
            dash_array="5,5"
        ).add_to(m)

    # Affichage de la carte avec Streamlit
    st_folium(m, width=700, height=500)
