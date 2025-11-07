import streamlit as st
import supabase
import os
import uuid
from datetime import datetime
from supabase import create_client
import tempfile
from PIL import Image
import io

# Configuration Supabase
SUPABASE_URL = "https://ruttkxnpgjehhmnegrjw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ1dHRreG5wZ2plaGhtbmVncmp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIxOTIyMTMsImV4cCI6MjA3Nzc2ODIxM30.kOc6IwlFp30ndedNnZE3KFJtp6_QtqRXLfioFVGwcUE"

# Initialisation Supabase
@st.cache_resource
def init_supabase():
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Test de connexion
        response = client.table('projects').select('*', count='exact').limit(1).execute()
        st.success("✅ Connexion à Supabase établie")
        return client
    except Exception as e:
        st.error(f"❌ Erreur de connexion à Supabase: {str(e)}")
        return None

supabase_client = init_supabase()

# Configuration de la page
st.set_page_config(
    page_title="Galerie de Projets",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
    }
    .project-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-pending { background-color: #fff3cd; color: #856404; padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; }
    .status-approved { background-color: #d1edff; color: #0c5460; padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; }
    .status-rejected { background-color: #f8d7da; color: #721c24; padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; }
    .tag { background-color: #3498db; color: white; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.7rem; margin-right: 0.3rem; }
    .feature-card { text-align: center; padding: 1.5rem; border-radius: 10px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .success-box { background-color: #d4edda; color: #155724; padding: 1rem; border-radius: 5px; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

# Gestion de l'authentification
def init_auth():
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None

def login_user(email, password):
    try:
        if not supabase_client:
            st.error("❌ Base de données non disponible")
            return
            
        auth_response = supabase_client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if auth_response.user:
            st.session_state.user = auth_response.user
            st.session_state.user_info = {
                'id': auth_response.user.id,
                'email': auth_response.user.email,
                'is_admin': auth_response.user.email == 'admin@gmail.com'
            }
            st.success("✅ Connexion réussie !")
            st.rerun()
        else:
            st.error("❌ Email ou mot de passe incorrect")
    except Exception as e:
        st.error(f"❌ Erreur de connexion: {str(e)}")

def register_user(email, password, confirm):
    if password != confirm:
        st.error("❌ Les mots de passe ne correspondent pas")
        return
    if len(password) < 6:
        st.error("❌ Le mot de passe doit faire au moins 6 caractères")
        return
    
    try:
        if not supabase_client:
            st.error("❌ Base de données non disponible")
            return
            
        auth_response = supabase_client.auth.sign_up({
            "email": email,
            "password": password,
        })
        if auth_response.user:
            st.success("✅ Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
        else:
            st.error("❌ Erreur lors de la création du compte")
    except Exception as e:
        st.error(f"❌ Cet email est peut-être déjà utilisé: {str(e)}")

def logout_user():
    st.session_state.user = None
    st.session_state.user_info = None
    st.success("✅ Déconnexion réussie")
    st.rerun()

# Fonctions utilitaires
def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in {'png', 'jpg', 'jpeg', 'gif'}:
        return 'image'
    elif ext == 'pdf':
        return 'pdf'
    elif ext in {'glb', 'gltf', 'obj', 'stl'}:
        return '3d'
    return 'unknown'

def upload_project(title, description, tags, file):
    try:
        # Vérifier la taille du fichier (max 50MB)
        if file.size > 50 * 1024 * 1024:
            st.error("❌ Le fichier est trop volumineux (max 50MB)")
            return
        
        # Générer un nom de fichier unique
        file_extension = file.name.split('.')[-1].lower()
        filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Préparer les données du projet
        project_data = {
            'title': title,
            'description': description,
            'file_path': filename,
            'file_type': get_file_type(file.name),
            'tags': tags,
            'author_id': st.session_state.user_info['id'],
            'author_name': st.session_state.user_info['email'],
            'status': 'approved' if st.session_state.user_info.get('is_admin') else 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        # Insérer dans la base de données
        response = supabase_client.table('projects').insert(project_data).execute()
        
        if response.data:
            if st.session_state.user_info.get('is_admin'):
                st.markdown('<div class="success-box">✅ Projet publié avec succès !</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="success-box">📨 Projet soumis ! En attente de validation par l\'administrateur.</div>', unsafe_allow_html=True)
            
            st.session_state.page = "projects"
            st.rerun()
        else:
            st.error("❌ Erreur lors de l'ajout du projet à la base de données")
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'ajout du projet : {str(e)}")

def delete_project(project_id):
    try:
        supabase_client.table('projects').delete().eq('id', project_id).execute()
        st.success("✅ Projet supprimé avec succès")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Erreur lors de la suppression du projet: {str(e)}")

def update_project_status(project_id, status):
    try:
        supabase_client.table('projects')\
            .update({'status': status})\
            .eq('id', project_id)\
            .execute()
        st.success(f"✅ Projet {'approuvé' if status == 'approved' else 'rejeté'} avec succès")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Erreur lors de la mise à jour du statut: {str(e)}")

# Pages
def home_page():
    st.markdown('<div class="main-header">🎓 Galerie de Projets Éducatifs</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); 
                color: white; border-radius: 10px; margin-bottom: 2rem;'>
        <h2>Découvrez, partagez et collaborez sur des projets créatifs</h2>
        <p>Dans un environnement éducatif stimulant</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features grid
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class='feature-card'>
            <div style='font-size: 2.5rem; margin-bottom: 1rem;'>📁</div>
            <h3>Multiformats</h3>
            <p>Images, PDFs et modèles 3D supportés</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='feature-card'>
            <div style='font-size: 2.5rem; margin-bottom: 1rem;'>🔍</div>
            <h3>Recherche Avancée</h3>
            <p>Trouvez rapidement des projets</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class='feature-card'>
            <div style='font-size: 2.5rem; margin-bottom: 1rem;'>👑</div>
            <h3>Validation Admin</h3>
            <p>Projets validés par les enseignants</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class='feature-card'>
            <div style='font-size: 2.5rem; margin-bottom: 1rem;'>🎯</div>
            <h3>Modération</h3>
            <p>Maintenez la qualité des contenus</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Navigation buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.user_info:
            if st.button("➕ Ajouter un projet", use_container_width=True):
                st.session_state.page = "add_project"
                st.rerun()
        else:
            if st.button("🚀 Commencer", use_container_width=True):
                st.session_state.page = "register"
                st.rerun()
    
    with col2:
        if st.button("👀 Voir les projets", use_container_width=True):
            st.session_state.page = "projects"
            st.rerun()
    
    with col3:
        if st.session_state.user_info:
            if st.button("🗂 Mes projets", use_container_width=True):
                st.session_state.page = "my_projects"
                st.rerun()
        else:
            if st.button("🔐 Se connecter", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()
    
    # Credits
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 2rem; background: #2c3e50; color: white; border-radius: 10px;'>
        <h3>🚀 Projet réalisé par :</h3>
        <h2 style='color: #3498db;'>Aissa Zemmour, Souhaib Chhbari, Mensour</h2>
        <p>Galerie de projets éducatifs - 2025 pour licee mouhos</p>
    </div>
    """, unsafe_allow_html=True)

def login_page():
    st.markdown('<div class="main-header">🔐 Connexion</div>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        email = st.text_input("📧 Email")
        password = st.text_input("🔒 Mot de passe", type="password")
        
        if st.form_submit_button("🚀 Se connecter", use_container_width=True):
            if email and password:
                login_user(email, password)
            else:
                st.error("❌ Veuillez remplir tous les champs")
    
    st.markdown("---")
    st.info("**Compte administrateur de test :** admin@gmail.com / admin12345")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Créer un compte", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()
    with col2:
        if st.button("🏠 Retour à l'accueil", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

def register_page():
    st.markdown('<div class="main-header">👤 Créer un compte</div>', unsafe_allow_html=True)
    
    with st.form("register_form"):
        email = st.text_input("📧 Email")
        password = st.text_input("🔒 Mot de passe (min. 6 caractères)", type="password")
        confirm = st.text_input("🔒 Confirmer le mot de passe", type="password")
        
        if st.form_submit_button("🚀 Créer un compte", use_container_width=True):
            if email and password and confirm:
                register_user(email, password, confirm)
            else:
                st.error("❌ Veuillez remplir tous les champs")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔐 Se connecter", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
    with col2:
        if st.button("🏠 Retour à l'accueil", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

def projects_page():
    st.markdown('<div class="main-header">🎨 Tous les projets</div>', unsafe_allow_html=True)
    
    # Filtres et recherche
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search = st.text_input("🔍 Rechercher un projet", placeholder="Titre, description, tags...")
    
    with col2:
        filter_type = st.selectbox("Type de fichier", ["Tous", "Images", "PDF", "3D"])
    
    with col3:
        if st.session_state.user_info and st.session_state.user_info.get('is_admin'):
            status_filter = st.selectbox("Statut", ["Tous", "En attente", "Approuvé", "Rejeté"])
        else:
            status_filter = "Approuvé"
    
    # Récupération des projets
    try:
        query = supabase_client.table('projects').select('*')
        
        # Appliquer les filtres
        if filter_type != "Tous":
            file_type_map = {"Images": "image", "PDF": "pdf", "3D": "3d"}
            query = query.eq('file_type', file_type_map[filter_type])
        
        if search:
            query = query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%,tags.ilike.%{search}%")
        
        if status_filter != "Tous" and st.session_state.user_info and st.session_state.user_info.get('is_admin'):
            status_map = {"En attente": "pending", "Approuvé": "approved", "Rejeté": "rejected"}
            query = query.eq('status', status_map[status_filter])
        elif not st.session_state.user_info or not st.session_state.user_info.get('is_admin'):
            query = query.eq('status', 'approved')
        
        response = query.order('created_at', desc=True).execute()
        projects = response.data if response.data else []
        
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des projets: {str(e)}")
        projects = []
    
    # Affichage des projets
    if not projects:
        st.info("ℹ️ Aucun projet trouvé avec ces critères de recherche.")
    else:
        for project in projects:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Type et statut
                    col_type, col_status = st.columns(2)
                    with col_type:
                        if project['file_type'] == 'image':
                            st.markdown("**🖼️ Image**")
                        elif project['file_type'] == 'pdf':
                            st.markdown("**📄 PDF**")
                        elif project['file_type'] == '3d':
                            st.markdown("**🎮 Modèle 3D**")
                    
                    with col_status:
                        status_class = f"status-{project['status']}"
                        status_text = {
                            'pending': '⏳ En attente',
                            'approved': '✅ Approuvé', 
                            'rejected': '❌ Rejeté'
                        }.get(project['status'], '⏳ En attente')
                        st.markdown(f'<div class="{status_class}">{status_text}</div>', unsafe_allow_html=True)
                    
                    # Titre et description
                    st.subheader(project['title'])
                    st.write(project['description'])
                    
                    # Tags
                    if project['tags']:
                        tags_html = "".join([f'<span class="tag">{tag.strip()}</span>' for tag in project['tags'].split(',')])
                        st.markdown(tags_html, unsafe_allow_html=True)
                    
                    # Auteur et date
                    st.caption(f"👤 {project['author_name']} • 📅 {project['created_at'][:10]}")
                
                with col2:
                    # Affichage du type de fichier
                    if project['file_type'] == 'image':
                        st.info("🖼️ Image")
                    elif project['file_type'] == 'pdf':
                        st.info("📄 PDF Document")
                    elif project['file_type'] == '3d':
                        st.info("🎮 Modèle 3D")
                    
                    # Boutons d'action
                    if st.button("👁️ Voir", key=f"view_{project['id']}", use_container_width=True):
                        st.session_state.selected_project = project
                        st.session_state.page = "project_detail"
                        st.rerun()
                    
                    # Bouton suppression pour l'auteur ou l'admin
                    if (st.session_state.user_info and 
                        (st.session_state.user_info['id'] == project['author_id'] or 
                         st.session_state.user_info.get('is_admin'))):
                        if st.button("🗑️ Supprimer", key=f"delete_{project['id']}", use_container_width=True):
                            delete_project(project['id'])
                
                st.markdown("---")
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.user_info:
            if st.button("➕ Ajouter un projet", use_container_width=True):
                st.session_state.page = "add_project"
                st.rerun()
    with col2:
        if st.button("🏠 Retour à l'accueil", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

def add_project_page():
    st.markdown('<div class="main-header">➕ Ajouter un projet</div>', unsafe_allow_html=True)
    
    if not supabase_client:
        st.error("❌ Base de données non disponible. Veuillez réessayer plus tard.")
        return
        
    if not st.session_state.user_info:
        st.error("❌ Veuillez vous connecter pour ajouter un projet")
        return
    
    with st.form("add_project_form", clear_on_submit=True):
        title = st.text_input("📝 Titre du projet *", placeholder="Titre de votre projet")
        description = st.text_area("📋 Description du projet *", height=100, placeholder="Décrivez votre projet...")
        tags = st.text_input("🏷️ Tags", placeholder="technologie, sujet, domaine... (séparés par des virgules)")
        file = st.file_uploader("📁 Fichier * (Image, PDF ou Modèle 3D - max 50MB)", 
                               type=['png', 'jpg', 'jpeg', 'gif', 'pdf', 'glb', 'gltf', 'obj', 'stl'])
        
        submitted = st.form_submit_button("🚀 Publier le projet", use_container_width=True)
        
        if submitted:
            if not title or not description or not file:
                st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
            else:
                with st.spinner("Publication en cours..."):
                    upload_project(title, description, tags, file)
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👀 Voir les projets", use_container_width=True):
            st.session_state.page = "projects"
            st.rerun()
    with col2:
        if st.button("🏠 Retour à l'accueil", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

def my_projects_page():
    st.markdown('<div class="main-header">🗂 Mes projets</div>', unsafe_allow_html=True)
    
    if not st.session_state.user_info:
        st.error("❌ Veuillez vous connecter")
        return
    
    try:
        response = supabase_client.table('projects')\
            .select('*')\
            .eq('author_id', st.session_state.user_info['id'])\
            .order('created_at', desc=True)\
            .execute()
        
        projects = response.data if response.data else []
        
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de vos projets: {str(e)}")
        projects = []
    
    if not projects:
        st.info("ℹ️ Vous n'avez pas encore de projets.")
        if st.button("➕ Ajouter mon premier projet", use_container_width=True):
            st.session_state.page = "add_project"
            st.rerun()
    else:
        for project in projects:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.subheader(project['title'])
                    st.write(project['description'])
                    
                    # Statut
                    status_class = f"status-{project['status']}"
                    status_text = {
                        'pending': '⏳ En attente',
                        'approved': '✅ Approuvé', 
                        'rejected': '❌ Rejeté'
                    }.get(project['status'], '⏳ En attente')
                    st.markdown(f'<div class="{status_class}">{status_text}</div>', unsafe_allow_html=True)
                    
                    st.caption(f"📅 {project['created_at'][:10]}")
                
                with col2:
                    if st.button("👁️ Voir", key=f"my_view_{project['id']}", use_container_width=True):
                        st.session_state.selected_project = project
                        st.session_state.page = "project_detail"
                        st.rerun()
                    
                    if st.button("🗑️ Supprimer", key=f"my_delete_{project['id']}", use_container_width=True):
                        delete_project(project['id'])
                
                st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Nouveau projet", use_container_width=True):
            st.session_state.page = "add_project"
            st.rerun()
    with col2:
        if st.button("🏠 Retour à l'accueil", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

def profile_page():
    st.markdown('<div class="main-header">👤 Mon Profil</div>', unsafe_allow_html=True)
    
    if not st.session_state.user_info:
        st.error("❌ Veuillez vous connecter")
        return
    
    user_info = st.session_state.user_info
    
    # Statistiques
    try:
        response = supabase_client.table('projects')\
            .select('*')\
            .eq('author_id', user_info['id'])\
            .execute()
        
        user_projects = response.data if response.data else []
        
        stats = {
            'total': len(user_projects),
            'pending': len([p for p in user_projects if p['status'] == 'pending']),
            'approved': len([p for p in user_projects if p['status'] == 'approved']),
            'rejected': len([p for p in user_projects if p['status'] == 'rejected'])
        }
    except Exception as e:
        stats = {'total': 0, 'pending': 0, 'approved': 0, 'rejected': 0}
    
    # Affichage des informations
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Informations personnelles")
        st.write(f"**📧 Email :** {user_info['email']}")
        st.write(f"**🆔 ID :** {user_info['id']}")
        if user_info.get('is_admin'):
            st.success("👑 Compte administrateur")
    
    with col2:
        st.subheader("Statistiques")
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("Total", stats['total'])
            st.metric("En attente", stats['pending'])
        with col_stat2:
            st.metric("Approuvés", stats['approved'])
            st.metric("Rejetés", stats['rejected'])
    
    # Navigation
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🗂 Mes projets", use_container_width=True):
            st.session_state.page = "my_projects"
            st.rerun()
    with col2:
        if st.button("➕ Nouveau projet", use_container_width=True):
            st.session_state.page = "add_project"
            st.rerun()
    with col3:
        if st.button("🏠 Accueil", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

def admin_page():
    st.markdown('<div class="main-header">👑 Dashboard Administrateur</div>', unsafe_allow_html=True)
    
    if not st.session_state.user_info or not st.session_state.user_info.get('is_admin'):
        st.error("❌ Accès non autorisé")
        return
    
    try:
        # Projets en attente
        pending_response = supabase_client.table('projects')\
            .select('*')\
            .eq('status', 'pending')\
            .order('created_at', asc=True)\
            .execute()
        
        pending_projects = pending_response.data if pending_response.data else []
        
        # Statistiques globales
        all_response = supabase_client.table('projects').select('*').execute()
        all_projects = all_response.data if all_response.data else []
        
        stats = {
            'total': len(all_projects),
            'pending': len([p for p in all_projects if p['status'] == 'pending']),
            'approved': len([p for p in all_projects if p['status'] == 'approved']),
            'rejected': len([p for p in all_projects if p['status'] == 'rejected'])
        }
        
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données: {str(e)}")
        pending_projects = []
        stats = {'total': 0, 'pending': 0, 'approved': 0, 'rejected': 0}
    
    # Statistiques
    st.subheader("📊 Statistiques globales")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", stats['total'])
    with col2:
        st.metric("En attente", stats['pending'])
    with col3:
        st.metric("Approuvés", stats['approved'])
    with col4:
        st.metric("Rejetés", stats['rejected'])
    
    # Projets en attente
    st.subheader(f"⏳ Projets en attente de validation ({len(pending_projects)})")
    
    if not pending_projects:
        st.success("🎉 Aucun projet en attente de validation !")
    else:
        for project in pending_projects:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**{project['title']}**")
                    st.write(project['description'])
                    st.caption(f"👤 {project['author_name']} • 📅 {project['created_at'][:10]}")
                
                with col2:
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("✅", key=f"approve_{project['id']}", use_container_width=True):
                            update_project_status(project['id'], 'approved')
                    with col_btn2:
                        if st.button("❌", key=f"reject_{project['id']}", use_container_width=True):
                            update_project_status(project['id'], 'rejected')
                
                st.markdown("---")
    
    # Actions rapides
    st.subheader("⚡ Actions rapides")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("👀 Voir tous les projets", use_container_width=True):
            st.session_state.page = "projects"
            st.rerun()
    with col2:
        if st.button("🔄 Actualiser", use_container_width=True):
            st.rerun()
    with col3:
        if st.button("🏠 Accueil", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

def project_detail_page():
    if 'selected_project' not in st.session_state:
        st.error("❌ Projet non trouvé")
        st.session_state.page = "projects"
        st.rerun()
        return
    
    project = st.session_state.selected_project
    st.markdown(f'<div class="main-header">{project["title"]}</div>', unsafe_allow_html=True)
    
    # Informations du projet
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write(f"**Description :** {project['description']}")
        st.write(f"**Auteur :** {project['author_name']}")
        st.write(f"**Date :** {project['created_at']}")
        st.write(f"**Type :** {project['file_type']}")
        
        status_class = f"status-{project['status']}"
        status_text = {
            'pending': '⏳ En attente',
            'approved': '✅ Approuvé', 
            'rejected': '❌ Rejeté'
        }.get(project['status'], '⏳ En attente')
        st.write(f"**Statut :** <span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)
        
        if project['tags']:
            st.write("**Tags :**")
            tags_html = "".join([f'<span class="tag">{tag.strip()}</span>' for tag in project['tags'].split(',')])
            st.markdown(tags_html, unsafe_allow_html=True)
    
    with col2:
        # Actions admin
        if st.session_state.user_info and st.session_state.user_info.get('is_admin') and project['status'] == 'pending':
            st.subheader("Actions admin")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("✅ Accepter", use_container_width=True):
                    update_project_status(project['id'], 'approved')
            with col_btn2:
                if st.button("❌ Refuser", use_container_width=True):
                    update_project_status(project['id'], 'rejected')
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 Retour aux projets", use_container_width=True):
            st.session_state.page = "projects"
            st.rerun()
    with col2:
        if st.button("🏠 Accueil", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

# Barre latérale
def sidebar():
    with st.sidebar:
        st.title("🎓 Navigation")
        
        if st.session_state.user_info:
            st.write(f"👤 **{st.session_state.user_info['email']}**")
            if st.session_state.user_info.get('is_admin'):
                st.success("👑 Administrateur")
            
            # Menu utilisateur
            menu_options = [
                "🏠 Accueil",
                "👀 Voir les projets", 
                "🗂 Mes projets",
                "👤 Mon profil"
            ]
            
            if st.session_state.user_info.get('is_admin'):
                menu_options.append("👑 Administration")
            
            selected_menu = st.selectbox("Menu", menu_options)
            
            # Mapping des sélections vers les pages
            page_map = {
                "🏠 Accueil": "home",
                "👀 Voir les projets": "projects",
                "🗂 Mes projets": "my_projects", 
                "👤 Mon profil": "profile",
                "👑 Administration": "admin"
            }
            
            if selected_menu:
                st.session_state.page = page_map[selected_menu]
            
            if st.button("🚪 Déconnexion", use_container_width=True):
                logout_user()
        
        else:
            st.info("Non connecté")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔐 Connexion", use_container_width=True):
                    st.session_state.page = "login"
                    st.rerun()
            with col2:
                if st.button("📝 Inscription", use_container_width=True):
                    st.session_state.page = "register"
                    st.rerun()

# Application principale
def main():
    init_auth()
    
    # Initialisation de la page
    if 'page' not in st.session_state:
        st.session_state.page = "home"
    
    # Barre latérale
    sidebar()
    
    # Navigation des pages
    if st.session_state.page == "home":
        home_page()
    elif st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "register":
        register_page()
    elif st.session_state.page == "projects":
        projects_page()
    elif st.session_state.page == "add_project":
        add_project_page()
    elif st.session_state.page == "my_projects":
        my_projects_page()
    elif st.session_state.page == "profile":
        profile_page()
    elif st.session_state.page == "admin":
        admin_page()
    elif st.session_state.page == "project_detail":
        project_detail_page()

if __name__ == "__main__":
    main()