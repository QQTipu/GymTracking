import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import hashlib
import os

# Configuration de la page
st.set_page_config(
    page_title="Tracker Musculation",
    page_icon="💪",
    layout="wide"
)

# ============= SYSTÈME D'AUTHENTIFICATION =============

def hash_password(password):
    """Hash un mot de passe avec SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Charge les utilisateurs depuis le fichier"""
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    """Sauvegarde les utilisateurs"""
    with open('users.json', 'w') as f:
        json.dump(users, f, indent=2)

def create_user(username, password):
    """Crée un nouvel utilisateur"""
    users = load_users()
    if username in users:
        return False
    users[username] = {
        'password': hash_password(password),
        'created_at': datetime.now().isoformat()
    }
    save_users(users)
    return True

def verify_user(username, password):
    """Vérifie les identifiants d'un utilisateur"""
    users = load_users()
    if username not in users:
        return False
    return users[username]['password'] == hash_password(password)

def login_page():
    """Affiche la page de connexion"""
    st.title("🔐 Connexion - Tracker Musculation")
    
    tab1, tab2 = st.tabs(["Se connecter", "Créer un compte"])
    
    with tab1:
        st.subheader("Connexion")
        username = st.text_input("Nom d'utilisateur", key="login_username")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        
        if st.button("Se connecter", type="primary"):
            if verify_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("✅ Connexion réussie !")
                st.rerun()
            else:
                st.error("❌ Identifiants incorrects")
    
    with tab2:
        st.subheader("Créer un compte")
        new_username = st.text_input("Nom d'utilisateur", key="signup_username")
        new_password = st.text_input("Mot de passe", type="password", key="signup_password")
        confirm_password = st.text_input("Confirmer le mot de passe", type="password", key="signup_confirm")
        
        if st.button("Créer le compte", type="primary"):
            if not new_username or not new_password:
                st.error("❌ Veuillez remplir tous les champs")
            elif len(new_password) < 6:
                st.error("❌ Le mot de passe doit contenir au moins 6 caractères")
            elif new_password != confirm_password:
                st.error("❌ Les mots de passe ne correspondent pas")
            elif create_user(new_username, new_password):
                st.success("✅ Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
            else:
                st.error("❌ Ce nom d'utilisateur existe déjà")

# Initialiser l'état de connexion
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Vérifier si l'utilisateur est connecté
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ============= APPLICATION PRINCIPALE =============

# Fonction pour obtenir le chemin du fichier utilisateur
def get_user_file(filename):
    """Retourne le chemin du fichier pour l'utilisateur connecté"""
    user_dir = f"user_data/{st.session_state.username}"
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, filename)

# Charger le programme depuis le CSV
@st.cache_data
def load_programme():
    df = pd.read_csv('programme.csv')
    return df

# Initialiser le session state
if 'history' not in st.session_state:
    st.session_state.history = {}

if 'current_weights' not in st.session_state:
    st.session_state.current_weights = {}

if 'start_date' not in st.session_state:
    st.session_state.start_date = datetime.now().strftime("%Y-%m-%d")

if 'skipped_days' not in st.session_state:
    st.session_state.skipped_days = []

# Fonction pour sauvegarder toutes les données (par utilisateur)
def save_all_data():
    data = {
        'history': st.session_state.history,
        'start_date': st.session_state.start_date,
        'skipped_days': st.session_state.skipped_days
    }
    with open(get_user_file('workout_data.json'), 'w') as f:
        json.dump(data, f, indent=2)

# Fonction pour charger toutes les données (par utilisateur)
def load_all_data():
    try:
        with open(get_user_file('workout_data.json'), 'r') as f:
            data = json.load(f)
            st.session_state.history = data.get('history', {})
            st.session_state.start_date = data.get('start_date', datetime.now().strftime("%Y-%m-%d"))
            st.session_state.skipped_days = data.get('skipped_days', [])
    except FileNotFoundError:
        st.session_state.history = {}
        st.session_state.start_date = datetime.now().strftime("%Y-%m-%d")
        st.session_state.skipped_days = []

# Charger les données au démarrage
load_all_data()

# Fonction pour calculer le jour du programme selon la date
def get_program_day(date):
    """
    Calcule le jour du programme (1-7) en fonction de la date de début
    et des jours skippés
    """
    start = datetime.strptime(st.session_state.start_date, "%Y-%m-%d").date()
    current = date if isinstance(date, datetime) else datetime.strptime(str(date), "%Y-%m-%d").date()
    
    # Calculer le nombre de jours depuis le début
    days_elapsed = (current - start).days
    
    # Soustraire les jours skippés avant cette date
    skipped_before = len([d for d in st.session_state.skipped_days if d < str(current)])
    effective_days = days_elapsed - skipped_before
    
    # Le jour du programme (1-7, avec cycle)
    program_day = (effective_days % 7) + 1
    
    return program_day

