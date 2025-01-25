import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString
from shapely.ops import split, unary_union, polygonize
import numpy as np
import json
from shapely.geometry import shape
import fiona

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
    """Crée un réseau de voies en grille"""
    bounds = polygon.bounds
    xmin, ymin, xmax, ymax = bounds
    
    # Calcul des intervalles de voies
    x_roads = np.arange(xmin + road_width, xmax, road_width * 4)
    y_roads = np.arange(ymin + road_width, ymax, road_width * 3)
    
    # Création des lignes de voies
    vertical = [LineString([(x, ymin), (x, ymax)]) for x in x_roads]
    horizontal = [LineString([(xmin, y), (xmax, y)]) for y in y_roads]
    
    # Découpe du polygone initial
    roads = unary_union(vertical + horizontal)
    return roads

def split_block(block, target_area, min_frontage, max_depth):
    """Découpe un îlot en lots adjacents"""
    lots = []
    current = block
    
    while current.area > target_area * 0.8:
        # Découpe selon la profondeur maximale
        bounds = current.bounds
        width = bounds[2] - bounds[0]
        
        if width > max_depth:
            cut = bounds[0] + max_depth
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
        
        if lot.area >= target_area * 0.8:
            lots.append(lot)
        
        current = remaining
        if current.is_empty:
            break
    
    return lots

def process_subdivision(gdf, params):
    try:
        geom = gdf.geometry.iloc[0]
        
        # Application des servitudes
        main_area = geom.buffer(-params['border_setback'])
        
        # Création du réseau de voies
        road_network = create_road_network(main_area, params['road_width'])
        
        # Découpe des îlots
        blocks = list(polygonize(road_network))
        
        # Génération des lots dans chaque îlot
        all_lots = []
        for block in blocks:
            if block.within(main_area):
                lots = split_block(block, 
                                 params['lot_area'],
                                 params['min_frontage'],
                                 params['max_depth'])
                all_lots.extend(lots)
        
        # Création des GeoDataFrames
        blocks_gdf = gpd.GeoDataFrame(geometry=blocks, crs=gdf.crs)
        lots_gdf = gpd.GeoDataFrame(geometry=all_lots, crs=gdf.crs)
        roads_gdf = gpd.GeoDataFrame(geometry=[road_network], crs=gdf.crs)
        
        return blocks_gdf, lots_gdf, roads_gdf
        
    except Exception as e:
        st.error(f"Erreur de traitement : {str(e)}")
        return None, None, None

if uploaded_file:
    try:
        # Lecture directe depuis le buffer mémoire
        content = uploaded_file.getvalue().decode('utf-8')
        geojson = json.loads(content)
        
        # Validation de la structure GeoJSON
        if not all(key in geojson for key in ['type', 'features']):
            raise ValueError("Format GeoJSON invalide")
            
        # Conversion en geometries Shapely
        geometries = []
        for feature in geojson['features']:
            geom = shape(feature['geometry'])
            if not geom.is_valid:
                geom = geom.buffer(0)  # Correction des géométries
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
    except fiona.errors.DriverError:
        st.error("Format de fichier non supporté - Utilisez un GeoJSON valide")
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
