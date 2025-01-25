import streamlit as st
import geopandas as gpd
import numpy as np
import json
from shapely.geometry import shape, Polygon, LineString
from shapely.ops import unary_union, polygonize
import matplotlib.pyplot as plt

def create_road_network(polygon, road_width):
    """Crée un réseau de voies avec validation des dimensions"""
    bounds = polygon.bounds
    xmin, ymin, xmax, ymax = bounds
    
    # Validation des dimensions
    if (xmax - xmin) < 2 * road_width or (ymax - ymin) < 2 * road_width:
        raise ValueError("La polygonale est trop petite pour les paramètres choisis")
    
    # Calcul sécurisé des intervalles
    x_step = max(road_width * 4, (xmax - xmin) / 4)
    y_step = max(road_width * 3, (ymax - ymin) / 3)
    
    x_roads = []
    current_x = xmin + road_width
    while current_x < xmax - road_width:
        x_roads.append(current_x)
        current_x += x_step
    
    y_roads = []
    current_y = ymin + road_width
    while current_y < ymax - road_width:
        y_roads.append(current_y)
        current_y += y_step
    
    # Création des voies
    vertical = [LineString([(x, ymin), (x, ymax)]) for x in x_roads]
    horizontal = [LineString([(xmin, y), (xmax, y)]) for y in y_roads]
    
    return unary_union(vertical + horizontal)

def process_subdivision(gdf, params):
    try:
        geom = gdf.geometry.iloc[0]
        
        # Application des servitudes avec validation
        buffered = geom.buffer(-params['border_setback'])
        if buffered.is_empty or buffered.area < 100:  # 100 m² minimum
            raise ValueError("La servitude de bordure rend la zone inutilisable")
        
        # Création du réseau de voies sécurisé
        road_network = create_road_network(buffered, params['road_width'])
        
        # Découpe des îlots
        blocks = list(polygonize(road_network))
        
        # Génération des lots avec contrôle de surface
        all_lots = []
        for block in blocks:
            if block.area >= params['lot_area'] * 0.8:
                lots = split_block(block, params)
                all_lots.extend(lots)
        
        return gpd.GeoDataFrame(geometry=all_lots, crs=gdf.crs)
    
    except Exception as e:
        st.error(f"Erreur : {str(e)}")
        return None

# Interface Streamlit et reste du code inchangé...
