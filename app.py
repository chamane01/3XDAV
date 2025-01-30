import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
from io import BytesIO

# Chargement des données
@st.cache_data
def load_data():
    return pd.read_csv("degradations_data.csv")

df = load_data()

# Interface utilisateur
st.title("Tableau de bord des dégradations routières")

# Carte interactive
st.subheader("Carte des dégradations")
map_center = [df["latitude"].mean(), df["longitude"].mean()]
map_ = folium.Map(location=map_center, zoom_start=12)

for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=5,
        color="red",
        fill=True,
        fill_color="red"
    ).add_to(map_)

folium_static(map_)

# Statistiques générales
st.subheader("Statistiques des dégradations")
st.write(df.describe())

# Graphiques
fig, ax = plt.subplots()
df["type_degradation"].value_counts().plot(kind="bar", ax=ax)
ax.set_title("Répartition des types de dégradations")
ax.set_xlabel("Type de dégradation")
ax.set_ylabel("Nombre de cas")
st.pyplot(fig)

# Fonction de génération du rapport
def generate_report():
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    return buffer

# Bouton de génération du rapport
if st.button("Générer le rapport"):
    report_buffer = generate_report()
    st.download_button(label="Télécharger le rapport", data=report_buffer, file_name="rapport.png", mime="image/png")
