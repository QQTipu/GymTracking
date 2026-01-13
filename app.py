import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import os
import numpy as np

# Imports locaux
import database
import auth
import utils

# Configuration de la page
st.set_page_config(
    page_title="Tracker Musculation",
    page_icon="💪",
    layout="wide"
)

# ============= CONFIGURATION SUPABASE =============
supabase = database.init_supabase()

# Initialiser l'état de connexion
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Vérifier si l'utilisateur est connecté
if not st.session_state.logged_in:
    auth.login_page(supabase)
    st.stop()

# ============= APPLICATION PRINCIPALE =============

# Initialiser le session state
if 'history' not in st.session_state:
    st.session_state.history = {}

if 'current_weights' not in st.session_state:
    st.session_state.current_weights = {}

if 'start_date' not in st.session_state:
    st.session_state.start_date = datetime.now().strftime("%Y-%m-%d")

if 'skipped_days' not in st.session_state:
    st.session_state.skipped_days = []

if 'skipped_exercises' not in st.session_state:
    st.session_state.skipped_exercises = {}

if 'body_weight_history' not in st.session_state:
    st.session_state.body_weight_history = {}

if 'target_body_weight' not in st.session_state:
    st.session_state.target_body_weight = 0.0

if 'target_body_weight_date' not in st.session_state:
    st.session_state.target_body_weight_date = None

if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

if 'selected_program_id' not in st.session_state:
    st.session_state.selected_program_id = 1  # ID par défaut

# Charger les données depuis Supabase
if not st.session_state.data_loaded:
    # S'assurer que le client utilise le bon token
    if 'session' in st.session_state and st.session_state.session:
        supabase.postgrest.auth(st.session_state.session.access_token)
    
    data = database.load_workout_data(supabase, st.session_state.user.id)
    if data:
        st.session_state.history = data.get('history', {})
        st.session_state.start_date = data.get('start_date', datetime.now().strftime("%Y-%m-%d"))
        st.session_state.skipped_days = data.get('skipped_days', [])
        st.session_state.skipped_exercises = data.get('skipped_exercises', {})
        st.session_state.body_weight_history = data.get('body_weight_history', {})
        st.session_state.target_body_weight = data.get('target_body_weight', 0.0)
        st.session_state.target_body_weight_date = data.get('target_body_weight_date', None)
        st.session_state.selected_program_id = data.get('selected_program_id', 1)
    st.session_state.data_loaded = True

# Fonction pour sauvegarder toutes les données
def save_all_data():
    data = {
        'history': st.session_state.history,
        'start_date': st.session_state.start_date,
        'skipped_days': st.session_state.skipped_days,
        'skipped_exercises': st.session_state.skipped_exercises,
        'body_weight_history': st.session_state.body_weight_history,
        'target_body_weight': st.session_state.target_body_weight,
        'target_body_weight_date': st.session_state.target_body_weight_date,
        'selected_program_id': st.session_state.selected_program_id
    }
    return database.save_workout_data(supabase, st.session_state.user.id, data)

# Header avec bouton de déconnexion
col1, col2 = st.columns([4, 1])
with col1:
    st.title("💪 Tracker de Musculation")
with col2:
    st.write(f"👤 {st.session_state.username}")
    if st.button("🚪 Déconnexion"):
        database.logout_user(supabase)
        st.session_state.clear()
        st.rerun()

st.markdown("---")

# Sidebar pour la navigation
page = st.sidebar.radio(
    "Navigation",
    ["📅 Séance du jour", "⚙️ Configuration", "📊 Historique", "📈 Statistiques"]
)

# Charger le programme actif depuis la DB
df_programme = database.load_program_by_id(supabase, st.session_state.selected_program_id)

if df_programme.empty:
    st.error("⚠️ Impossible de charger le programme. Vérifiez la base de données.")
    program_length = 1
else:
    program_length = df_programme['Jour'].max()

