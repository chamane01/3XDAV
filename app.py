import streamlit as st
import geopandas as gpd
import numpy as np
import json
from shapely.geometry import shape, Polygon, LineString
from shapely.ops import unary_union, polygonize
import matplotlib.pyplot as plt
from shapely.validation import make_valid
import pyproj

# Configuration de la page Streamlit
st.set_page_config(page_title="Générateur de Lotissement", layout="wide")
st.title("🏘️ Générateur de Lotissement Intelligent")

# Sidebar pour les paramètres
with st.sidebar:
    st.header("Paramètres de conception")
    lot_area = st.number_input("Superficie par lot (m²)", min_value=100, value=500)
    road_width = st.number_input("Largeur des voies (m)", min_value=5, value=8)
    border_setback = st.number_input("Servitude de bordure (m)", min_value=0, value=5)
    min_frontage = st.number_input("Largeur minimale de façade (m)", min_value=5, value=10)
    max_depth = st.number_input("Profondeur maximale des lots (m)", min_value=10, value=30)

# Téléversement du fichier
uploaded_file = st.file_uploader("Téléversez votre polygonale (GeoJSON)", type=["geojson"])

def get_utm_zone(longitude):
    """Détermine la zone UTM à partir de la longitude"""
    return int((longitude + 180) // 6) + 1

def reproject_to_utm(gdf):
    """Reprojette un GeoDataFrame en UTM"""
    centroid = gdf.geometry.centroid.iloc[0]
    utm_zone = get_utm_zone(centroid.x)
    hemisphere = "north" if centroid.y >= 0 else "south"
    epsg_code = 32600 + utm_zone if hemisphere == "north" else 32700 + utm_zone
    return gdf.to_crs(epsg=epsg_code)

def create_road_network(polygon, road_width):
    """Crée un réseau de voies en grille avec validation des dimensions"""
    bounds = polygon.bounds
    xmin, ymin, xmax, ymax = bounds
    
    # Validation des dimensions
    if (xmax - xmin) < 2 * road_width or (ymax - ymin) < 2 * road_width:
        raise ValueError("La polygonale est trop petite pour les paramètres choisis")
    
    # Calcul des intervalles de voies
    x_step = max(road_width * 4, (xmax - xmin) / 4)
    y_step = max(road_width * 3, (ymax - ymin) / 3)
    
    # Création des voies verticales
    x_roads = []
    current_x = xmin + road_width
    while current_x < xmax - road_width:
        x_roads.append(LineString([(current_x, ymin), (current_x, ymax)]))
        current_x += x_step
    
    # Création des voies horizontales
    y_roads = []
    current_y = ymin + road_width
    while current_y < ymax - road_width:
        y_roads.append(LineString([(xmin, current_y), (xmax, current_y)]))
        current_y += y_step
    
    # Union des voies
    return unary_union(x_roads + y_roads)

def split_block(block, params):
    """Découpe un îlot en lots adjacents"""
    lots = []
    current = block
    
    while current.area > params['lot_area'] * 0.8:
        bounds = current.bounds
        width = bounds[2] - bounds[0]
        
        if width > params['max_depth']:
            cut = bounds[0] + params['max_depth']
            lot = Polygon([
                (bounds[0], bounds[1]),
                (cut, bounds[1]),
                (cut, bounds[3]),
                (bounds[0], bounds[3])
            ])
            remaining = current.difference(lot)
        else:
            lot = current
            remaining = Polygon()
        
        if lot.area >= params['lot_area'] * 0.8:
            lots.append(lot)
        
        current = remaining
        if current.is_empty:
            break
    
    return lots

def process_subdivision(gdf, params):
    try:
        geom = gdf.geometry.iloc[0]
        
        # Application des servitudes avec validation dynamique
        min_buffer = 0.1  # 10 cm minimum pour éviter des géométries vides
        buffered = geom.buffer(-max(params['border_setback'], min_buffer))
        
        # Vérification de la zone utilisable
        if buffered.is_empty:
            raise ValueError("La servitude de bordure est trop grande pour la polygonale.")
        if buffered.area < params['lot_area']:
            raise ValueError(f"La zone utilisable ({buffered.area:.1f} m²) est trop petite pour créer un lot de {params['lot_area']} m².")
        
        # Création du réseau de voies
        road_network = create_road_network(buffered, params['road_width'])
        
        # Découpe des îlots
        blocks = list(polygonize(road_network))
        
        # Génération des lots
        all_lots = []
        for block in blocks:
            if block.area >= params['lot_area'] * 0.8:
                lots = split_block(block, params)
                all_lots.extend(lots)
        
        # Création des GeoDataFrames
        blocks_gdf = gpd.GeoDataFrame(geometry=blocks, crs=gdf.crs)
        lots_gdf = gpd.GeoDataFrame(geometry=all_lots, crs=gdf.crs)
        
        return blocks_gdf, lots_gdf
    
    except Exception as e:
        st.error(f"Erreur : {str(e)}")
        return None, None

if uploaded_file:
    try:
        # Lecture du fichier GeoJSON
        content = uploaded_file.getvalue().decode('utf-8')
        geojson = json.loads(content)
        
        # Validation de la structure GeoJSON
        if not all(key in geojson for key in ['type', 'features']):
            raise ValueError("Format GeoJSON invalide")
        
        # Conversion en géométries Shapely
        geometries = []
        for feature in geojson['features']:
            geom = shape(feature['geometry'])
            if not geom.is_valid:
                geom = make_valid(geom)  # Correction des géométries
            geometries.append(geom)
        
        # Création du GeoDataFrame
        gdf = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326")
        
        # Reprojection en UTM
        gdf_utm = reproject_to_utm(gdf)
        
        if not gdf_utm.empty:
            st.subheader("Visualisation du projet")
            fig, ax = plt.subplots(figsize=(10, 10))
            
            # Paramètres
            params = {
                'lot_area': lot_area,
                'road_width': road_width,
                'border_setback': border_setback,
                'min_frontage': min_frontage,
                'max_depth': max_depth
            }
            
            # Traitement
            blocks_gdf, lots_gdf = process_subdivision(gdf_utm, params)
            
            # Visualisation
            if blocks_gdf is not None:
                # Affichage des îlots (bordures uniquement)
                blocks_gdf.boundary.plot(ax=ax, color='blue', linewidth=1.5, zorder=2)
                
                # Affichage des lots (transparents avec bordures)
                lots_gdf.boundary.plot(ax=ax, color='red', linewidth=0.5, linestyle='--', zorder=3)
                
                # Légende
                ax.set_title(f"Plan de lotissement - {len(lots_gdf)} lots générés")
                st.pyplot(fig)
                
                # Export des résultats
                with tempfile.NamedTemporaryFile(suffix='.geojson') as tmp:
                    combined = gpd.GeoDataFrame(
                        geometry=blocks_gdf.geometry.append(lots_gdf.geometry),
                        crs=gdf_utm.crs
                    )
                    combined.to_file(tmp.name, driver='GeoJSON')
                    st.download_button(
                        label="📤 Télécharger le projet complet",
                        data=open(tmp.name, 'rb'),
                        file_name='lotissement.geojson'
                    )
    
    except json.JSONDecodeError:
        st.error("Erreur de décodage JSON - Vérifiez le format du fichier")
    except ValueError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Erreur inattendue : {str(e)}")
else:
    st.info("📤 Veuillez téléverser un fichier GeoJSON pour commencer")

st.markdown("""
**Fonctionnalités clés :**
- Reprojection automatique en UTM pour les calculs métriques.
- Gestion des fichiers en `EPSG:4326` (WGS84) ou UTM.
- Îlots bien définis avec des lots alignés.
- Routes implicites représentées par les espaces entre les îlots.
- Export vers SIG (format GeoJSON).
""")
