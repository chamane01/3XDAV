import streamlit as st
import folium
from streamlit_folium import st_folium

# Dataset of the top 20 most visited cities
data = [
    {"city": "Bangkok", "rank": 1, "visitors": 22.7, "lat": 13.7563, "lon": 100.5018},
    {"city": "Paris", "rank": 2, "visitors": 19.1, "lat": 48.8566, "lon": 2.3522},
    {"city": "London", "rank": 3, "visitors": 19.1, "lat": 51.5074, "lon": -0.1278},
    {"city": "Dubai", "rank": 4, "visitors": 16.7, "lat": 25.276987, "lon": 55.296249},
    {"city": "Singapore", "rank": 5, "visitors": 14.7, "lat": 1.3521, "lon": 103.8198},
    {"city": "Kuala Lumpur", "rank": 6, "visitors": 13.8, "lat": 3.139, "lon": 101.6869},
    {"city": "New York", "rank": 7, "visitors": 13.1, "lat": 40.7128, "lon": -74.006},
    {"city": "Istanbul", "rank": 8, "visitors": 12.8, "lat": 41.0082, "lon": 28.9784},
    {"city": "Tokyo", "rank": 9, "visitors": 12.5, "lat": 35.6895, "lon": 139.6917},
    {"city": "Antalya", "rank": 10, "visitors": 12.4, "lat": 36.8969, "lon": 30.7133},
    {"city": "Seoul", "rank": 11, "visitors": 11.3, "lat": 37.5665, "lon": 126.978},
    {"city": "Osaka", "rank": 12, "visitors": 10.2, "lat": 34.6937, "lon": 135.5023},
    {"city": "Makkah", "rank": 13, "visitors": 10, "lat": 21.3891, "lon": 39.8579},
    {"city": "Phuket", "rank": 14, "visitors": 9.9, "lat": 7.8804, "lon": 98.3923},
    {"city": "Pattaya", "rank": 15, "visitors": 9.4, "lat": 12.9236, "lon": 100.8825},
    {"city": "Milan", "rank": 16, "visitors": 9.1, "lat": 45.4642, "lon": 9.19},
    {"city": "Barcelona", "rank": 17, "visitors": 9, "lat": 41.3851, "lon": 2.1734},
    {"city": "Hong Kong", "rank": 18, "visitors": 8.9, "lat": 22.3193, "lon": 114.1694},
    {"city": "Palma de Mallorca", "rank": 19, "visitors": 8.8, "lat": 39.5696, "lon": 2.6502},
    {"city": "Bali", "rank": 20, "visitors": 8.3, "lat": -8.3405, "lon": 115.092},
]

# Function to determine marker color based on rank
def get_marker_color(rank):
    if 1 <= rank <= 5:
        return 'red'
    elif 6 <= rank <= 10:
        return 'blue'
    elif 11 <= rank <= 15:
        return 'green'
    elif 16 <= rank <= 20:
        return 'purple'

# Streamlit app layout
st.title("Top 20 Most Visited Cities in the World")
st.write("Click on a marker to view details about the city.")

# Initialize a folium map
m = folium.Map(location=[20, 0], zoom_start=2)

# Add markers to the map
for city in data:
    tooltip = f"{city['city']} (Rank {city['rank']})"
    popup_content = f"""
    <b>City:</b> {city['city']}<br>
    <b>Rank:</b> {city['rank']}<br>
    <b>Visitors (millions):</b> {city['visitors']}
    """
    folium.Marker(
        location=[city['lat'], city['lon']],
        popup=popup_content,
        tooltip=tooltip,
        icon=folium.Icon(color=get_marker_color(city['rank']))
    ).add_to(m)

# Custom legend HTML
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
    <b>&nbsp;Legend</b><br>
    &nbsp;<i class="fa fa-map-marker fa-2x" style="color:red"></i>&nbsp; Rank 1-5<br>
    &nbsp;<i class="fa fa-map-marker fa-2x" style="color:blue"></i>&nbsp; Rank 6-10<br>
    &nbsp;<i class="fa fa-map-marker fa-2x" style="color:green"></i>&nbsp; Rank 11-15<br>
    &nbsp;<i class="fa fa-map-marker fa-2x" style="color:purple"></i>&nbsp; Rank 16-20
</div>
"""

# Add the custom legend to the map
m.get_root().html.add_child(folium.Element(legend_html))


::contentReference[oaicite:0]{index=0}
 
