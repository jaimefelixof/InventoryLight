# licencas.py — InventoryLight
import streamlit as st
import pandas as pd
from datetime import date
from auth import get_supabase, is_admin, get_setor_id


# ── DADOS ────────────────────────────────────────────────────
def carregar_ativos_opcoes():
    sb = get_supabase()
    query = (
        sb.table("ativos")
        .select("id, nome, setor_id")
        .eq("deletado", False)
        .eq("tipo", "software")
        .order("nome")
    )
    if not is_admin():
        query = query.eq("setor_id", get_setor_id())
    res = query.execute()
    return res.data or []


def carregar_licencas():
    sb = get_supabase()
    res = (
        sb.table("licencas")
        .select("id, software, chave, validade, deletado, ativo_id, ativos(nome, setor_id, setores(nome))")
        .eq("deletado", False)
        .order("software")
        .execute()
    )
    dados = res.data or []
    if not is_admin():
        setor = get_setor_id()
        dados = [l for l in dados if l["ativos"]["setor_id"] == setor]
    return dados


def salvar_licenca(dados: dict, licenca_id: str = None):
    sb = get_supabase()
    if licenca_id:
        sb.table("licencas").update(dados).eq("id", licenca_id).execute()
    else:
        sb.table("licencas").insert(dados).execute()


def excluir_licenca(licenca_id: str):
    sb = get_supabase()
    sb.table("licencas").update({"deletado": True}).eq("id", licenca_id).execute()


# ── FORMULÁRIO ───────────────────────────────────────────────
def formulario_licenca(licenca: dict = None):
    ativos = carregar_ativos_opcoes()

    if not ativos:
        st.warning("Nenhum ativo do tipo 'software' cadastrado. Cadastre um ativo primeiro.")
        return None

    mapa_ativos    = {a["nome"]: a["id"] for a in ativos}
    ativo_atual    = licenca["ativos"]["nome"] if licenca else list(mapa_ativos.keys())[0]
    software_atual = licenca["software"]       if licenca else ""
    chave_atual    = licenca["chave"]          if licenca else ""
    validade_atual = date.fromisoformat(licenca["validade"]) if licenca and licenca["validade"] else None

    chave_form = "form_licenca_edicao" if licenca else "form_licenca_novo"

    with st.form(chave_form):
        ativo_sel  = st.selectbox("Ativo vinculado *", list(mapa_ativos.keys()),
                                  index=list(mapa_ativos.keys()).index(ativo_atual)
                                  if ativo_atual in mapa_ativos else 0)
        software   = st.text_input("Nome do Software *", value=software_atual)
        chave_lic  = st.text_input("Chave de Licença", value=chave_atual or "")
        validade   = st.date_input("Validade da Licença", value=validade_atual)

        col_s, col_c = st.columns(2)
        salvar   = col_s.form_submit_button("💾 Salvar",   use_container_width=True)
        cancelar = col_c.form_submit_button("✖ Cancelar", use_container_width=True)

    if cancelar:
        st.session_state["tela_licenca"] = "lista"
        st.rerun()

    if salvar:
        if not software:
            st.warning("Nome do software é obrigatório.")
            return None
        return {
            "ativo_id": mapa_ativos[ativo_sel],
            "software": software,
            "chave":    chave_lic or None,
            "validade": validade.isoformat() if validade else None,
        }
    return None


# ── TELA ─────────────────────────────────────────────────────
def tela_licencas():
    st.title("📄 Licenças de Software")

    if "tela_licenca" not in st.session_state:
        st.session_state["tela_licenca"] = "lista"

    # ── LISTAGEM ─────────────────────────────────────────────
    if st.session_state["tela_licenca"] == "lista":

        if st.session_state.pop("licenca_salva", False):
            st.success("✅ Licença salva com sucesso!")

        if is_admin():
            if st.button("➕ Nova Licença", type="primary"):
                st.session_state["tela_licenca"] = "novo"
                st.session_state["licenca_editar"] = None
                st.rerun()

        licencas = carregar_licencas()

        if not licencas:
            st.info("Nenhuma licença cadastrada.")
            return

        hoje = date.today()

        df = pd.DataFrame([{
            "Software": l["software"],
            "Ativo":    l["ativos"]["nome"] if l["ativos"] else "-",
            "Setor":    l["ativos"]["setores"]["nome"] if l["ativos"]["setores"] else "-",
            "Chave":    l["chave"] or "-",
            "Validade": l["validade"] or "-",
            "Situação": (
                "VENCIDA" if l["validade"] and date.fromisoformat(l["validade"]) < hoje
                else f"{(date.fromisoformat(l['validade']) - hoje).days} dias"
                if l["validade"] else "Sem validade"
            ),
        } for l in licencas])

        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(licencas)} licença(s) cadastrada(s)")

        if is_admin() and licencas:
            st.divider()
            nomes = [l["software"] for l in licencas]
            selecionado = st.selectbox("Selecione para editar ou excluir", nomes)
            lic_sel = next((l for l in licencas if l["software"] == selecionado), None)

            if lic_sel:
                col_ed, col_ex = st.columns(2)
                with col_ed:
                    if st.button("✏️ Editar", use_container_width=True):
                        st.session_state["tela_licenca"] = "editar"
                        st.session_state["licenca_editar"] = lic_sel
                        st.rerun()
                with col_ex:
                    if st.button("🗑️ Excluir", use_container_width=True, type="primary"):
                        excluir_licenca(lic_sel["id"])
                        st.success(f"Licença '{lic_sel['software']}' excluída.")
                        st.rerun()

    # ── NOVA LICENÇA ─────────────────────────────────────────
    elif st.session_state["tela_licenca"] == "novo":
        st.subheader("➕ Nova Licença")
        dados_form = formulario_licenca()
        if dados_form:
            salvar_licenca(dados_form)
            st.session_state["tela_licenca"] = "lista"
            st.session_state["licenca_salva"] = True
            st.rerun()

    # ── EDITAR LICENÇA ───────────────────────────────────────
    elif st.session_state["tela_licenca"] == "editar":
        lic = st.session_state.get("licenca_editar")
        st.subheader(f"✏️ Editando: {lic['software']}")
        dados_form = formulario_licenca(licenca=lic)
        if dados_form:
            salvar_licenca(dados_form, licenca_id=lic["id"])
            st.session_state["tela_licenca"] = "lista"
            st.session_state["licenca_salva"] = True
            st.rerun()
