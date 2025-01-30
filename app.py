import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt

# 📌 Charger les données
@st.cache_data
def charger_donnees():
    return pd.read_csv("data_defauts.csv")  # Assure-toi d'avoir ce fichier

df_defauts = charger_donnees()

# 📌 Interface principale
st.title("📊 Analyse des Dégradations Routières")

st.sidebar.header("Filtres")
ville_selectionnee = st.sidebar.selectbox("Sélectionnez une ville :", ["Toutes"] + list(df_defauts["ville"].unique()))

# 📌 Filtrage des données
if ville_selectionnee != "Toutes":
    df_defauts = df_defauts[df_defauts["ville"] == ville_selectionnee]

# 📊 **Graphique 1 : Répartition des Dégradations par Catégorie**
fig_categories = px.bar(df_defauts, x="categorie", title="Répartition des Dégradations par Catégorie", color="categorie")
st.plotly_chart(fig_categories)

# 📊 **Graphique 2 : Distribution des Niveaux de Gravité**
fig_gravite = px.histogram(df_defauts, x="gravite", title="Distribution des Niveaux de Gravité", nbins=5)
st.plotly_chart(fig_gravite)

# 📊 **Graphique 3 : Dégradations par Ville**
fig_ville = px.bar(df_defauts, x="ville", title="Dégradations par Ville", color="ville")
st.plotly_chart(fig_ville)

# 📊 **Graphique 4 : Évolution Temporelle des Dégradations**
df_defauts["date"] = pd.to_datetime(df_defauts["date"])
fig_date = px.line(df_defauts, x="date", y="nombre", title="Évolution Temporelle des Dégradations")
st.plotly_chart(fig_date)

# 📄 **Fonction pour générer un rapport PDF**
def generer_rapport(selection):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 📝 Ajouter un titre
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 50, "Rapport d'Inspection Routière")

    y_position = height - 80

    # 📌 Ajouter les statistiques globales si sélectionnées
    if "Statistiques Globales" in selection:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_position, "Statistiques Globales :")
        y_position -= 20
        c.setFont("Helvetica", 10)
        c.drawString(70, y_position, f"Nombre Total de Dégradations : {df_defauts.shape[0]}")
        y_position -= 15
        c.drawString(70, y_position, f"Nombre de Routes Inspectées : {df_defauts['route'].nunique()}")
        y_position -= 15
        c.drawString(70, y_position, f"Nombre de Villes Touchées : {df_defauts['ville'].nunique()}")
        y_position -= 30

    # 📌 Fonction pour insérer un graphe matplotlib dans le PDF
    def ajouter_graphique(fig, y_position):
        img_buffer = BytesIO()
        fig.savefig(img_buffer, format="png")
        img_buffer.seek(0)
        c.drawImage(img_buffer, 50, y_position - 200, width=500, height=180)
        return y_position - 210

    # 📌 Ajouter les graphiques sélectionnés
    if "Répartition des Dégradations par Catégorie" in selection:
        y_position -= 20
        fig_categories.write_image("categorie_chart.png")
        c.drawString(50, y_position, "Répartition des Dégradations par Catégorie :")
        y_position = ajouter_graphique(fig_categories, y_position)

    if "Distribution des Niveaux de Gravité" in selection:
        y_position -= 20
        fig_gravite.write_image("gravite_chart.png")
        c.drawString(50, y_position, "Distribution des Niveaux de Gravité :")
        y_position = ajouter_graphique(fig_gravite, y_position)

    if "Dégradations par Ville" in selection:
        y_position -= 20
        fig_ville.write_image("ville_chart.png")
        c.drawString(50, y_position, "Dégradations par Ville :")
        y_position = ajouter_graphique(fig_ville, y_position)

    if "Évolution Temporelle des Dégradations" in selection:
        y_position -= 20
        fig_date.write_image("date_chart.png")
        c.drawString(50, y_position, "Évolution Temporelle des Dégradations :")
        y_position = ajouter_graphique(fig_date, y_position)

    # 📌 Sauvegarde du PDF
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# 📌 **Interface de Génération de Rapport**
st.header("📄 Génération de Rapport")

# 📌 Options de sélection des sections du rapport
options = [
    "Statistiques Globales",
    "Répartition des Dégradations par Catégorie",
    "Distribution des Niveaux de Gravité",
    "Dégradations par Ville",
    "Évolution Temporelle des Dégradations"
]

selection = st.multiselect("📌 Sélectionnez les éléments à inclure :", options, default=options)

if st.button("📄 Générer Rapport PDF"):
    buffer = generer_rapport(selection)
    st.download_button("📥 Télécharger le Rapport", buffer, file_name="rapport_degradations.pdf", mime="application/pdf")
