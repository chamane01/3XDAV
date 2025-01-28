import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import Point, Polygon
import json

def reproject_to_utm(gdf):
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    try:
        centroid = gdf.geometry.unary_union.centroid
        utm_zone = int((centroid.x + 180) // 6) + 1
        utm_crs = f"EPSG:{326 if centroid.y >= 0 else 327}{utm_zone}"
        return gdf.to_crs(utm_crs)
    except Exception as e:
        raise ValueError(f"Erreur lors de la reprojection : {e}")

def create_buffer(gdf, distance):
    buffer_gdf = gdf.buffer(distance)
    buffer_gdf = gpd.GeoSeries(
        [geom if geom.is_valid else geom.buffer(0) for geom in buffer_gdf], 
        crs=gdf.crs
    )
    return buffer_gdf

def check_point_proximity(point, gdf, buffer_gdf):
    result = []
    for idx, row in gdf.iterrows():
        if point.within(row.geometry):
            result.append((row['ID'], row.get('name', 'N/A'), row.get('classe', 'N/A')))
        elif point.within(buffer_gdf.iloc[idx]):
            result.append((row['ID'], row.get('name', 'N/A'), row.get('classe', 'N/A')))
    return result

def display_geojson(file):
    try:
        geojson_data = json.load(file)
        assert "features" in geojson_data, "Le fichier GeoJSON ne contient pas de 'features'."
    except Exception as e:
        st.error(f"Erreur lors du chargement du GeoJSON : {e}")
        return None, None, None

    gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])
    gdf = gdf[gdf.geometry.notnull() & gdf.is_valid]

    try:
        gdf = reproject_to_utm(gdf)
    except ValueError as e:
        st.error(str(e))
        return None, None, None

    buffer_gdf = create_buffer(gdf, 10)
    buffer_gdf = buffer_gdf[buffer_gdf.notnull() & buffer_gdf.is_valid]

    try:
        m = folium.Map(location=[gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()], zoom_start=12)
        folium.GeoJson(
            gdf.to_crs("EPSG:4326").to_json(),
            name="Routes",
            tooltip=folium.GeoJsonTooltip(fields=['ID', 'name', 'classe'], aliases=['ID', 'Nom', 'Classe']),
        ).add_to(m)
        folium.GeoJson(
            gpd.GeoDataFrame(geometry=buffer_gdf).to_crs("EPSG:4326").to_json(),
            name="Zones Tampons",
            style_function=lambda x: {
                "fillColor": "blue",
                "color": "blue",
                "weight": 1,
                "fillOpacity": 0.2,
            },
        ).add_to(m)
    except Exception as e:
        st.error(f"Erreur lors de la création de la carte : {e}")
        return None, None, None

    return m, gdf, buffer_gdf

st.title("Analyse GeoJSON avec Tampon et Recherche de Proximité")
uploaded_file = st.file_uploader("Téléverser un fichier GeoJSON", type="geojson")

if uploaded_file:
    st.write("Fichier chargé avec succès !")
    map_object, gdf, buffer_gdf = display_geojson(uploaded_file)

    if map_object:
        try:
            st_data = st_folium(map_object, width=700, height=500)
        except Exception as e:
            st.error(f"Erreur lors de l'affichage de la carte : {e}")

        st.subheader("Vérification de la proximité")
        col1, col2 = st.columns(2)
        with col1:
            latitude = st.number_input("Latitude", format="%.6f")
        with col2:
            longitude = st.number_input("Longitude", format="%.6f")

        if latitude and longitude:
            point = Point(longitude, latitude)
            point_gdf = gpd.GeoSeries([point], crs="EPSG:4326").to_crs(gdf.crs)
            proximity_results = check_point_proximity(point_gdf.iloc[0], gdf, buffer_gdf)

            if proximity_results:
                st.write("Le point est proche des routes suivantes :")
                for res in proximity_results:
                    st.write(f"- ID: {res[0]}, Nom: {res[1]}, Classe: {res[2]}")
            else:
                st.write("Le point n'est proche d'aucune route.")
