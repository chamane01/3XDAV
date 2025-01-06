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
        if raster_type == 'DTM':
            grid[row, col] = min(grid[row, col], z[i]) if grid[row, col] != 0 else z[i]
        else:  # DSM
            grid[row, col] = max(grid[row, col], z[i])

    transform = from_origin(x_min, y_max, resolution, resolution)
    return grid, transform

# Streamlit app
st.title("LAZ/LAS to DTM/DSM Converter")

# File upload
uploaded_file = st.file_uploader("Upload a LAZ/LAS file", type=["laz", "las"])

if uploaded_file is not None:
    # Read the LAZ/LAS file
    las = laspy.read(uploaded_file)
    points = {'x': las.x, 'y': las.y, 'z': las.z}

    # Parameters
    resolution = st.slider("Resolution (meters)", 0.1, 10.0, 1.0)

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
