import streamlit as st
import overpy

# Fonction pour récupérer les routes nationales via l'API Overpass
def download_national_roads():
    api = overpy.Overpass()

    query = """
    way["highway"="primary"](5.25, -4.05, 5.30, -3.95);
    way["highway"="secondary"](5.25, -4.05, 5.30, -3.95);
    way["highway"="tertiary"](5.25, -4.05, 5.30, -3.95);
    node(w);
    out ids qt;
    """
    
    try:
        result = api.query(query)
        st.write(f"Données récupérées: {len(result.ways)} routes trouvées.")  # Debug

        # Par exemple, afficher les 3 premières routes récupérées
        for way in result.ways[:3]:
            st.write(f"ID: {way.id}, Name: {way.tags.get('name', 'Inconnu')}")
        
    except Exception as e:
        st.error(f"Une erreur est survenue : {e}")

# Appel de la fonction
download_national_roads()
