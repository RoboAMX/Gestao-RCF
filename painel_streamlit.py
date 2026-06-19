import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time
from datetime import datetime

try:
    import agente_almoxweb 
    robo_disponivel = True
except ModuleNotFoundError:
    robo_disponivel = False

# ==========================================
# 🎨 INJEÇÃO DE DESIGN (PADRÃO WEG + DASHBOARDS)
# ==========================================
st.set_page_config(page_title="Portal de Expedição", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #f4f6f9; }
        h1, h2, h3, h4 { color: #00579D !important; font-family: 'Segoe UI', sans-serif; }
        
        /* Botões Padrão WEG */
        div.stButton > button:first-child {
            background-color: #00579D; color: white; border-radius: 4px; border: none; font-weight: bold; width: 100%;
        }
        div.stButton > button:first-child:hover { background-color: #003A6B; transform: scale(1.02); }
        
        /* Caixa de Pesquisa */
        .css-1r6slb0, .css-1n76uvr {
            background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0px 4px 15px rgba(0,0,0,0.05); border-top: 4px solid #00579D;
        }
        
        /* Layout dos Itens da Lista */
        .item-linha {
            background-color: white; padding: 15px; margin-bottom: 10px; border-radius: 6px; box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
            border-left: 6px solid #00579D; display: flex; align-items: center;
        }
        .item-urgente { border-left: 6px solid #d32f2f; background-color: #ffebee; }
        .item-atencao { border-left: 6px solid #ff9800; background-color: #fff3e0; }
        .item-qualidade { border-left: 6px solid #9c27b0; }
        
        /* KPIs Magníficos do Topo */
        .kpi-card {
            background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        }
        .kpi-valor { font-size: 36px; font-weight: bold; margin-bottom: 5px; }
        .kpi-titulo { font-size: 14px; color: #666; font-weight: bold; text-transform: uppercase; }
        
        .kpi-azul .kpi-valor { color: #00579D; }
        .kpi-verde .kpi-valor { color: #2e7d32; }
        .kpi-amarelo .kpi-valor { color: #f57c00; }
        .kpi-vermelho .kpi-valor { color: #d32f2f; }
        .kpi-vermelho { border-bottom: 4px solid #d32f2f; }
        
        /* Badge de Status */
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; display: inline-block; margin-top: 5px;}
        .bg-red { background-color: #d32f2f; }
        .bg-yellow { background-color: #f57c00; }
        .bg-green { background-color: #2e7d32; }
        .bg-purple { background-color: #9c27b0; }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 1. CONEXÃO COM O BANCO DE DADOS
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
        conn.execute(text("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)"))
        conn.commit()

        if conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar() == 0:
            conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('roberto', 'weg2026', 'Admin')"))
            conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('expedicao', 'senha123', 'Operador')"))
            conn.commit()
    st.session_state["db_verificado"] = True

# ==========================================
# 2. LOGIN SEGURO
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
# 3. MENU LATERAL E ROBÔ
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
# 4. MOTOR DE CÁLCULO DE SLA (DIAS)
# ==========================================
def calcular_sla_pandas(df):
    """Calcula quantos dias a peça está parada desde a Data EM e aplica a regra WEG"""
    if df.empty: return df
    
    # Converte a Data EM para o formato de data real do Python (Lidando com os pontos do SAP)
    df['data_real'] = pd.to_datetime(df['data_em'], format='mixed', dayfirst=True, errors='coerce')
    
    # Calcula a diferença em dias (Hoje - Data EM)
    hoje = pd.Timestamp(datetime.now().date())
    df['dias_parado'] = (hoje - df['data_real']).dt.days.fillna(0).astype(int)
    
    # Aplica as regras de Status
    def classificar_regra(row):
        tipo = str(row['tipo_estoque']).upper()
        dias = row['dias_parado']
        
        if 'Q' in tipo or 'CQ' in tipo:
            return "QUALIDADE"
        
        # Regra de Ouro da WEG: Sem Q, analisa os dias
        if dias > 7: return "URGENTE"
        elif dias > 3: return "ATENÇÃO"
        else: return "NO PRAZO"

    df['status_sla'] = df.apply(classificar_regra, axis=1)
    return df


# ==========================================
# 5. TELA PRINCIPAL (DASHBOARD + LISTA)
# ==========================================
col_topo1, col_topo2 = st.columns([3, 1])
with col_topo1:
    st.markdown("<h1>📊 Gestão Logística 320</h1>", unsafe_allow_html=True)
with col_topo2:
    st.markdown(f"<div style='text-align: right; padding-top:20px; color:#666;'>Logado como: <b>{st.session_state['usuario_atual'].upper()}</b></div>", unsafe_allow_html=True)

# Lendo TUDO pendente para gerar os KPIs
query_bruta = "SELECT * FROM expedicao_completa WHERE status_envio = 'Pendente'"
df_bruto = pd.read_sql_query(query_bruta, engine)
df_bruto = calcular_sla_pandas(df_bruto)

# --- OS KPIS MAGNÍFICOS NO TOPO ---
if not df_bruto.empty:
    kpi_total = len(df_bruto)
    kpi_urgente = len(df_bruto[df_bruto['status_sla'] == 'URGENTE'])
    kpi_atencao = len(df_bruto[df_bruto['status_sla'] == 'ATENÇÃO'])
    kpi_no_prazo = len(df_bruto[df_bruto['status_sla'] == 'NO PRAZO'])
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-card kpi-azul'><div class='kpi-titulo'>Total Pendente</div><div class='kpi-valor'>{kpi_total}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card kpi-verde'><div class='kpi-titulo'>No Prazo (≤ 3 dias)</div><div class='kpi-valor'>{kpi_no_prazo}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-card kpi-amarelo'><div class='kpi-titulo'>Atenção (> 3 dias)</div><div class='kpi-valor'>{kpi_atencao}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-card kpi-vermelho'><div class='kpi-titulo'>Crítico (> 7 dias)</div><div class='kpi-valor'>{kpi_urgente}</div></div>", unsafe_allow_html=True)
    st.write("")

# --- ABAS ---
aba_pendentes, aba_historico = st.tabs(["📋 Módulo de Despacho", "💾 Relatório de Envios"])

# ------------------------------------------
# ABA: MÓDULO DE DESPACHO (A LISTA INTELIGENTE)
# ------------------------------------------
with aba_pendentes:
    
    # A Barra de Busca Global
    with st.container():
        st.markdown("<div class='css-1r6slb0'>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns([3, 1])
        busca_global = col_b1.text_input("🔎 Pesquise (Material, NF, Fornecedor, Posição):", placeholder="Digite e dê Enter...")
        filtro_urgencia = col_b2.selectbox("Focar Operação:", ["Mostrar Todos", "🚨 Apenas URGENTES (>7 dias)", "⚠️ Atenção e Urgentes", "🟣 Qualidade (CQ)"])
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.write("")

    if df_bruto.empty:
        st.success("Tudo limpo! Nenhum material pendente.")
    else:
        df_tela = df_bruto.copy()
        
        # Filtro de Urgência
        if filtro_urgencia == "🚨 Apenas URGENTES (>7 dias)": df_tela = df_tela[df_tela['status_sla'] == 'URGENTE']
        elif filtro_urgencia == "⚠️ Atenção e Urgentes": df_tela = df_tela[df_tela['status_sla'].isin(['URGENTE', 'ATENÇÃO'])]
        elif filtro_urgencia == "🟣 Qualidade (CQ)": df_tela = df_tela[df_tela['status_sla'] == 'QUALIDADE']

        # Filtro Global
        if busca_global:
            mask = df_tela.astype(str).apply(lambda x: x.str.contains(busca_global, case=False, na=False)).any(axis=1)
            df_tela = df_tela[mask]

        if df_tela.empty:
            st.warning("Nenhum material encontrado com os filtros atuais.")
        else:
            # BOTÃO DE DESPACHO EM MASSA (Se houver filtro)
            if busca_global or filtro_urgencia != "Mostrar Todos":
                st.info(f"Mostrando **{len(df_tela)}** itens nesta seleção.")
                if st.button(f"🚀 Despachar Todos os {len(df_tela)} itens listados abaixo de uma vez"):
                    with engine.connect() as conn:
                        for id_peca in df_tela["id"]:
                            conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Despachado' WHERE id = :id_peca"), {"id_peca": int(id_peca)})
                        conn.commit()
                    st.rerun()
            
            st.divider()

            # RENDERIZAÇÃO DOS CARDS COM AS CORES DE SLA
            for index, row in df_tela.iterrows():
                # Define as cores do cartão baseado no Status
                status = row['status_sla']
                dias = row['dias_parado']
                
                classe_css = "item-linha"
                badge_html = f"<span class='badge bg-green'>NO PRAZO ({dias} dias)</span>"
                
                if status == "URGENTE":
                    classe_css += " item-urgente"
                    badge_html = f"<span class='badge bg-red'>🚨 CRÍTICO: {dias} DIAS PARADO</span>"
                elif status == "ATENÇÃO":
                    classe_css += " item-atencao"
                    badge_html = f"<span class='badge bg-yellow'>⚠️ ATENÇÃO: {dias} DIAS</span>"
                elif status == "QUALIDADE":
                    classe_css += " item-qualidade"
                    badge_html = f"<span class='badge bg-purple'>🟣 BLOQ. QUALIDADE</span>"

                # Desenha o HTML do Card
                st.markdown(f"<div class='{classe_css}'>", unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns([1, 4, 2, 2])
                
                with c1:
                    st.markdown(f"<div style='text-align:center;'><span style='font-size:24px; font-weight:bold;'>{row['estoque']}</span><br><span style='font-size:10px; color:#666;'>QUANTIDADE</span></div>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**{row['material']}** &nbsp; {badge_html}<br><span style='font-size:14px; color:#444;'>{row['descricao']}</span>", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"<span style='font-size:12px; color:#666;'>Nota Fiscal / Fornecedor:</span><br><b>{row['nfe']}</b><br><span style='font-size:11px;'>{row['fornecedor']}</span>", unsafe_allow_html=True)
                with c4:
                    st.markdown(f"<span style='font-size:12px; color:#666;'>Endereçamento:</span><br><b style='color:#00579D;'>{row['posicao_dep']}</b>", unsafe_allow_html=True)
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
            st.divider()
            if st.button("🔄 Resetar Banco de Teste"):
                with engine.connect() as conn:
                    conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Pendente'"))
                    conn.commit()
                st.rerun()
