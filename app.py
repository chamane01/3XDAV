import overpy
import pandas as pd
import geojson

# Fonction pour récupérer les routes nationales via l'API Overpass
def download_national_roads():
    api = overpy.Overpass()

    # Requête Overpass pour récupérer les routes nationales (highway=primary, secondary, etc.) avec ID et nom
    query = """
    way["highway"="primary"](5.25, -4.05, 5.30, -3.95);
    way["highway"="secondary"](5.25, -4.05, 5.30, -3.95);
    way["highway"="tertiary"](5.25, -4.05, 5.30, -3.95);
    node(w);
    out ids qt;
    """

    # Exécuter la requête Overpass
    result = api.query(query)

    # Liste pour stocker les données
    roads_data = []
    geojson_data = {"type": "FeatureCollection", "features": []}

    # Parcours des ways et extraction des informations
    for way in result.ways:
        road = {
            "id": way.id,
            "name": way.tags.get("name", "Unknown"),
            "highway": way.tags.get("highway", "Unknown"),
            "nodes": [(node.lat, node.lon) for node in way.nodes]
        }
        roads_data.append(road)

        # Créer une feature GeoJSON pour chaque route
        geojson_feature = {
            "type": "Feature",
            "properties": {
                "id": way.id,
                "name": way.tags.get("name", "Unknown"),
                "highway": way.tags.get("highway", "Unknown")
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [(node.lon, node.lat) for node in way.nodes]
            }
        }
        geojson_data["features"].append(geojson_feature)

    # Convertir en DataFrame Pandas pour CSV
    df = pd.DataFrame(roads_data)

    # Enregistrer en format CSV
    df.to_csv("national_roads.csv", index=False)

    # Enregistrer en format GeoJSON
    with open("national_roads.geojson", "w") as f:
        geojson.dump(geojson_data, f)

    print("Données téléchargées et enregistrées en national_roads.csv et national_roads.geojson")

# Appeler la fonction
download_national_roads()
