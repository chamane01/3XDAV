import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from folium import LayerControl

# Initialisation des couches et des entités dans la session Streamlit
if "layers" not in st.session_state:
    st.session_state["layers"] = {"Routes": [], "Bâtiments": [], "Polygonale": []}

if "new_features" not in st.session_state:
    st.session_state["new_features"] = []

# Titre de l'application
st.title("Carte Dynamique avec Gestion Avancée des Couches")

# Description
st.markdown("""
Créez des entités géographiques (points, lignes, polygones) en les dessinant sur la carte et ajoutez-les à des couches spécifiques. 
Vous pouvez également activer ou désactiver des couches grâce au gestionnaire de couches.
""")

# Ajout d'une nouvelle couche par nom
st.header("Ajouter une nouvelle couche")
new_layer_name = st.text_input("Nom de la nouvelle couche à ajouter", "")
if st.button("Ajouter la couche") and new_layer_name:
    if new_layer_name not in st.session_state["layers"]:
        st.session_state["layers"][new_layer_name] = []
        st.success(f"La couche '{new_layer_name}' a été ajoutée.")
    else:
        st.warning(f"La couche '{new_layer_name}' existe déjà.")

# Sélection de la couche active pour ajouter les nouvelles entités
st.header("Sélectionner une couche active")
layer_name = st.selectbox(
    "Choisissez la couche à laquelle ajouter les entités",
    list(st.session_state["layers"].keys())
)

# Carte de base
m = folium.Map(location=[5.5, -4.0], zoom_start=8)

# Ajout des couches existantes à la carte
layer_groups = {}
for layer, features in st.session_state["layers"].items():
    layer_groups[layer] = folium.FeatureGroup(name=layer, show=True)
    for feature in features:
        feature_type = feature["geometry"]["type"]
        coordinates = feature["geometry"]["coordinates"]
        popup = folium.Popup(
            f"""
            Nom : {feature.get("properties", {}).get("name", "Entité")}
            """,
            max_width=250
        )

        if feature_type == "Point":
            lat, lon = coordinates[1], coordinates[0]
            folium.Marker(location=[lat, lon], popup=popup).add_to(layer_groups[layer])
        elif feature_type == "LineString":
            folium.PolyLine(locations=[(lat, lon) for lon, lat in coordinates], color="blue", popup=popup).add_to(layer_groups[layer])
        elif feature_type == "Polygon":
            folium.Polygon(locations=[(lat, lon) for lon, lat in coordinates[0]], color="green", fill=True, popup=popup).add_to(layer_groups[layer])

    # Ajout du groupe à la carte
    layer_groups[layer].add_to(m)

# Gestionnaire de dessin
draw = Draw(
    draw_options={
        "polyline": True,
        "polygon": True,
        "circle": False,
        "rectangle": True,
        "marker": True,
        "circlemarker": False,
    },
    edit_options={"edit": True, "remove": True},
)
draw.add_to(m)

# Ajout du gestionnaire de couches en mode plié
LayerControl(position="topleft", collapsed=True).add_to(m)

# Affichage interactif de la carte
output = st_folium(m, width=800, height=600, returned_objects=["last_active_drawing", "all_drawings"])

# Gestion des nouveaux dessins
if output and "last_active_drawing" in output and output["last_active_drawing"]:
    new_feature = output["last_active_drawing"]
    # Éviter les doublons en vérifiant si l'entité existe déjà
    if new_feature not in st.session_state["new_features"]:
        st.session_state["new_features"].append(new_feature)
        st.info("Nouvelle entité ajoutée temporairement. Cliquez sur 'Enregistrer les entités' pour les ajouter à la couche.")

# Bouton pour enregistrer les nouvelles entités
if st.button("Enregistrer les entités") and st.session_state["new_features"]:
    st.session_state["layers"][layer_name].extend(st.session_state["new_features"])
    st.session_state["new_features"] = []  # Réinitialisation des nouvelles entités
    st.success(f"Toutes les nouvelles entités ont été enregistrées dans la couche '{layer_name}'.")

# Gestion des entités avec édition des noms
st.header("Gestion des entités dans les couches")
selected_layer = st.selectbox("Choisissez une couche pour voir ses entités", list(st.session_state["layers"].keys()))
if st.session_state["layers"][selected_layer]:
    for idx, entity in enumerate(st.session_state["layers"][selected_layer]):
        name = entity.get("properties", {}).get("name", f"Entité {idx + 1}")
        st.write(f"Entité {idx + 1} : {name}")
        new_name = st.text_input(f"Modifier le nom de l'entité {idx + 1}", value=name, key=f"name_{selected_layer}_{idx}")

        if st.button(f"Appliquer modification {idx + 1}", key=f"apply_{selected_layer}_{idx}"):
            if "properties" not in entity:
                entity["properties"] = {}
            entity["properties"]["name"] = new_name
            st.success(f"Le nom de l'entité {idx + 1} a été mis à jour.")
else:
    st.write("Aucune entité dans cette couche pour le moment.")
