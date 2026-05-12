# ativos.py — InventoryLight
import streamlit as st
import pandas as pd
from datetime import date
from auth import get_supabase, is_admin, get_setor_id


# ── DADOS ────────────────────────────────────────────────────
def carregar_setores():
    sb = get_supabase()
    res = sb.table("setores").select("id, nome").eq("ativo", True).order("nome").execute()
    return res.data or []


def carregar_ativos():
    sb = get_supabase()
    query = (
        sb.table("ativos")
        .select("id, nome, tipo, numero_serie, status, data_aquisicao, data_garantia, observacoes, setor_id, setores(nome)")
        .eq("deletado", False)
        .order("nome")
    )
    if not is_admin():
        query = query.eq("setor_id", get_setor_id())
    res = query.execute()
    return res.data or []


def salvar_ativo(dados: dict, ativo_id: str = None):
    sb = get_supabase()
    if ativo_id:
        sb.table("ativos").update(dados).eq("id", ativo_id).execute()
        registrar_historico(ativo_id, dados)
    else:
        sb.table("ativos").insert(dados).execute()


def excluir_ativo(ativo_id: str):
    sb = get_supabase()
    sb.table("ativos").update({"deletado": True}).eq("id", ativo_id).execute()


def registrar_historico(ativo_id: str, dados: dict):
    sb = get_supabase()
    usuario_id = st.session_state.usuario.id
    registros = [
        {"ativo_id": ativo_id, "usuario_id": usuario_id, "campo": k, "valor_depois": str(v)}
        for k, v in dados.items()
    ]
    if registros:
        sb.table("historico").insert(registros).execute()


# ── FORMULÁRIO ───────────────────────────────────────────────
def formulario_ativo(ativo: dict = None):
    setores = carregar_setores()
    mapa_setores = {s["nome"]: s["id"] for s in setores}

    nome_atual        = ativo["nome"]            if ativo else ""
    tipo_atual        = ativo["tipo"]            if ativo else "hardware"
    serie_atual       = ativo["numero_serie"]    if ativo else ""
    status_atual      = ativo["status"]          if ativo else "ativo"
    obs_atual         = ativo["observacoes"]     if ativo else ""
    setor_nome_atual  = ativo["setores"]["nome"] if ativo else list(mapa_setores.keys())[0]
    aquisicao_atual   = date.fromisoformat(ativo["data_aquisicao"]) if ativo and ativo["data_aquisicao"] else None
    garantia_atual    = date.fromisoformat(ativo["data_garantia"])  if ativo and ativo["data_garantia"]  else None

    chave = "form_ativo_edicao" if ativo else "form_ativo_novo"

    with st.form(chave):
        col1, col2 = st.columns(2)
        with col1:
            nome         = st.text_input("Nome do Ativo *", value=nome_atual)
            tipo         = st.selectbox("Tipo *", ["hardware", "software", "outro"],
                                        index=["hardware", "software", "outro"].index(tipo_atual))
            numero_serie = st.text_input("Número de Série", value=serie_atual)
            status       = st.selectbox("Status *", ["ativo", "em_manutencao", "desativado"],
                                        index=["ativo", "em_manutencao", "desativado"].index(status_atual))
        with col2:
            setor_nome     = st.selectbox("Setor *", list(mapa_setores.keys()),
                                          index=list(mapa_setores.keys()).index(setor_nome_atual)
                                          if setor_nome_atual in mapa_setores else 0)
            data_aquisicao = st.date_input("Data de Aquisição", value=aquisicao_atual)
            data_garantia  = st.date_input("Vencimento da Garantia", value=garantia_atual)

        observacoes = st.text_area("Observações", value=obs_atual)

        col_s, col_c = st.columns(2)
        salvar    = col_s.form_submit_button("💾 Salvar",    use_container_width=True)
        cancelar  = col_c.form_submit_button("✖ Cancelar",  use_container_width=True)

    if cancelar:
        st.session_state["tela_ativo"] = "lista"
        st.rerun()

    if salvar:
        if not nome:
            st.warning("Nome do ativo é obrigatório.")
            return None
        return {
            "nome":           nome,
            "tipo":           tipo,
            "numero_serie":   numero_serie or None,
            "status":         status,
            "setor_id":       mapa_setores[setor_nome],
            "data_aquisicao": data_aquisicao.isoformat() if data_aquisicao else None,
            "data_garantia":  data_garantia.isoformat()  if data_garantia  else None,
            "observacoes":    observacoes or None,
            "criado_por":     st.session_state.usuario.id,
        }
    return None


