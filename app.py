import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Fonction pour afficher le tableau de bord
def dashboard():
    st.title("Tableau de Bord Ageroute Côte d'Ivoire")

    # Section 1: Carte Interactive des Routes
    st.header("Carte Interactive de Toutes les Routes")
    m = folium.Map(location=[7.5399, -5.5471], zoom_start=7)  # Centré sur la Côte d'Ivoire
    folium_static(m)

    # Section 2: Statistiques des Défauts
    st.header("Statistiques des Défauts")
    selected_month = st.selectbox("Sélectionner un mois", ["Jan", "Fév", "Mar", "Avr"])
    if selected_month:
        st.write(f"Statistiques pour {selected_month}:")
        st.write("- Fissures: En cours de développement")
        st.write("- Nids-de-poule: En cours de développement")
        st.write("- Usures: En cours de développement")

    # Section 3: Voir Toutes les Routes
    st.header("Voir Toutes les Routes")
    if st.button("Afficher toutes les routes"):
        st.write("Liste des routes:")
        st.write("- A1 - Autoroute du Nord (Abidjan-Yamoussoukro)")
        st.write("- A3 - Autoroute Abidjan-Grand Bassam")
        st.write("- Nationale A1 (Yamoussoukro-Bouaké)")
        st.write("- Nationale A3 (Abidjan-Adzopé)")
        st.write("- Pont HKB")

    # Section 4: Inspections Réalisées
    st.header("Inspections Réalisées")
    st.write("Statistiques des 5 derniers mois: En cours de développement")

    # Section 5: Génération de Rapports
    st.header("Générer des Rapports")
    report_type = st.radio("Type de rapport", ["Journalier", "Mensuel", "Annuel"])
    if st.button("Générer le rapport"):
        st.write(f"Génération du rapport {report_type.lower()} en cours de développement")

    # Section 6: Alertes
    st.header("Alertes")
    st.write("Nid-de-poule dangereux détecté sur l’Autoroute du Nord (Section Yamoussoukro-Bouaké)")
    st.write("Fissures multiples sur le Pont HKB à Abidjan")
    st.write("Usures importantes sur la Nationale A3 (Abidjan-Adzopé)")

    # Section 7: Inspections par Date
    st.header("Inspections par Date")
    selected_date = st.date_input("Sélectionner une date")
    if st.button("Voir les inspections pour cette date"):
        st.write(f"Inspections pour {selected_date}: En cours de développement")

    # Section 8: Options de Rapport
    st.header("Options de Rapport")
    if st.button("Voir statistiques par route"):
        st.write("Statistiques par route: En cours de développement")
    if st.button("Voir toutes les statistiques d’inspection"):
        st.write("Toutes les statistiques d’inspection: En cours de développement")

    # Pied de page
    st.sidebar.image("logo_gouvernement.png", width=100)
    st.sidebar.write("Gouvernement")
    st.sidebar.write("Agéroute")

# Fonction pour ajouter une mission
def add_mission():
    st.title("Ajouter une Mission")
    uploaded_files = st.file_uploader("Charger les images de la mission drone", type=["jpg", "png"], accept_multiple_files=True)
    if uploaded_files:
        st.write(f"{len(uploaded_files)} images chargées.")
        if st.button("Lancer l'analyse par IA"):
            st.write("Analyse en cours...")
            # Ici, vous pouvez ajouter le code pour l'analyse IA
            st.write("Résultats de l'analyse: En cours de développement")

# Page d'Accueil
st.sidebar.title("Navigation")
choice = st.sidebar.radio("Choisir une option", ["Tableau de Bord", "Ajouter une Mission"])

if choice == "Tableau de Bord":
    dashboard()
elif choice == "Ajouter une Mission":
    add_mission()