# --- MIGRATION AUTOMATIQUE DES DONNÉES (Index -> Nom) ---
# Convertit l'historique pour utiliser les noms d'exercices au lieu des index
if st.session_state.history or st.session_state.skipped_exercises:
    migrated = False
    
    # 1. Migration de l'historique des poids
    for date_str, session in st.session_state.history.items():
        new_weights = {}
        weights = session.get('weights', {})
        session_migrated = False
        
        for key, weight in weights.items():
            parts = key.split('_')
            # Si le format est date_INDEX_set (l'index est un nombre)
            if len(parts) == 3 and parts[1].isdigit():
                idx = int(parts[1])
                set_num = parts[2]
                if idx in df_programme.index:
                    ex_name = df_programme.loc[idx, 'Exercice']
                    new_key = f"{date_str}_{ex_name}_{set_num}"
                    new_weights[new_key] = weight
                    session_migrated = True
            else:
                new_weights[key] = weight
        
        if session_migrated:
            session['weights'] = new_weights
            migrated = True

    # 2. Migration des exercices skippés
    new_skipped_exercises = {}
    for key, val in st.session_state.skipped_exercises.items():
        parts = key.split('_')
        if len(parts) == 2 and parts[1].isdigit():
            idx = int(parts[1])
            if idx in df_programme.index:
                ex_name = df_programme.loc[idx, 'Exercice']
                new_key = f"{parts[0]}_{ex_name}"
                new_skipped_exercises[new_key] = val
                migrated = True
        else:
            new_skipped_exercises[key] = val
    
    if migrated:
        st.session_state.skipped_exercises = new_skipped_exercises
        save_all_data()
        st.toast("🔄 Historique migré vers le format robuste (Noms)", icon="🛠️")
        st.rerun()

