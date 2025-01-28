import json
import pandas as pd

# Charger le fichier GeoJSON
with open('votre_fichier.geojson', 'r') as f:
    data = json.load(f)

# Extraire les propriétés et les géométries
features = data['features']
rows = []
for feature in features:
    properties = feature['properties']
    geometry = feature['geometry']
    rows.append({**properties, 'geometry': str(geometry)})

# Convertir en DataFrame et exporter en CSV
df = pd.DataFrame(rows)
df.to_csv('votre_fichier.csv', index=False)
