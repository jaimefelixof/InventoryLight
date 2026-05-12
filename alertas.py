# alertas.py — InventoryLight
# Alertas de vencimento de garantia

import streamlit as st
import pandas as pd
from datetime import date
from auth import get_supabase, is_admin, get_setor_id


# ── DADOS ────────────────────────────────────────────────────
def carregar_ativos_garantia():
    sb = get_supabase()
    query = (
        sb.table("ativos")
        .select("id, nome, tipo, status, data_garantia, setor_id, setores(nome)")
        .eq("deletado", False)
        .not_.is_("data_garantia", "null")
    )
    if not is_admin():
        query = query.eq("setor_id", get_setor_id())

    res = query.execute()
    return res.data or []


# ── TELA ─────────────────────────────────────────────────────
def tela_alertas():
    st.title("⚠️ Alertas de Garantia")

    dados = carregar_ativos_garantia()

    if not dados:
        st.info("Nenhum ativo com garantia cadastrada.")
        return

    hoje = date.today()

    df = pd.DataFrame([{
        "Nome":      a["nome"],
        "Tipo":      a["tipo"],
        "Setor":     a["setores"]["nome"] if a["setores"] else "-",
        "Status":    a["status"],
        "Garantia":  a["data_garantia"],
        "Dias":      (date.fromisoformat(a["data_garantia"]) - hoje).days,
    } for a in dados])

    df = df.sort_values("Dias")

    # ── FILTRO POR PRAZO ─────────────────────────────────────
    prazo = st.radio(
        "Exibir garantias:",
        ["Vencidas", "Vencem em 30 dias", "Vencem em 90 dias", "Todas"],
        horizontal=True,
    )

    if prazo == "Vencidas":
        filtrado = df[df["Dias"] < 0]
    elif prazo == "Vencem em 30 dias":
        filtrado = df[(df["Dias"] >= 0) & (df["Dias"] <= 30)]
    elif prazo == "Vencem em 90 dias":
        filtrado = df[(df["Dias"] >= 0) & (df["Dias"] <= 90)]
    else:
        filtrado = df

    st.divider()

    # ── TOTALIZADORES ────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("🔴 Vencidas",          len(df[df["Dias"] < 0]))
    col2.metric("🟡 Vencem em 30 dias", len(df[(df["Dias"] >= 0) & (df["Dias"] <= 30)]))
    col3.metric("🟠 Vencem em 90 dias", len(df[(df["Dias"] >= 0) & (df["Dias"] <= 90)]))

    st.divider()

    if filtrado.empty:
        st.success("Nenhum ativo nesta categoria.")
        return

    # ── TABELA COM CORES ─────────────────────────────────────
    def colorir_linha(row):
        if row["Dias"] < 0:
            cor = "background-color: #4a0000; color: #ff6b6b"
        elif row["Dias"] <= 30:
            cor = "background-color: #4a3500; color: #ffd93d"
        elif row["Dias"] <= 90:
            cor = "background-color: #3a2800; color: #ffa94d"
        else:
            cor = ""
        return [cor] * len(row)

    # Cria coluna de exibição separada
    df_exibir = filtrado.copy()
    df_exibir["Situação"] = df_exibir["Dias"].apply(
        lambda x: f"VENCIDA há {abs(x)} dia(s)" if x < 0 else f"{x} dia(s)"
    )
    df_exibir = df_exibir.drop(columns=["Dias"])

    def colorir_linha(row):
        dias = filtrado.loc[row.name, "Dias"]
        if dias < 0:
            cor = "background-color: #4a0000; color: #ff6b6b"
        elif dias <= 30:
            cor = "background-color: #4a3500; color: #ffd93d"
        elif dias <= 90:
            cor = "background-color: #3a2800; color: #ffa94d"
        else:
            cor = ""
        return [cor] * len(row)

    st.dataframe(
        df_exibir.style.apply(colorir_linha, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(f"{len(filtrado)} ativo(s) encontrado(s) nesta categoria.")