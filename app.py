import streamlit as st
import requests
import folium
from folium.plugins import MarkerCluster

# Définir la zone géographique d'intérêt
south, west, north, east = 5.25, -4.05, 5.3, -3.95

# Construire l'URL de la requête Overpass
overpass_url = "https://overpass-api.de/api/interpreter"
overpass_query = f"""
<osm-script>
  <union into="_">
    <query type="way">
      <has-kv k="highway" modv="" v=""/>
      <bbox-query s="{south}" w="{west}" n="{north}" e="{east}"/>
    </query>
    <recurse type="way-node"/>
  </union>
  <print e="" from="_" geometry="skeleton" ids="yes" limit="" mode="ids_only" n="" order="quadtile" s="" w=""/>
</osm-script>
"""
response = requests.get(overpass_url, params={'data': overpass_query})
data = response.json()

# Créer une carte centrée sur la zone d'intérêt
m = folium.Map(location=[(south + north) / 2, (west + east) / 2], zoom_start=14)

# Ajouter un cluster de marqueurs
marker_cluster = MarkerCluster().add_to(m)

# Ajouter les routes à la carte
for element in data['elements']:
    if element['type'] == 'way':
        coordinates = [(node['lat'], node['lon']) for node in element['nodes']]
        folium.PolyLine(coordinates, color='blue', weight=2.5, opacity=1).add_to(marker_cluster)

# Afficher la carte dans Streamlit
st.title("Carte des routes")
st.markdown("Voici une carte dynamique affichant les routes dans la zone spécifiée.")
st_folium(m, width=700, height=500)
