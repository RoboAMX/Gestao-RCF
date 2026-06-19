import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time

# ==========================================
# 🤖 IMPORTAÇÃO INTELIGENTE DO ROBÔ
# ==========================================
try:
    import agente_almoxweb 
    robo_disponivel = True
except ModuleNotFoundError:
    robo_disponivel = False

st.set_page_config(page_title="Painel de Expedição WEG", layout="wide")

# ==========================================
# 1. CONEXÃO COM O POSTGRESQL (SUPABASE)
# ==========================================
# Puxa a senha do cofre invisível da nuvem ou da pasta .streamlit local
DATABASE_URL = st.secrets["banco_dados"]["url"]

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS expedicao_completa (
            id SERIAL PRIMARY KEY,
            item TEXT,
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
            fornecedor TEXT,
            status_envio TEXT DEFAULT 'Pendente' 
        )
    '''))

    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            senha TEXT,
            perfil TEXT
        )
    '''))
    conn.commit()

    qtd_usuarios = conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar()
    if qtd_usuarios == 0:
        conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('roberto', 'weg2026', 'Admin')"))
        conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('expedicao', 'senha123', 'Operador')"))
        conn.commit()


# ==========================================
# 2. SISTEMA DE LOGIN 
# ==========================================
if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["usuario_atual"] = ""
    st.session_state["perfil_atual"] = ""

if not st.session_state["logado"]:
    st.title("🔒 Acesso Restrito - Almoxarifado")
    
    col_vazia1, col_login, col_vazia2 = st.columns([1, 2, 1])
    with col_login:
        with st.form("form_login"):
            st.markdown("### Digite suas credenciais:")
            usuario_input = st.text_input("Usuário").lower().strip()
            senha_input = st.text_input("Senha", type="password")
            btn_entrar = st.form_submit_button("Entrar", type="primary")
            
            if btn_entrar:
                with engine.connect() as conn:
                    resultado = conn.execute(text("SELECT senha, perfil FROM usuarios WHERE usuario = :u"), {"u": usuario_input}).fetchone()
                
                if resultado and resultado[0] == senha_input:
                    st.session_state["logado"] = True
                    st.session_state["usuario_atual"] = usuario_input
                    st.session_state["perfil_atual"] = resultado[1]
                    st.success("Acesso Liberado!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos! Tente novamente.")
    st.stop()


# ==========================================
# 3. APLICATIVO PRINCIPAL
# ==========================================
st.title("📦 Portal da Expedição (SAD 320)")

st.sidebar.markdown(f"👨‍💻 Logado como: **{st.session_state['usuario_atual'].upper()}**")
st.sidebar.markdown(f"🛡️ Nível: **{st.session_state['perfil_atual']}**")

if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state["logado"] = False
    st.session_state["usuario_atual"] = ""
    st.session_state["perfil_atual"] = ""
    st.rerun()

st.sidebar.divider()

