import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time

try:
    import agente_almoxweb 
    robo_disponivel = True
except ModuleNotFoundError:
    robo_disponivel = False

st.set_page_config(page_title="Painel de Expedição WEG", layout="wide")

# ==========================================
# 1. CONEXÃO COM O POSTGRESQL (SUPABASE) E BANCO
# ==========================================
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
# 2. SISTEMA DE LOGIN E CARRINHO (MEMÓRIA)
# ==========================================
if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["usuario_atual"] = ""
    st.session_state["perfil_atual"] = ""

# Criando a memória do "Carrinho de Expedição"
if "carrinho_expedicao" not in st.session_state:
    st.session_state["carrinho_expedicao"] = []

if not st.session_state["logado"]:
    st.title("🔒 Acesso Restrito - Almoxarifado")
    col_vazia1, col_login, col_vazia2 = st.columns([1, 2, 1])
    with col_login:
        with st.form("form_login"):
            st.markdown("### Digite suas credenciais:")
            usuario_input = st.text_input("Usuário").lower().strip()
            senha_input = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary"):
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
                    st.error("❌ Usuário ou senha incorretos!")
    st.stop()

# ==========================================
# 3. MENU LATERAL
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/WEG_logo.svg/1200px-WEG_logo.svg.png", width=120)
st.sidebar.markdown(f"👨‍💻 Olá, **{st.session_state['usuario_atual'].upper()}**")
st.sidebar.markdown(f"🛡️ Nível: **{st.session_state['perfil_atual']}**")

if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    st.session_state["logado"] = False
    st.session_state["usuario_atual"] = ""
    st.session_state["perfil_atual"] = ""
    st.session_state["carrinho_expedicao"] = [] # Limpa o carrinho ao sair
    st.rerun()

st.sidebar.divider()

if st.session_state["perfil_atual"] == "Admin":
    st.sidebar.markdown("### 🤖 Operações Base")
    if not robo_disponivel:
        st.sidebar.info("🌐 O robô de extração opera apenas no servidor local da WEG.")
    else:
        if st.sidebar.button("⚡ Acionar Robô AlmoxWeb", type="primary", use_container_width=True):
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
                    st.sidebar.success(f"✅ {len(df_para_banco)} itens salvos!")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.sidebar.error("❌ Falha ao extrair dados.")

# ==========================================
# 4. TELA PRINCIPAL
# ==========================================
st.title("📦 Portal da Expedição (SAD 320)")

aba_pendentes, aba_historico = st.tabs(["📋 Pendentes de Despacho", "💾 Histórico (Já Despachados)"])

# ------------------------------------------
# ABA: PENDENTES (COM MÚLTIPLOS FILTROS)
# ------------------------------------------
with aba_pendentes:
    
    # 1. Os Filtros no Topo
    st.markdown("##### 🔍 Filtros de Busca")
    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
    f_mat = col_f1.text_input("Material")
    f_nf = col_f2.text_input("Nota Fiscal (NFE)")
    f_data = col_f3.text_input("Data EM")
    f_pos = col_f4.text_input("Posição")
    f_forn = col_f5.text_input("Fornecedor")
    
    filtro_status = st.radio("Filtre o Tipo de Estoque:", ["📦 Mostrar Tudo", "🟢 Apenas Livre", "🔴 Apenas CQ"], horizontal=True)
    st.divider()

    # 2. Lendo os Dados Brutos do Banco
    query = "SELECT * FROM expedicao_completa WHERE status_envio = 'Pendente'"
    if filtro_status == "🟢 Apenas Livre": query += " AND tipo_estoque = 'Livre'"
    elif filtro_status == "🔴 Apenas CQ": query += " AND tipo_estoque = 'CQ'"
    df_tela = pd.read_sql_query(query, engine)

    # 3. Aplicando os Filtros Múltiplos (Via Pandas para não dar dor de cabeça com SQL Dinâmico)
    if not df_tela.empty:
        # Garante que tudo é texto para evitar erro de filtro
        for col in ['material', 'nfe', 'data_em', 'posicao_dep', 'fornecedor']:
            df_tela[col] = df_tela[col].fillna('').astype(str)
            
        if f_mat: df_tela = df_tela[df_tela['material'].str.contains(f_mat, case=False)]
        if f_nf: df_tela = df_tela[df_tela['nfe'].str.contains(f_nf, case=False)]
        if f_data: df_tela = df_tela[df_tela['data_em'].str.contains(f_data, case=False)]
        if f_pos: df_tela = df_tela[df_tela['posicao_dep'].str.contains(f_pos, case=False)]
        if f_forn: df_tela = df_tela[df_tela['fornecedor'].str.contains(f_forn, case=False)]

    # 4. Exibindo a Tabela e o Carrinho Mágico
    if df_tela.empty:
        st.success("Tudo limpo! Nenhum material encontrado com esses filtros.")
    else:
        # A Mágica do Carrinho: Marca como TRUE só quem estiver na memória
        df_tela.insert(0, "Selecionar", df_tela['id'].isin(st.session_state["carrinho_expedicao"]))
        colunas_bloqueadas = [col for col in df_tela.columns if col != "Selecionar"]
        
        df_editado = st.data_editor(
            df_tela, 
            hide_index=True, 
            use_container_width=True, 
            disabled=colunas_bloqueadas,
            height=400
        )
        
        # O SISTEMA LÊ QUEM FOI CLICADO E GUARDA NO CARRINHO
        for index, row in df_editado.iterrows():
            id_linha = row['id']
            ta_marcado = row['Selecionar']
            
            if ta_marcado and id_linha not in st.session_state["carrinho_expedicao"]:
                st.session_state["carrinho_expedicao"].append(id_linha)
            elif not ta_marcado and id_linha in st.session_state["carrinho_expedicao"]:
                st.session_state["carrinho_expedicao"].remove(id_linha)

        # Mostra o Status do Carrinho
        qtd_carrinho = len(st.session_state["carrinho_expedicao"])
        
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            st.info(f"🛒 **Carrinho de Expedição:** Você selecionou **{qtd_carrinho}** itens no total.")
            
        with col_btn2:
            if st.button("🚀 Despachar Itens do Carrinho", type="primary", use_container_width=True):
                if qtd_carrinho == 0:
                    st.error("O carrinho está vazio! Selecione os itens.")
                else:
                    with engine.connect() as conn:
                        for id_peca in st.session_state["carrinho_expedicao"]:
                            conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Despachado' WHERE id = :id_peca"), {"id_peca": int(id_peca)})
                        conn.commit()
                        
                    # Limpa o carrinho depois de despachar
                    st.session_state["carrinho_expedicao"] = []
                    st.success("✅ Materiais Despachados com sucesso! Atualizando...")
                    time.sleep(1.5)
                    st.rerun()

# ------------------------------------------
# ABA: HISTÓRICO
# ------------------------------------------
with aba_historico:
    st.markdown("### 📦 Materiais já Despachados")
    
    query_hist = "SELECT * FROM expedicao_completa WHERE status_envio = 'Despachado'"
    df_hist = pd.read_sql_query(query_hist, engine)
    
    if df_hist.empty:
        st.info("Nenhum material foi despachado ainda.")
    else:
        st.dataframe(df_hist, hide_index=True, use_container_width=True, height=400)
        
        st.divider()
        if st.session_state["perfil_atual"] == "Admin":
            if st.button("🔄 Resetar Teste (Voltar todos para Pendente)"):
                with engine.connect() as conn:
                    conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Pendente'"))
                    conn.commit()
                # Limpa o carrinho também pra não dar bug no reset
                st.session_state["carrinho_expedicao"] = []
                st.rerun()
