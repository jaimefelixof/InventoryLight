# setores.py — InventoryLight
import streamlit as st
from auth import get_supabase


# ── DADOS ────────────────────────────────────────────────────
def carregar_setores():
    sb = get_supabase()
    res = sb.table("setores").select("id, nome, ativo, criado_em").order("nome").execute()
    return res.data or []


def criar_setor(nome: str):
    sb = get_supabase()
    sb.table("setores").insert({"nome": nome}).execute()


def atualizar_setor(setor_id: str, nome: str, ativo: bool):
    sb = get_supabase()
    sb.table("setores").update({"nome": nome, "ativo": ativo}).eq("id", setor_id).execute()


# ── TELA ─────────────────────────────────────────────────────
def tela_setores():
    st.title("🏢 Gerenciar Setores")

    if "tela_setor" not in st.session_state:
        st.session_state["tela_setor"] = "lista"

    # ── LISTAGEM ─────────────────────────────────────────────
    if st.session_state["tela_setor"] == "lista":

        if st.session_state.pop("setor_salvo", False):
            st.success("✅ Setor salvo com sucesso!")

        if st.button("➕ Novo Setor", type="primary"):
            st.session_state["tela_setor"] = "novo"
            st.session_state["setor_editar"] = None
            st.rerun()

        setores = carregar_setores()

        if not setores:
            st.info("Nenhum setor cadastrado.")
            return

        for s in setores:
            status_label = "✅ Ativo" if s["ativo"] else "❌ Inativo"
            with st.expander(f"**{s['nome']}** — {status_label}"):
                col_ed, col_ex = st.columns(2)
                with col_ed:
                    if st.button("✏️ Editar", key=f"ed_{s['id']}", use_container_width=True):
                        st.session_state["tela_setor"] = "editar"
                        st.session_state["setor_editar"] = s
                        st.rerun()

    # ── NOVO SETOR ───────────────────────────────────────────
    elif st.session_state["tela_setor"] == "novo":
        st.subheader("➕ Novo Setor")

        with st.form("form_novo_setor"):
            nome = st.text_input("Nome do Setor *")

            col_s, col_c = st.columns(2)
            salvar   = col_s.form_submit_button("💾 Salvar",   use_container_width=True)
            cancelar = col_c.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state["tela_setor"] = "lista"
            st.rerun()

        if salvar:
            if not nome:
                st.warning("Nome do setor é obrigatório.")
            else:
                try:
                    criar_setor(nome)
                    st.session_state["tela_setor"] = "lista"
                    st.session_state["setor_salvo"] = True
                    st.rerun()
                except Exception as e:
                    if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                        st.warning(f"Setor '{nome}' já existe.")
                    else:
                        st.error(f"Erro ao criar setor: {e}")

    # ── EDITAR SETOR ─────────────────────────────────────────
    elif st.session_state["tela_setor"] == "editar":
        s = st.session_state.get("setor_editar")
        st.subheader(f"✏️ Editando: {s['nome']}")

        with st.form("form_editar_setor"):
            nome  = st.text_input("Nome do Setor", value=s["nome"])
            ativo = st.toggle("Setor ativo", value=s["ativo"])

            col_s, col_c = st.columns(2)
            salvar   = col_s.form_submit_button("💾 Salvar",   use_container_width=True)
            cancelar = col_c.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state["tela_setor"] = "lista"
            st.rerun()

        if salvar:
            if not nome:
                st.warning("Nome do setor é obrigatório.")
            else:
                atualizar_setor(s["id"], nome, ativo)
                st.session_state["tela_setor"] = "lista"
                st.session_state["setor_salvo"] = True
                st.rerun()