# PAGE: Configuration
if page == "⚙️ Configuration":
    st.header("⚙️ Configuration du programme")
    
    # --- SÉLECTION DU PROGRAMME ---
    st.subheader("📚 Choix du programme")
    
    # Récupérer la liste des programmes
    available_programs = database.get_all_programs(supabase)
    
    if available_programs:
        # Créer un dictionnaire pour le selectbox {Nom: ID}
        prog_options = {p['name']: p['id'] for p in available_programs}
        
        # Trouver l'index du programme actuel
        current_index = 0
        current_id = st.session_state.selected_program_id
        for i, p in enumerate(available_programs):
            if p['id'] == current_id:
                current_index = i
                break
        
        selected_name = st.selectbox(
            "Programme actif",
            options=list(prog_options.keys()),
            index=current_index
        )
        
        new_program_id = prog_options[selected_name]
        
        # Afficher la description
        description = next((p['description'] for p in available_programs if p['id'] == new_program_id), "")
        if description:
            st.caption(f"ℹ️ {description}")
            
        if new_program_id != st.session_state.selected_program_id:
            if st.button("🔄 Changer de programme"):
                st.session_state.selected_program_id = new_program_id
                save_all_data()
                st.success(f"Programme changé pour : {selected_name}")
                st.rerun()
    else:
        st.warning("Aucun programme trouvé dans la base de données.")
    
    st.markdown("---")
    
    st.subheader("📆 Date de début du programme")
    
    col1, col2 = st.columns(2)
    with col1:
        new_start_date = st.date_input(
            "Première séance (Jour 1 - PUSH #1)",
            value=datetime.strptime(st.session_state.start_date, "%Y-%m-%d"),
            format="DD/MM/YYYY"
        )
        
        if st.button("💾 Mettre à jour la date de début"):
            st.session_state.start_date = new_start_date.strftime("%Y-%m-%d")
            if save_all_data():
                st.success("✅ Date de début mise à jour !")
                st.rerun()
    
    with col2:
        st.info(f"**Date actuelle de début:** {st.session_state.start_date}")
        today_day = utils.get_program_day(datetime.now().date(), st.session_state.start_date, st.session_state.skipped_days)
        st.info(f"**Jour du programme aujourd'hui:** Jour {today_day}")
    
    st.markdown("---")
    st.subheader("⏭️ Gérer les jours skippés")
    
    st.write("Si vous avez manqué une séance, vous pouvez la marquer comme skippée. Le programme se décalera automatiquement.")
    
    # Afficher les jours skippés
    if st.session_state.skipped_days:
        st.write("**Jours actuellement skippés:**")
        for skip_date in sorted(st.session_state.skipped_days, reverse=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"📅 {skip_date}")
            with col2:
                if st.button("❌ Annuler", key=f"unskip_{skip_date}"):
                    st.session_state.skipped_days.remove(skip_date)
                    save_all_data()
                    st.rerun()
    else:
        st.info("Aucun jour skippé pour le moment.")
    
    st.markdown("---")
    st.subheader("🏋️ Objectif de poids du corps")
    
    col1, col2 = st.columns(2)
    with col1:
        new_target_weight = st.number_input(
            "Poids cible (kg)",
            min_value=0.0,
            value=float(st.session_state.target_body_weight or 0.0),
            step=0.5,
            format="%.1f"
        )
    
    with col2:
        current_target_date = None
        if st.session_state.target_body_weight_date:
            try:
                current_target_date = datetime.strptime(st.session_state.target_body_weight_date, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                current_target_date = None # Garder None si la date est invalide

        new_target_date = st.date_input(
            "Échéance pour atteindre l'objectif",
            value=current_target_date,
            format="DD/MM/YYYY"
        )

    if st.button("💾 Enregistrer l'objectif de poids"):
        st.session_state.target_body_weight = new_target_weight
        st.session_state.target_body_weight_date = new_target_date.strftime("%Y-%m-%d") if new_target_date else None
        if save_all_data():
            st.success("✅ Objectif de poids mis à jour !")

    st.markdown("---")
    st.subheader("🗑️ Réinitialiser toutes les données")
    
    if st.button("⚠️ RÉINITIALISER TOUT", type="secondary"):
        st.session_state.history = {}
        st.session_state.start_date = datetime.now().strftime("%Y-%m-%d")
        st.session_state.skipped_days = []
        save_all_data()
        st.success("Toutes les données ont été réinitialisées !")
        st.rerun()

# PAGE: Séance du jour
elif page == "📅 Séance du jour":
    st.header("Séance du jour")
    
    # Sélection de la date
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_date = st.date_input(
            "Date de la séance",
            value=datetime.now(),
            format="DD/MM/YYYY"
        )
    
    date_str = selected_date.strftime("%Y-%m-%d")
    day_number = utils.get_program_day(selected_date, st.session_state.start_date, st.session_state.skipped_days)
    
    with col2:
        st.metric("Jour du programme", f"Jour {day_number}")
    
    with col3:
        # Vérifier si ce jour est déjà skippé
        is_skipped = date_str in st.session_state.skipped_days
        
        if is_skipped:
            if st.button("✅ Réactiver", type="secondary"):
                st.session_state.skipped_days.remove(date_str)
                save_all_data()
                st.rerun()
            st.warning("⏭️ Jour skippé")
        else:
            if st.button("⏭️ Skip séance", type="secondary"):
                if date_str not in st.session_state.skipped_days:
                    st.session_state.skipped_days.append(date_str)
                    save_all_data()
                    st.success("Séance skippée ! Le programme est décalé.")
                    st.rerun()
    
    # Afficher info sur le prochain jour
    tomorrow, next_day = utils.get_next_scheduled_day(st.session_state.start_date, st.session_state.skipped_days)
    next_day_in_cycle = (next_day - 1) % program_length + 1
    next_workout = df_programme[df_programme['Jour'] == next_day_in_cycle].iloc[0]['Type']
    st.info(f"📅 Demain ({tomorrow.strftime('%d/%m/%Y')}): Jour {next_day} - {next_workout}")

    st.markdown("---")
    st.subheader("⚖️ Poids du corps du jour")
    
    # Récupérer le poids déjà enregistré pour ce jour, s'il existe
    default_body_weight = st.session_state.body_weight_history.get(date_str, 0.0)
    
    body_weight = st.number_input(
        "Poids (kg)",
        min_value=0.0,
        value=float(default_body_weight),
        step=0.1,
        format="%.1f",
        key=f"bw_{date_str}"
    )
    
    # Mettre à jour l'historique si la valeur a changé et est supérieure à 0
    if body_weight > 0 and body_weight != default_body_weight:
        st.session_state.body_weight_history[date_str] = body_weight
        if save_all_data():
            st.toast("⚖️ Poids du corps enregistré !", icon="✅")

    st.markdown("---")
    
    # Filtrer le programme pour le jour sélectionné
    day_in_cycle = (day_number - 1) % program_length + 1
    day_workout = df_programme[df_programme['Jour'] == day_in_cycle]
    
    if not day_workout.empty:
        workout_type = day_workout.iloc[0]['Type']
        
        if workout_type == "Repos":
            st.info("🧘‍♂️ Jour de repos - Profitez-en pour récupérer !")
        else:
            st.subheader(f"🏋️ {workout_type}")
            
            # Afficher si la séance est déjà complétée
            if date_str in st.session_state.history:
                st.success("✅ Séance déjà enregistrée pour cette date")
            
            # Charger les poids existants pour cette date si disponibles
            if date_str in st.session_state.history:
                st.session_state.current_weights = st.session_state.history[date_str].get('weights', {})
            else:
                st.session_state.current_weights = {}
            
            # Afficher chaque exercice
            for idx, row in day_workout.iterrows():
                exercise_key = f"{date_str}_{row['Exercice']}"
                is_exercise_skipped = st.session_state.skipped_exercises.get(exercise_key, False)
                
                with st.expander(f"**{row['Exercice']}**", expanded=not is_exercise_skipped):
                    # Bouton pour skip l'exercice
                    col_skip1, col_skip2 = st.columns([3, 1])
                    with col_skip2:
                        if is_exercise_skipped:
                            if st.button("✅ Réactiver", key=f"unskip_ex_{exercise_key}"):
                                st.session_state.skipped_exercises[exercise_key] = False
                                save_all_data()
                                st.rerun()
                        else:
                            if st.button("⏭️ Skip exercice", key=f"skip_ex_{exercise_key}"):
                                st.session_state.skipped_exercises[exercise_key] = True
                                # Supprimer les poids de cet exercice
                                for serie_num in range(int(row['Séries'])):
                                    key = f"{date_str}_{row['Exercice']}_{serie_num}"
                                    if key in st.session_state.current_weights:
                                        del st.session_state.current_weights[key]
                                save_all_data()
                                st.rerun()
                    
                    if is_exercise_skipped:
                        st.warning("⏭️ Exercice skippé - aucune donnée ne sera enregistrée")
                    else:
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Répétitions:** {row['Répétitions (RPE)']}")
                            
                            # Récupérer et afficher les stats de l'exercice
                            last_max, all_time_max = utils.get_exercise_stats(
                                row['Exercice'], 
                                st.session_state.history, 
                                df_programme, 
                                program_length, 
                                current_date_str=date_str
                            )
                            
                            notes_and_stats = []
                            if pd.notna(row['Notes']) and row['Notes']:
                                notes_and_stats.append(f"📝 {row['Notes']}")
                            
                            if all_time_max is not None:
                                if last_max == all_time_max:
                                    notes_and_stats.append(f"**Dernier max :** {last_max} kg (🏅 Record)")
                                else:
                                    notes_and_stats.append(f"**Dernier max :** {last_max} kg | **Record :** {all_time_max} kg")
                            
                            if notes_and_stats:
                                st.caption(" | ".join(notes_and_stats))
                        
                        with col2:
                            st.write(f"**Séries:** {int(row['Séries'])}")
                        
                        # Inputs pour les poids de chaque série
                        st.write("**Poids de travail (kg):**")
                        cols = st.columns(int(row['Séries']))
                        
                        for serie_num in range(int(row['Séries'])):
                            with cols[serie_num]:
                                key = f"{date_str}_{row['Exercice']}_{serie_num}"
                                default_value = st.session_state.current_weights.get(key, 0.0)
                                
                                weight = st.number_input(
                                    f"Série {serie_num + 1}",
                                    min_value=0.0,
                                    max_value=500.0,
                                    value=float(default_value),
                                    step=0.5,
                                    key=key
                                )
                                st.session_state.current_weights[key] = weight
            
            st.markdown("---")
            
            # Bouton pour sauvegarder la séance
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("✅ Enregistrer la séance", type="primary", use_container_width=True):
                    # Filtrer les poids pour exclure les exercices skippés
                    filtered_weights = {}
                    for key, weight in st.session_state.current_weights.items():
                        # Extraire l'index de l'exercice de la clé
                        parts = key.split('_')
                        if len(parts) >= 3:
                            exercise_key = f"{parts[0]}_{'_'.join(parts[1:-1])}"
                            # N'inclure que si l'exercice n'est pas skippé
                            if not st.session_state.skipped_exercises.get(exercise_key, False):
                                filtered_weights[key] = weight
                    
                    # Sauvegarder dans l'historique
                    st.session_state.history[date_str] = {
                        'workout_type': workout_type,
                        'day_number': day_number,
                        'weights': filtered_weights,
                        'timestamp': datetime.now().isoformat()
                    }
                    if save_all_data():
                        st.success("✅ Séance enregistrée avec succès !")
                        st.balloons()

# PAGE: Historique
elif page == "📊 Historique":
    st.header("Historique des séances")
    
    if not st.session_state.history:
        st.info("Aucune séance enregistrée pour le moment.")
    else:
        # Trier les dates par ordre décroissant
        sorted_dates = sorted(st.session_state.history.keys(), reverse=True)
        
        for date_str in sorted_dates:
            session = st.session_state.history[date_str]
            
            with st.expander(f"📅 {date_str} - {session['workout_type']} (Jour {session['day_number']})", expanded=False):
                st.write(f"**Type d'entraînement:** {session['workout_type']}")
                st.write(f"**Jour du programme:** Jour {session['day_number']}")
                
                # Afficher les poids enregistrés
                weights = session['weights']
                
                if weights:
                    # Regrouper par exercice
                    exercises = {}
                    for key, weight in weights.items():
                        if weight > 0:
                            parts = key.split('_')
                            if len(parts) >= 3:
                                ex_name = "_".join(parts[1:-1])
                                serie_num = int(parts[-1])
                                
                                if ex_name not in exercises:
                                    exercises[ex_name] = []
                                exercises[ex_name].append((serie_num, weight))
                    
                    # Afficher les exercices et leurs poids
                    day_in_cycle = (session['day_number'] - 1) % program_length + 1
                    day_workout = df_programme[df_programme['Jour'] == day_in_cycle]
                    
                    for idx, row in day_workout.iterrows():
                        if row['Exercice'] in exercises:
                            st.write(f"**{row['Exercice']}**")
                            series_data = sorted(exercises[row['Exercice']])
                            weights_str = " | ".join([f"S{s+1}: {w}kg" for s, w in series_data])
                            st.caption(weights_str)
                
                # Bouton pour supprimer la séance
                if st.button(f"🗑️ Supprimer", key=f"del_{date_str}"):
                    del st.session_state.history[date_str]
                    save_all_data()
                    st.rerun()

# PAGE: Statistiques
elif page == "📈 Statistiques":
    st.header("Statistiques et progression")
    
    if not st.session_state.history and not st.session_state.body_weight_history:
        st.info("Aucune donnée disponible. Enregistrez vos séances ou votre poids pour voir vos statistiques.")
    else:
        # Onglets pour différentes vues
        tab1, tab2, tab3 = st.tabs(["📊 Par exercice", "📈 Volume global", "⚖️ Poids du corps"])
        
        with tab1:
            # Sélection de l'exercice à analyser
            all_exercises = df_programme[df_programme['Type'] != 'Repos']['Exercice'].unique()
            
            selected_exercise = st.selectbox(
                "Choisir un exercice",
                options=all_exercises
            )
            
            if selected_exercise:
                # Collecter les données pour cet exercice
                exercise_data = []
                
                for date_str, session in sorted(st.session_state.history.items()):
                    weights = session['weights']
                    day_number = session['day_number']
                    
                    # Trouver l'exercice dans le programme du jour
                    day_in_cycle = (day_number - 1) % program_length + 1
                    day_workout = df_programme[df_programme['Jour'] == day_in_cycle]
                    exercise_row = day_workout[day_workout['Exercice'] == selected_exercise]
                    
                    if not exercise_row.empty:
                        # Collecter les poids pour cet exercice
                        exercise_weights = []
                        for key, weight in weights.items():
                            # Vérifier que la clé correspond exactement à l'exercice
                            parts = key.split('_')
                            stored_name = "_".join(parts[1:-1])
                            if len(parts) >= 3 and stored_name == selected_exercise and weight > 0:
                                exercise_weights.append(weight)
                        
                        if exercise_weights:
                            exercise_data.append({
                                'date': date_str,
                                'max_weight': max(exercise_weights),
                                'avg_weight': sum(exercise_weights) / len(exercise_weights),
                                'total_volume': sum(exercise_weights) * len(exercise_weights)
                            })
                
                if exercise_data:
                    df_stats = pd.DataFrame(exercise_data)
                    df_stats['date'] = pd.to_datetime(df_stats['date'])
                    
                    # Regrouper par date en prenant la valeur maximale pour chaque date
                    df_stats = df_stats.groupby('date').agg({
                        'max_weight': 'max',
                        'avg_weight': 'mean',
                        'total_volume': 'sum'
                    }).reset_index()
                    
                    df_stats = df_stats.sort_values('date')
                    
                    # Graphique de progression
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Charge maximale
                        fig_max = go.Figure()
                        fig_max.add_trace(go.Scatter(
                            x=df_stats['date'],
                            y=df_stats['max_weight'],
                            mode='lines+markers',
                            name='Charge max',
                            line=dict(color='#FF6B6B', width=3),
                            marker=dict(size=8)
                        ))
                        fig_max.update_layout(
                            title="Charge maximale",
                            xaxis_title="Date",
                            yaxis_title="Poids (kg)",
                            hovermode='x unified',
                            xaxis=dict(
                                tickformat='%d-%m-%Y'
                            )
                        )
                        st.plotly_chart(fig_max, use_container_width=True)
                    
                    with col2:
                        # Charge moyenne
                        fig_avg = go.Figure()
                        fig_avg.add_trace(go.Scatter(
                            x=df_stats['date'],
                            y=df_stats['avg_weight'],
                            mode='lines+markers',
                            name='Charge moyenne',
                            line=dict(color='#4ECDC4', width=3),
                            marker=dict(size=8)
                        ))
                        fig_avg.update_layout(
                            title="Charge moyenne",
                            xaxis_title="Date",
                            yaxis_title="Poids (kg)",
                            hovermode='x unified',
                            xaxis=dict(
                                tickformat='%d-%m-%Y'
                            )
                        )
                        st.plotly_chart(fig_avg, use_container_width=True)
                    
                    # Volume pour cet exercice
                    fig_volume = go.Figure()
                    fig_volume.add_trace(go.Bar(
                        x=df_stats['date'],
                        y=df_stats['total_volume'],
                        name='Volume total',
                        marker_color='#95E1D3'
                    ))
                    fig_volume.update_layout(
                        title=f"Volume total - {selected_exercise}",
                        xaxis_title="Date",
                        yaxis_title="Volume (kg)",
                        xaxis=dict(
                            tickformat='%d-%m-%Y'
                        )
                    )
                    st.plotly_chart(fig_volume, use_container_width=True)
                    
                    # Statistiques récapitulatives
                    st.markdown("---")
                    st.subheader("📊 Récapitulatif")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Record personnel",
                            f"{df_stats['max_weight'].max():.1f} kg"
                        )
                    
                    with col2:
                        st.metric(
                            "Charge moyenne",
                            f"{df_stats['avg_weight'].mean():.1f} kg"
                        )
                    
                    with col3:
                        if len(df_stats) > 1:
                            progression = ((df_stats['max_weight'].iloc[-1] - df_stats['max_weight'].iloc[0]) 
                                           / df_stats['max_weight'].iloc[0] * 100)
                            st.metric(
                                "Progression",
                                f"{progression:.1f}%"
                            )
                        else:
                            st.metric("Progression", "N/A")
                    
                    with col4:
                        st.metric(
                            "Séances total",
                            len(df_stats)
                        )
                    
                else:
                    st.warning(f"Aucune donnée enregistrée pour l'exercice: {selected_exercise}")
        
        with tab2:
            st.subheader("Volume d'entraînement global")
            
            # Calculer le volume total par séance avec type
            volume_data = []
            
            for date_str, session in sorted(st.session_state.history.items()):
                weights = session['weights']
                workout_type = session['workout_type']
                
                # Calculer le volume total de la séance
                total_volume = sum([w for w in weights.values() if w > 0])
                
                if total_volume > 0:
                    # Déterminer la catégorie
                    if 'PUSH' in workout_type:
                        category = 'PUSH'
                        color = '#FF6B6B'
                    elif 'PULL' in workout_type:
                        category = 'PULL'
                        color = '#4ECDC4'
                    elif 'LEGS' in workout_type or 'LEG' in workout_type:
                        category = 'LEGS'
                        color = '#95E1D3'
                    else:
                        category = 'Autre'
                        color = '#A8A8A8'
                    
                    volume_data.append({
                        'date': date_str,
                        'volume': total_volume,
                        'type': category,
                        'color': color,
                        'workout_name': workout_type
                    })
            
            if volume_data:
                df_volume = pd.DataFrame(volume_data)
                df_volume['date'] = pd.to_datetime(df_volume['date'])
                
                # Regrouper par date et type pour éviter les doublons
                df_volume = df_volume.groupby(['date', 'type', 'color']).agg({
                    'volume': 'sum',
                    'workout_name': 'first'
                }).reset_index()
                
                df_volume = df_volume.sort_values('date')
                
                # Créer le graphique avec code couleur
                fig_global = go.Figure()
                
                # Ajouter une barre pour chaque type
                for workout_type in ['PUSH', 'PULL', 'LEGS', 'Autre']:
                    df_type = df_volume[df_volume['type'] == workout_type]
                    if not df_type.empty:
                        fig_global.add_trace(go.Bar(
                            x=df_type['date'],
                            y=df_type['volume'],
                            name=workout_type,
                            marker_color=df_type['color'].iloc[0],
                            hovertemplate='<b>%{x|%d/%m/%Y}</b><br>' +
                                        'Volume: %{y:.0f} kg<br>' +
                                        '<extra></extra>'
                        ))
                
                fig_global.update_layout(
                    title="Volume total par séance",
                    xaxis_title="Date",
                    yaxis_title="Volume total (kg)",
                    barmode='group',
                    hovermode='x unified',
                    legend=dict(
                        title="Type de séance",
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    xaxis=dict(
                        tickformat='%d-%m-%Y',
                        dtick=86400000.0  # 1 jour en millisecondes
                    ),
                    height=500
                )
                
                st.plotly_chart(fig_global, use_container_width=True)
                
                # Statistiques globales
                st.markdown("---")
                st.subheader("📊 Statistiques globales")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Volume total",
                        f"{df_volume['volume'].sum():.0f} kg"
                    )
                
                with col2:
                    st.metric(
                        "Volume moyen/séance",
                        f"{df_volume['volume'].mean():.0f} kg"
                    )
                
                with col3:
                    st.metric(
                        "Séance max",
                        f"{df_volume['volume'].max():.0f} kg"
                    )
                
                with col4:
                    st.metric(
                        "Total séances",
                        len(df_volume)
                    )
                
                # Volume par type
                st.markdown("---")
                st.subheader("📈 Volume par type de séance")
                
                col1, col2, col3 = st.columns(3)
                
                for idx, workout_type in enumerate(['PUSH', 'PULL', 'LEGS']):
                    df_type = df_volume[df_volume['type'] == workout_type]
                    with [col1, col2, col3][idx]:
                        if not df_type.empty:
                            st.metric(
                                f"{workout_type}",
                                f"{df_type['volume'].sum():.0f} kg",
                                f"{len(df_type)} séances"
                            )
                        else:
                            st.metric(f"{workout_type}", "0 kg", "0 séances")
            else:
                st.info("Aucune donnée disponible pour le volume global.")

        with tab3:
            st.subheader("⚖️ Évolution du poids de corps")
            
            if not st.session_state.body_weight_history:
                st.info("Aucun poids enregistré pour le moment. Enregistrez votre poids dans l'onglet 'Séance du jour'.")
            else:
                # Préparation des données
                bw_data = [
                    {'date': date, 'weight': weight} 
                    for date, weight in st.session_state.body_weight_history.items()
                ]
                df_bw = pd.DataFrame(bw_data)
                df_bw['date'] = pd.to_datetime(df_bw['date'])
                df_bw = df_bw.sort_values('date')
                
                # Graphique
                fig_bw = go.Figure()
                
                # Courbe de poids (réelle)
                fig_bw.add_trace(go.Scatter(
                    x=df_bw['date'],
                    y=df_bw['weight'],
                    mode='lines+markers',
                    name='Poids actuel',
                    line=dict(color='#3B8ED0', width=3),
                    marker=dict(size=8)
                ))
                
                # Ligne d'objectif
                target_weight = st.session_state.target_body_weight
                target_date_str = st.session_state.target_body_weight_date
                
                if target_weight > 0:
                    fig_bw.add_hline(
                        y=target_weight, 
                        line_dash="dash", 
                        line_color="#28a745", 
                        annotation_text=f"Objectif: {target_weight}kg",
                        annotation_position="bottom right"
                    )
                    
                    if target_date_str:
                        target_date = pd.to_datetime(target_date_str)
                        start_date = df_bw['date'].iloc[0]
                        start_weight = df_bw['weight'].iloc[0]
                        
                        # Point cible (étoile)
                        fig_bw.add_trace(go.Scatter(
                            x=[target_date],
                            y=[target_weight],
                            mode='markers',
                            name='Objectif cible',
                            marker=dict(color='#28a745', size=12, symbol='star')
                        ))
                        
                        # 1. Trajectoire Idéale (Ligne pointillée Start -> Target)
                        fig_bw.add_trace(go.Scatter(
                            x=[start_date, target_date],
                            y=[start_weight, target_weight],
                            mode='lines',
                            name='Trajectoire Idéale',
                            line=dict(color='rgba(40, 167, 69, 0.5)', width=2, dash='dot')
                        ))
                        
                        # 2. Régression linéaire (Tendance actuelle)
                        if len(df_bw) > 1:
                            # Convert dates to days from start for regression
                            days_from_start = (df_bw['date'] - start_date).dt.days
                            # Calculate fit
                            z = np.polyfit(days_from_start, df_bw['weight'], 1)
                            p = np.poly1d(z)
                            
                            # Calculate trend line
                            trend_y = p(days_from_start)
                            
                            fig_bw.add_trace(go.Scatter(
                                x=df_bw['date'],
                                y=trend_y,
                                mode='lines',
                                name='Tendance',
                                line=dict(color='#FFA07A', width=2)
                            ))
                
                fig_bw.update_layout(
                    title="Évolution du poids",
                    xaxis_title="Date",
                    yaxis_title="Poids (kg)",
                    hovermode='x unified',
                    xaxis=dict(tickformat='%d-%m-%Y')
                )
                
                st.plotly_chart(fig_bw, use_container_width=True)
                
                # Métriques existantes
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                
                current_weight = df_bw.iloc[-1]['weight']
                start_weight = df_bw.iloc[0]['weight']
                
                with col1:
                    st.metric("Poids actuel", f"{current_weight:.1f} kg")
                
                with col2:
                    change = current_weight - start_weight
                    st.metric("Variation totale", f"{change:+.1f} kg", delta=f"{change:.1f} kg")
                
                with col3:
                    if target_weight > 0:
                        diff_to_target = current_weight - target_weight
                        st.metric(
                            "Objectif", 
                            f"{target_weight:.1f} kg", 
                            delta=f"{abs(diff_to_target):.1f} kg d'écart", 
                            delta_color="off"
                        )
                    else:
                        st.metric("Objectif", "Non défini")
                        
                with col4:
                     if target_weight > 0 and start_weight != target_weight:
                        total_diff = target_weight - start_weight
                        current_diff = current_weight - start_weight
                        if total_diff != 0:
                            progress = (current_diff / total_diff) * 100
                            display_progress = max(0, min(100, progress))
                            st.metric("Avancement", f"{display_progress:.1f}%")
                        else:
                            st.metric("Avancement", "N/A")
                     else:
                        st.metric("Avancement", "N/A")
                
                # NOUVEAU BLOC : ANALYSE ET PRÉDICTIONS
                if target_weight > 0 and target_date_str:
                    st.markdown("### 🧭 Analyse de l'objectif")
                    
                    target_date = pd.to_datetime(target_date_str)
                    today = pd.to_datetime(datetime.now().date())
                    
                    # Seulement si la date cible est dans le futur
                    if target_date > today:
                         days_remaining = (target_date - today).days
                         weeks_remaining = days_remaining / 7
                         
                         weight_diff_total = target_weight - current_weight
                         
                         col_a, col_b = st.columns(2)
                         
                         with col_a:
                             # Calcul du rythme nécessaire
                             if weeks_remaining > 0:
                                 rate_needed = weight_diff_total / weeks_remaining
                                 action = "perdre" if weight_diff_total < 0 else "prendre"
                                 st.metric(
                                     "Rythme nécessaire",
                                     f"{abs(rate_needed):.2f} kg/semaine",
                                     f"Pour atteindre {target_weight}kg le {target_date.strftime('%d/%m')}"
                                 )
                             else:
                                 st.info("L'échéance est trop proche.")
                         
                         with col_b:
                             # Calcul de l'avance/retard
                             start_date = df_bw['date'].iloc[0]
                             total_days_plan = (target_date - start_date).days
                             days_passed = (today - start_date).days
                             
                             if total_days_plan > 0:
                                 # Où devrais-je être aujourd'hui théoriquement ?
                                 progress_ratio = days_passed / total_days_plan
                                 ideal_weight_today = start_weight + (target_weight - start_weight) * progress_ratio
                                 
                                 diff_vs_ideal = current_weight - ideal_weight_today
                                 
                                 # Logique pour déterminer bon/mauvais selon qu'on veut perdre ou gagner
                                 is_weight_loss_goal = target_weight < start_weight
                                 
                                 if is_weight_loss_goal:
                                     # Objectif perte : Si Actuel < Idéal => Avance (Bien)
                                     is_ahead = diff_vs_ideal < 0
                                     delta_val = abs(diff_vs_ideal)
                                     delta_color = "normal" if is_ahead else "inverse"
                                     status_text = "En avance" if is_ahead else "En retard"
                                 else:
                                     # Objectif gain : Si Actuel > Idéal => Avance (Bien)
                                     is_ahead = diff_vs_ideal > 0
                                     delta_val = abs(diff_vs_ideal)
                                     delta_color = "normal" if is_ahead else "inverse"
                                     status_text = "En avance" if is_ahead else "En retard"
                                     
                                 st.metric(
                                     "Statut actuel",
                                     status_text,
                                     f"{delta_val:.1f} kg vs Trajectoire idéale",
                                     delta_color=delta_color
                                 )

