import streamlit as st
import geopandas as gpd
import numpy as np
import json
from shapely.geometry import shape, Polygon, LineString
from shapely.ops import unary_union, polygonize
import matplotlib.pyplot as plt
from shapely.validation import make_valid

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
        
        # Application des servitudes avec validation
        buffered = geom.buffer(-params['border_setback'])
        if buffered.is_empty or buffered.area < 100:  # 100 m² minimum
            raise ValueError("La servitude de bordure rend la zone inutilisable")
        
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
        roads_gdf = gpd.GeoDataFrame(geometry=[road_network], crs=gdf.crs)
        
        return blocks_gdf, lots_gdf, roads_gdf
    
    except Exception as e:
        st.error(f"Erreur : {str(e)}")
        return None, None, None

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
        gdf = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326").to_crs("EPSG:3857")
        
        if not gdf.empty:
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
            blocks_gdf, lots_gdf, roads_gdf = process_subdivision(gdf, params)
            
            # Visualisation
            gdf.plot(ax=ax, color='lightgrey', zorder=1)
            
            if blocks_gdf is not None:
                # Affichage des îlots (bordures uniquement)
                blocks_gdf.boundary.plot(ax=ax, color='blue', linewidth=1.5, zorder=2)
                
                # Affichage des lots (transparents avec bordures)
                lots_gdf.boundary.plot(ax=ax, color='red', linewidth=0.5, linestyle='--', zorder=3)
                
                # Affichage des voies
                roads_gdf.plot(ax=ax, color='black', linewidth=2, zorder=4)
                
                # Légende
                ax.set_title(f"Plan de lotissement - {len(lots_gdf)} lots générés")
                st.pyplot(fig)
                
                # Export des résultats
                with tempfile.NamedTemporaryFile(suffix='.geojson') as tmp:
                    combined = gpd.GeoDataFrame(
                        geometry=blocks_gdf.geometry.append(lots_gdf.geometry).append(roads_gdf.geometry),
                        crs=gdf.crs
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
- Réseau de voies intégré automatiquement
- Lots alignés et adjacents dans chaque îlot
- Respect des servitudes et des règles d'urbanisme
- Visualisation hiérarchique (bordures > voies > lots)
- Export vers SIG (format GeoJSON)
""")
