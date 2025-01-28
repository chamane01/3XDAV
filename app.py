import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster

# Données des routes (extraites de ta liste)
data = {
    "@id": [5009057, 5009058, 5009089, 5009090, 5009101, 19581591, 22702967, 22702968, 22702975, 22702976],
    "name": ["", "Boulevard Hortense Aka Anghui", "Avenue Nanan Yamousso", "Avenue Françis Wodié", "Avenue Mathieu Ekra", 
             "Rue A18", "Boulevard Hassan II", "Avenue Fologo Laurent Dona", "Boulevard Latrille", "Boulevard Latrille"],
    "@lat": [5.2671426, 5.2604487, 5.2967983, 5.2950101, 5.3183904, 5.2895384, 5.3296352, 5.3601100, 5.3280068, 5.3998713],
    "@lon": [-3.9613224, -3.9670066, -4.0032469, -4.0045306, -4.0120359, -4.0084709, -4.0091982, -4.0169686, -4.0048825, -3.9913531]
}

# Créer un DataFrame à partir des données
df = pd.DataFrame(data)

# Création de la carte avec folium
map_center = [df["@lat"].mean(), df["@lon"].mean()]  # Centrer la carte sur la moyenne des coordonnées
m = folium.Map(location=map_center, zoom_start=13)

# Ajouter un cluster de marqueurs
marker_cluster = MarkerCluster().add_to(m)

# Ajouter les marqueurs à la carte
for idx, row in df.iterrows():
    folium.Marker(
        location=[row["@lat"], row["@lon"]],
        popup=f"{row['name'] if row['name'] else 'Route'} (ID: {row['@id']})",
    ).add_to(marker_cluster)

# Afficher la carte dans Streamlit
st.title("Carte des Routes")
st.markdown("Voici une carte interactive des routes avec leurs coordonnées.")
st.dataframe(df)  # Afficher la table des routes
st.write("Cliquez sur un marqueur pour voir le nom et l'ID de la route.")
st.components.v1.html(m._repr_html_(), height=500)
