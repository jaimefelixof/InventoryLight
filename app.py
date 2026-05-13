# app.py — InventoryLight
import streamlit as st
from auth import init_session, tela_login, logout, get_nome_usuario, is_admin

st.set_page_config(
    page_title="InventoryLight",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session()

if not st.session_state.logado:
    tela_login()
    st.stop()

# ── ESTADO DE NAVEGAÇÃO ──────────────────────────────────────
if "rota" not in st.session_state:
    st.session_state.rota = "dashboard"

# ── SIDEBAR ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🖥️ InventoryLight")
    st.markdown(f"**{get_nome_usuario()}**")
    st.caption("Administrador" if is_admin() else "Usuário")
    st.divider()

    if is_admin():
        st.caption("MENU")

    menu_principal = {
        "📊 Dashboard": "dashboard",
        "🖥️ Ativos":    "ativos",
        "📄 Licenças":  "licencas",
        "⚠️ Alertas":   "alertas",
        "📥 Exportar":  "exportar",
        "🤖 Assistente IA": "assistente",
    }

    for label, rota in menu_principal.items():
        ativo = st.session_state.rota == rota
        if st.button(label, use_container_width=True,
                     type="primary" if ativo else "secondary"):
            st.session_state.rota = rota
            st.rerun()

    if is_admin():
        st.divider()
        st.caption("ADMINISTRAÇÃO")

        menu_admin = {
            "👤 Usuários": "usuarios",
            "🏢 Setores":  "setores",
        }

        for label, rota in menu_admin.items():
            ativo = st.session_state.rota == rota
            if st.button(label, use_container_width=True,
                         type="primary" if ativo else "secondary"):
                st.session_state.rota = rota
                st.rerun()

    st.divider()
    if st.button("Sair", use_container_width=True):
        logout()

# ── PÁGINAS ──────────────────────────────────────────────────
rota = st.session_state.rota

if rota == "dashboard":
    from dashboard import tela_dashboard
    tela_dashboard()

elif rota == "ativos":
    from ativos import tela_ativos
    tela_ativos()

elif rota == "licencas":
    from licencas import tela_licencas
    tela_licencas()

elif rota == "alertas":
    from alertas import tela_alertas
    tela_alertas()

elif rota == "exportar":
    from exportar import tela_exportar
    tela_exportar()

elif rota == "usuarios":
    from usuarios import tela_usuarios
    tela_usuarios()

elif rota == "setores":
    from setores import tela_setores
    tela_setores()

elif rota == "assistente":
    from assistente import tela_assistente
    tela_assistente()
