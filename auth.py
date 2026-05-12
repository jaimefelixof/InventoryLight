# auth.py — InventoryLight
# Gerencia login, logout e sessão via Supabase Auth

import streamlit as st
from supabase import create_client, Client
import os

# ── CONFIGURAÇÃO ─────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]


@st.cache_resource
def get_supabase() -> Client:
    """Cria client Supabase uma única vez (cache global)."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ── SESSÃO ───────────────────────────────────────────────────
def init_session():
    """Inicializa as chaves de sessão necessárias."""
    defaults = {
        "usuario": None,   # dados do auth.users
        "perfil": None,    # dados da tabela perfis (papel, setor_id)
        "logado": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def carregar_perfil(user_id: str) -> dict | None:
    """Busca perfil e setor do usuário na tabela public.perfis."""
    sb = get_supabase()
    res = (
        sb.table("perfis")
        .select("nome, papel, setor_id, setores(nome)")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return res.data if res.data else None


# ── LOGIN ────────────────────────────────────────────────────
def tela_login():
    """Renderiza o formulário de login e processa autenticação."""
    st.title("🔒 InventoryLight")
    st.subheader("Acesso ao Sistema")

    with st.form("form_login"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", use_container_width=True)

    if entrar:
        if not email or not senha:
            st.warning("Preencha e-mail e senha.")
            return

        sb = get_supabase()
        try:
            res = sb.auth.sign_in_with_password({"email": email, "password": senha})

            if res.user:
                perfil = carregar_perfil(res.user.id)
                if not perfil:
                    st.error("Usuário sem perfil cadastrado. Contate o administrador.")
                    return

                st.session_state.usuario = res.user
                st.session_state.perfil  = perfil
                st.session_state.logado  = True
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")

        except Exception as e:
            st.error(f"Erro ao autenticar: {e}")


# ── LOGOUT ───────────────────────────────────────────────────
def logout():
    """Encerra sessão e limpa estado."""
    sb = get_supabase()
    try:
        sb.auth.sign_out()
    except Exception:
        pass
    for k in ["usuario", "perfil", "logado"]:
        st.session_state[k] = None if k != "logado" else False
    st.rerun()


# ── HELPERS ──────────────────────────────────────────────────
def is_admin() -> bool:
    return st.session_state.get("perfil", {}).get("papel") == "admin"


def get_setor_id() -> str | None:
    return st.session_state.get("perfil", {}).get("setor_id")


def get_nome_usuario() -> str:
    return st.session_state.get("perfil", {}).get("nome", "Usuário")
