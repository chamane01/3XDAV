import numpy as np
import geopandas as gpd
from shapely.geometry import shape
import streamlit as st

def calculate_area(polygon):
    """Calcule la surface d'un polygone en mètres carrés."""
    geom = shape(polygon)
    return geom.area

def calculate_volume_without_mnt(mns, mns_bounds, polygons_gdf, reference_altitude):
    """
    Calcule le volume sans utiliser de MNT en utilisant une altitude de référence.
    
    :param mns: Données MNS (Modèle Numérique de Surface)
    :param mns_bounds: Bornes géographiques du MNS
    :param polygons_gdf: GeoDataFrame contenant les polygones
    :param reference_altitude: Altitude de référence pour le calcul du volume
    :return: Volume positif, volume négatif, volume réel
    """
    positive_volume = 0.0
    negative_volume = 0.0
    
    for idx, polygon in polygons_gdf.iterrows():
        try:
            # Masquer les données en dehors du polygone courant
            mask = polygon.geometry
            mns_masked = np.where(mask, mns, np.nan)
            
            # Calculer la différence entre le MNS et l'altitude de référence
            diff = mns_masked - reference_altitude
            
            # Calculer les volumes positif et négatif
            positive_volume += np.nansum(np.where(diff > 0, diff, 0)) * (mns_bounds[2] - mns_bounds[0]) * (mns_bounds[3] - mns_bounds[1]) / (mns.shape[0] * mns.shape[1])
            negative_volume += np.nansum(np.where(diff < 0, diff, 0)) * (mns_bounds[2] - mns_bounds[0]) * (mns_bounds[3] - mns_bounds[1]) / (mns.shape[0] * mns.shape[1])
        except Exception as e:
            st.error(f"Erreur lors du calcul du volume pour le polygone {idx + 1} : {e}")
    
    # Calculer le volume réel (différence entre positif et négatif)
    real_volume = positive_volume + negative_volume
    
    return positive_volume, negative_volume, real_volume

# Exemple d'utilisation
mns = np.random.rand(100, 100) * 100  # Exemple de données MNS
mns_bounds = [0, 0, 100, 100]  # Bornes géographiques
polygons_gdf = gpd.GeoDataFrame({
    'geometry': [shape({
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 50], [50, 50], [50, 0], [0, 0]]]
    })]
})
reference_altitude = 0.0

# Calcul de la surface
area = calculate_area(polygons_gdf.iloc[0].geometry)
st.write(f"Surface du polygone : {area:.2f} m²")

# Calcul du volume
positive_volume, negative_volume, real_volume = calculate_volume_without_mnt(mns, mns_bounds, polygons_gdf, reference_altitude)
st.write(f"Volume positif : {positive_volume:.2f} m³")
st.write(f"Volume négatif : {negative_volume:.2f} m³")
st.write(f"Volume réel : {real_volume:.2f} m³")