# Fonction pour obtenir le prochain jour prévu du programme
def get_next_scheduled_day():
    """Retourne la date et le jour du programme pour demain"""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    next_day = get_program_day(tomorrow)
    return tomorrow, next_day

# Header avec bouton de déconnexion
col1, col2 = st.columns([4, 1])
with col1:
    st.title("💪 Tracker de Musculation")
with col2:
    st.write(f"👤 {st.session_state.username}")
    if st.button("🚪 Déconnexion"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

st.markdown("---")

# Sidebar pour la navigation
page = st.sidebar.radio(
    "Navigation",
    ["📅 Séance du jour", "⚙️ Configuration", "📊 Historique", "📈 Statistiques"]
)

# Charger le programme
df_programme = load_programme()

# PAGE: Configuration
if page == "⚙️ Configuration":
    st.header("⚙️ Configuration du programme")
    
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
            save_all_data()
            st.success("✅ Date de début mise à jour !")
            st.rerun()
    
    with col2:
        st.info(f"**Date actuelle de début:** {st.session_state.start_date}")
        today_day = get_program_day(datetime.now().date())
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
    day_number = get_program_day(selected_date)
    
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
    tomorrow, next_day = get_next_scheduled_day()
    next_workout = df_programme[df_programme['Jour'] == next_day].iloc[0]['Type']
    st.info(f"📅 Demain ({tomorrow.strftime('%d/%m/%Y')}): Jour {next_day} - {next_workout}")
    
    # Filtrer le programme pour le jour sélectionné
    day_workout = df_programme[df_programme['Jour'] == day_number]
    
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
                with st.expander(f"**{row['Exercice']}**", expanded=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Répétitions:** {row['Répétitions (RPE)']}")
                        if pd.notna(row['Notes']) and row['Notes']:
                            st.caption(f"📝 {row['Notes']}")
                    
                    with col2:
                        st.write(f"**Séries:** {int(row['Séries'])}")
                    
                    # Inputs pour les poids de chaque série
                    st.write("**Poids de travail (kg):**")
                    cols = st.columns(int(row['Séries']))
                    
                    for serie_num in range(int(row['Séries'])):
                        with cols[serie_num]:
                            key = f"{date_str}_{idx}_{serie_num}"
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
                    # Sauvegarder dans l'historique
                    st.session_state.history[date_str] = {
                        'workout_type': workout_type,
                        'day_number': day_number,
                        'weights': st.session_state.current_weights.copy(),
                        'timestamp': datetime.now().isoformat()
                    }
                    save_all_data()
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
                                exercise_idx = parts[1]
                                serie_num = int(parts[2])
                                
                                if exercise_idx not in exercises:
                                    exercises[exercise_idx] = []
                                exercises[exercise_idx].append((serie_num, weight))
                    
                    # Afficher les exercices et leurs poids
                    day_workout = df_programme[df_programme['Jour'] == session['day_number']]
                    
                    for idx, row in day_workout.iterrows():
                        exercise_idx = str(idx)
                        if exercise_idx in exercises:
                            st.write(f"**{row['Exercice']}**")
                            series_data = sorted(exercises[exercise_idx])
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
    
    if not st.session_state.history:
        st.info("Aucune donnée disponible. Enregistrez vos séances pour voir vos statistiques.")
    else:
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
                day_workout = df_programme[df_programme['Jour'] == day_number]
                exercise_row = day_workout[day_workout['Exercice'] == selected_exercise]
                
                if not exercise_row.empty:
                    idx = exercise_row.index[0]
                    
                    # Collecter les poids pour cet exercice
                    exercise_weights = []
                    for key, weight in weights.items():
                        if str(idx) in key and weight > 0:
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
                        hovermode='x unified'
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
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_avg, use_container_width=True)
                
                # Volume total
                fig_volume = go.Figure()
                fig_volume.add_trace(go.Bar(
                    x=df_stats['date'],
                    y=df_stats['total_volume'],
                    name='Volume total',
                    marker_color='#95E1D3'
                ))
                fig_volume.update_layout(
                    title="Volume total d'entraînement",
                    xaxis_title="Date",
                    yaxis_title="Volume (kg)",
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

# Sidebar - Informations
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Calendrier du programme")

# Afficher le calendrier de la semaine en cours
today = datetime.now().date()
for i in range(7):
    day_date = today + timedelta(days=i)
    day_num = get_program_day(day_date)
    workout_info = df_programme[df_programme['Jour'] == day_num].iloc[0]['Type']
    
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
    """
)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("💪 Tracker de Musculation v3.0")