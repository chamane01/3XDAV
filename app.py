import streamlit as st
import folium
from streamlit_folium import st_folium

# Liste des 20 villes les plus visitées avec leurs coordonnées
data = [
    {"city": "Bangkok", "rank": 1, "visitors": 22.7, "lat": 13.7563, "lon": 100.5018},
    {"city": "Paris", "rank": 2, "visitors": 19.1, "lat": 48.8566, "lon": 2.3522},
    {"city": "Londres", "rank": 3, "visitors": 19.1, "lat": 51.5074, "lon": -0.1278},
    {"city": "Dubaï", "rank": 4, "visitors": 16.7, "lat": 25.276987, "lon": 55.296249},
    {"city": "Singapour", "rank": 5, "visitors": 14.7, "lat": 1.3521, "lon": 103.8198},
    {"city": "Kuala Lumpur", "rank": 6, "visitors": 13.8, "lat": 3.139, "lon": 101.6869},
    {"city": "New York", "rank": 7, "visitors": 13.1, "lat": 40.7128, "lon": -74.006},
    {"city": "Istanbul", "rank": 8, "visitors": 12.8, "lat": 41.0082, "lon": 28.9784},
    {"city": "Tokyo", "rank": 9, "visitors": 12.5, "lat": 35.6895, "lon": 139.6917},
    {"city": "Antalya", "rank": 10, "visitors": 12.4, "lat": 36.8969, "lon": 30.7133},
    {"city": "Séoul", "rank": 11, "visitors": 11.3, "lat": 37.5665, "lon": 126.978},
    {"city": "Osaka", "rank": 12, "visitors": 10.2, "lat": 34.6937, "lon": 135.5023},
    {"city": "La Mecque", "rank": 13, "visitors": 10, "lat": 21.3891, "lon": 39.8579},
    {"city": "Phuket", "rank": 14, "visitors": 9.9, "lat": 7.8804, "lon": 98.3923},
    {"city": "Pattaya", "rank": 15, "visitors": 9.4, "lat": 12.9236, "lon": 100.8825},
    {"city": "Milan", "rank": 16, "visitors": 9.1, "lat": 45.4642, "lon": 9.19},
    {"city": "Barcelone", "rank": 17, "visitors": 9, "lat": 41.3851, "lon": 2.1734},
    {"city": "Hong Kong", "rank": 18, "visitors": 8.9, "lat": 22.3193, "lon": 114.1694},
    {"city": "Palma de Majorque", "rank": 19, "visitors": 8.8, "lat": 39.5696, "lon": 2.6502},
    {"city": "Bali", "rank": 20, "visitors": 8.3, "lat": -8.3405, "lon": 115.092},
]

# Fonction pour déterminer la couleur du marqueur en fonction du rang
def get_marker_color(rank):
    if 1 <= rank <= 5:
        return 'red'
    elif 6 <= rank <= 10:
        return 'blue'
    elif 11 <= rank <= 15:
        return 'green'
    elif 16 <= rank <= 20:
        return 'purple'

# Configuration de l'application Streamlit
st.title("Top 20 des villes les plus visitées au monde")
st.write("Cliquez sur un marqueur pour voir les détails de la ville.")

# Initialisation de la carte Folium
m = folium.Map(location=[20, 0], zoom_start=2)

# Ajout des marqueurs sur la carte
for city in data:
    tooltip = f"{city['city']} (Rang {city['rank']})"
    popup_content = f"""
    <b>Ville :</b> {city['city']}<br>
    <b>Rang :</b> {city['rank']}<br>
    <b>Visiteurs (millions) :</b> {city['visitors']}
    """
    folium.Marker(
        location=[city['lat'], city['lon']],
        popup=popup_content,
        tooltip=tooltip,
        icon=folium.Icon(color=get_marker_color(city['rank']))
    ).add_to(m)

# HTML personnalisé pour la légende
legend_html = """
<div style="
    position: fixed;
    bottom: 50px;
    left: 50px;
    width: 150px;
    height: 120px;
    background-color: white;
    border:2px solid grey;
    z-index:9999;
    font-size:14px;
    ">
    <b>&nbsp;Légende</b><br>
    &nbsp;<i class="fa fa-map-marker fa-2x" style="color:red"></i>&nbsp; Rang 1-5<br>
    &nbsp;<i class="fa fa-map-marker fa-2x" style="color:blue"></i>&nbsp; Rang 6-10<br>
    &nbsp;<i class="fa fa-map-marker fa-2x" style="color:green"></i>&nbsp; Rang 11-15<br>
    &nbsp;<i class="fa fa-map-marker fa-2x" style="color:purple"></i>&nbsp; Rang 16-20
</div>
"""

# Ajout de la légende personnalisée à la carte
m.get_root().html.add_child(folium.Element(legend_html))

# Affichage de la carte dans Streamlit
st_folium(m, width=800, height=600)
