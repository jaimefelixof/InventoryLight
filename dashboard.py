# dashboard.py — InventoryLight
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from auth import get_supabase, is_admin, get_setor_id


# ── DADOS ────────────────────────────────────────────────────
def carregar_dados():
    sb = get_supabase()
    query = (
        sb.table("ativos")
        .select("id, nome, tipo, status, data_garantia, setor_id, setores(nome)")
        .eq("deletado", False)
    )
    if not is_admin():
        query = query.eq("setor_id", get_setor_id())
    res = query.execute()
    return res.data or []


# ── TELA ─────────────────────────────────────────────────────
def tela_dashboard():
    st.title("📊 Dashboard")

    dados = carregar_dados()

    if not dados:
        st.info("Nenhum ativo cadastrado ainda.")
        return

    df = pd.DataFrame([{
        "nome":          a["nome"],
        "tipo":          a["tipo"],
        "status":        a["status"],
        "setor":         a["setores"]["nome"] if a["setores"] else "Sem Setor",
        "data_garantia": a["data_garantia"],
    } for a in dados])

    hoje = date.today()

    def dias_garantia(val):
        if not val or not isinstance(val, str):
            return None
        try:
            return (date.fromisoformat(val) - hoje).days
        except Exception:
            return None

    df["dias_garantia"] = df["data_garantia"].apply(dias_garantia)

    # ── INDICADORES ──────────────────────────────────────────
    total        = len(df)
    ativos_count = len(df[df["status"] == "ativo"])
    manut_count  = len(df[df["status"] == "em_manutencao"])
    venc_30      = len(df[df["dias_garantia"].apply(lambda x: x is not None and 0 <= x <= 30)])
    venc_90      = len(df[df["dias_garantia"].apply(lambda x: x is not None and 0 <= x <= 90)])

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total de Ativos",      total)
    col2.metric("Ativos",               ativos_count)
    col3.metric("Em Manutenção",        manut_count)
    col4.metric("⚠️ Venc. 30 dias",    venc_30,
                delta=None if venc_30 == 0 else f"-{venc_30}", delta_color="inverse")
    col5.metric("⚠️ Venc. 90 dias",    venc_90,
                delta=None if venc_90 == 0 else f"-{venc_90}", delta_color="inverse")

    st.divider()

    # ── LINHA 1: Status + Tipo ────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Ativos por Status")
        status_count = df["status"].value_counts().reset_index()
        status_count.columns = ["Status", "Quantidade"]
        cores = {"ativo": "#2ecc71", "em_manutencao": "#f39c12", "desativado": "#e74c3c"}
        fig1 = px.pie(
            status_count, names="Status", values="Quantidade",
            color="Status", color_discrete_map=cores, hole=0.4
        )
        fig1.update_layout(
            height=250,
            margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            legend_title=None,
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        st.subheader("Ativos por Tipo")
        tipo_count = df["tipo"].value_counts().reset_index()
        tipo_count.columns = ["Tipo", "Quantidade"]
        fig2 = px.bar(
            tipo_count, x="Tipo", y="Quantidade",
            color="Tipo", text="Quantidade",
            color_discrete_sequence=["#184287", "#FCD523", "#61C3D9"]
        )
        fig2.update_layout(
            height=250,
            margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False,
        )
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── LINHA 2: Setor + Garantias ────────────────────────────
    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("Ativos por Setor")
        setor_count = df["setor"].value_counts().reset_index()
        setor_count.columns = ["Setor", "Quantidade"]
        fig3 = px.bar(
            setor_count, x="Quantidade", y="Setor",
            orientation="h", text="Quantidade",
            color_discrete_sequence=["#184287"]
        )
        fig3.update_layout(
            height=250,
            margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False,
            yaxis=dict(autorange="reversed"),
        )
        fig3.update_traces(textposition="outside")
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        st.subheader("Garantias a Vencer (90 dias)")
        df_venc = df[df["dias_garantia"].apply(
            lambda x: x is not None and 0 <= x <= 90
        )].copy()

        if df_venc.empty:
            st.success("Nenhuma garantia vencendo nos próximos 90 dias.")
        else:
            df_venc = df_venc.sort_values("dias_garantia")
            fig4 = px.bar(
                df_venc, x="nome", y="dias_garantia",
                labels={"nome": "Ativo", "dias_garantia": "Dias restantes"},
                color="dias_garantia",
                color_continuous_scale=["#e74c3c", "#f39c12", "#2ecc71"],
                text="dias_garantia"
            )
            fig4.update_layout(
                height=250,
                margin=dict(t=10, b=10, l=10, r=10),
                showlegend=False,
                coloraxis_showscale=False,
            )
            fig4.update_traces(textposition="outside")
            st.plotly_chart(fig4, use_container_width=True)
