import streamlit as st
import folium
import sqlite3
import json
import pandas as pd
import plotly.express as px
from streamlit_folium import st_folium
from io import BytesIO

# Connexion à la base de données SQLite
conn = sqlite3.connect('routes_defauts.db')
cur = conn.cursor()

# Charger les données des routes à partir du fichier JSON
with open("routeQSD.txt", "r") as f:
    routes_data = json.load(f)

# Extraire les coordonnées et noms des routes sous forme de LineStrings
routes_ci = []
for feature in routes_data["features"]:
    if feature["geometry"]["type"] == "LineString":
        routes_ci.append({
            "coords": feature["geometry"]["coordinates"],
            "nom": feature["properties"].get("ID", "Route inconnue")
        })

# Récupérer les données des dégradations depuis la base de données
cur.execute("SELECT route, categorie, gravite, latitude, longitude, date, heure, ville FROM Defauts")
defauts_data = cur.fetchall()
df_defauts = pd.DataFrame(defauts_data, columns=["route", "categorie", "gravite", "latitude", "longitude", "date", "heure", "ville"])

# Dégradations et couleurs associées
degradations = {
    "déformation orniérage": "red",
    "fissure de fatigue": "blue",
    "faïençage de fatigue": "green",
    "fissure de retrait": "purple",
    "fissure anarchique": "orange",
    "réparation": "pink",
    "nid de poule": "brown",
    "arrachements": "gray",
    "fluage": "yellow",
    "dénivellement accotement": "cyan",
    "chaussée détruite": "black",
    "envahissement végétation": "magenta",
    "assainissement": "teal"
}

# Interface Streamlit
st.title("Dégradations Routières : Carte des Inspections Réelles")

# Carte Folium
m = folium.Map(location=[6.5, -5], zoom_start=7)

# Ajouter les routes
for route in routes_ci:
    folium.PolyLine(
        locations=[(lat, lon) for lon, lat in route["coords"]],
        color="blue",
        weight=3,
        opacity=0.7,
        tooltip=route["nom"]
    ).add_to(m)

# Ajouter les dégradations
for defaut in defauts_data:
    route, categorie, gravite, lat, lon, date, heure, ville = defaut
    couleur = degradations.get(categorie, "gray")
    
    folium.Circle(
        location=[lat, lon],
        radius=3 + gravite * 2,
        color=couleur,
        fill=True,
        fill_color=couleur,
        popup=(
            f"Route: {route}<br>"
            f"Catégorie: {categorie}<br>"
            f"Gravité: {gravite}<br>"
            f"Date: {date}<br>"
            f"Heure: {heure}<br>"
            f"Ville: {ville}"
        ),
        tooltip=f"{categorie} (Gravité {gravite})"
    ).add_to(m)

# Affichage de la carte
st_folium(m, width=800, height=600)

# Tableau de bord
st.header("Tableau de Bord des Dégradations Routières")

# Statistiques
st.subheader("Statistiques Globales")
col1, col2, col3 = st.columns(3)
col1.metric("Nombre Total de Dégradations", df_defauts.shape[0])
col2.metric("Nombre de Routes Inspectées", df_defauts["route"].nunique())
col3.metric("Nombre de Villes Touchées", df_defauts["ville"].nunique())

# Graphiques
st.subheader("Répartition des Dégradations par Catégorie")
fig_categories = px.pie(df_defauts, names="categorie", title="Répartition des Dégradations par Catégorie")
st.plotly_chart(fig_categories)

st.subheader("Distribution des Niveaux de Gravité")
fig_gravite = px.histogram(df_defauts, x="gravite", nbins=10, title="Distribution des Niveaux de Gravité")
st.plotly_chart(fig_gravite)

st.subheader("Dégradations par Ville")
defauts_par_ville = df_defauts["ville"].value_counts().reset_index()
defauts_par_ville.columns = ["ville", "nombre_de_degradations"]
fig_ville = px.bar(defauts_par_ville, x="ville", y="nombre_de_degradations", title="Nombre de Dégradations par Ville")
st.plotly_chart(fig_ville)

st.subheader("Évolution Temporelle des Dégradations")
df_defauts["date"] = pd.to_datetime(df_defauts["date"])
defauts_par_date = df_defauts.groupby(df_defauts["date"].dt.date).size().reset_index(name="nombre_de_degradations")
fig_date = px.line(defauts_par_date, x="date", y="nombre_de_degradations", title="Évolution du Nombre de Dégradations au Fil du Temps")
st.plotly_chart(fig_date)

# Section Génération de Rapport
st.header("📄 Génération de Rapport Personnalisé")

# Sélections utilisateur
st.subheader("Sélectionnez les éléments à inclure dans le rapport")

col1, col2 = st.columns(2)

# Filtres
selected_categories = col1.multiselect("Catégories de Dégradations", df_defauts["categorie"].unique(), default=df_defauts["categorie"].unique())
selected_villes = col2.multiselect("Villes", df_defauts["ville"].unique(), default=df_defauts["ville"].unique())

# Sélection des champs à inclure
selected_columns = st.multiselect("Champs à inclure dans le rapport", df_defauts.columns.tolist(), default=df_defauts.columns.tolist())

# Filtrer les données selon les choix
filtered_df = df_defauts[(df_defauts["categorie"].isin(selected_categories)) & (df_defauts["ville"].isin(selected_villes))][selected_columns]

# Affichage du rapport
st.subheader("📊 Rapport Généré")
st.dataframe(filtered_df)

# Bouton d'exportation CSV
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

csv_data = convert_df_to_csv(filtered_df)

st.download_button(
    label="📥 Télécharger le Rapport (CSV)",
    data=csv_data,
    file_name="rapport_degradations.csv",
    mime="text/csv"
)

# Fermeture de la connexion à la base de données
conn.close()
