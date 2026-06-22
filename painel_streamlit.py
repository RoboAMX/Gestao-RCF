import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time
from datetime import datetime
import io
import plotly.graph_objects as go  # 🚀 BIBLIOTECA NOVA PARA OS GRÁFICOS (VELOCÍMETROS)

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
except ImportError:
    pass

try:
    from PIL import Image
    from pylibdmtx.pylibdmtx import decode as decode_dm
    leitor_ativo = True
except ImportError:
    leitor_ativo = False

try:
    import agente_almoxweb 
    robo_disponivel = True
except ModuleNotFoundError:
    robo_disponivel = False

# ==========================================
# 🎨 CONFIGURAÇÕES DE PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="Portal Inbound WEG", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #E6F0F9; } 
        h1, h2, h3, h4, h5 { color: #00579D !important; font-family: 'Segoe UI', sans-serif; }
        div.stButton > button:first-child { background-color: #00579D; color: white; border-radius: 4px; border: none; font-weight: bold; width: 100%; }
        div.stButton > button:first-child:hover { background-color: #003A6B; transform: scale(1.02); }
        .kpi-card { background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0px 4px 10px rgba(0,87,157,0.1); margin-bottom: 20px; }
        .kpi-valor { font-size: 36px; font-weight: bold; margin-bottom: 5px; }
        .kpi-titulo { font-size: 14px; color: #666; font-weight: bold; text-transform: uppercase; }
        .kpi-azul .kpi-valor { color: #00579D; } .kpi-verde .kpi-valor { color: #2e7d32; }
        .kpi-amarelo .kpi-valor { color: #f57c00; } .kpi-vermelho .kpi-valor { color: #d32f2f; }
        .kpi-roxo .kpi-valor { color: #9c27b0; }
        .kpi-vermelho { border-bottom: 4px solid #d32f2f; } .kpi-roxo { border-bottom: 4px solid #9c27b0; }
        .css-1r6slb0, .css-1n76uvr { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0px 4px 15px rgba(0,87,157,0.1); border-top: 4px solid #00579D; }
        div[data-testid="stCameraInput"] button { background-color: #2e7d32 !important; }
    </style>
""", unsafe_allow_html=True)

LOGO_WEG = "https://logospng.org/download/weg/logo-weg-2048.png"

# ==========================================
# 1. CONEXÃO E ATUALIZAÇÃO DO BANCO
# ==========================================
DATABASE_URL = st.secrets["banco_dados"]["url"]
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS expedicao_completa (
            id SERIAL PRIMARY KEY, item TEXT, material TEXT, descricao TEXT, 
            centro_dep TEXT, tipo_estoque TEXT, lote TEXT, tp TEXT, 
            posicao_dep TEXT, estoque REAL, data_em TEXT, data_necess TEXT, 
            nfe TEXT, fornecedor TEXT, status_envio TEXT DEFAULT 'Pendente'
        )
    '''))
    conn.execute(text("ALTER TABLE expedicao_completa ADD COLUMN IF NOT EXISTS lote_envio TEXT"))
    conn.execute(text("ALTER TABLE expedicao_completa ADD COLUMN IF NOT EXISTS operador_separacao TEXT"))
    conn.execute(text("ALTER TABLE expedicao_completa ADD COLUMN IF NOT EXISTS deposito_destino TEXT"))
    conn.execute(text("ALTER TABLE expedicao_completa ADD COLUMN IF NOT EXISTS data_hora_despacho TEXT"))
    conn.execute(text("ALTER TABLE expedicao_completa ADD COLUMN IF NOT EXISTS umb TEXT")) 
    
    conn.execute(text("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS depositos_destino (id SERIAL PRIMARY KEY, nome_deposito TEXT UNIQUE, responsavel TEXT)"))
    conn.execute(text("ALTER TABLE depositos_destino ADD COLUMN IF NOT EXISTS emails_cc TEXT")) 
    conn.execute(text("CREATE TABLE IF NOT EXISTS operadores_fisicos (id SERIAL PRIMARY KEY, nome TEXT UNIQUE)"))
    
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS ocorrencias_chat (
            id SERIAL PRIMARY KEY, lote_ref TEXT, usuario TEXT, perfil TEXT, data_hora TEXT, mensagem TEXT
        )
    '''))
    
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS fila_emails (
            id SERIAL PRIMARY KEY, lote_envio TEXT, tipo_evento TEXT, destino TEXT, 
            operador TEXT, status TEXT DEFAULT 'Pendente', data_criacao TEXT
        )
    '''))
    conn.commit()

    if conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar() == 0:
        conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('roberto', 'weg2026', 'Admin')"))
        conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('almox', '1234', 'Almoxarifado')"))
        conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('doca1', '1234', 'Recebimento')"))
        conn.commit()
        
    if conn.execute(text("SELECT COUNT(*) FROM operadores_fisicos")).scalar() == 0:
        conn.execute(text("INSERT INTO operadores_fisicos (nome) VALUES ('João Silva (Exemplo)')"))
        conn.commit()

# ==========================================
# 2. LOGIN SEGURO E MEMÓRIA
# ==========================================
if "logado" not in st.session_state: st.session_state["logado"] = False
if "usuario_atual" not in st.session_state: st.session_state["usuario_atual"] = ""
if "perfil_atual" not in st.session_state: st.session_state["perfil_atual"] = ""
if "precisa_mudar_senha" not in st.session_state: st.session_state["precisa_mudar_senha"] = False 
if "carrinho_expedicao" not in st.session_state: st.session_state["carrinho_expedicao"] = []
if "pdf_pronto" not in st.session_state: st.session_state["pdf_pronto"] = None
if "busca_global" not in st.session_state: st.session_state["busca_global"] = "" 

if not st.session_state["logado"]:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image(LOGO_WEG, width=150)
        st.markdown("## Portal Inbound (Doca ➡️ Almox)")
        with st.form("form_login"):
            usuario_input = st.text_input("Usuário (Login PC)").lower().strip()
            senha_input = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema"):
                with engine.connect() as conn:
                    resultado = conn.execute(text("SELECT senha, perfil FROM usuarios WHERE usuario = :u"), {"u": usuario_input}).fetchone()
                if resultado and resultado[0] == senha_input:
                    st.session_state["logado"] = True
                    st.session_state["usuario_atual"] = usuario_input
                    st.session_state["perfil_atual"] = resultado[1]
                    if senha_input == "1234": st.session_state["precisa_mudar_senha"] = True
                    else: st.session_state["precisa_mudar_senha"] = False
                    st.success("Acesso Liberado!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
    st.stop()

if st.session_state["precisa_mudar_senha"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_t1, col_t2, col_t3 = st.columns([1, 2, 1])
    with col_t2:
        st.warning("⚠️ **Ação Obrigatória:** Este é o seu primeiro acesso. Por favor, crie uma nova senha.")
        st.markdown("<div class='css-1r6slb0'>", unsafe_allow_html=True)
        st.markdown(f"### Olá, {st.session_state['usuario_atual'].upper()}")
        with st.form("form_mudar_senha"):
            nova_senha = st.text_input("Digite a Nova Senha:", type="password")
            confirma_senha = st.text_input("Confirme a Nova Senha:", type="password")
            if st.form_submit_button("Atualizar Senha e Entrar"):
                if nova_senha == "" or confirma_senha == "": st.error("As senhas não podem ser vazias.")
                elif nova_senha == "1234": st.error("Sua nova senha não pode ser 1234. Escolha outra mais segura.")
                elif nova_senha != confirma_senha: st.error("As senhas não coincidem.")
                else:
                    with engine.connect() as conn:
                        conn.execute(text("UPDATE usuarios SET senha = :s WHERE usuario = :u"), {"s": nova_senha, "u": st.session_state["usuario_atual"]})
                        conn.commit()
                    st.session_state["precisa_mudar_senha"] = False
                    st.success("✅ Senha atualizada com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. MENU LATERAL
# ==========================================
st.sidebar.image(LOGO_WEG, width=100)
st.sidebar.markdown(f"👨‍💻 Sistema: **{st.session_state['usuario_atual'].upper()}**")
st.sidebar.markdown(f"🛡️ Nível: **{st.session_state['perfil_atual']}**")

if st.sidebar.button("🚪 Sair do Sistema"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
st.sidebar.divider()

def limpar_sujeira_sap(valor):
    if pd.isna(valor): return ''
    v = str(valor).strip().upper()
    if v.endswith('.0'): return v[:-2]
    if v == 'NAN' or v == 'NONE': return ''
    return v

if st.session_state["perfil_atual"] == "Admin":
    st.sidebar.markdown("### 🤖 Sincronização SAP")
    if robo_disponivel:
        if st.sidebar.button("⚡ Sincronizar com SAP"):
            with st.spinner("Extraindo e comparando dados..."):
                dados_novos = agente_almoxweb.extrair_dados_almoxweb()
                if dados_novos:
                    df_robo = pd.DataFrame(dados_novos)
                    df_pb = pd.DataFrame()
                    df_pb['item'] = df_robo.get('Item', '').apply(limpar_sujeira_sap)
                    df_pb['material'] = df_robo.get('Material', '').apply(limpar_sujeira_sap)
                    df_pb['descricao'] = df_robo.get('Descricao', df_robo.get('Descrição', ''))
                    df_pb['centro_dep'] = df_robo.get('Centro_Dep', df_robo.get('Centro | Dep.', '')).apply(limpar_sujeira_sap)
                    df_pb['tipo_estoque'] = df_robo.get('TipoEstoq.', df_robo.get('TipoEstoq', 'Livre'))
                    df_pb['lote'] = df_robo.get('Lote', '').apply(limpar_sujeira_sap)
                    df_pb['tp'] = df_robo.get('Tp.', df_robo.get('Tp', '')).apply(limpar_sujeira_sap)
                    df_pb['posicao_dep'] = df_robo.get('Posicao', df_robo.get('Posição Dep.', '')).apply(limpar_sujeira_sap)
                    df_pb['nfe'] = df_robo.get('NF', df_robo.get('NFE', '')).apply(limpar_sujeira_sap)
                    estoque_sujo = df_robo.get('Quantidade', df_robo.get('Estoque', '')).astype(str)
                    df_pb['umb'] = estoque_sujo.str.replace(r'[\d.,\s]', '', regex=True).str.upper() 
                    df_pb['estoque'] = estoque_sujo.str.replace(r'[^\d.,]', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    df_pb['estoque'] = pd.to_numeric(df_pb['estoque'], errors='coerce').fillna(0.0)
                    df_pb['data_em'] = df_robo.get('Data_Entrada', df_robo.get('Data EM', ''))
                    df_pb['data_necess'] = df_robo.get('Data_Necess', df_robo.get('Data Necess.', ''))
                    df_pb['fornecedor'] = df_robo.get('Fornecedor', '')

                    df_pb['chave_comparacao'] = df_pb['material'] + "|" + df_pb['nfe'] + "|" + df_pb['posicao_dep']
                    
                    query_banco = "SELECT id, status_envio, COALESCE(material, '') || '|' || COALESCE(nfe, '') || '|' || COALESCE(posicao_dep, '') as chave_banco FROM expedicao_completa"
                    df_banco = pd.read_sql_query(query_banco, engine)
                    
                    chaves_no_banco = set(df_banco['chave_banco'])
                    chaves_pendentes_banco = set(df_banco[df_banco['status_envio'].isin(['Pendente', 'Em Trânsito Interno'])]['chave_banco'])
                    chaves_do_sap = set(df_pb['chave_comparacao'])

                    df_inserir = df_pb[~df_pb['chave_comparacao'].isin(chaves_no_banco)].copy()
                    df_inserir = df_inserir.drop(columns=['chave_comparacao'])
                    chaves_sumiram = chaves_pendentes_banco - chaves_do_sap

                    if not df_inserir.empty:
                        df_inserir.to_sql(name='expedicao_completa', con=engine, if_exists='append', index=False)
                    
                    if chaves_sumiram:
                        with engine.connect() as conn:
                            for chave in chaves_sumiram:
                                conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Baixado Direto no SAP' WHERE status_envio IN ('Pendente', 'Em Trânsito Interno') AND COALESCE(material, '') || '|' || COALESCE(nfe, '') || '|' || COALESCE(posicao_dep, '') = :c"), {"c": chave})
                            conn.commit()

                    st.sidebar.success(f"✅ Sincronizado! \n{len(df_inserir)} novos.\n{len(chaves_sumiram)} baixados.")
                    time.sleep(3)
                    st.rerun()

# ==========================================
# 4. FUNÇÕES GERAIS E PDF
# ==========================================
def calcular_sla_pandas(df):
    if df.empty: 
        df['SLA'] = []
        return df
    df['data_real'] = pd.to_datetime(df['data_em'], format='mixed', dayfirst=True, errors='coerce')
    hoje = pd.Timestamp(datetime.now().date())
    df['dias_parado'] = (hoje - df['data_real']).dt.days.fillna(0).astype(int)
    def classificar_regra(row):
        tipo = str(row['tipo_estoque']).upper()
        if 'Q' in tipo or 'CQ' in tipo: return "🟣 BLOQ. QUALIDADE"
        if row['dias_parado'] > 7: return "🔴 URGENTE (>7d)"
        elif row['dias_parado'] > 3: return "🟡 ATENÇÃO (>3d)"
        else: return "🟢 NO PRAZO"
    df['SLA'] = df.apply(classificar_regra, axis=1)
    # NÃO REMOVER 'dias_parado' aqui, vamos usar no Dashboard!
    return df.drop(columns=['data_real'])

def calcular_sla_acondicionamento(df):
    if df.empty or 'data_hora_despacho' not in df.columns: 
        df['SLA_Interno'] = []
        return df
    df['dh_despacho'] = pd.to_datetime(df['data_hora_despacho'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    hoje_agora = pd.Timestamp(datetime.now())
    df['horas_transito'] = (hoje_agora - df['dh_despacho']).dt.total_seconds() / 3600
    def classificar_sla_int(row):
        if pd.isna(row['horas_transito']): return "⚪ N/A"
        if row['horas_transito'] > 24: return "🔴 ATRASADO (>24h)"
        elif row['horas_transito'] > 12: return "🟡 ATENÇÃO (>12h)"
        else: return "🟢 NO PRAZO (<24h)"
    df['SLA_Interno'] = df.apply(classificar_sla_int, axis=1)
    return df.drop(columns=['dh_despacho', 'horas_transito'])

def gerar_proximo_lote():
    with engine.connect() as conn:
        ultimo_lote = conn.execute(text("SELECT MAX(lote_envio) FROM expedicao_completa WHERE lote_envio IS NOT NULL")).scalar()
        if not ultimo_lote: return "00000000001"
        else: return str(int(ultimo_lote) + 1).zfill(11)

def gerar_pdf_remessa_sap(lote, origem, destino, operador, df_itens):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elementos = []
    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(name='TituloSAP', fontName='Helvetica-Bold', fontSize=14, textColor=colors.black, alignment=1)
    estilo_info = ParagraphStyle(name='InfoSAP', fontName='Helvetica', fontSize=10, textColor=colors.black)
    
    elementos.append(Paragraph(f"GUIA DE TRANSFERÊNCIA DE MATERIAIS - WEG", estilo_titulo))
    elementos.append(Spacer(1, 15))
    data_hora = df_itens['data_hora_despacho'].iloc[0] if 'data_hora_despacho' in df_itens.columns and not pd.isna(df_itens['data_hora_despacho'].iloc[0]) else datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    info_html = f"<b>Número da Remessa:</b> {lote} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Emissão:</b> {data_hora}<br/><b>Origem:</b> {origem} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Destino:</b> {destino}<br/><b>Identificador:</b> {operador} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Emissor do Sistema:</b> {st.session_state['usuario_atual'].upper()}"
    elementos.append(Paragraph(info_html, estilo_info))
    elementos.append(Spacer(1, 20))
    
    dados_tabela = [["Material", "Descrição", "Qtd UMB", "Posição", "Nota Fiscal", "Fornecedor"]]
    for _, row in df_itens.iterrows():
        umb = row.get('umb', '')
        if pd.isna(umb): umb = ''
        qtd_formatada = f"{row['estoque']} {umb}".strip()
        dados_tabela.append([str(row['material']), str(row['descricao'])[:45], qtd_formatada, str(row['posicao_dep']), str(row['nfe']), str(row['fornecedor'])[:35]])
        
    tabela = Table(dados_tabela, colWidths=[80, 260, 50, 80, 110, 220])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E0E0E0')), ('TEXTCOLOR', (0,0), (-1,0), colors.black), ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 9), ('BOTTOMPADDING', (0,0), (-1,0), 6), ('TOPPADDING', (0,0), (-1,0), 6),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'), ('FONTSIZE', (0,1), (-1,-1), 8), ('ALIGN', (2,1), (2,-1), 'CENTER'), ('ALIGN', (3,1), (3,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))
    elementos.append(tabela)
    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()

config_colunas_gerais = {
    "Selecionar": st.column_config.CheckboxColumn("☑️", width="small"),
    "Acondicionado": st.column_config.CheckboxColumn("☑️ Recebido?", width="small"),
    "lote_envio": st.column_config.TextColumn("Número da Remessa", width="small"),
    "deposito_destino": st.column_config.TextColumn("Destino", width="medium"),
    "operador_separacao": st.column_config.TextColumn("Identificador", width="medium"),
    "SLA": st.column_config.TextColumn("Status Doca", width="medium"),
    "SLA_Interno": st.column_config.TextColumn("Relógio Almox.", width="medium"),
    "material": st.column_config.TextColumn("Material", width="small"),
    "descricao": st.column_config.TextColumn("Descrição", width="large"), 
    "estoque": st.column_config.NumberColumn("Qtd", width="small"), 
    "umb": st.column_config.TextColumn("UM", width="small"),             
    "posicao_dep": st.column_config.TextColumn("Posição", width="small"),
    "nfe": st.column_config.TextColumn("NF", width="medium"),
    "fornecedor": st.column_config.TextColumn("Fornecedor", width="medium"),
    "status_envio": st.column_config.TextColumn("Situação Atual", width="small")
}

# ==========================================
# 5. TELA PRINCIPAL E DASHBOARD
# ==========================================
col_topo1, col_topo2 = st.columns([3, 1])
with col_topo1: st.markdown("<h1>📊 Hub Inbound (Entrada de Material)</h1>", unsafe_allow_html=True)

query_bruta = "SELECT * FROM expedicao_completa WHERE status_envio IN ('Pendente', 'Em Trânsito Interno')"
df_bruto = pd.read_sql_query(query_bruta, engine)
df_bruto = calcular_sla_pandas(df_bruto)

aba_dashboard, aba_recebimento, aba_almoxarifado, aba_historico, aba_chat, aba_admin = st.tabs([
    "📊 0. GESTÃO À VISTA",
    "📋 1. ENVIAR (Recebimento Físico)", 
    "📦 2. ACONDICIONAR (Almoxarifado)", 
    "💾 3. HISTÓRICO GERAL",
    "💬 4. MURAL DE OCORRÊNCIAS", 
    "⚙️ 5. ADMINISTRAÇÃO"
])

# ------------------------------------------
# 🚀 NOVA ABA 0: DASHBOARD E GESTÃO À VISTA
# ------------------------------------------
with aba_dashboard:
    df_dashboard = df_bruto[df_bruto['status_envio'] == 'Pendente'] if not df_bruto.empty else pd.DataFrame()
    
    if df_dashboard.empty:
        st.success("🎉 Tudo limpo! Nenhum material parado aguardando envio na Doca.")
    else:
        # --- CARDS GERAIS (Que ficavam flutuando antes) ---
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(f"<div class='kpi-card kpi-azul'><div class='kpi-titulo'>Total no Recebimento</div><div class='kpi-valor'>{len(df_dashboard)}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi-card kpi-verde'><div class='kpi-titulo'>Prazo (≤3d)</div><div class='kpi-valor'>{len(df_dashboard[df_dashboard['SLA'] == '🟢 NO PRAZO'])}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='kpi-card kpi-amarelo'><div class='kpi-titulo'>Atenção (>3d)</div><div class='kpi-valor'>{len(df_dashboard[df_dashboard['SLA'] == '🟡 ATENÇÃO (>3d)'])}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='kpi-card kpi-vermelho'><div class='kpi-titulo'>Crítico (>7d)</div><div class='kpi-valor'>{len(df_dashboard[df_dashboard['SLA'] == '🔴 URGENTE (>7d)'])}</div></div>", unsafe_allow_html=True)
        c5.markdown(f"<div class='kpi-card kpi-roxo'><div class='kpi-titulo'>Qualidade (CQ)</div><div class='kpi-valor'>{len(df_dashboard[df_dashboard['SLA'] == '🟣 BLOQ. QUALIDADE'])}</div></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # --- DIVISÃO DAS REGIÕES: QUALIDADE VS RECEBIMENTO ---
        df_qualidade = df_dashboard[df_dashboard['SLA'] == '🟣 BLOQ. QUALIDADE'].copy()
        df_recebimento = df_dashboard[df_dashboard['SLA'] != '🟣 BLOQ. QUALIDADE'].copy()
        
        total_q = len(df_qualidade)
        total_r = len(df_recebimento)
        
        # O que é "Prioridade"? Vamos assumir Itens Atrasados (> 3 dias parados)
        prioridade_q = len(df_qualidade[df_qualidade['dias_parado'] > 3]) if not df_qualidade.empty else 0
        prioridade_r = len(df_recebimento[df_recebimento['dias_parado'] > 3]) if not df_recebimento.empty else 0
        
        antigo_q_dias = int(df_qualidade['dias_parado'].max()) if not df_qualidade.empty and pd.notna(df_qualidade['dias_parado'].max()) else 0
        antigo_r_dias = int(df_recebimento['dias_parado'].max()) if not df_recebimento.empty and pd.notna(df_recebimento['dias_parado'].max()) else 0
        
        antigo_q_data = df_qualidade.loc[df_qualidade['dias_parado'].idxmax(), 'data_em'] if not df_qualidade.empty else "N/A"
        antigo_r_data = df_recebimento.loc[df_recebimento['dias_parado'].idxmax(), 'data_em'] if not df_recebimento.empty else "N/A"

        # --- FUNÇÃO DO GRÁFICO ---
        def criar_gauge(valor, maximo, titulo):
            maximo = maximo if maximo > 0 else 1 # Evitar erro de divisão por zero
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=valor, title={'text': titulo, 'font': {'size': 18}},
                gauge={
                    'axis': {'range': [None, maximo]}, 'bar': {'color': "#00579D"},
                    'steps': [
                        {'range': [0, maximo*0.5], 'color': "lightgreen"},
                        {'range': [maximo*0.5, maximo*0.8], 'color': "yellow"},
                        {'range': [maximo*0.8, maximo], 'color': "salmon"}
                    ]
                }
            ))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
            return fig

        # --- CONSTRUÇÃO VISUAL DAS 3 COLUNAS ---
        col_esq, col_meio, col_dir = st.columns([1, 1.2, 1])

        with col_esq:
            st.markdown("<h3 style='text-align: center; border-bottom: 1px solid #ccc; padding-bottom: 10px;'>Laboratório Qualidade</h3>", unsafe_allow_html=True)
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(criar_gauge(prioridade_q, total_q, "Atrasados"), use_container_width=True)
            with g2: st.plotly_chart(criar_gauge(total_q, len(df_dashboard), "Total (CQ)"), use_container_width=True)
            st.markdown(f"""
                <div style="display: flex; gap: 10px; text-align: center; font-size: 24px; font-weight: bold; color: white;">
                    <div style="flex: 1; background-color: #4CAF50; padding: 15px; border-radius: 5px;">{total_q - prioridade_q}</div>
                    <div style="flex: 1; background-color: #F44336; padding: 15px; border-radius: 5px;">{prioridade_q}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_meio:
            st.markdown("<h3 style='text-align: center; border-bottom: 1px solid #ccc; padding-bottom: 10px;'>Relógio de Permanência</h3>", unsafe_allow_html=True)
            st.markdown(f"""
                <div style="text-align: center; margin-top: 20px;">
                    <p style="font-size: 18px; margin: 0; font-weight: bold; color: #666;">Material mais Antigo na Qualidade</p>
                    <p style="font-size: 16px; margin: 0;">Esquecido há {antigo_q_dias} dias</p>
                    <p style="font-size: 22px; font-weight: bold; color: #9c27b0;">{antigo_q_data}</p>
                </div>
                <div style="text-align: center; margin-top: 40px;">
                    <p style="font-size: 18px; margin: 0; font-weight: bold; color: #666;">Material mais Antigo no Recebimento</p>
                    <p style="font-size: 16px; margin: 0;">Esquecido há {antigo_r_dias} dias</p>
                    <p style="font-size: 22px; font-weight: bold; color: #00579D;">{antigo_r_data}</p>
                </div>
            """, unsafe_allow_html=True)

        with col_dir:
            st.markdown("<h3 style='text-align: center; border-bottom: 1px solid #ccc; padding-bottom: 10px;'>Doca (Recebimento)</h3>", unsafe_allow_html=True)
            g3, g4 = st.columns(2)
            with g3: st.plotly_chart(criar_gauge(prioridade_r, total_r, "Atrasados"), use_container_width=True)
            with g4: st.plotly_chart(criar_gauge(total_r, len(df_dashboard), "Total Livre"), use_container_width=True)
            st.markdown(f"""
                <div style="display: flex; gap: 10px; text-align: center; font-size: 24px; font-weight: bold; color: white;">
                    <div style="flex: 1; background-color: #4CAF50; padding: 15px; border-radius: 5px;">{total_r - prioridade_r}</div>
                    <div style="flex: 1; background-color: #00579D; padding: 15px; border-radius: 5px;">{total_r}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        
        # --- TABELAS TOP 10 EM ATRASO ---
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("#### 🔴 Top 10 Itens Esquecidos (Laboratório Qualidade)")
            if not df_qualidade.empty:
                top_q = df_qualidade[['dias_parado', 'material', 'descricao', 'nfe', 'fornecedor']].sort_values(by='dias_parado', ascending=False).head(10)
                st.dataframe(top_q, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum item na qualidade.")

        with col_t2:
            st.markdown("#### 🟡 Top 10 Itens Esquecidos (Recebimento Livre)")
            if not df_recebimento.empty:
                top_r = df_recebimento[['dias_parado', 'material', 'descricao', 'nfe', 'fornecedor']].sort_values(by='dias_parado', ascending=False).head(10)
                st.dataframe(top_r, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum item em atraso no recebimento.")

# ------------------------------------------
# ABA 1: ENVIAR (RECEBIMENTO FÍSICO)
# ------------------------------------------
with aba_recebimento:
    if st.session_state["pdf_pronto"] is not None:
        st.markdown("<div class='css-1r6slb0' style='text-align:center;'>", unsafe_allow_html=True)
        st.success(f"🎉 Carga enviada com sucesso! (Remessa: {st.session_state['pdf_pronto']['lote']})")
        st.download_button(
            label="🖨️ Baixar Guia de Remessa (PDF)",
            data=st.session_state["pdf_pronto"]["bytes"], file_name=f"Guia_Transferencia_{st.session_state['pdf_pronto']['lote']}.pdf",
            mime="application/pdf", type="primary", use_container_width=True
        )
        st.divider()
        if st.button("🔄 Voltar para a Tela de Envio", use_container_width=True):
            st.session_state["pdf_pronto"] = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
    else:
        if st.session_state["perfil_atual"] == "Almoxarifado":
            st.error("⛔ Acesso Restrito: O seu perfil é de **Almoxarifado**.")
        else:
            with st.container():
                st.markdown("<div class='css-1r6slb0'>", unsafe_allow_html=True)
                col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
                
                with col_b1.expander("📸 Abrir Leitor de Etiqueta (Câmera)"):
                    foto_camera = st.camera_input("Aponte para o código Data Matrix")
                    if foto_camera and leitor_ativo:
                        if st.session_state.get("ultima_foto_processada") != foto_camera.getvalue():
                            st.session_state["ultima_foto_processada"] = foto_camera.getvalue()
                            with st.spinner("Analisando..."):
                                try:
                                    img = Image.open(foto_camera)
                                    codigos = decode_dm(img)
                                    if codigos:
                                        texto_bruto = codigos[0].data.decode('utf-8')
                                        mat_limpo = texto_bruto.split("240")[-1].strip() if "240" in texto_bruto and len(texto_bruto) > 15 else texto_bruto
                                        ids_achados = df_bruto[df_bruto['material'] == mat_limpo]['id'].tolist()
                                        for idx in ids_achados:
                                            if idx not in st.session_state["carrinho_expedicao"]: st.session_state["carrinho_expedicao"].append(idx)
                                        st.session_state["busca_global"] = mat_limpo
                                        st.rerun() 
                                    else: st.error("❌ Etiqueta não reconhecida.")
                                except Exception as e: st.error(f"⚠️ Erro ao decodificar a imagem: {e}")
                    elif foto_camera and not leitor_ativo: st.error("⚠️ Bibliotecas de câmera faltando.")
                
                st.session_state["busca_global"] = col_b2.text_input("🔎 Pesquisa Manual (Laser/Teclado):", value=st.session_state["busca_global"], placeholder="Ex: NF-1234...")
                filtro_urgencia = col_b3.selectbox("Focar Operação:", ["Mostrar Todos", "🔴 URGENTE (>7d)", "🟡 ATENÇÃO (>3d)", "🟣 BLOQ. QUALIDADE"])
                st.markdown("</div>", unsafe_allow_html=True)

            if df_bruto.empty:
                st.success("Tudo limpo! Nenhuma carga no Recebimento para enviar.")
            else:
                df_tela = df_bruto.copy()
                df_tela['status_envio'] = df_tela['status_envio'].replace({'Pendente': '🟢 Aguardando Envio no Recebimento', 'Em Trânsito Interno': '🚚 Aguardando confirmação do Almox'})
                if filtro_urgencia != "Mostrar Todos": df_tela = df_tela[df_tela['SLA'] == filtro_urgencia]
                
                if st.session_state["busca_global"]:
                    busca_txt = st.session_state["busca_global"]
                    if len(busca_txt) > 15 and " " in busca_txt:
                        mat_extraido = busca_txt.split("240")[-1].strip() if "240" in busca_txt else busca_txt
                        df_tela = df_tela[df_tela['material'] == mat_extraido]
                    else:
                        mask = df_tela.astype(str).apply(lambda x: x.str.contains(busca_txt, case=False, na=False)).any(axis=1)
                        df_tela = df_tela[mask]

                if df_tela.empty: st.warning("Nenhum material encontrado.")
                else:
                    colunas_visiveis = ['id', 'status_envio', 'SLA', 'material', 'descricao', 'estoque', 'umb', 'posicao_dep', 'nfe', 'fornecedor']
                    if 'umb' not in df_tela.columns: df_tela['umb'] = ""
                    df_tela = df_tela[colunas_visiveis]
                    
                    if st.session_state["perfil_atual"] == "Almoxarifado":
                        st.info("👀 Modo Leitura.")
                        st.dataframe(df_tela, hide_index=True, use_container_width=True, height=400, column_config=config_colunas_gerais)
                    else:
                        area_botoes_expedicao = st.container()
                        df_tela.insert(0, "Selecionar", df_tela['id'].isin(st.session_state["carrinho_expedicao"]))
                        colunas_bloqueadas = [col for col in df_tela.columns if col != "Selecionar"]
                        
                        df_editado = st.data_editor(
                            df_tela, hide_index=True, use_container_width=True, height=400,
                            disabled=colunas_bloqueadas, column_config=config_colunas_gerais
                        )
                        
                        for index, row in df_editado.iterrows():
                            id_linha = row['id']
                            if row['Selecionar'] and id_linha not in st.session_state["carrinho_expedicao"]: st.session_state["carrinho_expedicao"].append(id_linha)
                            elif not row['Selecionar'] and id_linha in st.session_state["carrinho_expedicao"]: st.session_state["carrinho_expedicao"].remove(id_linha)

                        with area_botoes_expedicao:
                            qtd_carrinho = len(st.session_state["carrinho_expedicao"])
                            st.markdown("#### 👷 Fechamento de Remessa")
                            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1.5, 1.5, 1.5])
                            
                            with col_btn1: st.info(f"🛒 **{qtd_carrinho}** itens selecionados.")
                            with col_btn2:
                                df_operadores = pd.read_sql_query("SELECT nome FROM operadores_fisicos ORDER BY nome", engine)
                                lista_op = ["-- Selecione o Identificador --"] + df_operadores['nome'].tolist()
                                operador_selecionado = st.selectbox("1. Quem identificou?", lista_op)
                            with col_btn3:
                                df_depositos = pd.read_sql_query("SELECT nome_deposito FROM depositos_destino ORDER BY nome_deposito", engine)
                                lista_dep = ["-- Selecione o Destino --"] + df_depositos['nome_deposito'].tolist()
                                deposito_selecionado = st.selectbox("2. Para onde vai?", lista_dep)
                            with col_btn4:
                                st.write("") 
                                if st.button(f"🖨️ Gerar Lote e Enviar (PDF)", type="primary", use_container_width=True):
                                    itens_selecionados_df = df_bruto[df_bruto['id'].isin(st.session_state["carrinho_expedicao"])]
                                    itens_ja_despachados = itens_selecionados_df[itens_selecionados_df['status_envio'] == 'Em Trânsito Interno']
                                    
                                    if qtd_carrinho == 0: st.error("Carrinho vazio!")
                                    elif not itens_ja_despachados.empty: st.error("⚠️ Você selecionou um item que JÁ FOI ENVIADO!")
                                    elif operador_selecionado == "-- Selecione o Identificador --": st.error("Selecione o Identificador!")
                                    elif deposito_selecionado == "-- Selecione o Destino --": st.error("Selecione o Destino!")
                                    else:
                                        novo_lote = gerar_proximo_lote()
                                        df_pdf = df_bruto[df_bruto['id'].isin(st.session_state["carrinho_expedicao"])]
                                        agora_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        
                                        with engine.connect() as conn:
                                            for id_peca in st.session_state["carrinho_expedicao"]:
                                                conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Em Trânsito Interno', lote_envio = :lote, operador_separacao = :op, deposito_destino = :dep, data_hora_despacho = :dh WHERE id = :id_peca"), 
                                                             {"lote": novo_lote, "op": operador_selecionado, "dep": deposito_selecionado, "dh": agora_str, "id_peca": int(id_peca)})
                                            
                                            conn.execute(text("INSERT INTO fila_emails (lote_envio, tipo_evento, destino, operador, data_criacao) VALUES (:l, 'DESPACHO', :d, :o, :dt)"),
                                                         {"l": novo_lote, "d": deposito_selecionado, "o": operador_selecionado, "dt": agora_str})
                                            conn.commit()
                                        
                                        pdf_bytes = gerar_pdf_remessa_sap(novo_lote, "Recebimento Físico", deposito_selecionado, operador_selecionado, df_pdf)
                                        st.session_state["pdf_pronto"] = {"lote": novo_lote, "bytes": pdf_bytes}
                                        st.session_state["carrinho_expedicao"] = []
                                        st.session_state["busca_global"] = ""
                                        st.rerun()
                            st.divider()

# ------------------------------------------
# ABA 2: ACONDICIONAR (ALMOXARIFADO)
# ------------------------------------------
with aba_almoxarifado:
    if st.session_state["perfil_atual"] == "Recebimento":
        st.error("⛔ Acesso Restrito: O seu perfil é do **Recebimento Físico**.")
    else:
        query_rec = "SELECT id, lote_envio, operador_separacao, deposito_destino, data_hora_despacho, material, descricao, estoque, umb, posicao_dep, nfe, fornecedor, status_envio FROM expedicao_completa WHERE status_envio = 'Em Trânsito Interno'"
        df_rec = pd.read_sql_query(query_rec, engine)
        
        df_rec = calcular_sla_acondicionamento(df_rec)
        
        if df_rec.empty: st.success("Nenhuma carga aguardando confirmação no momento.")
        else:
            df_rec['status_envio'] = df_rec['status_envio'].replace({'Em Trânsito Interno': '🚚 Aguardando confirmação do Almox'})
            
            lista_lotes = df_rec['lote_envio'].dropna().unique().tolist()
            lista_lotes.sort(reverse=True)
            
            opcoes_menu = ["Mostrar Todas as Remessas"] + lista_lotes
            lote_selecionado = st.selectbox("Filtre por Número da Remessa:", opcoes_menu)
            
            area_botoes_recebimento = st.container()
            
            if lote_selecionado == "Mostrar Todas as Remessas": df_lote = df_rec.copy()
            else: df_lote = df_rec[df_rec['lote_envio'] == lote_selecionado].copy()
            
            df_lote.insert(0, "Acondicionado", False)
            colunas_bloqueadas_rec = [col for col in df_lote.columns if col != "Acondicionado"]
            
            df_editado_rec = st.data_editor(
                df_lote, hide_index=True, use_container_width=True, height=400, 
                disabled=colunas_bloqueadas_rec, column_config=config_colunas_gerais
            )
            selecionados_rec = df_editado_rec[df_editado_rec["Acondicionado"] == True]
            
            with area_botoes_recebimento:
                st.divider()
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    texto_btn_tudo = f"✅ Confirmar Lote inteiro ({len(df_lote)} peças)" if lote_selecionado == "Mostrar Todas as Remessas" else f"✅ Confirmar Lote {lote_selecionado} INTEIRO"
                    if st.button(texto_btn_tudo, type="primary", use_container_width=True):
                        agora_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        with engine.connect() as conn:
                            if lote_selecionado == "Mostrar Todas as Remessas":
                                conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Acondicionado no Almoxarifado' WHERE status_envio = 'Em Trânsito Interno'"))
                            else:
                                conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Acondicionado no Almoxarifado' WHERE lote_envio = :lote"), {"lote": lote_selecionado})
                                destino = df_lote['deposito_destino'].iloc[0]
                                operador = df_lote['operador_separacao'].iloc[0]
                                conn.execute(text("INSERT INTO fila_emails (lote_envio, tipo_evento, destino, operador, data_criacao) VALUES (:l, 'ACONDICIONAMENTO', :d, :o, :dt)"),
                                             {"l": lote_selecionado, "d": destino, "o": operador, "dt": agora_str})
                            conn.commit()
                        st.success("Lote Confirmado com sucesso!")
                        time.sleep(1.5)
                        st.rerun()
                        
                with col_r2:
                    if st.button("✅ Confirmar APENAS os itens marcados na tabela", use_container_width=True):
                        if selecionados_rec.empty: st.error("Marque as caixinhas dos materiais!")
                        else:
                            with engine.connect() as conn:
                                for id_peca in selecionados_rec["id"]:
                                    conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Acondicionado no Almoxarifado' WHERE id = :id_peca"), {"id_peca": int(id_peca)})
                                conn.commit()
                            st.success(f"{len(selecionados_rec)} peças confirmadas!")
                            time.sleep(1.5)
                            st.rerun()
                st.write("") 

# ------------------------------------------
# ABA 3: HISTÓRICO GERAL
# ------------------------------------------
with aba_historico:
    st.markdown("### 💾 Base de Dados Histórica")
    query_hist = "SELECT lote_envio, operador_separacao, deposito_destino, data_hora_despacho, id, material, descricao, estoque, umb, nfe, status_envio FROM expedicao_completa WHERE status_envio != 'Pendente' ORDER BY id DESC"
    df_hist = pd.read_sql_query(query_hist, engine)
    
    if df_hist.empty: st.info("Nenhum material movimentado.")
    else: 
        df_hist['status_envio'] = df_hist['status_envio'].replace({
            'Em Trânsito Interno': '🚚 Aguardando confirmação do Almox',
            'Acondicionado no Almoxarifado': '✅ Recebido e Guardado',
            'Baixado Direto no SAP': '📉 Baixado Direto no SAP'
        })
        
        lista_lotes_hist = df_hist['lote_envio'].dropna().unique().tolist()
        lista_lotes_hist.sort(reverse=True)
        col_h1, col_h2 = st.columns([3, 1])
        lote_hist_selecionado = col_h1.selectbox("Filtrar Histórico por Remessa:", ["Mostrar Histórico Completo"] + lista_lotes_hist)
        
        if lote_hist_selecionado == "Mostrar Histórico Completo":
            st.dataframe(df_hist, hide_index=True, use_container_width=True, height=400, column_config=config_colunas_gerais)
        else:
            df_hist_lote = df_hist[df_hist['lote_envio'] == lote_hist_selecionado].copy()
            st.dataframe(df_hist_lote, hide_index=True, use_container_width=True, height=400, column_config=config_colunas_gerais)
            with col_h2:
                st.write(""); st.write("")
                try:
                    op_hist = df_hist_lote['operador_separacao'].iloc[0]
                    dest_hist = df_hist_lote['deposito_destino'].iloc[0]
                    pdf_bytes_hist = gerar_pdf_remessa_sap(lote_hist_selecionado, "Recebimento Físico", dest_hist, op_hist, df_hist_lote)
                    st.download_button(label="🖨️ Re-Imprimir Guia (PDF)", data=pdf_bytes_hist, file_name=f"Guia_Reimpressa_{lote_hist_selecionado}.pdf", mime="application/pdf", use_container_width=True)
                except: pass

# ------------------------------------------
# 🚀 ABA 4: OCORRÊNCIAS E CHAT LOGÍSTICO
# ------------------------------------------
with aba_chat:
    st.markdown("### 💬 Mural de Ocorrências Logísticas")
    st.write("Relate problemas físicos (Avarias, Falta de Peça) vinculados a uma Remessa específica.")
    
    df_lotes_chat = pd.read_sql_query("SELECT DISTINCT lote_envio FROM expedicao_completa WHERE lote_envio IS NOT NULL ORDER BY lote_envio DESC", engine)
    lista_lotes_chat = df_lotes_chat['lote_envio'].tolist()
    
    lote_ocorr = st.selectbox("Selecione a Remessa para abrir o Chat:", ["-- Selecione a Remessa --"] + lista_lotes_chat)
    st.divider()
    
    if lote_ocorr != "-- Selecione a Remessa --":
        df_msgs = pd.read_sql_query(f"SELECT usuario, perfil, data_hora, mensagem FROM ocorrencias_chat WHERE lote_ref = '{lote_ocorr}' ORDER BY id ASC", engine)
        
        st.markdown(f"#### 📜 Registro de Eventos da Remessa: {lote_ocorr}")
        
        if df_msgs.empty:
            st.info("Nenhuma ocorrência registrada para esta remessa ainda.")
        else:
            for _, msg in df_msgs.iterrows():
                avatar_chat = "👷‍♂️" if msg['perfil'] == "Recebimento" else "👨‍💼"
                with st.chat_message(name=msg['usuario'], avatar=avatar_chat):
                    st.markdown(f"**{msg['usuario'].upper()}** ({msg['data_hora']}):")
                    st.write(msg['mensagem'])
        
        st.write("")
        nova_msg = st.chat_input("Digite uma ocorrência (Ex: Caixa rasgada, Peça faltando)...")
        if nova_msg:
            agora_chat = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            with engine.connect() as conn:
                conn.execute(text("INSERT INTO ocorrencias_chat (lote_ref, usuario, perfil, data_hora, mensagem) VALUES (:l, :u, :p, :d, :m)"),
                             {"l": lote_ocorr, "u": st.session_state["usuario_atual"], "p": st.session_state["perfil_atual"], "d": agora_chat, "m": nova_msg})
                conn.commit()
            st.rerun()

# ------------------------------------------
# ABA 5: ADMINISTRAÇÃO 
# ------------------------------------------
with aba_admin:
    if st.session_state["perfil_atual"] != "Admin":
        st.error("⛔ Acesso Restrito aos Administradores.")
    else:
        st.markdown("### ⚙️ Painel de Controle Avançado")
        tab_usuarios, tab_operadores, tab_depositos, tab_sistema = st.tabs(["💻 Usuários do Sistema", "👷 Identificadores (Equipe)", "🏭 Depósitos Destino", "⚠️ Zona de Risco"])
        
        with tab_usuarios:
            with st.form("form_novo_usuario"):
                col_u1, col_u2 = st.columns(2)
                novo_usu = col_u1.text_input("Login do Usuário")
                novo_perfil = col_u2.selectbox("Perfil de Acesso", ["Almoxarifado", "Recebimento", "Admin"])
                if st.form_submit_button("Criar Usuário"):
                    if novo_usu:
                        try:
                            with engine.connect() as conn:
                                conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES (:u, '1234', :p)"), {"u": novo_usu.lower(), "p": novo_perfil})
                                conn.commit()
                            st.rerun()
                        except: st.error("Erro: Usuário já existe!")
            
            df_usuarios = pd.read_sql_query("SELECT usuario, perfil FROM usuarios", engine)
            st.dataframe(df_usuarios, hide_index=True, use_container_width=True)
            usu_deletar = st.selectbox("Selecione um usuário para remover:", [""] + df_usuarios['usuario'].tolist())
            if st.button("🗑️ Excluir Usuário") and usu_deletar:
                with engine.connect() as conn:
                    conn.execute(text("DELETE FROM usuarios WHERE usuario = :u"), {"u": usu_deletar})
                    conn.commit()
                st.rerun()

        with tab_operadores:
            with st.form("form_op_fisico"):
                novo_op = st.text_input("Nome Completo do Identificador:")
                if st.form_submit_button("Cadastrar Identificador"):
                    if novo_op:
                        try:
                            with engine.connect() as conn:
                                conn.execute(text("INSERT INTO operadores_fisicos (nome) VALUES (:n)"), {"n": novo_op.strip().upper()})
                                conn.commit()
                            st.rerun()
                        except: st.error("Este nome já existe!")
            
            df_ops = pd.read_sql_query("SELECT * FROM operadores_fisicos ORDER BY nome", engine)
            if not df_ops.empty:
                st.dataframe(df_ops, hide_index=True, use_container_width=True)
                op_deletar = st.selectbox("Remover Identificador:", [""] + df_ops['nome'].tolist())
                if st.button("🗑️ Excluir Identificador") and op_deletar:
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM operadores_fisicos WHERE nome = :n"), {"n": op_deletar})
                        conn.commit()
                    st.rerun()

        with tab_depositos:
            with st.form("form_novo_deposito"):
                col_d1, col_d2, col_d3 = st.columns(3)
                novo_deposito = col_d1.text_input("Nome do Setor")
                novo_responsavel = col_d2.text_input("E-mail do Líder (Responsável)")
                novo_cc = col_d3.text_input("E-mails em Cópia (Separados por ';')")
                if st.form_submit_button("Salvar Setor"):
                    if novo_deposito and novo_responsavel:
                        try:
                            with engine.connect() as conn:
                                conn.execute(text("INSERT INTO depositos_destino (nome_deposito, responsavel, emails_cc) VALUES (:n, :r, :c)"), 
                                             {"n": novo_deposito, "r": novo_responsavel, "c": novo_cc})
                                conn.commit()
                            st.rerun()
                        except: st.error("Este Setor já existe.")
                    else: st.warning("Preencha o Nome e o Responsável!")
            
            df_depositos = pd.read_sql_query("SELECT * FROM depositos_destino ORDER BY id", engine)
            if not df_depositos.empty:
                st.dataframe(df_depositos, hide_index=True, use_container_width=True)
                dep_deletar = st.selectbox("Remover Setor:", [""] + df_depositos['nome_deposito'].tolist())
                if st.button("🗑️ Excluir Setor") and dep_deletar:
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM depositos_destino WHERE nome_deposito = :d"), {"d": dep_deletar})
                        conn.commit()
                    st.rerun()

        with tab_sistema:
            if st.button("🗑️ LIMPAR APENAS ITENS PENDENTES (Limpar Duplicidades de Teste)"):
                with engine.connect() as conn:
                    conn.execute(text("DELETE FROM expedicao_completa WHERE status_envio = 'Pendente'"))
                    conn.commit()
                st.session_state["carrinho_expedicao"] = []
                st.rerun()