# ==========================================
# 🤖 BOTÃO DO ROBÔ (ADMIN & LOCAL)
# ==========================================
if st.session_state["perfil_atual"] == "Admin":
    st.sidebar.markdown("### 🤖 Robô de Extração")
    
    # Se o robô não estiver instalado (Nuvem), mostra aviso. Se estiver (PC da WEG), mostra o botão!
    if not robo_disponivel:
        st.sidebar.info("🌐 Modo Nuvem: O robô de extração opera apenas no servidor local da WEG.")
    else:
        if st.sidebar.button("⚡ Extrair AlmoxWeb e Salvar no SQL", type="primary"):
            with st.spinner("O Robô está extraindo os dados da WEG... Aguarde!"):
                dados_novos = agente_almoxweb.extrair_dados_almoxweb()
                
                if dados_novos and len(dados_novos) > 0:
                    df_robo = pd.DataFrame(dados_novos)
                    df_para_banco = pd.DataFrame()
                    
                    df_para_banco['item'] = df_robo.get('Item', '')
                    df_para_banco['material'] = df_robo.get('Material', '')
                    df_para_banco['descricao'] = df_robo.get('Descricao', df_robo.get('Descrição', ''))
                    df_para_banco['centro_dep'] = df_robo.get('Centro_Dep', df_robo.get('Centro | Dep.', ''))
                    df_para_banco['tipo_estoque'] = df_robo.get('TipoEstoq.', df_robo.get('TipoEstoq', 'Livre'))
                    df_para_banco['lote'] = df_robo.get('Lote', '')
                    df_para_banco['tp'] = df_robo.get('Tp.', df_robo.get('Tp', ''))
                    df_para_banco['posicao_dep'] = df_robo.get('Posicao', df_robo.get('Posição Dep.', ''))
                    
                    df_para_banco['estoque'] = df_robo.get('Quantidade', df_robo.get('Estoque', 0))
                    df_para_banco['estoque'] = df_para_banco['estoque'].astype(str).str.replace(r'[^\d.,]', '', regex=True)
                    df_para_banco['estoque'] = df_para_banco['estoque'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    df_para_banco['estoque'] = pd.to_numeric(df_para_banco['estoque'], errors='coerce').fillna(0.0)

                    df_para_banco['data_em'] = df_robo.get('Data_Entrada', df_robo.get('Data EM', ''))
                    df_para_banco['data_necess'] = df_robo.get('Data_Necess', df_robo.get('Data Necess.', ''))
                    df_para_banco['nfe'] = df_robo.get('NF', df_robo.get('NFE', ''))
                    df_para_banco['fornecedor'] = df_robo.get('Fornecedor', '')
                    
                    df_para_banco.to_sql(name='expedicao_completa', con=engine, if_exists='append', index=False)
                    
                    st.sidebar.success(f"✅ Sucesso! {len(df_para_banco)} itens salvos no Banco!")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.sidebar.error("❌ Falha ao extrair dados ou tabela vazia.")


# ==========================================
# CRIANDO AS ABAS DO SISTEMA
# ==========================================
aba_pendentes, aba_historico = st.tabs(["📋 Pendentes de Despacho", "💾 Histórico (Já Despachados)"])

with aba_pendentes:
    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown("### 🔍 Filtros")
        filtro_status = st.radio("Status de Qualidade:", ["Mostrar Tudo", "Apenas Livre", "Apenas CQ"])
        
    query = "SELECT * FROM expedicao_completa WHERE status_envio = 'Pendente'"

    if filtro_status == "Apenas Livre": query += " AND tipo_estoque = 'Livre'"
    elif filtro_status == "Apenas CQ": query += " AND tipo_estoque = 'CQ'"

    df_tela = pd.read_sql_query(query, engine)

    with col2:
        if df_tela.empty:
            st.success("🎉 Tudo limpo! Nenhum material pendente na doca.")
        else:
            df_tela.insert(0, "Selecionar", False)
            colunas_bloqueadas = [col for col in df_tela.columns if col != "Selecionar"]
            
            df_editado = st.data_editor(
                df_tela, hide_index=True, use_container_width=True,
                disabled=colunas_bloqueadas 
            )
            
            if st.button("🚀 Despachar Selecionados", type="primary"):
                selecionados = df_editado[df_editado["Selecionar"] == True]
                if selecionados.empty:
                    st.error("Selecione pelo menos um item!")
                else:
                    with engine.connect() as conn:
                        for id_peca in selecionados["id"]:
                            conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Despachado' WHERE id = :id_peca"), {"id_peca": int(id_peca)})
                        conn.commit()
                        
                    st.success("✅ Despachado no Banco de Dados! Atualizando tela...")
                    time.sleep(1)
                    st.rerun()

with aba_historico:
    st.markdown("### 📦 Materiais já Despachados")
    
    query_hist = "SELECT * FROM expedicao_completa WHERE status_envio = 'Despachado'"
    df_hist = pd.read_sql_query(query_hist, engine)
    
    if df_hist.empty:
        st.info("Nenhum material foi despachado ainda.")
    else:
        st.dataframe(df_hist, hide_index=True, use_container_width=True)
        
        st.markdown("---")
        if st.session_state["perfil_atual"] == "Admin":
            if st.button("🔄 Desfazer todos os envios (Resetar Teste)"):
                with engine.connect() as conn:
                    conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Pendente'"))
                    conn.commit()
                st.rerun()
