import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    
    options.add_argument("--lang=pt-BR")
    options.add_argument("accept-language=pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7")
    
    return webdriver.Chrome(options=options)

def accept_cookies(driver):
    """Tenta fechar o banner de cookies se ele existir para liberar cliques na tela."""
    try:
        xpath_cookies = "//button[contains(., 'Aceitar') or contains(., 'Accept') or contains(., 'Agree')]"
        btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_cookies)))
        btn.click()
        time.sleep(1)
        print(" -> Banner de cookies fechado.")
    except:
        pass 

def extract_table_data(html, side_or_context=None):
    """Lê uma tabela HTML padrão e a transforma em uma lista de dicionários."""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        return []

    headers = [th.text.strip() for th in table.find('thead').find_all('th')] if table.find('thead') else []
    
    data = []
    tbody = table.find('tbody')
    if tbody:
        for row in tbody.find_all('tr'):
            cols = row.find_all('td')
            if cols:
                row_data = {}
                for i, col in enumerate(cols):
                    text = " ".join(col.text.strip().split())
                    col_name = headers[i] if i < len(headers) else f"Col_{i}"
                    row_data[col_name] = text
                
                if side_or_context:
                    row_data['Lado/Contexto'] = side_or_context
                    
                data.append(row_data)
    return data

def scrape_teams(driver, base_url):
    print("\n--- Iniciando Extração de Times ---")
    driver.get(f"{base_url}/team")
    
    accept_cookies(driver)
    
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    except:
        print("Aviso: A tabela principal não foi encontrada na página inicial.")

    time.sleep(3)
    all_teams_data = []
    
    lados_busca = [
        ("Ambos", ["Ambos", "AMBOS", "ambos", "Both", "BOTH", "both"]),
        ("Azul", ["Azul", "AZUL", "azul", "Blue", "BLUE", "blue"]),
        ("Vermelho", ["Vermelho", "VERMELHO", "vermelho", "Red", "RED", "red"])
    ]
    tabela_anterior = ""

    for nome_excel, palavras in lados_busca:
        print(f"\nBuscando estatísticas do time: Lado {nome_excel}...")
        try:
            condicoes = " or ".join([f"normalize-space(.)='{p}'" for p in palavras])
            xpath = f"//*[({condicoes}) and not(*[{condicoes}])]"
            
            elementos = driver.find_elements(By.XPATH, xpath)
            clicou = False

            for btn in elementos:
                try:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", btn)
                        print(f" -> Clique realizado no botão '{nome_excel}'. Aguardando atualização...")
                        clicou = True
                        break
                except Exception:
                    continue

            if not clicou:
                print(f" -> Não achou ou não clicou no botão {nome_excel}. Usando dados atuais da tela.")

            tentativas = 0
            dados_mudaram = False
            html_final = driver.page_source

            if clicou and nome_excel != "Ambos":
                while tentativas < 10:
                    time.sleep(1)
                    html_atual = driver.page_source
                    soup = BeautifulSoup(html_atual, 'html.parser')
                    tbody = str(soup.find('tbody'))

                    if tbody != tabela_anterior:
                        dados_mudaram = True
                        tabela_anterior = tbody
                        html_final = html_atual
                        break
                    tentativas += 1

                if not dados_mudaram:
                    print(" -> Aviso: Tabela parece igual à anterior (site não atualizou a tempo).")
            elif nome_excel == "Ambos":
                soup = BeautifulSoup(html_final, 'html.parser')
                tabela_anterior = str(soup.find('tbody'))

            data = extract_table_data(html_final, side_or_context=nome_excel)
            
            if data:
                preview_time = data[0].get('Time', data[0].get('Team', 'N/A'))
                preview_wr = data[0].get('Taxa de vitória', data[0].get('Win Rate', 'N/A'))
                print(f" -> Sucesso: {len(data)} linhas. Preview 1º Time: {preview_time} - WinRate: {preview_wr}")
                all_teams_data.extend(data)
            else:
                print(" -> Nenhuma tabela encontrada.")

        except Exception as e:
            print(f" -> Erro na aba {nome_excel}: {type(e).__name__}")
            
    df = pd.DataFrame(all_teams_data)
    
    if not df.empty:
        cols_check = [col for col in df.columns if col != 'Lado/Contexto']
        df = df.drop_duplicates(subset=cols_check)
        
    return df

