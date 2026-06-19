import streamlit as st
import pandas as pd
import sqlite3

# Configuração da página
st.set_page_config(page_title="Painel de Expedição WEG", layout="wide")
st.title("📦 Portal da Expedição (SAD 320)")
st.markdown("Dados lidos **em tempo real** direto do Banco de Dados SQL.")

# 1. Abre a conexão com o seu Banco de Dados
# O comando check_same_thread=False é necessário no Streamlit
conexao = sqlite3.connect("banco_almoxweb.db", check_same_thread=False)

# 2. Criando Filtros na Tela
col1, col2 = st.columns([1, 3])

with col1:
    st.markdown("### 🔍 Filtros")
    # Um botão de rádio para filtrar pelo Status (CQ ou Livre)
    filtro_status = st.radio(
        "Status de Qualidade (TipoEstoq):", 
        ["Mostrar Tudo", "Apenas Livre", "Apenas CQ (Bloqueado)"]
    )
    
    # Campo de pesquisa de material
    pesquisa_mat = st.text_input("Buscar por Material (Ex: 1000):")

# 3. A MÁGICA DO SQL: Montando a pergunta (Query) baseada no filtro do usuário!
# Começamos com a pergunta básica: "Pegue tudo"
query = "SELECT * FROM dados_expedicao WHERE 1=1"

# Se ele clicou em "Livre", a gente adiciona uma regra no SQL
if filtro_status == "Apenas Livre":
    query = query + " AND tipo_estoque = 'Livre'"
# Se clicou em "CQ", adiciona outra regra
elif filtro_status == "Apenas CQ (Bloqueado)":
    query = query + " AND tipo_estoque = 'CQ'"

# Se ele digitou algo na pesquisa (Usamos o LIKE e o curinga % do SQL)
if pesquisa_mat != "":
    query = query + f" AND material LIKE '%{pesquisa_mat}%'"

# 4. Lendo os dados com Pandas usando a nossa Query montada
df_tela = pd.read_sql_query(query, conexao)

# 5. Mostrando a Tabela Bonitona no Streamlit
with col2:
    # Cria uma métrica rápida
    st.metric("Total de Itens Encontrados", len(df_tela))
    
    # Exibe o DataFrame
    if df_tela.empty:
        st.warning("Nenhum material encontrado com esses filtros.")
    else:
        st.dataframe(
            df_tela,
            use_container_width=True,
            hide_index=True # Esconde aquele número da linha do Pandas (deixa só o nosso ID oficial)
        )

# Fecha a conexão no final
conexao.close()