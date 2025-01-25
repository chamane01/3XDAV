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

# Téléversement du fichier
uploaded_file = st.file_uploader("Téléversez votre polygonale (GeoJSON)", type=["geojson"])


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
        gdf = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326")  # WGS84
        
        # Conversion en système de coordonnées projetées (Web Mercator)
        gdf = gdf.to_crs("EPSG:3857")  # Pour les calculs métriques
        
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
# Interface Streamlit et reste du code inchangé...