def scrape_players(driver, base_url):
    print("\n--- A Iniciar Extração de Jogadores ---")
    driver.get(f"{base_url}/player")
    time.sleep(4)
    
    try:
        xpath = "//*[self::button or self::a or self::div][contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'estatísticas do jogador') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'player stats')]"
        elementos = driver.find_elements(By.XPATH, xpath)
        
        clicou = False
        for btn in reversed(elementos): 
            try:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", btn)
                    clicou = True
                    time.sleep(2) 
                    break
            except:
                continue
                
        if clicou:
            print(" -> Clique no sub-menu realizado com sucesso.")
        else:
            print(" -> Aviso: Não conseguiu clicar. Tentando extrair a tabela mesmo assim.")

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        except:
            print(" -> Aviso: A tabela não apareceu a tempo.")

        html = driver.page_source
        players_data = extract_table_data(html)
        
        if players_data:
            print(f" -> Sucesso: {len(players_data)} jogadores extraídos.")
        else:
            print(" -> Falha: Nenhuma tabela de jogadores foi encontrada.")
            
        return pd.DataFrame(players_data)
        
    except Exception as e:
        print(f" -> Erro crítico em jogadores: {e}")
        return pd.DataFrame()
    print("\n--- A Iniciar Extração de Jogadores ---")
    driver.get(f"{base_url}/player")
    time.sleep(4) 
    
    try:
        xpath = "//*[self::button or self::a or self::div][contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'estatísticas do jogador') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'player stats')]"
        elementos = driver.find_elements(By.XPATH, xpath)
        
        clicou = False
        for btn in elementos:
            try:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", btn)
                    print(" -> Visualização de Tabela de Jogadores ativada.")
                    clicou = True
                    break
            except:
                continue
                
        if not clicou:
            print(" -> Aviso: Não foi possível clicar no botão de Tabela. A tentar extrair mesmo assim...")

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        except:
            print(" -> Aviso: A tabela não apareceu a tempo.")

        time.sleep(2)
        html = driver.page_source
        players_data = extract_table_data(html)
        
        if players_data:
            print(f" -> Sucesso: {len(players_data)} jogadores extraídos.")
        else:
            print(" -> Falha: Nenhuma tabela de jogadores foi encontrada.")
            
        return pd.DataFrame(players_data)
        
    except Exception as e:
        print(f" -> Erro crítico em jogadores: {e}")
        return pd.DataFrame()

def scrape_champions(driver, base_url):
    print("\n--- Iniciando Extração de Campeões ---")
    driver.get(f"{base_url}/champion") 
    time.sleep(3)
    
    try:
        html = driver.page_source
        champs_data = extract_table_data(html)
        
        if champs_data:
            print(f" -> Sucesso: {len(champs_data)} campeões extraídos.")
        else:
            print(" -> Nenhuma tabela de campeões encontrada.")
            
        return pd.DataFrame(champs_data)
        
    except Exception as e:
        print(f" -> Erro ao extrair campeões: {e}")
        return pd.DataFrame()

def scrape_matches(driver, base_url):
    import re
