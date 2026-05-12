# exportar.py — InventoryLight
# Exportação de dados em CSV

import streamlit as st
import pandas as pd
from datetime import date
from auth import get_supabase, is_admin, get_setor_id


# ── DADOS ────────────────────────────────────────────────────
def carregar_ativos():
    sb = get_supabase()
    query = (
        sb.table("ativos")
        .select("nome, tipo, numero_serie, status, data_aquisicao, data_garantia, observacoes, setores(nome)")
        .eq("deletado", False)
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
        .select("software, chave, validade, ativos(nome, setor_id, setores(nome))")
        .eq("deletado", False)
        .order("software")
        .execute()
    )
    dados = res.data or []
    if not is_admin():
        setor = get_setor_id()
        dados = [l for l in dados if l["ativos"]["setor_id"] == setor]
    return dados


def carregar_historico():
    sb = get_supabase()
    res = (
        sb.table("historico")
        .select("campo, valor_antes, valor_depois, alterado_em, ativos(nome)")
        .order("alterado_em", desc=True)
        .execute()
    )
    return res.data or []


# ── CONVERSORES ──────────────────────────────────────────────
def ativos_para_df(ativos):
    return pd.DataFrame([{
        "Nome":          a["nome"],
        "Tipo":          a["tipo"],
        "Setor":         a["setores"]["nome"] if a["setores"] else "-",
        "Status":        a["status"],
        "Número de Série": a["numero_serie"] or "-",
        "Data Aquisição": a["data_aquisicao"] or "-",
        "Garantia":      a["data_garantia"] or "-",
        "Observações":   a["observacoes"] or "-",
    } for a in ativos])


def licencas_para_df(licencas):
    hoje = date.today()
    return pd.DataFrame([{
        "Software":  l["software"],
        "Ativo":     l["ativos"]["nome"] if l["ativos"] else "-",
        "Setor":     l["ativos"]["setores"]["nome"] if l["ativos"]["setores"] else "-",
        "Chave":     l["chave"] or "-",
        "Validade":  l["validade"] or "-",
        "Situação":  (
            "VENCIDA" if l["validade"] and date.fromisoformat(l["validade"]) < hoje
            else f"{(date.fromisoformat(l['validade']) - hoje).days} dias"
            if l["validade"] else "Sem validade"
        ),
    } for l in licencas])


def historico_para_df(historico):
    return pd.DataFrame([{
        "Ativo":        h["ativos"]["nome"] if h["ativos"] else "-",
        "Campo":        h["campo"],
        "Valor Antes":  h["valor_antes"] or "-",
        "Valor Depois": h["valor_depois"] or "-",
        "Alterado em":  h["alterado_em"],
        "Usuário":      "-",
    } for h in historico])


# ── TELA ─────────────────────────────────────────────────────
def tela_exportar():
    st.title("📥 Exportação de Dados")
    st.caption("Os dados exportados refletem apenas o que você tem permissão de visualizar.")

    st.divider()

    # ── ATIVOS ───────────────────────────────────────────────
    st.subheader("🖥️ Ativos")
    ativos = carregar_ativos()
    if ativos:
        df_ativos = ativos_para_df(ativos)
        st.dataframe(df_ativos, use_container_width=True, hide_index=True)
        st.download_button(
            label=f"⬇️ Exportar Ativos ({len(ativos)} registros)",
            data=df_ativos.to_csv(index=False, sep=";", encoding="utf-8-sig"),
            file_name=f"ativos_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("Nenhum ativo disponível para exportar.")

    st.divider()

    # ── LICENÇAS ─────────────────────────────────────────────
    st.subheader("📄 Licenças")
    licencas = carregar_licencas()
    if licencas:
        df_licencas = licencas_para_df(licencas)
        st.dataframe(df_licencas, use_container_width=True, hide_index=True)
        st.download_button(
            label=f"⬇️ Exportar Licenças ({len(licencas)} registros)",
            data=df_licencas.to_csv(index=False, sep=";", encoding="utf-8-sig"),
            file_name=f"licencas_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("Nenhuma licença disponível para exportar.")

    # ── HISTÓRICO (somente admin) ─────────────────────────────
    if is_admin():
        st.divider()
        st.subheader("📋 Histórico de Alterações")
        historico = carregar_historico()
        if historico:
            df_historico = historico_para_df(historico)
            st.dataframe(df_historico, use_container_width=True, hide_index=True)
            st.download_button(
                label=f"⬇️ Exportar Histórico ({len(historico)} registros)",
                data=df_historico.to_csv(index=False, sep=";", encoding="utf-8-sig"),
                file_name=f"historico_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("Nenhum histórico disponível.")
