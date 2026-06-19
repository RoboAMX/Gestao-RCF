import streamlit as st
import pandas as pd
import sqlite3
import time  # Faltava isso aqui!

st.set_page_config(page_title="Painel de Expedição WEG", layout="wide")
st.title("📦 Portal da Expedição (SAD 320)")

# Mudamos o nome do arquivo para forçar o servidor a criar um banco virgem!
conexao = sqlite3.connect("banco_expedicao_v2.db", check_same_thread=False)
cursor = conexao.cursor()

# Cria a tabela com a coluna nova
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

# Insere os dados de teste se estiver vazio
cursor.execute("SELECT COUNT(*) FROM dados_expedicao")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO dados_expedicao (material, descricao, tipo_estoque, lote, estoque) VALUES ('1000888', 'PLACA ELETRONICA', 'Livre', 'L-111', 10)")
    cursor.execute("INSERT INTO dados_expedicao (material, descricao, tipo_estoque, lote, estoque) VALUES ('1000999', 'CABO DE REDE 5M', 'CQ', 'L-222', 100)")
    cursor.execute("INSERT INTO dados_expedicao (material, descricao, tipo_estoque, lote, estoque) VALUES ('1000777', 'DISJUNTOR 50A', 'Livre', 'L-333', 5)")
    conexao.commit()

# --- FILTROS ---
col1, col2 = st.columns([1, 3])

with col1:
    st.markdown("### 🔍 Filtros")
    filtro_status = st.radio("Status de Qualidade:", ["Mostrar Tudo", "Apenas Livre", "Apenas CQ"])
    
# --- LENDO O BANCO DE DADOS ---
query = "SELECT id, material, descricao, tipo_estoque, lote, estoque, status_envio FROM dados_expedicao WHERE status_envio = 'Pendente'"

if filtro_status == "Apenas Livre":
    query += " AND tipo_estoque = 'Livre'"
elif filtro_status == "Apenas CQ":
    query += " AND tipo_estoque = 'CQ'"

df_tela = pd.read_sql_query(query, conexao)

with col2:
    st.markdown("### 📋 Materiais Pendentes de Despacho")
    
    if df_tela.empty:
        st.success("Tudo limpo! Nenhum material pendente.")
    else:
        # Coluna de Checkbox
        df_tela.insert(0, "Selecionar", False)
        
        # Tabela Interativa
        df_editado = st.data_editor(
            df_tela,
            hide_index=True,
            use_container_width=True,
            disabled=["id", "material", "descricao", "tipo_estoque", "lote", "estoque", "status_envio"] 
        )
        
        # Botão de Ação
        if st.button("🚀 Despachar Selecionados", type="primary"):
            selecionados = df_editado[df_editado["Selecionar"] == True]
            
            if selecionados.empty:
                st.error("Selecione pelo menos um item marcando a caixinha!")
            else:
                for id_peca in selecionados["id"]:
                    cursor.execute("UPDATE dados_expedicao SET status_envio = 'Despachado' WHERE id = ?", (int(id_peca),))
                
                conexao.commit()
                st.success("✅ Materiais despachados com sucesso! Atualizando tela...")
                time.sleep(1.5)
                st.rerun()

conexao.close()
