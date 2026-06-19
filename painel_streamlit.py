import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Painel de Expedição WEG", layout="wide")
st.title("📦 Portal da Expedição (SAD 320)")

conexao = sqlite3.connect("banco_almoxweb.db", check_same_thread=False)
cursor = conexao.cursor()

# Cria a tabela e insere dados de teste (A nossa proteção)
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
# Adicionei a coluna "status_envio" para a gente poder dar baixa!

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
        # 1. Adicionamos uma coluna Falsa de Checkbox chamada "Selecionar"
        df_tela.insert(0, "Selecionar", False)
        
        # 2. Mostramos a tabela INTERATIVA (data_editor em vez de dataframe)
        df_editado = st.data_editor(
            df_tela,
            hide_index=True,
            use_container_width=True,
            disabled=["id", "material", "descricao", "tipo_estoque", "lote", "estoque", "status_envio"] # Bloqueia edição dos dados reais
        )
        
        # 3. O Botão de Ação!
        if st.button("🚀 Despachar Selecionados", type="primary"):
            # Pega só as linhas onde a caixinha "Selecionar" foi marcada
            selecionados = df_editado[df_editado["Selecionar"] == True]
            
            if selecionados.empty:
                st.error("Selecione pelo menos um item marcando a caixinha!")
            else:
                # Faz um UPDATE no Banco de Dados para cada ID selecionado
                for id_peca in selecionados["id"]:
                    cursor.execute("UPDATE dados_expedicao SET status_envio = 'Despachado' WHERE id = ?", (id_peca,))
                
                conexao.commit()
                st.success("✅ Materiais despachados com sucesso! Atualizando tela...")
                time.sleep(1) # Espera 1 segundo e recarrega a página
                st.rerun()

conexao.close()
