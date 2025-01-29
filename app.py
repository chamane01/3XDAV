import streamlit as st
import folium
import random
from streamlit_folium import st_folium

# Définition des catégories de dégradations et niveaux de gravité
defauts = {
    "Déformation Orniérage": "red",
    "Fissure de Fatigue": "blue",
    "Faïençage de Fatigue": "green",
    "Fissure de Retrait": "orange",
    "Fissure Anarchique": "purple",
    "Réparation": "pink",
    "Nid de Poule": "brown",
    "Arrachements": "gray",
    "Fluage": "cyan",
    "Dénivellement Accotement": "yellow",
    "Chaussée Détruite": "black",
    "Envahissement Végétation": "darkgreen",
    "Assainissement": "lightblue"
}

# Création de la base de données virtuelle des défauts
base_donnees = []
for _ in range(100):
    categorie = random.choice(list(defauts.keys()))
    gravite = random.randint(1, 3)
    lat = random.uniform(-90, 90)  # Coordonnées latitude aléatoires
    lon = random.uniform(-180, 180)  # Coordonnées longitude aléatoires
    base_donnees.append({
        "categorie": categorie,
        "gravite": gravite,
        "lat": lat,
        "lon": lon,
        "couleur": defauts[categorie]
    })

# Fonction pour ajuster la teinte selon la gravité
def get_color(couleur_base, gravite):
    if gravite == 1:
        return couleur_base
    elif gravite == 2:
        return couleur_base + "4D"  # Ajout d'une transparence
    elif gravite == 3:
        return couleur_base + "99"  # Plus clair

# Configuration de l'application Streamlit
st.title("Dégradations Routières : Carte des Inspections Virtuelles")
st.write("Cliquez sur un marqueur pour voir les détails du défaut.")

# Initialisation de la carte Folium
m = folium.Map(location=[0, 0], zoom_start=2)

# Ajout des marqueurs pour chaque défaut
for defaut in base_donnees:
    tooltip = f"{defaut['categorie']} (Gravité {defaut['gravite']})"
    popup_content = f"""
    <b>Catégorie :</b> {defaut['categorie']}<br>
    <b>Niveau de Gravité :</b> {defaut['gravite']}<br>
    <b>Latitude :</b> {defaut['lat']:.2f}, <b>Longitude :</b> {defaut['lon']:.2f}
    """
    folium.Marker(
        location=[defaut['lat'], defaut['lon']],
        popup=popup_content,
        tooltip=tooltip,
        icon=folium.Icon(color=defaut['couleur'])
    ).add_to(m)

# Génération de la légende
legend_html = """
<div style="
    position: fixed;
    bottom: 50px;
    left: 50px;
    width: 200px;
    height: auto;
    background-color: white;
    border:2px solid grey;
    z-index:9999;
    font-size:12px;
    padding:10px;
    ">
    <b>Légende</b><br>
"""
for categorie, couleur in defauts.items():
    legend_html += f"&nbsp;<i class='fa fa-map-marker fa-2x' style='color:{couleur}'></i> {categorie}<br>"
legend_html += "</div>"
m.get_root().html.add_child(folium.Element(legend_html))

# Affichage de la carte dans Streamlit
st_folium(m, width=800, height=600)
