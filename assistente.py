# assistente.py — InventoryLight
# Assistente IA com RAG — contexto dos ativos como base de conhecimento

import streamlit as st
import requests
import json
from datetime import date
from auth import get_supabase, is_admin, get_setor_id


# ── CONFIGURAÇÃO ─────────────────────────────────────────────
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


# ── RAG: CONTEXTO DO BANCO ────────────────────────────────────
def carregar_contexto():
    """Carrega ativos e licenças do banco e monta contexto para a IA."""
    sb = get_supabase()
    hoje = date.today().isoformat()

    # Ativos
    query = (
        sb.table("ativos")
        .select("nome, tipo, status, data_garantia, data_aquisicao, numero_serie, setores(nome)")
        .eq("deletado", False)
        .order("nome")
    )
    if not is_admin():
        query = query.eq("setor_id", get_setor_id())
    ativos = query.execute().data or []

    # Licenças
    lic_res = (
        sb.table("licencas")
        .select("software, chave, validade, ativos(nome, setor_id, setores(nome))")
        .eq("deletado", False)
        .execute()
    )
    licencas = lic_res.data or []
    if not is_admin():
        setor = get_setor_id()
        licencas = [l for l in licencas if l["ativos"]["setor_id"] == setor]

    # Monta contexto textual
    ctx = f"Data de hoje: {hoje}\n\n"

    ctx += f"=== ATIVOS DE TI ({len(ativos)} registros) ===\n"
    for a in ativos:
        setor = a["setores"]["nome"] if a["setores"] else "Sem setor"
        garantia = a["data_garantia"] or "Não informada"
        ctx += (f"- {a['nome']} | Tipo: {a['tipo']} | Status: {a['status']} "
                f"| Setor: {setor} | Garantia: {garantia} | Série: {a['numero_serie'] or '-'}\n")

    ctx += f"\n=== LICENÇAS DE SOFTWARE ({len(licencas)} registros) ===\n"
    for l in licencas:
        ativo = l["ativos"]["nome"] if l["ativos"] else "-"
        setor = l["ativos"]["setores"]["nome"] if l["ativos"] and l["ativos"]["setores"] else "-"
        validade = l["validade"] or "Sem validade"
        ctx += f"- {l['software']} | Ativo: {ativo} | Setor: {setor} | Validade: {validade}\n"

    return ctx


# ── CHAMADA À API GEMINI ──────────────────────────────────────
def perguntar_gemini(pergunta: str, contexto: str, historico: list) -> str:
    api_key = st.secrets["GEMINI_API_KEY"]

    system_prompt = f"""Você é um assistente especializado em gestão de ativos de TI da empresa Auto Viação Dragão do Mar.
Responda sempre em português brasileiro, de forma clara e objetiva.
Base seus dados EXCLUSIVAMENTE nas informações abaixo — não invente dados.
Se a informação não estiver disponível, diga que não encontrou nos registros.

{contexto}"""

    # Monta histórico no formato Gemini
    contents = []
    for msg in historico:
        contents.append({
            "role": msg["role"],
            "parts": [{"text": msg["content"]}]
        })
    contents.append({
        "role": "user",
        "parts": [{"text": pergunta}]
    })

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        }
    }

    try:
        res = requests.post(
            f"{GEMINI_URL}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        data = res.json()

        if res.status_code != 200:
            erro = data.get("error", {}).get("message", "Erro desconhecido")
            return f"⚠️ Erro na API: {erro}"

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except requests.exceptions.Timeout:
        return "⚠️ A IA demorou para responder. Tente novamente."
    except Exception as e:
        return f"⚠️ Erro ao conectar com a IA: {str(e)}"


# ── TELA ─────────────────────────────────────────────────────
def tela_assistente():
    st.title("🤖 Assistente IA")
    st.caption("Faça perguntas sobre os ativos de TI em linguagem natural.")

    # Inicializa histórico
    if "chat_historico" not in st.session_state:
        st.session_state["chat_historico"] = []

    if "contexto_ia" not in st.session_state:
        with st.spinner("Carregando dados dos ativos..."):
            st.session_state["contexto_ia"] = carregar_contexto()

    # Botão para recarregar contexto
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Atualizar dados", use_container_width=True):
            st.session_state["contexto_ia"] = carregar_contexto()
            st.session_state["chat_historico"] = []
            st.success("Dados atualizados!")
            st.rerun()

    st.divider()

    # Sugestões de perguntas
    if not st.session_state["chat_historico"]:
        st.markdown("**💡 Sugestões de perguntas:**")
        sugestoes = [
            "Quais ativos estão em manutenção?",
            "Quais garantias vencem nos próximos 30 dias?",
            "Quantos ativos temos por setor?",
            "Liste todas as licenças de software vencidas",
            "Quais equipamentos pertencem ao setor de TI?",
        ]
        cols = st.columns(2)
        for i, s in enumerate(sugestoes):
            with cols[i % 2]:
                if st.button(s, use_container_width=True, key=f"sug_{i}"):
                    st.session_state["chat_historico"].append(
                        {"role": "user", "content": s}
                    )
                    with st.spinner("Consultando IA..."):
                        resposta = perguntar_gemini(
                            s,
                            st.session_state["contexto_ia"],
                            st.session_state["chat_historico"][:-1]
                        )
                    st.session_state["chat_historico"].append(
                        {"role": "model", "content": resposta}
                    )
                    st.rerun()

    # Histórico do chat
    for msg in st.session_state["chat_historico"]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])

    # Input do usuário
    pergunta = st.chat_input("Digite sua pergunta sobre os ativos...")

    if pergunta:
        st.session_state["chat_historico"].append(
            {"role": "user", "content": pergunta}
        )
        with st.chat_message("user"):
            st.write(pergunta)

        with st.chat_message("assistant"):
            with st.spinner("Consultando IA..."):
                resposta = perguntar_gemini(
                    pergunta,
                    st.session_state["contexto_ia"],
                    st.session_state["chat_historico"][:-1]
                )
            st.write(resposta)

        st.session_state["chat_historico"].append(
            {"role": "model", "content": resposta}
        )
        st.rerun()

    # Botão limpar conversa
    if st.session_state["chat_historico"]:
        st.divider()
        if st.button("🗑️ Limpar conversa", use_container_width=True):
            st.session_state["chat_historico"] = []
            st.rerun()
