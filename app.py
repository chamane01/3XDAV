# Module 1: Importations des bibliothèques
import streamlit as st
import folium
import rasterio
from rasterio.warp import calculate_default_transform, reproject
import geopandas as gpd
from shapely.geometry import Polygon, Point, LineString
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import uuid
import dask.array as da
from fpdf import FPDF
import os

# Module 2: Dictionnaire des couleurs pour les types de fichiers GeoJSON
geojson_colors = {
    "roads": "red",
    "buildings": "blue",
    "waterways": "green",
    # Ajoutez d'autres types de fichiers GeoJSON et leurs couleurs ici
}

# Module 3: Fonctions principales

# 3.1. Reprojection d'un fichier TIFF
def reproject_tiff(input_tiff, target_crs):
    with rasterio.open(input_tiff) as src:
        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        output_tiff = f"reprojected_{uuid.uuid4()}.tif"
        with rasterio.open(output_tiff, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=rasterio.enums.Resampling.nearest)
    return output_tiff

# 3.2. Application d'un gradient de couleur à un MNT/MNS
def apply_color_gradient(tiff_path, output_path):
    with rasterio.open(tiff_path) as src:
        data = src.read(1)
        plt.imshow(data, cmap='terrain')
        plt.colorbar()
        plt.savefig(output_path)
        plt.close()

# 3.3. Génération de cartes de contours
def generate_contour_map(tiff_path, output_path, interval=10):
    with rasterio.open(tiff_path) as src:
        data = src.read(1)
        x = np.linspace(0, src.width, src.width)
        y = np.linspace(0, src.height, src.height)
        X, Y = np.meshgrid(x, y)
        plt.contour(X, Y, data, levels=np.arange(data.min(), data.max(), interval))
        plt.savefig(output_path)
        plt.close()

# 3.4. Ajout d'une image TIFF à la carte
def add_image_overlay(map_object, tiff_path, bounds, name):
    folium.raster_layers.ImageOverlay(
        image=tiff_path,
        bounds=bounds,
        name=name
    ).add_to(map_object)

# 3.5. Calcul des limites d'un GeoJSON
def calculate_geojson_bounds(geojson_data):
    gdf = gpd.GeoDataFrame.from_features(geojson_data)
    return gdf.total_bounds

# 3.6. Chargement d'un fichier TIFF
def load_tiff(tiff_path):
    with rasterio.open(tiff_path) as src:
        data = src.read(1)
        bounds = src.bounds
        transform = src.transform
        return data, bounds, transform

# 3.7. Validation de la projection et de l'emprise
def validate_projection_and_extent(raster_path, polygons_gdf, target_crs):
    with rasterio.open(raster_path) as src:
        if polygons_gdf.crs != src.crs:
            st.warning("Les polygones ne sont pas dans la même projection que le raster.")
        if not polygons_gdf.within(Polygon.from_bounds(*src.bounds)).all():
            st.warning("Certains polygones sont en dehors de l'emprise du raster.")

# 3.8. Calcul du volume et de la surface
def calculate_volume_and_area_for_each_polygon(mns_path, mnt_path, polygons_gdf):
    with rasterio.open(mns_path) as mns_src, rasterio.open(mnt_path) as mnt_src:
        for index, polygon in polygons_gdf.iterrows():
            mns_data, _ = rasterio.mask.mask(mns_src, [polygon.geometry], crop=True)
            mnt_data, _ = rasterio.mask.mask(mnt_src, [polygon.geometry], crop=True)
            volume = np.sum(mns_data - mnt_data)
            area = polygon.geometry.area
            st.write(f"Polygon {index}: Volume = {volume}, Area = {area}")

# 3.9. Extraction des points sur les bords d'une polygonale
def extract_boundary_points(polygon):
    boundary = polygon.boundary
    return list(boundary.coords)

# 3.10. Calcul de la cote moyenne des élévations sur les bords
def calculate_average_elevation_on_boundary(mns_path, polygon):
    boundary_points = extract_boundary_points(polygon)
    elevations = []
    with rasterio.open(mns_path) as src:
        for point in boundary_points:
            row, col = src.index(point[0], point[1])
            elevations.append(src.read(1)[row, col])
    return np.mean(elevations)