# ── TELA ─────────────────────────────────────────────────────
def tela_ativos():
    st.title("🖥️ Gestão de Ativos")

    if "tela_ativo" not in st.session_state:
        st.session_state["tela_ativo"] = "lista"

    # ── LISTAGEM ─────────────────────────────────────────────
    if st.session_state["tela_ativo"] == "lista":

        if st.session_state.pop("ativo_salvo", False):
            st.success("✅ Ativo salvo com sucesso!")

        if is_admin():
            if st.button("➕ Novo Ativo", type="primary"):
                st.session_state["tela_ativo"] = "novo"
                st.session_state["ativo_editar"] = None
                st.rerun()

        ativos = carregar_ativos()

        if not ativos:
            st.info("Nenhum ativo cadastrado.")
            return

        col1, col2 = st.columns(2)
        with col1:
            filtro_status = st.selectbox("Status", ["Todos", "ativo", "em_manutencao", "desativado"])
        with col2:
            filtro_tipo = st.selectbox("Tipo", ["Todos", "hardware", "software", "outro"])

        dados = ativos
        if filtro_status != "Todos":
            dados = [a for a in dados if a["status"] == filtro_status]
        if filtro_tipo != "Todos":
            dados = [a for a in dados if a["tipo"] == filtro_tipo]

        df = pd.DataFrame([{
            "Nome":    a["nome"],
            "Tipo":    a["tipo"],
            "Setor":   a["setores"]["nome"] if a["setores"] else "-",
            "Status":  a["status"],
            "Garantia": a["data_garantia"] or "-",
            "Série":   a["numero_serie"] or "-",
        } for a in dados])

        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(dados)} ativo(s) encontrado(s)")

        if is_admin() and dados:
            st.divider()
            nomes = [a["nome"] for a in dados]
            selecionado = st.selectbox("Selecione para editar ou excluir", nomes)
            ativo_sel = next((a for a in dados if a["nome"] == selecionado), None)

            if ativo_sel:
                col_ed, col_ex = st.columns(2)
                with col_ed:
                    if st.button("✏️ Editar", use_container_width=True):
                        st.session_state["tela_ativo"] = "editar"
                        st.session_state["ativo_editar"] = ativo_sel
                        st.rerun()
                with col_ex:
                    if st.button("🗑️ Excluir", use_container_width=True, type="primary"):
                        excluir_ativo(ativo_sel["id"])
                        st.success(f"Ativo '{ativo_sel['nome']}' excluído.")
                        st.rerun()

    # ── NOVO ATIVO ───────────────────────────────────────────
    elif st.session_state["tela_ativo"] == "novo":
        st.subheader("➕ Novo Ativo")
        dados_form = formulario_ativo()
        if dados_form:
            salvar_ativo(dados_form)
            st.session_state["tela_ativo"] = "lista"
            st.session_state["ativo_salvo"] = True
            st.rerun()

    # ── EDITAR ATIVO ─────────────────────────────────────────
    elif st.session_state["tela_ativo"] == "editar":
        ativo = st.session_state.get("ativo_editar")
        st.subheader(f"✏️ Editando: {ativo['nome']}")
        dados_form = formulario_ativo(ativo=ativo)
        if dados_form:
            salvar_ativo(dados_form, ativo_id=ativo["id"])
            st.session_state["tela_ativo"] = "lista"
            st.session_state["ativo_salvo"] = True
            st.rerun()
