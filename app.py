import streamlit as st
import folium
from folium import GeoJson
import json

# Données GeoJSON (les coordonnées doivent être en EPSG:4326)
geoJsonData = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "@id": "way/5009101",
                "destination": "1er Pont Félix Houphouët-Boigny",
                "foot": "no",
                "highway": "primary",
                "lanes": 2,
                "lit": "yes",
                "maxspeed": 60,
                "maxspeed:bus": 50,
                "maxspeed:hgv": 50,
                "maxspeed:tourist_bus": 50,
                "name": "Avenue Mathieu Ekra",
                "oneway": "yes",
                "sidewalk": "no",
                "source": "MCLU/PADA",
                "source:date": "2023/05/03",
                "source:maxspeed": "CI:urban",
                "surface": "asphalt",
                "color": "#FF5733"  # Code couleur unique pour ce ID
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-4.0113663, 5.3187904],
                    [-4.0114749, 5.3186976],
                    [-4.0115648, 5.3186175],
                    [-4.0116647, 5.3185387],
                    [-4.0117659, 5.3184733],
                    [-4.011894, 5.3184052],
                    [-4.0122092, 5.3182503],
                    [-4.0127054, 5.3179905]
                ]
            },
            "id": "way/5009101"
        },
        {
            "type": "Feature",
            "properties": {
                "@id": "way/22703839",
                "highway": "trunk",
                "lanes": 3,
                "lit": "yes",
                "maxheight": 5.25,
                "maxspeed": 100,
                "name": "Boulevard Jean-Baptiste Mockey",
                "oneway": "yes",
                "ref": "A100",
                "short_name": "Blvd VGE",
                "source": "MCLU/PADA",
                "source:date": "2023/05/03",
                "surface": "asphalt",
                "color": "#33FF57"  # Code couleur unique pour ce ID
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-3.9009539, 5.2400795],
                    [-3.9011152, 5.2401055],
                    [-3.901729, 5.2402092],
                    [-3.9023834, 5.2403107],
                    [-3.9027818, 5.2403624],
                    [-3.9035516, 5.2404803],
                    [-3.9044106, 5.2406167],
                    [-3.904976, 5.2406965],
                    [-3.9053707, 5.2407607],
                    [-3.9061788, 5.2408903],
                    [-3.9067498, 5.2409826],
                    [-3.9072895, 5.2410698],
                    [-3.9080946, 5.2411853],
                    [-3.9101332, 5.2415037],
                    [-3.9117014, 5.2417584]
                ]
            },
            "id": "way/22703839"
        },
        {
            "type": "Feature",
            "properties": {
                "@id": "way/22703947",
                "highway": "primary",
                "lanes": 2,
                "maxspeed": 60,
                "maxspeed:bus": 50,
                "maxspeed:hgv": 50,
                "maxspeed:tourist_bus": 50,
                "oneway": "yes",
                "source": "yahoo",
                "source:maxspeed": "CI:urban",
                "surface": "asphalt",
                "color": "#3357FF"  # Code couleur unique pour ce ID
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-4.0192387, 5.3145579],
                    [-4.0192237, 5.3092212]
                ]
            },
            "id": "way/22703947"
        },
        {
            "type": "Feature",
            "properties": {
                "@id": "way/22703949",
                "bridge": "yes",
                "bridge:name": "Pont Félix-Houphouët-Boigny",
                "bridge:structure": "beam",
                "foot": "no",
                "highway": "primary",
                "lanes": 2,
                "layer": 2,
                "maxspeed": 60,
                "maxspeed:bus": 50,
                "maxspeed:hgv": 50,
                "maxspeed:tourist_bus": 50,
                "name": "Pont Felix Houphouét Boigny (FHB)",
                "oneway": "yes",
                "source": "MCLU/PADA",
                "source:date": "2023/05/03",
                "source:maxspeed": "CI:urban",
                "surface": "asphalt",
                "color": "#FF5733"  # Code couleur unique pour ce ID
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-4.0194623, 5.3145579],
                    [-4.0192387, 5.3095622]
                ]
            },
            "id": "way/22703949"
        }
    ]
}

# Création de la carte Folium centrée sur un point de coordonnées
m = folium.Map(location=[5.3187904, -4.0113663], zoom_start=15, control_scale=True)

# Ajout des données GeoJSON sur la carte
folium.GeoJson(
    geoJsonData,
    name="Routes",
    style_function=lambda feature: {
        'color': feature['properties']['color'],
        'weight': 5,
        'opacity': 0.7
    }
).add_to(m)

# Affichage de la carte dans Streamlit
st.title("Carte des Routes")
st.markdown("Voici une carte affichant plusieurs routes avec leurs caractéristiques.")
st.components.v1.html(m._repr_html_(), height=600)
