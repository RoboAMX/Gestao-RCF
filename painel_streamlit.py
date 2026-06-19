import streamlit as st
import pandas as pd
import sqlite3
import time

st.set_page_config(page_title="Painel de Expedição WEG", layout="wide")
st.title("📦 Portal da Expedição (SAD 320)")

conexao = sqlite3.connect("banco_expedicao_v2.db", check_same_thread=False)
cursor = conexao.cursor()

# 1. PROTEÇÃO E CRIAÇÃO DO BANCO
cursor.execute('''
    CREATE TABLE IF NOT EXISTS dados_expedicao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material TEXT,
        descricao TEXT,
        tipo_estoque TEXT,
        lote TEXT,
        estoque REAL,
        status_envio TEXT DEFAULT 'Pendente' 
    )
''')

cursor.execute("SELECT COUNT(*) FROM dados_expedicao")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO dados_expedicao (material, descricao, tipo_estoque, lote, estoque) VALUES ('1000888', 'PLACA ELETRONICA', 'Livre', 'L-111', 10)")
    cursor.execute("INSERT INTO dados_expedicao (material, descricao, tipo_estoque, lote, estoque) VALUES ('1000999', 'CABO DE REDE 5M', 'CQ', 'L-222', 100)")
    cursor.execute("INSERT INTO dados_expedicao (material, descricao, tipo_estoque, lote, estoque) VALUES ('1000777', 'DISJUNTOR 50A', 'Livre', 'L-333', 5)")
    conexao.commit()

# ==========================================
# CRIANDO AS ABAS DO SISTEMA
# ==========================================
aba_pendentes, aba_historico = st.tabs(["📋 Pendentes de Despacho", "💾 Histórico (Já Despachados)"])

# ------------------------------------------
# TELA 1: PENDENTES
# ------------------------------------------
with aba_pendentes:
    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown("### 🔍 Filtros")
        filtro_status = st.radio("Status de Qualidade:", ["Mostrar Tudo", "Apenas Livre", "Apenas CQ"])
        
    query = "SELECT id, material, descricao, tipo_estoque, lote, estoque, status_envio FROM dados_expedicao WHERE status_envio = 'Pendente'"

    if filtro_status == "Apenas Livre":
        query += " AND tipo_estoque = 'Livre'"
    elif filtro_status == "Apenas CQ":
        query += " AND tipo_estoque = 'CQ'"

    df_tela = pd.read_sql_query(query, conexao)

    with col2:
        if df_tela.empty:
            st.success("🎉 Tudo limpo! Nenhum material pendente na doca.")
        else:
            df_tela.insert(0, "Selecionar", False)
            
            df_editado = st.data_editor(
                df_tela,
                hide_index=True,
                use_container_width=True,
                disabled=["id", "material", "descricao", "tipo_estoque", "lote", "estoque", "status_envio"] 
            )
            
            if st.button("🚀 Despachar Selecionados", type="primary"):
                selecionados = df_editado[df_editado["Selecionar"] == True]
                
                if selecionados.empty:
                    st.error("Selecione pelo menos um item marcando a caixinha!")
                else:
                    for id_peca in selecionados["id"]:
                        cursor.execute("UPDATE dados_expedicao SET status_envio = 'Despachado' WHERE id = ?", (int(id_peca),))
                    
                    conexao.commit()
                    st.success("✅ Materiais despachados com sucesso! Atualizando tela...")
                    time.sleep(1)
                    st.rerun()

# ------------------------------------------
# TELA 2: HISTÓRICO
# ------------------------------------------
with aba_historico:
    st.markdown("### 📦 Materiais já Despachados")
    
    # Aqui a mágica inverte: buscamos SÓ o que foi Despachado!
    query_hist = "SELECT id, material, descricao, tipo_estoque, lote, estoque, status_envio FROM dados_expedicao WHERE status_envio = 'Despachado'"
    df_hist = pd.read_sql_query(query_hist, conexao)
    
    if df_hist.empty:
        st.info("Nenhum material foi despachado ainda.")
    else:
        st.dataframe(df_hist, hide_index=True, use_container_width=True)
        
        # Um botão bônus para você testar (Desfaz o envio de tudo)
        st.markdown("---")
        if st.button("🔄 Desfazer todos os envios (Resetar Teste)"):
            cursor.execute("UPDATE dados_expedicao SET status_envio = 'Pendente'")
            conexao.commit()
            st.rerun()

conexao.close()
