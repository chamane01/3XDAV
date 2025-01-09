import streamlit as st
import sqlite3
from datetime import datetime

# Fonction pour se connecter à la base de données SQLite
def connect_to_db():
    conn = sqlite3.connect('ageroute.db')
    return conn

# Fonction pour afficher toutes les missions
def show_missions(conn):
    cur = conn.cursor()
    cur.execute('SELECT * FROM Missions')
    missions = cur.fetchall()
    if missions:
        st.write("### Liste des Missions")
        for mission in missions:
            st.write(f"**ID:** {mission[0]}, **Date:** {mission[1]}, **Images:** {mission[2]}")
    else:
        st.write("Aucune mission trouvée.")

# Fonction pour afficher tous les défauts
def show_defauts(conn):
    cur = conn.cursor()
    cur.execute('SELECT * FROM Defauts')
    defauts = cur.fetchall()
    if defauts:
        st.write("### Liste des Défauts")
        for defaut in defauts:
            st.write(f"**ID:** {defaut[0]}, **Mission ID:** {defaut[1]}, **Type:** {defaut[2]}, **Latitude:** {defaut[3]}, **Longitude:** {defaut[4]}")
    else:
        st.write("Aucun défaut trouvé.")

# Fonction pour ajouter une mission
def add_mission(date, images):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO Missions (date, images)
        VALUES (?, ?)
    ''', (date, images))
    conn.commit()
    conn.close()
    st.success("Mission ajoutée avec succès !")

# Fonction pour supprimer une mission
def delete_mission(mission_id):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM Missions WHERE id = ?', (mission_id,))
    conn.commit()
    conn.close()
    st.success("Mission supprimée avec succès !")

# Fonction pour mettre à jour une mission
def update_mission(mission_id, date, images):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute('''
        UPDATE Missions
        SET date = ?, images = ?
        WHERE id = ?
    ''', (date, images, mission_id))
    conn.commit()
    conn.close()
    st.success("Mission mise à jour avec succès !")

# Interface Streamlit
def main():
    st.title("Tableau de Bord Ageroute Côte d'Ivoire")

    # Connexion à la base de données
    conn = connect_to_db()

    # Navigation
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Choisir une option", ["Voir les Missions", "Ajouter une Mission", "Supprimer une Mission", "Mettre à Jour une Mission"])

    if choice == "Voir les Missions":
        st.header("Voir les Missions et Défauts")
        show_missions(conn)
        show_defauts(conn)

    elif choice == "Ajouter une Mission":
        st.header("Ajouter une Mission")
        date = st.date_input("Date de la mission")
        images = st.text_input("Images (séparées par des virgules)")
        if st.button("Ajouter la mission"):
            add_mission(date, images)

    elif choice == "Supprimer une Mission":
        st.header("Supprimer une Mission")
        mission_id = st.number_input("ID de la mission à supprimer", min_value=1)
        if st.button("Supprimer la mission"):
            delete_mission(mission_id)

    elif choice == "Mettre à Jour une Mission":
        st.header("Mettre à Jour une Mission")
        mission_id = st.number_input("ID de la mission à mettre à jour", min_value=1)
        date = st.date_input("Nouvelle date de la mission")
        images = st.text_input("Nouvelles images (séparées par des virgules)")
        if st.button("Mettre à jour la mission"):
            update_mission(mission_id, date, images)

    # Fermer la connexion
    conn.close()

if __name__ == "__main__":
    main()
