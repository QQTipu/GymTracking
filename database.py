import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

def init_supabase():
    """Initialise et retourne le client Supabase"""
    try:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
        
        if 'supabase_client' not in st.session_state:
            st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        return st.session_state.supabase_client
    except Exception as e:
        st.error("⚠️ Configuration Supabase manquante. Voir les instructions dans le README.")
        st.stop()

def create_user_account(supabase, username, password):
    """Crée un compte utilisateur dans Supabase Auth"""
    try:
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

def login_user(supabase, username, password):
    """Connecte un utilisateur"""
    try:
        email = f"{username}@workout.app"
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if response.user and response.session:
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

def logout_user(supabase):
    """Déconnecte l'utilisateur"""
    try:
        supabase.auth.sign_out()
    except:
        pass

def save_workout_data(supabase, user_id, data):
    """Sauvegarde les données d'entraînement de l'utilisateur"""
    try:
        result = supabase.table('user_data').select("*").eq('user_id', user_id).execute()
        
        if len(result.data) > 0:
            supabase.table('user_data').update({
                'workout_data': data,
                'updated_at': datetime.now().isoformat()
            }).eq('user_id', user_id).execute()
        else:
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

def load_workout_data(supabase, user_id):
    """Charge les données d'entraînement de l'utilisateur"""
    try:
        result = supabase.table('user_data').select("workout_data").eq('user_id', user_id).execute()
        if len(result.data) > 0:
            return result.data[0]['workout_data']
        return None
    except Exception as e:
        st.error(f"Erreur chargement: {str(e)}")
        return None

def get_all_programs(supabase):
    """Récupère la liste des programmes disponibles"""
    try:
        response = supabase.table('programs').select("*").order('id').execute()
        return response.data
    except Exception as e:
        st.error(f"Erreur chargement liste programmes: {str(e)}")
        return []

def load_program_by_id(supabase, program_id):
    """Charge les exercices d'un programme spécifique"""
    try:
        response = supabase.table('exercices').select("*").eq('program_id', program_id).order('id').execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            # Renommer les colonnes pour correspondre à ce que l'app attend (format CSV original)
            df = df.rename(columns={
                'day_number': 'Jour',
                'workout_type': 'Type',
                'exercise_name': 'Exercice',
                'sets': 'Séries',
                'reps_rpe': 'Répétitions (RPE)',
                'notes': 'Notes'
            })
        return df
    except Exception as e:
        st.error(f"Erreur chargement détails programme: {str(e)}")
        return pd.DataFrame()