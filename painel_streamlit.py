import streamlit as st
import pandas as pd
import sqlite3

# Configuração da página
st.set_page_config(page_title="Painel de Expedição WEG", layout="wide")
st.title("📦 Portal da Expedição (SAD 320)")
st.markdown("Dados lidos **em tempo real** direto do Banco de Dados SQL.")

# 1. Abre a conexão com o seu Banco de Dados
conexao = sqlite3.connect("banco_almoxweb.db", check_same_thread=False)

# =======================================================
# 🚀 A PROTEÇÃO INTELIGENTE (Cria o banco se não existir)
# =======================================================
cursor = conexao.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS dados_expedicao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material TEXT,
        descricao TEXT,
        centro_dep TEXT,
        tipo_estoque TEXT,
        lote TEXT,
        tp TEXT,
        posicao_dep TEXT,
        estoque REAL, 
        data_em TEXT,
        data_necess TEXT,
        nfe TEXT,
        fornecedor TEXT
    )
''')

# Verifica se a tabela está vazia. Se estiver, coloca 3 itens de teste pra você ver na tela!
cursor.execute("SELECT COUNT(*) FROM dados_expedicao")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO dados_expedicao (material, descricao, tipo_estoque, lote, estoque) VALUES ('1000888', 'PLACA ELETRONICA', 'Livre', 'L-111', 10)")
    cursor.execute("INSERT INTO dados_expedicao (material, descricao, tipo_estoque, lote, estoque) VALUES ('1000999', 'CABO DE REDE 5M', 'CQ', 'L-222', 100)")
    cursor.execute("INSERT INTO dados_expedicao (material, descricao, tipo_estoque, lote, estoque) VALUES ('1000777', 'DISJUNTOR 50A', 'Livre', 'L-333', 5)")
    conexao.commit()
# =======================================================

# 2. Criando Filtros na Tela
col1, col2 = st.columns([1, 3])

with col1:
    st.markdown("### 🔍 Filtros")
    filtro_status = st.radio(
        "Status de Qualidade (TipoEstoq):", 
        ["Mostrar Tudo", "Apenas Livre", "Apenas CQ (Bloqueado)"]
    )
    
    pesquisa_mat = st.text_input("Buscar por Material (Ex: 1000):")

# 3. A MÁGICA DO SQL: Montando a pergunta (Query)
query = "SELECT * FROM dados_expedicao WHERE 1=1"

if filtro_status == "Apenas Livre":
    query = query + " AND tipo_estoque = 'Livre'"
elif filtro_status == "Apenas CQ (Bloqueado)":
    query = query + " AND tipo_estoque = 'CQ'"

if pesquisa_mat != "":
    query = query + f" AND material LIKE '%{pesquisa_mat}%'"

# 4. Lendo os dados com Pandas usando a Query
df_tela = pd.read_sql_query(query, conexao)

# 5. Mostrando a Tabela Bonitona no Streamlit
with col2:
    st.metric("Total de Itens Encontrados", len(df_tela))
    
    if df_tela.empty:
        st.warning("Nenhum material encontrado com esses filtros.")
    else:
        st.dataframe(
            df_tela,
            use_container_width=True,
            hide_index=True 
        )

# Fecha a conexão no final
conexao.close()
