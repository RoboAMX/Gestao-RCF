import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time

try:
    import agente_almoxweb 
    robo_disponivel = True
except ModuleNotFoundError:
    robo_disponivel = False

# ==========================================
# 🎨 INJEÇÃO DE DESIGN (PADRÃO WEG)
# ==========================================
st.set_page_config(page_title="Portal de Expedição", layout="wide", initial_sidebar_state="collapsed")

# CSS MÁGICO PARA MUDAR A CARA DO STREAMLIT
st.markdown("""
    <style>
        /* Esconde o menu feio do Streamlit no topo */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Cor de fundo do site */
        .stApp { background-color: #f4f6f9; }
        
        /* Títulos com o Azul WEG */
        h1, h2, h3 { color: #00579D !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        
        /* Estilizando os Botões (Botão é Botão!) */
        div.stButton > button:first-child {
            background-color: #00579D;
            color: white;
            border-radius: 4px;
            border: none;
            padding: 5px 15px;
            font-weight: bold;
            transition: all 0.3s ease;
            width: 100%;
        }
        div.stButton > button:first-child:hover {
            background-color: #003A6B; /* Azul mais escuro ao passar o mouse */
            box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
            transform: scale(1.02);
        }
        
        /* Caixa de Login e Filtros (Efeito Card SharePoint) */
        .css-1r6slb0, .css-1n76uvr {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.05);
            border-top: 4px solid #00579D;
        }
        
        /* Linha dos Itens */
        .item-linha {
            background-color: white;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-left: 5px solid #00579D;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 1. CONEXÃO COM O POSTGRESQL (SUPABASE)
# ==========================================
DATABASE_URL = st.secrets["banco_dados"]["url"]
engine = create_engine(DATABASE_URL)

if "db_verificado" not in st.session_state:
    with engine.connect() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS expedicao_completa (
                id SERIAL PRIMARY KEY, item TEXT, material TEXT, descricao TEXT, 
                centro_dep TEXT, tipo_estoque TEXT, lote TEXT, tp TEXT, 
                posicao_dep TEXT, estoque REAL, data_em TEXT, data_necess TEXT, 
                nfe TEXT, fornecedor TEXT, status_envio TEXT DEFAULT 'Pendente' 
            )
        '''))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)'''))
        conn.commit()

        if conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar() == 0:
            conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('roberto', 'weg2026', 'Admin')"))
            conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('expedicao', 'senha123', 'Operador')"))
            conn.commit()
    st.session_state["db_verificado"] = True

# ==========================================
# 2. SISTEMA DE LOGIN (DESIGN LIMPO)
# ==========================================
if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["usuario_atual"] = ""
    st.session_state["perfil_atual"] = ""

if not st.session_state["logado"]:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/WEG_logo.svg/1200px-WEG_logo.svg.png", width=150)
        st.markdown("## Portal de Expedição SAD 320")
        with st.form("form_login"):
            usuario_input = st.text_input("Usuário").lower().strip()
            senha_input = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema"):
                with engine.connect() as conn:
                    resultado = conn.execute(text("SELECT senha, perfil FROM usuarios WHERE usuario = :u"), {"u": usuario_input}).fetchone()
                if resultado and resultado[0] == senha_input:
                    st.session_state["logado"] = True
                    st.session_state["usuario_atual"] = usuario_input
                    st.session_state["perfil_atual"] = resultado[1]
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
    st.stop()

# ==========================================
# 3. MENU LATERAL (OCULTO POR PADRÃO)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/WEG_logo.svg/1200px-WEG_logo.svg.png", width=100)
st.sidebar.markdown(f"👨‍💻 Usuário: **{st.session_state['usuario_atual'].upper()}**")

if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()

if st.session_state["perfil_atual"] == "Admin":
    st.sidebar.markdown("### 🤖 Robô AlmoxWeb")
    if robo_disponivel:
        if st.sidebar.button("⚡ Sincronizar com SAP"):
            with st.spinner("Extraindo dados da Intranet..."):
                dados_novos = agente_almoxweb.extrair_dados_almoxweb()
                if dados_novos:
                    df_robo = pd.DataFrame(dados_novos)
                    df_pb = pd.DataFrame()
                    df_pb['item'] = df_robo.get('Item', '')
                    df_pb['material'] = df_robo.get('Material', '')
                    df_pb['descricao'] = df_robo.get('Descricao', df_robo.get('Descrição', ''))
                    df_pb['centro_dep'] = df_robo.get('Centro_Dep', df_robo.get('Centro | Dep.', ''))
                    df_pb['tipo_estoque'] = df_robo.get('TipoEstoq.', df_robo.get('TipoEstoq', 'Livre'))
                    df_pb['lote'] = df_robo.get('Lote', '')
                    df_pb['tp'] = df_robo.get('Tp.', df_robo.get('Tp', ''))
                    df_pb['posicao_dep'] = df_robo.get('Posicao', df_robo.get('Posição Dep.', ''))
                    df_pb['estoque'] = df_robo.get('Quantidade', df_robo.get('Estoque', 0))
                    df_pb['estoque'] = df_pb['estoque'].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    df_pb['estoque'] = pd.to_numeric(df_pb['estoque'], errors='coerce').fillna(0.0)
                    df_pb['data_em'] = df_robo.get('Data_Entrada', df_robo.get('Data EM', ''))
                    df_pb['data_necess'] = df_robo.get('Data_Necess', df_robo.get('Data Necess.', ''))
                    df_pb['nfe'] = df_robo.get('NF', df_robo.get('NFE', ''))
                    df_pb['fornecedor'] = df_robo.get('Fornecedor', '')
                    
                    df_pb.to_sql(name='expedicao_completa', con=engine, if_exists='append', index=False)
                    st.sidebar.success("✅ Base Atualizada!")
                    time.sleep(1.5)
                    st.rerun()

# ==========================================
# 4. TELA PRINCIPAL
# ==========================================
col_topo1, col_topo2 = st.columns([3, 1])
with col_topo1:
    st.markdown("<h1>📦 Gestão de Expedição</h1>", unsafe_allow_html=True)
with col_topo2:
    st.markdown(f"<div style='text-align: right; padding-top:20px; color:#666;'>Logado como: <b>{st.session_state['usuario_atual'].upper()}</b></div>", unsafe_allow_html=True)

aba_pendentes, aba_historico = st.tabs(["📋 Módulo de Despacho", "💾 Relatório de Envios"])

# ------------------------------------------
# ABA: MÓDULO DE DESPACHO (LISTA DE CARTÕES)
# ------------------------------------------
with aba_pendentes:
    
    # --- BARRA DE BUSCA (Estilo Google) ---
    with st.container():
        st.markdown("<div class='css-1r6slb0'>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns([3, 1])
        busca_global = col_b1.text_input("🔎 Pesquise por NF, Material, Fornecedor ou Posição (Pressione Enter):")
        filtro_status = col_b2.selectbox("Filtro de Qualidade:", ["Mostrar Tudo", "Apenas Livre", "Apenas CQ"])
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.write("")

    # Busca no Banco
    query = "SELECT * FROM expedicao_completa WHERE status_envio = 'Pendente'"
    if filtro_status == "Apenas Livre": query += " AND tipo_estoque = 'Livre'"
    elif filtro_status == "Apenas CQ": query += " AND tipo_estoque = 'CQ'"
    df_bruto = pd.read_sql_query(query, engine)

    if df_bruto.empty:
        st.success("Tudo limpo! Nenhum material pendente.")
    else:
        # Aplica a busca global na tabela
        df_tela = df_bruto.copy()
        if busca_global:
            mask = df_tela.astype(str).apply(lambda x: x.str.contains(busca_global, case=False, na=False)).any(axis=1)
            df_tela = df_tela[mask]

        if df_tela.empty:
            st.warning("Nenhum material encontrado com essa pesquisa.")
        else:
            # BOTÃO PARA DESPACHAR TUDO DA TELA DE UMA VEZ
            if busca_global:
                st.info(f"Foram encontrados **{len(df_tela)}** itens nesta pesquisa.")
                if st.button(f"🚀 Despachar Todos os {len(df_tela)} itens desta busca de uma vez"):
                    with engine.connect() as conn:
                        for id_peca in df_tela["id"]:
                            conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Despachado' WHERE id = :id_peca"), {"id_peca": int(id_peca)})
                        conn.commit()
                    st.rerun()
            
            st.divider()

            # RENDERIZAÇÃO DOS MATERIAIS EM LINHAS (BOTÃO É BOTÃO!)
            for index, row in df_tela.iterrows():
                # Desenha o "Card" da linha
                st.markdown("<div class='item-linha'>", unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns([1, 4, 2, 2])
                
                with c1:
                    st.markdown(f"<span style='font-size:24px; font-weight:bold; color:#00579D;'>{row['estoque']}</span><br><span style='font-size:12px; color:#666;'>QUANTIDADE</span>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**{row['material']}**<br><span style='font-size:14px;'>{row['descricao']}</span>", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"**NF:** {row['nfe']}<br>**Posição:** {row['posicao_dep']}", unsafe_allow_html=True)
                with c4:
                    st.markdown("<br>", unsafe_allow_html=True) # Espaçamento para o botão alinhar
                    # O BOTÃO INDIVIDUAL DE DESPACHO
                    if st.button(f"✔️ Despachar", key=f"btn_{row['id']}"):
                        with engine.connect() as conn:
                            conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Despachado' WHERE id = :id_peca"), {"id_peca": int(row['id'])})
                            conn.commit()
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------
# ABA: HISTÓRICO
# ------------------------------------------
with aba_historico:
    st.markdown("### 📦 Materiais já Despachados")
    query_hist = "SELECT material, descricao, estoque, nfe, fornecedor FROM expedicao_completa WHERE status_envio = 'Despachado'"
    df_hist = pd.read_sql_query(query_hist, engine)
    
    if df_hist.empty:
        st.info("Nenhum material foi despachado ainda.")
    else:
        st.dataframe(df_hist, hide_index=True, use_container_width=True)
        
        if st.session_state["perfil_atual"] == "Admin":
            if st.button("🔄 Resetar Banco de Teste"):
                with engine.connect() as conn:
                    conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Pendente'"))
                    conn.commit()
                st.rerun()
