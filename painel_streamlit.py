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
        .kpi-card { background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0px 4px 10px rgba(0,87,157,0.1); }
        .kpi-valor { font-size: 36px; font-weight: bold; margin-bottom: 5px; }
        .kpi-titulo { font-size: 14px; color: #666; font-weight: bold; text-transform: uppercase; }
        .kpi-azul .kpi-valor { color: #00579D; } .kpi-verde .kpi-valor { color: #2e7d32; }
        .kpi-amarelo .kpi-valor { color: #f57c00; } .kpi-vermelho .kpi-valor { color: #d32f2f; }
        .kpi-roxo .kpi-valor { color: #9c27b0; }
        .kpi-vermelho { border-bottom: 4px solid #d32f2f; } .kpi-roxo { border-bottom: 4px solid #9c27b0; }
        .css-1r6slb0, .css-1n76uvr { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0px 4px 15px rgba(0,87,157,0.1); border-top: 4px solid #00579D; }
    </style>
""", unsafe_allow_html=True)

LOGO_WEG = "https://logospng.org/download/weg/logo-weg-2048.png"

# ==========================================
# 1. CONEXÃO E ATUALIZAÇÃO DO BANCO
# ==========================================
DATABASE_URL = st.secrets["banco_dados"]["url"]
engine = create_engine(DATABASE_URL)

if "db_verificado" not in st.session_state:
    with engine.connect() as conn:
        # A TABELA AGORA JÁ NASCE COM TODAS AS COLUNAS OFICIAIS
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS expedicao_completa (
                id SERIAL PRIMARY KEY, item TEXT, material TEXT, descricao TEXT, 
                centro_dep TEXT, tipo_estoque TEXT, lote TEXT, tp TEXT, 
                posicao_dep TEXT, estoque REAL, data_em TEXT, data_necess TEXT, 
                nfe TEXT, fornecedor TEXT, status_envio TEXT DEFAULT 'Pendente',
                lote_envio TEXT, operador_separacao TEXT
            )
        '''))
        conn.execute(text("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS depositos_destino (id SERIAL PRIMARY KEY, nome_deposito TEXT UNIQUE, responsavel TEXT)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS operadores_fisicos (id SERIAL PRIMARY KEY, nome TEXT UNIQUE)"))
        conn.commit()

        if conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar() == 0:
            conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('roberto', 'weg2026', 'Admin')"))
            conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('almox', '1234', 'Almoxarifado')"))
            conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('doca1', '1234', 'Recebimento')"))
            conn.commit()
            
        if conn.execute(text("SELECT COUNT(*) FROM operadores_fisicos")).scalar() == 0:
            conn.execute(text("INSERT INTO operadores_fisicos (nome) VALUES ('João Silva (Exemplo)')"))
            conn.commit()
            
    st.session_state["db_verificado"] = True

# ==========================================
# 2. LOGIN SEGURO E MEMÓRIA
# ==========================================
if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["usuario_atual"] = ""
    st.session_state["perfil_atual"] = ""
    st.session_state["precisa_mudar_senha"] = False 

if "carrinho_expedicao" not in st.session_state:
    st.session_state["carrinho_expedicao"] = []

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

# ==========================================
# 🚨 TELA DE TROCA DE SENHA OBRIGATÓRIA 
# ==========================================
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
                elif nova_senha == "1234": st.error("Sua nova senha não pode ser 1234.")
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
# 3. MENU LATERAL E ROBÔ
# ==========================================
st.sidebar.image(LOGO_WEG, width=100)
st.sidebar.markdown(f"👨‍💻 Sistema: **{st.session_state['usuario_atual'].upper()}**")
st.sidebar.markdown(f"🛡️ Nível: **{st.session_state['perfil_atual']}**")

if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state.clear()
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
                    df_pb['estoque'] = df_robo.get('Quantidade', df_robo.get('Estoque', 0))
                    df_pb['estoque'] = df_pb['estoque'].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    df_pb['estoque'] = pd.to_numeric(df_pb['estoque'], errors='coerce').fillna(0.0)
                    df_pb['data_em'] = df_robo.get('Data_Entrada', df_robo.get('Data EM', ''))
                    df_pb['data_necess'] = df_robo.get('Data_Necess', df_robo.get('Data Necess.', ''))
                    df_pb['fornecedor'] = df_robo.get('Fornecedor', '')

                    df_pb['chave_comparacao'] = df_pb['material'] + "|" + df_pb['nfe'] + "|" + df_pb['posicao_dep']
                    
                    query_banco = "SELECT id, status_envio, COALESCE(material, '') || '|' || COALESCE(nfe, '') || '|' || COALESCE(posicao_dep, '') as chave_banco FROM expedicao_completa"
                    df_banco = pd.read_sql_query(query_banco, engine)
                    
                    chaves_no_banco = set(df_banco['chave_banco'])
                    chaves_pendentes_banco = set(df_banco[df_banco['status_envio'] == 'Pendente']['chave_banco'])
                    chaves_do_sap = set(df_pb['chave_comparacao'])

                    df_inserir = df_pb[~df_pb['chave_comparacao'].isin(chaves_no_banco)].copy()
                    df_inserir = df_inserir.drop(columns=['chave_comparacao'])
                    chaves_sumiram = chaves_pendentes_banco - chaves_do_sap

                    if not df_inserir.empty:
                        df_inserir.to_sql(name='expedicao_completa', con=engine, if_exists='append', index=False)
                    
                    if chaves_sumiram:
                        with engine.connect() as conn:
                            for chave in chaves_sumiram:
                                conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Baixado Direto no SAP' WHERE status_envio = 'Pendente' AND COALESCE(material, '') || '|' || COALESCE(nfe, '') || '|' || COALESCE(posicao_dep, '') = :c"), {"c": chave})
                            conn.commit()

                    st.sidebar.success(f"✅ Sincronizado! \n{len(df_inserir)} novos.\n{len(chaves_sumiram)} baixados.")
                    time.sleep(3)
                    st.rerun()

# ==========================================
# 4. FUNÇÕES DE SLA E LOTES
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
    return df.drop(columns=['data_real', 'dias_parado'])

def gerar_proximo_lote():
    with engine.connect() as conn:
        ultimo_lote = conn.execute(text("SELECT MAX(lote_envio) FROM expedicao_completa WHERE lote_envio IS NOT NULL")).scalar()
        if not ultimo_lote: return "00000000001"
        else: return str(int(ultimo_lote) + 1).zfill(11)

config_colunas_gerais = {
    "Selecionar": st.column_config.CheckboxColumn("☑️", width="small"),
    "Acondicionado": st.column_config.CheckboxColumn("☑️ Recebido?", width="small"),
    "lote_envio": st.column_config.TextColumn("Lote", width="small"),
    "operador_separacao": st.column_config.TextColumn("Separador", width="medium"),
    "SLA": st.column_config.TextColumn("Status SLA", width="medium"),
    "material": st.column_config.TextColumn("Material", width="small"),
    "descricao": st.column_config.TextColumn("Descrição", width="large"), 
    "estoque": st.column_config.NumberColumn("Qtd", width="small"),              
    "posicao_dep": st.column_config.TextColumn("Posição", width="small"),
    "nfe": st.column_config.TextColumn("NF", width="medium"),
    "fornecedor": st.column_config.TextColumn("Fornecedor", width="medium")
}

# ==========================================
# 5. TELA PRINCIPAL (DASHBOARD + ABAS)
# ==========================================
col_topo1, col_topo2 = st.columns([3, 1])
with col_topo1: st.markdown("<h1>📊 Hub Inbound (Entrada de Material)</h1>", unsafe_allow_html=True)

query_bruta = "SELECT * FROM expedicao_completa WHERE status_envio = 'Pendente'"
df_bruto = pd.read_sql_query(query_bruta, engine)
df_bruto = calcular_sla_pandas(df_bruto)

# DASHBOARD DE TOPO
if not df_bruto.empty:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(f"<div class='kpi-card kpi-azul'><div class='kpi-titulo'>Total na Doca</div><div class='kpi-valor'>{len(df_bruto)}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card kpi-verde'><div class='kpi-titulo'>Prazo (≤3d)</div><div class='kpi-valor'>{len(df_bruto[df_bruto['SLA'] == '🟢 NO PRAZO'])}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-card kpi-amarelo'><div class='kpi-titulo'>Atenção (>3d)</div><div class='kpi-valor'>{len(df_bruto[df_bruto['SLA'] == '🟡 ATENÇÃO (>3d)'])}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-card kpi-vermelho'><div class='kpi-titulo'>Crítico (>7d)</div><div class='kpi-valor'>{len(df_bruto[df_bruto['SLA'] == '🔴 URGENTE (>7d)'])}</div></div>", unsafe_allow_html=True)
    c5.markdown(f"<div class='kpi-card kpi-roxo'><div class='kpi-titulo'>Qualidade (CQ)</div><div class='kpi-valor'>{len(df_bruto[df_bruto['SLA'] == '🟣 BLOQ. QUALIDADE'])}</div></div>", unsafe_allow_html=True)
    st.write("")

aba_recebimento, aba_almoxarifado, aba_historico, aba_admin = st.tabs([
    "📋 1. DESPACHAR (Doca de Recebimento)", 
    "📦 2. ACONDICIONAR (Almoxarifado)", 
    "💾 3. HISTÓRICO GERAL", 
    "⚙️ 4. ADMINISTRAÇÃO"
])

# ------------------------------------------
# ABA 1: DESPACHO PELA DOCA DE RECEBIMENTO
# ------------------------------------------
with aba_recebimento:
    if st.session_state["perfil_atual"] == "Almoxarifado":
        st.error("⛔ Acesso Restrito: O seu perfil é de **Almoxarifado**. Sua função é receber as cargas internas. Vá para a aba 2.")
    else:
        with st.container():
            st.markdown("<div class='css-1r6slb0'>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns([3, 1])
            busca_global = col_b1.text_input("🔎 Pesquise o material que chegou (NF, Material, Fornecedor):", placeholder="Ex: NF-1234...")
            filtro_urgencia = col_b2.selectbox("Focar Operação:", ["Mostrar Todos", "🔴 URGENTE (>7d)", "🟡 ATENÇÃO (>3d)", "🟣 BLOQ. QUALIDADE"])
            st.markdown("</div>", unsafe_allow_html=True)
        st.write("")

        if df_bruto.empty:
            st.success("Tudo limpo! Nenhuma carga na Doca para despachar.")
        else:
            df_tela = df_bruto.copy()
            if filtro_urgencia != "Mostrar Todos": df_tela = df_tela[df_tela['SLA'] == filtro_urgencia]
            if busca_global:
                mask = df_tela.astype(str).apply(lambda x: x.str.contains(busca_global, case=False, na=False)).any(axis=1)
                df_tela = df_tela[mask]

            if df_tela.empty:
                st.warning("Nenhum material encontrado com os filtros atuais.")
            else:
                colunas_visiveis = ['id', 'SLA', 'material', 'descricao', 'estoque', 'posicao_dep', 'nfe', 'fornecedor']
                df_tela = df_tela[colunas_visiveis]
                
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

                qtd_carrinho = len(st.session_state["carrinho_expedicao"])
                
                st.divider()
                st.markdown("#### 👷 Fechamento do Lote e Rastreabilidade")
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                
                with col_btn1: 
                    st.info(f"🛒 Você selecionou **{qtd_carrinho}** itens para enviar.")
                    
                with col_btn2:
                    df_operadores = pd.read_sql_query("SELECT nome FROM operadores_fisicos ORDER BY nome", engine)
                    lista_op = ["-- Selecione o Operador Físico --"] + df_operadores['nome'].tolist()
                    operador_selecionado = st.selectbox("Quem separou/identificou esta carga fisicamente?", lista_op)
                    
                with col_btn3:
                    st.write("") 
                    if st.button("🚚 Gerar Lote e Despachar", type="primary", use_container_width=True):
                        if qtd_carrinho == 0: 
                            st.error("Carrinho vazio!")
                        elif operador_selecionado == "-- Selecione o Operador Físico --":
                            st.error("⚠️ Obrigatório selecionar o Operador Físico para rastreabilidade!")
                        else:
                            novo_lote = gerar_proximo_lote()
                            with engine.connect() as conn:
                                for id_peca in st.session_state["carrinho_expedicao"]:
                                    conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Em Trânsito Interno', lote_envio = :lote, operador_separacao = :op WHERE id = :id_peca"), 
                                                 {"lote": novo_lote, "op": operador_selecionado, "id_peca": int(id_peca)})
                                conn.commit()
                            st.session_state["carrinho_expedicao"] = []
                            st.success(f"✅ Carga Despachada! Lote de Envio Gerado: **{novo_lote}**")
                            time.sleep(2)
                            st.rerun()

# ------------------------------------------
# ABA 2: ACONDICIONAR (ALMOXARIFADO LENDO LOTES)
# ------------------------------------------
with aba_almoxarifado:
    if st.session_state["perfil_atual"] == "Recebimento":
        st.error("⛔ Acesso Restrito: O seu perfil é da **Doca**. Você não pode acondicionar materiais.")
    else:
        st.markdown("### 📦 Painel do Almoxarifado (Acondicionar Cargas)")
        
        query_rec = "SELECT id, lote_envio, operador_separacao, material, descricao, estoque, posicao_dep, nfe, fornecedor, status_envio FROM expedicao_completa WHERE status_envio = 'Em Trânsito Interno'"
        df_rec = pd.read_sql_query(query_rec, engine)
        
        if df_rec.empty: st.success("Nenhuma carga em trânsito internamente no momento.")
        else:
            lista_lotes = df_rec['lote_envio'].dropna().unique().tolist()
            lista_lotes.sort(reverse=True)
            
            lote_selecionado = st.selectbox("Lotes em Trânsito (Mais recentes primeiro):", ["Selecione um Lote..."] + lista_lotes)
            st.divider()

            if lote_selecionado != "Selecione um Lote...":
                df_lote = df_rec[df_rec['lote_envio'] == lote_selecionado].copy()
                st.markdown(f"**Itens dentro do Lote: {lote_selecionado}** (Total: {len(df_lote)} peças)")
                
                df_lote.insert(0, "Acondicionado", False)
                colunas_bloqueadas_rec = [col for col in df_lote.columns if col != "Acondicionado"]
                
                df_editado_rec = st.data_editor(
                    df_lote, hide_index=True, use_container_width=True, height=300, 
                    disabled=colunas_bloqueadas_rec, column_config=config_colunas_gerais
                )
                selecionados_rec = df_editado_rec[df_editado_rec["Acondicionado"] == True]
                
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    if st.button("✅ Acondicionar LOTE INTEIRO de uma vez", type="primary", use_container_width=True):
                        with engine.connect() as conn:
                            conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Acondicionado no Almoxarifado' WHERE lote_envio = :lote"), {"lote": lote_selecionado})
                            conn.commit()
                        st.success(f"Lote {lote_selecionado} inteiro recebido com sucesso!")
                        time.sleep(1.5)
                        st.rerun()
                with col_r2:
                    if st.button("✅ Acondicionar APENAS itens selecionados", use_container_width=True):
                        if selecionados_rec.empty: st.error("Marque as caixinhas dos materiais!")
                        else:
                            with engine.connect() as conn:
                                for id_peca in selecionados_rec["id"]:
                                    conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Acondicionado no Almoxarifado' WHERE id = :id_peca"), {"id_peca": int(id_peca)})
                                conn.commit()
                            st.success(f"{len(selecionados_rec)} peças acondicionadas!")
                            time.sleep(1.5)
                            st.rerun()

# ------------------------------------------
# ABA 3: HISTÓRICO GERAL
# ------------------------------------------
with aba_historico:
    st.markdown("### 💾 Base de Dados Histórica")
    query_hist = "SELECT lote_envio, operador_separacao, id, material, descricao, estoque, nfe, status_envio FROM expedicao_completa WHERE status_envio != 'Pendente' ORDER BY id DESC"
    df_hist = pd.read_sql_query(query_hist, engine)
    
    if df_hist.empty: st.info("Nenhum material movimentado.")
    else: st.dataframe(df_hist, hide_index=True, use_container_width=True, height=400, column_config=config_colunas_gerais)

# ------------------------------------------
# ABA 4: ADMINISTRAÇÃO 
# ------------------------------------------
with aba_admin:
    if st.session_state["perfil_atual"] != "Admin":
        st.error("⛔ Acesso Restrito aos Administradores.")
    else:
        st.markdown("### ⚙️ Painel de Controle Avançado")
        tab_usuarios, tab_operadores, tab_depositos, tab_sistema = st.tabs(["💻 Usuários do Sistema", "👷 Operadores Físicos", "🏭 Depósitos Destino", "⚠️ Zona de Risco"])
        
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
                            st.success(f"Usuário {novo_usu} cadastrado!")
                            time.sleep(1)
                            st.rerun()
                        except: st.error("Erro: Usuário já existe!")
            
            df_usuarios = pd.read_sql_query("SELECT usuario, perfil FROM usuarios", engine)
            st.dataframe(df_usuarios, hide_index=True, use_container_width=True)
            
            usu_deletar = st.selectbox("Selecione um usuário para remover:", [""] + df_usuarios['usuario'].tolist())
            if st.button("🗑️ Excluir Usuário") and usu_deletar:
                if usu_deletar == "roberto": st.error("Você não pode excluir a si mesmo!")
                else:
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM usuarios WHERE usuario = :u"), {"u": usu_deletar})
                        conn.commit()
                    st.rerun()

        with tab_operadores:
            st.info("Cadastre os nomes de quem bate caixa física. Eles aparecerão na lista de 'Quem Separou' na Doca.")
            with st.form("form_op_fisico"):
                novo_op = st.text_input("Nome Completo do Operador Físico:")
                if st.form_submit_button("Cadastrar Operador"):
                    if novo_op:
                        try:
                            with engine.connect() as conn:
                                conn.execute(text("INSERT INTO operadores_fisicos (nome) VALUES (:n)"), {"n": novo_op.strip().upper()})
                                conn.commit()
                            st.success(f"Operador {novo_op} cadastrado!")
                            time.sleep(1)
                            st.rerun()
                        except: st.error("Este nome já existe!")
            
            df_ops = pd.read_sql_query("SELECT * FROM operadores_fisicos ORDER BY nome", engine)
            if not df_ops.empty:
                st.dataframe(df_ops, hide_index=True, use_container_width=True)
                op_deletar = st.selectbox("Remover Operador:", [""] + df_ops['nome'].tolist())
                if st.button("🗑️ Excluir Operador") and op_deletar:
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM operadores_fisicos WHERE nome = :n"), {"n": op_deletar})
                        conn.commit()
                    st.rerun()

        with tab_depositos:
            with st.form("form_novo_deposito"):
                col_d1, col_d2 = st.columns(2)
                novo_deposito = col_d1.text_input("Nome do Setor")
                novo_responsavel = col_d2.text_input("Líder Responsável")
                if st.form_submit_button("Salvar Setor"):
                    if novo_deposito and novo_responsavel:
                        try:
                            with engine.connect() as conn:
                                conn.execute(text("INSERT INTO depositos_destino (nome_deposito, responsavel) VALUES (:n, :r)"), {"n": novo_deposito, "r": novo_responsavel})
                                conn.commit()
                            st.rerun()
                        except: st.error("Este Setor já existe.")
            
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
            st.warning("⚠️ Cuidado: Ações irreversiveis.")
            if st.button("🔄 Resetar Status de Todos os Materiais"):
                with engine.connect() as conn:
                    conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Pendente', lote_envio = NULL, operador_separacao = NULL"))
                    conn.commit()
                st.session_state["carrinho_expedicao"] = []
                st.rerun()
                
            if st.button("🗑️ ZERAR BANCO DE DADOS DE ESTOQUE"):
                with engine.connect() as conn:
                    conn.execute(text("DELETE FROM expedicao_completa"))
                    conn.commit()
                st.session_state["carrinho_expedicao"] = []
                st.rerun()
