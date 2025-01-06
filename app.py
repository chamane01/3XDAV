import streamlit as st
import laspy
import numpy as np
import rasterio
from rasterio.transform import from_origin
import leafmap.foliumap as leafmap

# Function to create a raster from point cloud data
def create_raster(points, resolution, raster_type='DTM'):
    x = points['x']
    y = points['y']
    z = points['z']

    # Create a grid
    x_min, x_max = np.min(x), np.max(x)
    y_min, y_max = np.min(y), np.max(y)

    cols = int((x_max - x_min) / resolution)
    rows = int((y_max - y_min) / resolution)

    grid = np.zeros((rows, cols), dtype=np.float32)

    for i in range(len(x)):
        col = int((x[i] - x_min) / resolution)
        row = int((y_max - y[i]) / resolution)

        # Ensure indices are within bounds
        if 0 <= row < rows and 0 <= col < cols:
            if raster_type == 'DTM':
                grid[row, col] = min(grid[row, col], z[i]) if grid[row, col] != 0 else z[i]
            else:  # DSM
                grid[row, col] = max(grid[row, col], z[i])

    if np.all(grid == 0):
        raise ValueError("No points fall within the grid bounds. Check the resolution or coordinate range.")

    transform = from_origin(x_min, y_max, resolution, resolution)
    return grid, transform

# Streamlit app
st.title("LAZ/LAS to DTM/DSM Converter")

# File upload
uploaded_file = st.file_uploader("Upload a LAZ/LAS file", type=["laz", "las"])

if uploaded_file is not None:
    try:
        # Read the LAZ/LAS file
        las = laspy.read(uploaded_file)
        st.write(f"Number of points: {len(las.points)}")  # Debug: Check number of points
        st.write(f"X range: {np.min(las.x)} to {np.max(las.x)}")  # Debug: Check X range
        st.write(f"Y range: {np.min(las.y)} to {np.max(las.y)}")  # Debug: Check Y range
        st.write(f"Z range: {np.min(las.z)} to {np.max(las.z)}")  # Debug: Check Z range

        if len(las.points) == 0:
            st.error("The file contains no points. Please upload a valid LAZ/LAS file.")
        else:
            points = {'x': las.x, 'y': las.y, 'z': las.z}

            # Parameters
            resolution = st.slider("Resolution (meters)", 0.1, 10.0, 1.0)

            try:
                # Create DTM and DSM
                dtm, dtm_transform = create_raster(points, resolution, 'DTM')
                dsm, dsm_transform = create_raster(points, resolution, 'DSM')

                # Save rasters to temporary files
                dtm_path = "dtm.tif"
                dsm_path = "dsm.tif"

                with rasterio.open(dtm_path, 'w', driver='GTiff', height=dtm.shape[0], width=dtm.shape[1],
                                   count=1, dtype=dtm.dtype, crs='EPSG:4326', transform=dtm_transform) as dst:
                    dst.write(dtm, 1)

                with rasterio.open(dsm_path, 'w', driver='GTiff', height=dsm.shape[0], width=dsm.shape[1],
                                   count=1, dtype=dsm.dtype, crs='EPSG:4326', transform=dsm_transform) as dst:
                    dst.write(dsm, 1)

                # Display rasters on an interactive map
                st.subheader("DTM and DSM Visualization")
                m = leafmap.Map()
                m.add_raster(dtm_path, layer_name="DTM", colormap="terrain")
                m.add_raster(dsm_path, layer_name="DSM", colormap="terrain")
                m.to_streamlit(height=500)

            except ValueError as e:
                st.error(str(e))

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
