import streamlit as st
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import folium
from folium.plugins import Draw
from streamlit_folium import folium_static
import numpy as np
from shapely.geometry import shape
import pyproj

# Set page title
st.title('Volume Calculation from DEM and TIFF')

# File uploaders
tiff_file = st.file_uploader("Upload TIFF file", type=["tiff", "tif"])
dem_file = st.file_uploader("Upload DEM file", type=["tiff", "tif", "dem"])

if tiff_file and dem_file:
    # Read TIFF file
    tiff_bytes = tiff_file.read()
    tiff_raster = rasterio.MemoryFile(tiff_bytes).open()
    tiff_crs = tiff_raster.crs.to_epsg()  # Get CRS as EPSG code
    tiff_transform = tiff_raster.transform
    tiff_array = tiff_raster.read(1)

    # Read DEM file
    dem_bytes = dem_file.read()
    dem_raster = rasterio.MemoryFile(dem_bytes).open()
    dem_crs = dem_raster.crs.to_epsg()  # Get CRS as EPSG code
    dem_transform = dem_raster.transform
    dem_array = dem_raster.read(1)

    # Reproject DEM to match TIFF CRS if necessary
    if dem_crs != tiff_crs:
        st.write(f"Reprojecting DEM from EPSG:{dem_crs} to EPSG:{tiff_crs}...")
        transform, width, height = calculate_default_transform(
            f"EPSG:{dem_crs}", f"EPSG:{tiff_crs}", dem_raster.width, dem_raster.height, *dem_raster.bounds
        )
        reprojected_dem = np.empty((height, width))
        reproject(
            source=dem_array,
            destination=reprojected_dem,
            src_transform=dem_transform,
            src_crs=f"EPSG:{dem_crs}",
            dst_transform=transform,
            dst_crs=f"EPSG:{tiff_crs}",
            resampling=Resampling.nearest
        )
        dem_array = reprojected_dem
        dem_transform = transform

    # Reproject TIFF and DEM to EPSG:4326 for Folium display
    if tiff_crs != 4326:
        st.write(f"Reprojecting TIFF from EPSG:{tiff_crs} to EPSG:4326 for map display...")
        transform_4326, width_4326, height_4326 = calculate_default_transform(
            f"EPSG:{tiff_crs}", "EPSG:4326", tiff_raster.width, tiff_raster.height, *tiff_raster.bounds
        )
        reprojected_tiff = np.empty((height_4326, width_4326))
        reproject(
            source=tiff_array,
            destination=reprojected_tiff,
            src_transform=tiff_transform,
            src_crs=f"EPSG:{tiff_crs}",
            dst_transform=transform_4326,
            dst_crs="EPSG:4326",
            resampling=Resampling.nearest
        )
        tiff_array = reprojected_tiff
        tiff_transform = transform_4326

    # Create a folium map centered on the TIFF raster
    bounds = rasterio.warp.transform_bounds(f"EPSG:{tiff_crs}", "EPSG:4326", *tiff_raster.bounds)
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    m = folium.Map(location=center, zoom_start=10)

    # Display TIFF as an image overlay
    folium.raster_layers.ImageOverlay(
        image=tiff_array,
        bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        opacity=0.7,
        interactive=True,
        cross_origin=False,
        zindex=1
    ).add_to(m)

    # Add Draw plugin for drawing polygons
    draw = Draw(export=True)
    draw.add_to(m)

    # Display the map using folium_static
    folium_static(m)

    # Button to confirm the drawn polygon
    if st.button("Confirm Polygon"):
        # Use JavaScript to capture the drawn polygon and send it to Streamlit
        st.markdown(
            """
            <script>
            // Listen for draw events
            map.on('draw:created', function (e) {
                const layer = e.layer;
                const geoJSON = layer.toGeoJSON();
                const data = JSON.stringify(geoJSON);
                // Send the data to Streamlit
                parent.window.stSessionState.set('drawn_polygon', data);
            });
            </script>
            """,
            unsafe_allow_html=True
        )

        # Get the drawn polygon from Streamlit's session state
        if 'drawn_polygon' in st.session_state:
            drawn_polygon = st.session_state.drawn_polygon
            if drawn_polygon:
                drawn_polygon = shape(drawn_polygon['geometry'])

                # Reproject the polygon to match the DEM CRS
                transformer = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{dem_crs}", always_xy=True)
                polygon_coords = list(drawn_polygon.exterior.coords)
                reprojected_coords = [transformer.transform(x, y) for x, y in polygon_coords]
                reprojected_polygon = Polygon(reprojected_coords)

                # Create a mask for the DEM using the polygon
                from rasterio.features import geometry_mask
                mask = geometry_mask([reprojected_polygon], transform=dem_transform, out_shape=dem_array.shape, invert=True)

                # Extract elevation values within the polygon
                elevation_values = dem_array[mask]

                # Calculate the volume
                cell_area = abs(dem_transform[0] * dem_transform[4])  # Cell area in square meters
                volume = np.sum(elevation_values) * cell_area  # Volume in cubic meters

                # Display the result
                st.write(f"**Calculated Volume:** {volume:.2f} cubic meters")
        else:
            st.warning("Please draw a polygon on the map and confirm it.")

else:
    st.write("Please upload both TIFF and DEM files.")
