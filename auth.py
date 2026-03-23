import streamlit as st
import database
import json
import os
import base64

AUTH_FILE = ".gymtracking_auth.json"

def save_auth_state(username, password):
    """Sauvegarde les accès en local pour persister la session"""
    try:
        # Obfuscation basique pour ne pas stocker en clair pur
        encoded_pw = base64.b64encode(password.encode()).decode()
        with open(AUTH_FILE, "w") as f:
            json.dump({"username": username, "password": encoded_pw}, f)
    except Exception as e:
        print(f"Erreur sauvegarde auth: {e}")

def load_auth_state():
    """Charge les accès locaux si présents"""
    try:
        if os.path.exists(AUTH_FILE):
            with open(AUTH_FILE, "r") as f:
                data = json.load(f)
                pw = base64.b64decode(data["password"].encode()).decode()
                return data["username"], pw
    except Exception as e:
        print(f"Erreur chargement auth: {e}")
    return None, None

def clear_auth_state():
    """Supprime la session locale lors de la déconnexion"""
    try:
        if os.path.exists(AUTH_FILE):
            os.remove(AUTH_FILE)
    except:
        pass

def login_page(supabase):
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
                    user, session, error = database.login_user(supabase, username, password)
                    if user and session:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.session_state.session = session
                        st.session_state.username = username
                        save_auth_state(username, password)
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
                    success, message = database.create_user_account(supabase, new_username, new_password)
                    if success:
                        st.success(f"✅ {message} Vous pouvez maintenant vous connecter.")
                    else:
                        st.error(f"❌ {message}")