# Sidebar - Informations
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Calendrier du programme")

# Afficher le calendrier de la semaine en cours
today = datetime.now().date()
for i in range(7):
    day_date = today + timedelta(days=i)
    day_num = utils.get_program_day(day_date, st.session_state.start_date, st.session_state.skipped_days)
    day_in_cycle = (day_num - 1) % program_length + 1
    workout_info = df_programme[df_programme['Jour'] == day_in_cycle].iloc[0]['Type']
    
    is_today = day_date == today
    is_skipped = day_date.strftime("%Y-%m-%d") in st.session_state.skipped_days
    
    prefix = "➡️ " if is_today else "   "
    skip_marker = " ⏭️" if is_skipped else ""
    
    st.sidebar.caption(f"{prefix}{day_date.strftime('%d/%m')}: J{day_num} - {workout_info}{skip_marker}")

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Informations")
st.sidebar.info(
    """
    **Comment utiliser l'app:**
    
    1. ⚙️ Configurez la date de début
    2. 📅 Enregistrez vos poids
    3. ⏭️ Skippez si besoin (décale auto)
    4. 📊 Consultez votre historique
    5. 📈 Suivez votre progression
    
    💾 Données sauvegardées dans le cloud !
    """
)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("💪 Tracker de Musculation v4.2 - Powered by Supabase")