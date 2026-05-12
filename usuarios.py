# usuarios.py — InventoryLight
import streamlit as st
from auth import get_supabase


# ── ADMIN CLIENT ─────────────────────────────────────────────
def get_supabase_admin():
    from supabase import create_client
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


# ── DADOS ────────────────────────────────────────────────────
def carregar_usuarios():
    sb = get_supabase()
    res = (
        sb.table("perfis")
        .select("id, nome, papel, setor_id, setores(nome), criado_em")
        .order("nome")
        .execute()
    )
    return res.data or []


def carregar_setores():
    sb = get_supabase()
    res = sb.table("setores").select("id, nome").eq("ativo", True).order("nome").execute()
    return res.data or []


def criar_usuario(email: str, senha: str, nome: str, papel: str, setor_id: str):
    sb = get_supabase_admin()
    res = sb.auth.admin.create_user({
        "email": email,
        "password": senha,
        "email_confirm": True,
    })
    if not res.user:
        raise Exception("Erro ao criar usuário no Auth.")
    sb.table("perfis").insert({
        "id":       res.user.id,
        "nome":     nome,
        "papel":    papel,
        "setor_id": setor_id if papel == "usuario" else None,
    }).execute()


def atualizar_perfil(user_id: str, nome: str, papel: str, setor_id: str):
    sb = get_supabase()
    sb.table("perfis").update({
        "nome":     nome,
        "papel":    papel,
        "setor_id": setor_id if papel == "usuario" else None,
    }).eq("id", user_id).execute()


def excluir_usuario(user_id: str):
    sb = get_supabase_admin()
    sb.auth.admin.delete_user(user_id)
    sb.table("perfis").delete().eq("id", user_id).execute()


# ── TELA ─────────────────────────────────────────────────────
def tela_usuarios():
    st.title("👤 Gerenciar Usuários")

    if "tela_usuario" not in st.session_state:
        st.session_state["tela_usuario"] = "lista"

    setores = carregar_setores()
    mapa_setores = {s["nome"]: s["id"] for s in setores}

    # ── LISTAGEM ─────────────────────────────────────────────
    if st.session_state["tela_usuario"] == "lista":

        if st.session_state.pop("usuario_salvo", False):
            st.success("✅ Usuário salvo com sucesso!")

        if st.button("➕ Novo Usuário", type="primary"):
            st.session_state["tela_usuario"] = "novo"
            st.session_state["usuario_editar"] = None
            st.rerun()

        usuarios = carregar_usuarios()

        if not usuarios:
            st.info("Nenhum usuário cadastrado.")
            return

        for u in usuarios:
            setor_nome = u["setores"]["nome"] if u["setores"] else "Todos (Admin)"
            with st.expander(f"**{u['nome']}** — {u['papel'].upper()} | {setor_nome}"):
                col_ed, col_ex = st.columns(2)
                with col_ed:
                    if st.button("✏️ Editar", key=f"ed_{u['id']}", use_container_width=True):
                        st.session_state["tela_usuario"] = "editar"
                        st.session_state["usuario_editar"] = u
                        st.rerun()
                with col_ex:
                    if st.button("🗑️ Excluir", key=f"ex_{u['id']}", use_container_width=True, type="primary"):
                        if u["id"] == st.session_state.usuario.id:
                            st.error("Você não pode excluir seu próprio usuário.")
                        else:
                            excluir_usuario(u["id"])
                            st.success("Usuário excluído.")
                            st.rerun()

    # ── NOVO USUÁRIO ─────────────────────────────────────────
    elif st.session_state["tela_usuario"] == "novo":
        st.subheader("➕ Novo Usuário")

        with st.form("form_novo_usuario"):
            nome  = st.text_input("Nome completo *")
            email = st.text_input("E-mail *")
            senha = st.text_input("Senha *", type="password")
            papel = st.selectbox("Papel *", ["usuario", "admin"])

            setor_opcoes = ["— (Admin, sem restrição)"] + list(mapa_setores.keys())
            setor_sel    = st.selectbox("Setor", setor_opcoes)

            col_s, col_c = st.columns(2)
            salvar   = col_s.form_submit_button("💾 Salvar",   use_container_width=True)
            cancelar = col_c.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state["tela_usuario"] = "lista"
            st.rerun()

        if salvar:
            if not nome or not email or not senha:
                st.warning("Preencha todos os campos obrigatórios.")
            else:
                try:
                    setor_id = mapa_setores.get(setor_sel) if setor_sel != "— (Admin, sem restrição)" else None
                    criar_usuario(email, senha, nome, papel, setor_id)
                    st.session_state["tela_usuario"] = "lista"
                    st.session_state["usuario_salvo"] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao criar usuário: {e}")

    # ── EDITAR USUÁRIO ───────────────────────────────────────
    elif st.session_state["tela_usuario"] == "editar":
        u = st.session_state.get("usuario_editar")
        st.subheader(f"✏️ Editando: {u['nome']}")

        setor_opcoes = ["— (Admin, sem restrição)"] + list(mapa_setores.keys())
        setor_atual  = u["setores"]["nome"] if u["setores"] else "— (Admin, sem restrição)"

        with st.form("form_editar_usuario"):
            nome  = st.text_input("Nome", value=u["nome"])
            papel = st.selectbox("Papel", ["admin", "usuario"],
                                 index=["admin", "usuario"].index(u["papel"]))
            setor_sel = st.selectbox("Setor", setor_opcoes,
                                     index=setor_opcoes.index(setor_atual)
                                     if setor_atual in setor_opcoes else 0)

            col_s, col_c = st.columns(2)
            salvar   = col_s.form_submit_button("💾 Salvar",   use_container_width=True)
            cancelar = col_c.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state["tela_usuario"] = "lista"
            st.rerun()

        if salvar:
            setor_id = mapa_setores.get(setor_sel) if setor_sel != "— (Admin, sem restrição)" else None
            atualizar_perfil(u["id"], nome, papel, setor_id)
            st.session_state["tela_usuario"] = "lista"
            st.session_state["usuario_salvo"] = True
            st.rerun()
