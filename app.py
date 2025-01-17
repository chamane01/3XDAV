import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
from folium import LayerControl

# Initialisation des couches et des entités dans la session Streamlit
if "layers" not in st.session_state:
    st.session_state["layers"] = {"Routes": [], "Bâtiments": [], "Polygonale": []}

# Initialisation des nouvelles entités temporairement dessinées
if "new_features" not in st.session_state:
    st.session_state["new_features"] = []

# Titre de l'application
st.title("Carte Dynamique avec Gestion Avancée des Couches")

# Description
st.markdown("""
Créez des entités géographiques (points, lignes, polygones) en les dessinant sur la carte et ajoutez-les à des couches spécifiques. 
Vous pouvez également activer ou désactiver des couches grâce au gestionnaire de couches.
""")

# Première sidebar (permanente)
with st.sidebar:
    st.header("Gestion des Couches")

    # Ajout d'une nouvelle couche par nom
    st.subheader("Ajouter une nouvelle couche")
    new_layer_name = st.text_input("Nom de la nouvelle couche à ajouter", "")
    if st.button("Ajouter la couche") and new_layer_name:
        if new_layer_name not in st.session_state["layers"]:
            st.session_state["layers"][new_layer_name] = []
            st.success(f"La couche '{new_layer_name}' a été ajoutée.")
        else:
            st.warning(f"La couche '{new_layer_name}' existe déjà.")

    # Sélection de la couche active pour ajouter les nouvelles entités
    st.subheader("Sélectionner une couche active")
    layer_name = st.selectbox(
        "Choisissez la couche à laquelle ajouter les entités",
        list(st.session_state["layers"].keys())
    )

    # Affichage des entités temporairement dessinées
    if st.session_state["new_features"]:
        st.write(f"**Entités dessinées temporairement ({len(st.session_state['new_features'])}) :**")
        for idx, feature in enumerate(st.session_state["new_features"]):
            st.write(f"- Entité {idx + 1}: {feature['geometry']['type']}")

    # Bouton pour enregistrer les nouvelles entités dans la couche active
    if st.button("Enregistrer les entités"):
        # Ajouter les entités non dupliquées à la couche sélectionnée
        current_layer = st.session_state["layers"][layer_name]
        for feature in st.session_state["new_features"]:
            if feature not in current_layer:
                current_layer.append(feature)
        st.session_state["new_features"] = []  # Réinitialisation des entités temporaires
        st.success(f"Toutes les nouvelles entités ont été enregistrées dans la couche '{layer_name}'.")

    # Suppression et modification d'une entité dans une couche
    st.subheader("Gestion des entités dans les couches")
    selected_layer = st.selectbox("Choisissez une couche pour voir ses entités", list(st.session_state["layers"].keys()))
    if st.session_state["layers"][selected_layer]:
        entity_idx = st.selectbox(
            "Sélectionnez une entité à gérer",
            range(len(st.session_state["layers"][selected_layer])),
            format_func=lambda idx: f"Entité {idx + 1}: {st.session_state['layers'][selected_layer][idx]['geometry']['type']}"
        )
        selected_entity = st.session_state["layers"][selected_layer][entity_idx]
        current_name = selected_entity.get("properties", {}).get("name", "")
        new_name = st.text_input("Nom de l'entité", current_name)

        if st.button("Modifier le nom", key=f"edit_{entity_idx}"):
            if "properties" not in selected_entity:
                selected_entity["properties"] = {}
            selected_entity["properties"]["name"] = new_name
            st.success(f"Le nom de l'entité a été mis à jour en '{new_name}'.")

        if st.button("Supprimer l'entité sélectionnée", key=f"delete_{entity_idx}"):
            st.session_state["layers"][selected_layer].pop(entity_idx)
            st.success(f"L'entité sélectionnée a été supprimée de la couche '{selected_layer}'.")
    else:
        st.write("Aucune entité dans cette couche pour le moment.")

# Deuxième Sidebar (calcul des volumes) avec affichage conditionnel
if st.button("Calculer des volumes"):
    with st.sidebar:
        st.header("Calcul des Volumes")

        # Ajoutez ici des éléments pour le calcul des volumes, par exemple:
        volume_data = st.text_input("Entrez les dimensions pour calculer le volume")
        if st.button("Calculer"):
            st.write(f"Volume calculé pour : {volume_data}")
        else:
            st.write("Entrez des données pour effectuer le calcul.")

# Carte de base
m = folium.Map(location=[5.5, -4.0], zoom_start=8)

# Ajout des couches existantes à la carte
layer_groups = {}
for layer, features in st.session_state["layers"].items():
    layer_groups[layer] = folium.FeatureGroup(name=layer, show=True)
    for feature in features:
        feature_type = feature["geometry"]["type"]
        coordinates = feature["geometry"]["coordinates"]
        popup = feature.get("properties", {}).get("name", f"{layer} - Entité")

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
    # Ajouter l'entité temporairement si elle n'existe pas déjà
    if new_feature not in st.session_state["new_features"]:
        st.session_state["new_features"].append(new_feature)
        st.info("Nouvelle entité ajoutée temporairement. Cliquez sur 'Enregistrer les entités' pour les ajouter à la couche.")
