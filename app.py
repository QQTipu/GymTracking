import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client, Client
import os

# Configuration de la page
st.set_page_config(
    page_title="Tracker Musculation",
    page_icon="💪",
    layout="wide"
)

# ============= CONFIGURATION SUPABASE =============
# À configurer dans Streamlit Cloud Secrets ou .streamlit/secrets.toml
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    
    # Initialiser sans session au début
    if 'supabase_client' not in st.session_state:
        st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    supabase = st.session_state.supabase_client
except Exception as e:
    st.error("⚠️ Configuration Supabase manquante. Voir les instructions dans le README.")
    st.stop()

# ============= FONCTIONS SUPABASE =============

def create_user_account(username, password):
    """Crée un compte utilisateur dans Supabase Auth"""
    try:
        # Créer l'utilisateur avec email fictif (username@workout.app)
        email = f"{username}@workout.app"
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "username": username
                },
                "email_redirect_to": None
            }
        })
        if response.user:
            return True, "Compte créé avec succès !"
        return False, "Erreur lors de la création du compte"
    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
            return False, "Ce nom d'utilisateur existe déjà"
        return False, f"Erreur : {error_msg}"

def login_user(username, password):
    """Connecte un utilisateur"""
    try:
        email = f"{username}@workout.app"
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if response.user and response.session:
            # Mettre à jour le client avec le token d'accès
            supabase.postgrest.auth(response.session.access_token)
            return response.user, response.session, None
        return None, None, "Identifiants incorrects"
    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
            return None, None, "Identifiants incorrects"
        elif "Email not confirmed" in error_msg:
            return None, None, "Email non confirmé. Vérifiez la configuration Supabase."
        return None, None, f"Erreur : {error_msg}"

def logout_user():
    """Déconnecte l'utilisateur"""
    try:
        supabase.auth.sign_out()
    except:
        pass

