import streamlit as st
import folium
from streamlit_folium import st_folium

# Create a dataset of the most visited cities
data = [
    {"city": "Bangkok", "rank": 1, "visitors": 22.7, "lat": 13.7563, "lon": 100.5018},
    {"city": "Paris", "rank": 2, "visitors": 19.1, "lat": 48.8566, "lon": 2.3522},
    {"city": "London", "rank": 3, "visitors": 19.1, "lat": 51.5074, "lon": -0.1278},
    {"city": "Dubai", "rank": 4, "visitors": 16.7, "lat": 25.276987, "lon": 55.296249},
    {"city": "Singapore", "rank": 5, "visitors": 14.7, "lat": 1.3521, "lon": 103.8198},
]

# Streamlit app layout
st.title("Most Visited Cities in the World")
st.write("Click on a point on the map to view details about the city.")

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
    ).add_to(m)

# Display the map in Streamlit
st_map = st_folium(m, width=800, height=600)