def scrape_match_links(driver):
    print("\n--- Coletando Links das Partidas (Mar a Jun) ---")
    driver.get("https://esports.op.gg/schedules?league=cblol")
    time.sleep(5)
    accept_cookies(driver)
    
    meses_alvo = ['mar', 'abr', 'mai', 'jun']
    match_urls_com_data = []
    
    for mes in meses_alvo:
        print(f" -> Navegando para o mês: {mes.capitalize()}...")
        try:
            dropdowns = driver.find_elements(By.CSS_SELECTOR, '[id^="headlessui-menu-button"]')
            btn_mes = None
            meses_lista = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
            
            for d in dropdowns:
                if d.text.strip().lower() in meses_lista:
                    btn_mes = d
                    break
                    
            if btn_mes:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_mes)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", btn_mes)
                time.sleep(1)
                
                opcoes = driver.find_elements(By.CSS_SELECTOR, '[role="menuitem"]')
                clicou = False
                for opt in opcoes:
                    if opt.text.strip().lower() == mes:
                        driver.execute_script("arguments[0].click();", opt)
                        clicou = True
                        print(f"    Mês {mes.capitalize()} selecionado. Aguardando dados...")
                        time.sleep(4)
                        break
                        
                if not clicou:
                    print(f"    Opção {mes.capitalize()} não encontrada no dropdown. Tentando próximo.")
            else:
                print("    Botão dropdown do mês não encontrado.")
            
            elementos = driver.find_elements(By.XPATH, "//div[contains(@class, 'bg-gray-800') or contains(@class, 'bg-gray-900') or a]")
            
            data_atual = "Data Desconhecida"
            for el in elementos:
                texto = el.text.strip()
                if not texto:
                    continue
                if len(texto) > 10 and "." in texto and ("sáb" in texto.lower() or "dom" in texto.lower() or "sex" in texto.lower() or "seg" in texto.lower() or "ter" in texto.lower() or "qua" in texto.lower() or "qui" in texto.lower()):
                    data_atual = texto.split('\n')[0]
                
                links = el.find_elements(By.TAG_NAME, "a")
                for a in links:
                    href = a.get_attribute("href")
                    if href and "/matches/" in href:
                        if "encerrada" in a.text.lower() or "completed" in a.text.lower():
                            if (href, data_atual) not in match_urls_com_data:
                                match_urls_com_data.append((href, data_atual))
            
        except Exception as e:
            print(f" -> Erro ao processar o mês {mes}: {e}")
            
    print(f" -> Total de URLs coletadas: {len(match_urls_com_data)}")
    return match_urls_com_data

def extrair_numero(texto):
    """Extrai apenas números de uma string"""
    import re
    numeros = re.findall(r'\d+', str(texto))
    return int(numeros[0]) if numeros else 0

