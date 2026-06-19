import os
import time
import pandas as pd
import traceback
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from io import StringIO
from datetime import datetime

# ==========================================
# PASTA BLINDADA (No perfil do usuário)
# ==========================================
# Mudamos de "C:\temp\Agente902" para a pasta do AppData do usuario para evitar bloqueios de rede GPO.
USER_DIR = os.getenv('APPDATA') or os.path.expanduser("~")
PASTA_TRABALHO = os.path.join(USER_DIR, "Agente902_Local")

def preparar_ambiente():
    if not os.path.exists(PASTA_TRABALHO): 
        try: os.makedirs(PASTA_TRABALHO, exist_ok=True)
        except Exception as e: print(f"Erro ao criar pasta base: {e}")

def extrair_dados_almoxweb():
    preparar_ambiente()
    print(f"🚀 Ligando o Robô do AlmoxWeb Autônomo na pasta {PASTA_TRABALHO}...")
    
    arquivo_saida = os.path.join(PASTA_TRABALHO, "almoxweb_SAD320.xlsx")
    
    opcoes = webdriver.ChromeOptions()
    perfil_robo = os.path.join(PASTA_TRABALHO, "Chrome_Robo")
    if not os.path.exists(perfil_robo):
        try: os.makedirs(perfil_robo, exist_ok=True)
        except Exception as e: print(f"Erro ao criar perfil do Chrome: {e}")
        
    opcoes.add_argument(f"user-data-dir={perfil_robo}")
    opcoes.add_argument('--ignore-certificate-errors')
    
    # Executa invisivel (Headless) opcional: 
    # opcoes.add_argument('--headless')
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opcoes)
    except Exception as e:
        print("\n=== ERRO AO ABRIR O CHROME ===")
        print(traceback.format_exc())
        return None
    
    try:
        print("🌐 Acessando Portal AlmoxWeb...")
        driver.get("https://almoxweb.weg.net/")
        
        wait = WebDriverWait(driver, 20)
        
        print("🤖 Iniciando navegação automática...")

        # PASSO 0: Clicar no botão 'Warehouse' (Usando o DNA exato do HTML)
        try:
            print("👉 Clicando no botão 'Warehouse'...")
            btn_warehouse = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-info') and text()='Warehouse']")))
            btn_warehouse.click()
            time.sleep(1.5)
        except Exception as e:
            print(f"⚠️ Não achei o botão 'Warehouse'. Talvez a tela já tenha avançado? Tentando prosseguir...")
        
        # PASSO 1: Clicar no botão '320'
        try:
            print("👉 Procurando o botão do Depósito 320...")
            btn_320 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '320')]")))
            btn_320.click()
            time.sleep(1.5) 
        except Exception as e:
            print(f"⚠️ Não achei o botão '320'. Erro: {e}")

        # PASSO 2: Clicar no ícone de 'Lista'
        try:
            print("👉 Abrindo o menu de relatórios...")
            icone_lista = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='fa-2x svg-inline--fa fa-list-alt fa-w-16'] | //*[contains(@class, 'fa-list-alt')] | //a[.//svg[contains(@class, 'fa-list-alt')]]")))
            icone_lista.click()
            time.sleep(1.5)
        except Exception as e:
            print(f"⚠️ Não achei o ícone de lista. Erro: {e}")

        # PASSO 3: Clicar no botão 'Lista Geral'
        try:
            print("👉 Selecionando 'Lista Geral'...")
            btn_geral = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Lista Geral')]")))
            btn_geral.click()
            # 8 Segundos de respiro para o site mastigar 800 linhas do banco da WEG
            print("⏳ Aguardando a tabela (reportTable) ser desenhada pelo site...")
            time.sleep(8) 
        except Exception as e:
            print(f"⚠️ Não achei o botão 'Lista Geral'. Erro: {e}")

        # PASSO 4: Extrair a Tabela
        try:
            wait.until(EC.presence_of_element_located((By.ID, "reportTable")))
            print("👁️ Tabela Encontrada! O Robô foi mais rápido que um humano!")
            time.sleep(2) 
        except Exception as e_time:
            print("❌ Tempo esgotado! A tabela não apareceu na tela.")
            driver.quit()
            return None

        print("🧠 Lendo HTML da Tabela AlmoxWeb...")
        codigo_html = driver.page_source
        
        print("🔄 Convertendo e Limpando dados...")
        try:
            df_list = pd.read_html(StringIO(codigo_html), attrs={'id': 'reportTable'})
        except ValueError:
            df_list = pd.read_html(StringIO(codigo_html))
            
        if df_list:
            df = df_list[0] 
            
            try: df = df.iloc[1:].reset_index(drop=True)
            except: pass
            
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df = df.astype(str)
            df = df.replace(['nan', 'NaN', 'None', ''], '')
            
            novos_nomes = []
            for col in df.columns:
                nome_limpo = str(col).strip()
                if "Item" in nome_limpo: novos_nomes.append("Item")
                elif "Material" in nome_limpo: novos_nomes.append("Material")
                elif "Descrição" in nome_limpo or "Descri" in nome_limpo: novos_nomes.append("Descricao")
                elif "Centro" in nome_limpo: novos_nomes.append("Centro_Dep")
                elif "Lote" in nome_limpo: novos_nomes.append("Lote")
                elif "Posição" in nome_limpo or "Posi" in nome_limpo: novos_nomes.append("Posicao")
                elif "Estoque" in nome_limpo: novos_nomes.append("Quantidade")
                elif "Data EM" in nome_limpo: novos_nomes.append("Data_Entrada")
                elif "NFE" in nome_limpo or "NF" in nome_limpo: novos_nomes.append("NF")
                elif "Fornecedor" in nome_limpo: novos_nomes.append("Fornecedor")
                else: novos_nomes.append(nome_limpo)
            df.columns = novos_nomes
            
            df['Data_Real'] = pd.to_datetime(df['Data_Entrada'], format='%d.%m.%Y', errors='coerce')
            if df['Data_Real'].isnull().all():
                df['Data_Real'] = pd.to_datetime(df['Data_Entrada'], dayfirst=True, format='mixed', errors='coerce')
                
            hoje = pd.Timestamp(datetime.now().date())
            df['Dias_Retencao'] = (hoje - df['Data_Real']).dt.days
            df['Dias_Retencao'] = df['Dias_Retencao'].fillna(0).astype(int)
            
            df = df.sort_values(by='Dias_Retencao', ascending=False)
            
            print("💾 Salvando arquivo AlmoxWeb SAD320.xlsx...")
            df.to_excel(arquivo_saida, index=False)
            print(f"✅ SUCESSO ABSOLUTO! Tabela extraída!")
            
            driver.quit()
            return df.to_dict('records')
        else:
            print("❌ Pandas não achou lista de dados HTML.")
            driver.quit()
            return None
            
    except Exception as e:
        print("\n=== ATENÇÃO: ERRO FATAL DETECTADO NA NAVEGAÇÃO ===")
        print(traceback.format_exc())
        try: driver.quit() 
        except: pass
        return None

if __name__ == "__main__":
    extrair_dados_almoxweb()