import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import split, unary_union
import tempfile
import os

st.title("🛣️ Morcellement de Polygonale pour Lotissement")

# Sidebar pour les paramètres
with st.sidebar:
    st.header("Paramètres de Morcellement")
    lot_area = st.number_input("Superficie désirée par lot (m²)", min_value=100, value=500)
    min_lot_width = st.number_input("Largeur minimale des lots (m)", min_value=5, value=10)
    road_width = st.number_input("Largeur des voies (m)", min_value=3, value=8)
    border_setback = st.number_input("Servitude de bordure (m)", min_value=0, value=5)
    spacing = st.number_input("Espacement entre lots (m)", min_value=0, value=2)

# Téléversement du fichier
uploaded_file = st.file_uploader("Téléversez votre polygonale (GeoJSON/Shapefile)", type=["geojson", "shp"])

def process_subdivision(gdf, params):
    """Fonction principale de traitement"""
    try:
        geom = gdf.geometry.iloc[0]
        
        # Application de la servitude de bordure
        buffered = geom.buffer(-params['border_setback'])
        
        # Vérification de la géométrie
        if buffered.is_empty:
            st.error("La servitude de bordure est trop grande pour la polygonale !")
            return None
            
        # Conversion en UTM pour les calculs métriques
        gdf_utm = gdf.to_crs(epsg=32630)  # À adapter selon la localisation
        
        # Calcul des dimensions globales
        bounds = buffered.bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        
        # Orientation de découpe
        split_axis = 0 if width > height else 1
        
        # Algorithme simplifié de subdivision
        subdivisions = []
        current_polygons = [buffered]
        
        while current_polygons:
            poly = current_polygons.pop()
            area = poly.area
            
            if area < params['lot_area'] * 1.2:  # Marge pour les erreurs
                subdivisions.append(poly)
                continue
                
            # Découpe selon l'axe
            minx, miny, maxx, maxy = poly.bounds
            if split_axis == 0:
                cut_position = minx + (maxx - minx) / 2
                cutter = LineString([(cut_position, miny), (cut_position, maxy)])
            else:
                cut_position = miny + (maxy - miny) / 2
                cutter = LineString([(minx, cut_position), (maxx, cut_position)])
            
            # Application de la découpe
            divided = split(poly, cutter)
            
            # Ajout des nouvelles divisions
            current_polygons.extend(divided.geoms)
        
        # Création du GeoDataFrame résultat
        result_gdf = gpd.GeoDataFrame(geometry=subdivisions, crs=gdf_utm.crs)
        result_gdf['area'] = result_gdf.geometry.area
        
        return result_gdf.to_crs(gdf.crs)
        
    except Exception as e:
        st.error(f"Erreur lors du traitement : {str(e)}")
        return None

if uploaded_file:
    # Lecture du fichier
    with tempfile.TemporaryDirectory() as tmp_dir:
        if uploaded_file.name.endswith('.geojson'):
            path = os.path.join(tmp_dir, 'upload.geojson')
            with open(path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            gdf = gpd.read_file(path)
        else:  # Shapefile
            # Gestion des fichiers .shp nécessaires
            pass
        
        if not gdf.empty:
            # Affichage de la polygonale originale
            st.subheader("Visualisation")
            fig, ax = plt.subplots()
            gdf.plot(ax=ax, color='lightgrey')
            
            # Paramètres
            params = {
                'lot_area': lot_area,
                'min_lot_width': min_lot_width,
                'road_width': road_width,
                'border_setback': border_setback,
                'spacing': spacing
            }
            
            # Traitement
            result_gdf = process_subdivision(gdf, params)
            
            if result_gdf is not None:
                # Affichage des résultats
                result_gdf.plot(ax=ax, edgecolor='red', facecolor='none')
                ax.set_title(f"{len(result_gdf)} lots créés")
                st.pyplot(fig)
                
                # Téléchargement des résultats
                with tempfile.NamedTemporaryFile(suffix='.geojson') as tmp:
                    result_gdf.to_file(tmp.name, driver='GeoJSON')
                    st.download_button(
                        label="Télécharger les lots",
                        data=open(tmp.name, 'rb'),
                        file_name='lots.geojson'
                    )
else:
    st.info("Veuillez téléverser un fichier de polygonale pour commencer")

st.markdown("""
**Notes d'utilisation :**
1. Le fichier doit être dans un système de coordonnées projetées (UTM)
2. L'algorithme est simplifié pour la démonstration
3. Les paramètres idéaux dépendent de la forme de la polygonale
""")