def scrape_match_details(driver, url, match_date):
    print(f"\n--- Extraindo Detalhes: {url} ---")
    sets_data = []
    players_data = []
    
    try:
        driver.get(url)
        time.sleep(5)
        set_buttons = driver.find_elements(By.XPATH, "//button[@type='button' and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'set')]")
        
        if not set_buttons:
            print(" -> Nenhum Set encontrado. Pulando...")
            return sets_data, players_data
            
        for idx, btn in enumerate(set_buttons):
            set_name = btn.text.strip()
            print(f" -> Processando {set_name}...")
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3) 
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            body_text = soup.get_text(separator=' ', strip=True)
            
            # --- Duração ---
            duration = "00:00"
            import re
            dur_match = re.search(r'Postgame Breakdown\s*Ver\.\s*[\d\.]+\s*(\d{2}:\d{2})', body_text)
            if dur_match:
                duration = dur_match.group(1)
            else:
                dur_match2 = re.search(r'Postgame Breakdown.*?(\d{2}:\d{2})', soup.text, re.IGNORECASE)
                if dur_match2:
                    duration = dur_match2.group(1)
                    
            # --- Vencedor ---
            winner = "Desconhecido"
            victory_tags = soup.find_all(string=lambda t: t and t.strip() == "Victory")
            if victory_tags:
                parent = victory_tags[0].parent.parent
                if parent:
                    # Ex: "PNG Victory Blue Side" -> "PNG"
                    winner_text = parent.get_text(separator=' ').split()[0]
                    winner = winner_text
                    
            # --- KDAs Gerais (Times) ---
            kda_time1, kda_time2 = "-", "-"
            kdas_partida = re.findall(r'(\d+\s*/\s*\d+\s*/\s*\d+)', soup.text)
            if len(kdas_partida) >= 2:
                kda_time1 = kdas_partida[0]
                kda_time2 = kdas_partida[1]
            
            # --- Objetivos (SVGs) ---
            obj_counts = {'time1': {}, 'time2': {}}
            obj_mapping = {
                'M12 2.944': 'Voidgrub',
                'M19.857 16.233': 'Ancient Drake',
                'M13.25 14.5a1.25': 'Rift Herald',
                'm18 12-3 12H9': 'Tower',
                'M12 2c5.523': 'Inhibitor',
                'M9.6 2 4': 'Baron Nashor'
            }
            
            object_label = soup.find(string=lambda t: t and t.strip() == "Object")
            if object_label and object_label.parent and object_label.parent.parent:
                obj_container = object_label.parent.parent
                svgs = obj_container.find_all('svg')
                
                # A primeira metade dos ícones pertence ao Time 1, a segunda ao Time 2
                meio = len(svgs) // 2
                
                for i, svg in enumerate(svgs):
                    path = svg.find('path')
                    if path:
                        d_attr = path.get('d', '')
                        
                        obj_name = None
                        for key, val in obj_mapping.items():
                            if d_attr.startswith(key):
                                obj_name = val
                                break
                                
                        if obj_name:
                            # O número está no container pai (junto com o svg)
                            parent_text = svg.parent.text.strip()
                            num = extrair_numero(parent_text)
                            
                            if i < meio:
                                obj_counts['time1'][obj_name] = num
                            else:
                                obj_counts['time2'][obj_name] = num
            
            sets_data.append({
                'URL': url,
                'Data': match_date,
                'Set': set_name,
                'Vencedor': winner,
                'Duração': duration,
                'KDA_Time_Esquerda': kda_time1,
                'KDA_Time_Direita': kda_time2,
                'Objetivos_Esquerda': str(obj_counts['time1']),
                'Objetivos_Direita': str(obj_counts['time2'])
            })
            
            # --- Tabelas de Jogadores ---
            tables = soup.find_all('table')
            for t_idx, table in enumerate(tables):
                team_side = "Esquerda" if t_idx == 0 else "Direita"
                headers = [th.text.strip() for th in table.find('thead').find_all('th')] if table.find('thead') else []
                tbody = table.find('tbody')
                if tbody:
                    for row in tbody.find_all('tr'):
                        cols = row.find_all('td')
                        if cols:
                            row_data = {
                                'URL': url,
                                'Data': match_date,
                                'Set': set_name,
                                'Lado': team_side
                            }
                            for c_idx, col in enumerate(cols):
                                text = " ".join(col.text.strip().split())
                                
                                # Captura do Campeão ou Imagens vazias
                                if not text and c_idx == 0:
                                    img = col.find('img')
                                    if img and img.get('alt'):
                                        text = img.get('alt')
                                    else:
                                        a_tag = col.find('a')
                                        if a_tag and a_tag.get('href'):
                                            text = a_tag.get('href').split('/')[-1]
                                            
                                col_name = headers[c_idx] if c_idx < len(headers) else f"Col_{c_idx}"
                                row_data[col_name] = text
                            
                            players_data.append(row_data)

    except Exception as e:
        print(f" -> Erro ao extrair detalhes da partida {url}: {e}")
        
    return sets_data, players_data

def main():
    driver = setup_driver()
    
    try:
        urls_com_data = scrape_match_links(driver)
        
        all_sets = []
        all_players = []
        
        for url, date in urls_com_data:
            s_data, p_data = scrape_match_details(driver, url, date)
            all_sets.extend(s_data)
            all_players.extend(p_data)
            
        df_sets = pd.DataFrame(all_sets)
        df_players = pd.DataFrame(all_players)
        
        output_file = 'opgg_cblol_stats_detailed.xlsx'
        print(f"\nSalvando dados em {output_file}...")
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            if not df_sets.empty:
                df_sets.to_excel(writer, sheet_name='Sets_Data', index=False)
            if not df_players.empty:
                df_players.to_excel(writer, sheet_name='Players_Data', index=False)
                
        print("✅ Processo concluído com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro crítico durante a execução: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass 

if __name__ == "__main__":
    main()