# 3.11. Conversion des polygones en GeoDataFrame
def convert_polygons_to_gdf(polygons):
    return gpd.GeoDataFrame(geometry=polygons)

# 3.12. Conversion des entités dessinées en GeoDataFrame
def convert_drawn_features_to_gdf(features):
    geometries = []
    for feature in features:
        if feature['geometry']['type'] == 'Polygon':
            geometries.append(Polygon(feature['geometry']['coordinates'][0]))
        elif feature['geometry']['type'] == 'LineString':
            geometries.append(LineString(feature['geometry']['coordinates']))
        elif feature['geometry']['type'] == 'Point':
            geometries.append(Point(feature['geometry']['coordinates']))
    return gpd.GeoDataFrame(geometry=geometries)

# 3.13. Trouver un point
def find_point(lat, lon):
    m = folium.Map(location=[lat, lon], zoom_start=15)
    folium.Marker([lat, lon]).add_to(m)
    return m

# 3.14. Génération de rapports
def generate_report(volumes, areas, output_format="PDF"):
    if output_format == "PDF":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for i, (volume, area) in enumerate(zip(volumes, areas)):
            pdf.cell(200, 10, txt=f"Polygon {i}: Volume = {volume}, Area = {area}", ln=True)
        pdf.output("report.pdf")
    elif output_format == "CSV":
        import csv
        with open("report.csv", "w") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Polygon", "Volume", "Area"])
            for i, (volume, area) in enumerate(zip(volumes, areas)):
                writer.writerow([i, volume, area])

# 3.15. Dessin automatique
def auto_draw(mns_path, elevation_threshold):
    with rasterio.open(mns_path) as src:
        data = src.read(1)
        polygons = []
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                if data[i, j] > elevation_threshold:
                    polygons.append(Polygon([(j, i), (j+1, i), (j+1, i+1), (j, i+1)]))
        return polygons

# Module 4: Interface utilisateur avec Streamlit
def main():
    st.title("Application d'Analyse Spatiale")
    st.sidebar.title("Gestion des Couches")

    # Gestion des fichiers téléversés
    uploaded_tiff = st.sidebar.file_uploader("Téléverser un fichier TIFF", type=["tif", "tiff"])
    uploaded_geojson = st.sidebar.file_uploader("Téléverser un fichier GeoJSON", type=["geojson"])

    # Affichage de la carte
    m = folium.Map(location=[5.360, -4.008], zoom_start=8)
    if uploaded_tiff:
        tiff_path = f"uploaded_{uuid.uuid4()}.tif"
        with open(tiff_path, "wb") as f:
            f.write(uploaded_tiff.getbuffer())
        data, bounds, transform = load_tiff(tiff_path)
        add_image_overlay(m, tiff_path, bounds, "TIFF Overlay")
    
    if uploaded_geojson:
        geojson_path = f"uploaded_{uuid.uuid4()}.geojson"
        with open(geojson_path, "wb") as f:
            f.write(uploaded_geojson.getbuffer())
        gdf = gpd.read_file(geojson_path)
        for _, row in gdf.iterrows():
            folium.GeoJson(row.geometry).add_to(m)

    # Affichage de la carte dans Streamlit
    folium_static(m)

# Module 5: Gestion des couches et des entités
def manage_layers():
    if "layers" not in st.session_state:
        st.session_state["layers"] = []
    if "uploaded_layers" not in st.session_state:
        st.session_state["uploaded_layers"] = []
    if "new_features" not in st.session_state:
        st.session_state["new_features"] = []

# Module 6: Affichage de la carte
def display_map():
    m = folium.Map(location=[5.360, -4.008], zoom_start=8)
    return m

# Module 7: Analyse spatiale
def spatial_analysis():
    pass

# Module 8: Optimisations et bonnes pratiques
def optimizations():
    pass

# Module 9: Erreurs potentielles
def handle_errors():
    pass

# Module 10: Améliorations supplémentaires
def additional_improvements():
    pass

# Exécution de l'application
if __name__ == "__main__":
    main()
