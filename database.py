import streamlit as st
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