def save_workout_data(user_id, data):
    """Sauvegarde les données d'entraînement de l'utilisateur"""
    try:
        # Vérifier si l'utilisateur existe déjà
        result = supabase.table('user_data').select("*").eq('user_id', user_id).execute()
        
        if len(result.data) > 0:
            # Mise à jour
            supabase.table('user_data').update({
                'workout_data': data,
                'updated_at': datetime.now().isoformat()
            }).eq('user_id', user_id).execute()
        else:
            # Insertion
            supabase.table('user_data').insert({
                'user_id': user_id,
                'workout_data': data,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).execute()
        return True
    except Exception as e:
        st.error(f"Erreur sauvegarde: {str(e)}")
        return False

def load_workout_data(user_id):
    """Charge les données d'entraînement de l'utilisateur"""
    try:
        result = supabase.table('user_data').select("workout_data").eq('user_id', user_id).execute()
        if len(result.data) > 0:
            return result.data[0]['workout_data']
        return None
    except Exception as e:
        st.error(f"Erreur chargement: {str(e)}")
        return None

# ============= INTERFACE DE CONNEXION =============

def login_page():
    """Affiche la page de connexion"""
    st.title("🔐 Connexion - Tracker Musculation")
    
    st.markdown("""
    ### 📊 Suivi de performance en musculation
    Trackez vos séances, suivez votre progression, atteignez vos objectifs ! 💪
    """)
    
    tab1, tab2 = st.tabs(["Se connecter", "Créer un compte"])
    
    with tab1:
        st.subheader("Connexion")
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            submit = st.form_submit_button("Se connecter", type="primary", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("❌ Veuillez remplir tous les champs")
                else:
                    user, session, error = login_user(username, password)
                    if user and session:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.session_state.session = session
                        st.session_state.username = username
                        st.success("✅ Connexion réussie !")
                        st.rerun()
                    else:
                        st.error(f"❌ {error}")
    
    with tab2:
        st.subheader("Créer un compte")
        with st.form("signup_form"):
            new_username = st.text_input("Nom d'utilisateur", key="signup_username")
            new_password = st.text_input("Mot de passe (min. 6 caractères)", type="password", key="signup_password")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password")
            submit = st.form_submit_button("Créer le compte", type="primary", use_container_width=True)
            
            if submit:
                if not new_username or not new_password:
                    st.error("❌ Veuillez remplir tous les champs")
                elif len(new_password) < 6:
                    st.error("❌ Le mot de passe doit contenir au moins 6 caractères")
                elif new_password != confirm_password:
                    st.error("❌ Les mots de passe ne correspondent pas")
                else:
                    success, message = create_user_account(new_username, new_password)
                    if success:
                        st.success(f"✅ {message} Vous pouvez maintenant vous connecter.")
                    else:
                        st.error(f"❌ {message}")

# Initialiser l'état de connexion
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Vérifier si l'utilisateur est connecté
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ============= APPLICATION PRINCIPALE =============

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

if 'skipped_exercises' not in st.session_state:
    st.session_state.skipped_exercises = {}

if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# Charger les données depuis Supabase
if not st.session_state.data_loaded:
    # S'assurer que le client utilise le bon token
    if 'session' in st.session_state and st.session_state.session:
        supabase.postgrest.auth(st.session_state.session.access_token)
    
    data = load_workout_data(st.session_state.user.id)
    if data:
        st.session_state.history = data.get('history', {})
        st.session_state.start_date = data.get('start_date', datetime.now().strftime("%Y-%m-%d"))
        st.session_state.skipped_days = data.get('skipped_days', [])
        st.session_state.skipped_exercises = data.get('skipped_exercises', {})
    st.session_state.data_loaded = True

# Fonction pour sauvegarder toutes les données
def save_all_data():
    data = {
        'history': st.session_state.history,
        'start_date': st.session_state.start_date,
        'skipped_days': st.session_state.skipped_days,
        'skipped_exercises': st.session_state.skipped_exercises
    }
    return save_workout_data(st.session_state.user.id, data)

# Fonction pour calculer le jour du programme selon la date
def get_program_day(date):
    """
    Calcule le jour du programme en fonction de la date de début
    et des jours skippés. Le jour est absolu (pas de cycle).
    """
    start = datetime.strptime(st.session_state.start_date, "%Y-%m-%d").date()
    current = date if isinstance(date, datetime) else datetime.strptime(str(date), "%Y-%m-%d").date()
    
    # Si la date est avant la date de début, retourner 1
    if current < start:
        return 1
    
    # Calculer le nombre de jours depuis le début
    days_elapsed = (current - start).days
    
    # Soustraire les jours skippés avant cette date
    skipped_before = len([d for d in st.session_state.skipped_days if d < str(current)])
    effective_days = days_elapsed - skipped_before
    
    # Le jour du programme est le nombre de jours effectifs + 1
    program_day = effective_days + 1
    
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
        logout_user()
        st.session_state.clear()
        st.rerun()

st.markdown("---")

# Sidebar pour la navigation
page = st.sidebar.radio(
    "Navigation",
    ["📅 Séance du jour", "⚙️ Configuration", "📊 Historique", "📈 Statistiques"]
)

# Charger le programme
df_programme = load_programme()
program_length = df_programme['Jour'].max()

def get_exercise_stats(exercise_name, history, df_programme, program_length, current_date_str):
    """
    Calcule la charge maximale de la dernière séance et la charge maximale all-time
    pour un exercice donné, pour les séances antérieures à une date donnée.
    """
    exercise_history = []
    
    # Parcourir l'historique des séances (trié par date pour que le dernier soit le plus récent)
    for date_str, session in sorted(history.items()):
        # On ne considère que les séances passées
        if date_str >= current_date_str:
            continue

        weights = session.get('weights', {})
        if not weights:
            continue
            
        day_number = session['day_number']
        day_in_cycle = (day_number - 1) % program_length + 1
        day_workout_df = df_programme[df_programme['Jour'] == day_in_cycle]
        
        exercise_rows = day_workout_df[day_workout_df['Exercice'] == exercise_name]
        
        if not exercise_rows.empty:
            exercise_idx = str(exercise_rows.index[0])
            session_weights = []
            for key, weight in weights.items():
                parts = key.split('_')
                if len(parts) >= 3 and parts[1] == exercise_idx and weight > 0:
                    session_weights.append(weight)
            
            if session_weights:
                exercise_history.append({
                    'date': date_str,
                    'max_weight': max(session_weights)
                })

    if not exercise_history:
        return None, None

    # Le dernier élément de la liste est la séance la plus récente
    last_max = exercise_history[-1]['max_weight']
    all_time_max = max(item['max_weight'] for item in exercise_history)
    
    return last_max, all_time_max

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
            if save_all_data():
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
    next_day_in_cycle = (next_day - 1) % program_length + 1
    next_workout = df_programme[df_programme['Jour'] == next_day_in_cycle].iloc[0]['Type']
    st.info(f"📅 Demain ({tomorrow.strftime('%d/%m/%Y')}): Jour {next_day} - {next_workout}")
    
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
                exercise_key = f"{date_str}_{idx}"
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
                                    key = f"{date_str}_{idx}_{serie_num}"
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
                            last_max, all_time_max = get_exercise_stats(
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
                    # Filtrer les poids pour exclure les exercices skippés
                    filtered_weights = {}
                    for key, weight in st.session_state.current_weights.items():
                        # Extraire l'index de l'exercice de la clé
                        parts = key.split('_')
                        if len(parts) >= 3:
                            exercise_key = f"{parts[0]}_{parts[1]}"
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
                                exercise_idx = parts[1]
                                serie_num = int(parts[2])
                                
                                if exercise_idx not in exercises:
                                    exercises[exercise_idx] = []
                                exercises[exercise_idx].append((serie_num, weight))
                    
                    # Afficher les exercices et leurs poids
                    day_in_cycle = (session['day_number'] - 1) % program_length + 1
                    day_workout = df_programme[df_programme['Jour'] == day_in_cycle]
                    
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
        # Onglets pour différentes vues
        tab1, tab2 = st.tabs(["📊 Par exercice", "📈 Volume global"])
        
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
                        idx = exercise_row.index[0]
                        
                        # Collecter les poids pour cet exercice
                        exercise_weights = []
                        for key, weight in weights.items():
                            # Vérifier que la clé correspond exactement à l'exercice
                            parts = key.split('_')
                            if len(parts) >= 3 and parts[1] == str(idx) and weight > 0:
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

# Sidebar - Informations
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Calendrier du programme")

# Afficher le calendrier de la semaine en cours
today = datetime.now().date()
for i in range(7):
    day_date = today + timedelta(days=i)
    day_num = get_program_day(day_date)
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
st.sidebar.caption("💪 Tracker de Musculation v4.0 - Powered by Supabase")