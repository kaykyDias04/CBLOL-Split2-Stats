from mwrogue.esports_client import EsportsClient
from mwrogue.auth_credentials import AuthCredentials
import pandas as pd

credentials = AuthCredentials(user_file="me")
site = EsportsClient('lol', credentials=credentials)

torneio = input("Digite o nome exato do torneio (ex: CBLOL 2026 Split 1): ")

print(f"\nIniciando a extração de dados para: '{torneio}'...\n")

response_jogadores_partida = site.cargo_client.query(
    tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Tournaments=T",
    join_on="SG.GameId=SP.GameId, SG.OverviewPage=T.OverviewPage",
    fields="""
    SG.DateTime_UTC, SG.Gamelength, SG.Patch,
    SP.Link, SP.Team, SP.Side, SP.Role, SP.Champion,
    SP.Kills, SP.Deaths, SP.Assists, SP.Gold, SP.CS,
    SP.DamageToChampions, SP.VisionScore,
    SP.Items__full=Items, SP.Pentakills, 
    SP.SummonerSpells__full=SummonerSpells
    
    """,
    where=f"T.Name='{torneio}'",
)
df_jogadores_partida = pd.DataFrame(response_jogadores_partida)

response_times_partida = site.cargo_client.query(
    tables="ScoreboardGames=SG, ScoreboardTeams=ST, Tournaments=T",
    join_on="SG.GameId=ST.GameId, SG.OverviewPage=T.OverviewPage",
    fields="""
    SG.DateTime_UTC, SG.Gamelength, SG.Patch,
    ST.Team, ST.Side, ST.IsWinner, ST.Kills, ST.Gold, ST.Towers,
    ST.Dragons, ST.Clouds, ST.Infernals, ST.Mountains, ST.Oceans, ST.Chemtechs, ST.Hextechs, ST.Elders, ST.RiftHeralds, ST.Barons, ST.Bans__full=Bans, ST.Picks__full=Picks
    """,
    where=f"T.Name='{torneio}'"
)
df_times_partida = pd.DataFrame(response_times_partida)

response_dados_gerais = site.cargo_client.query(
    tables="Tournaments=T, TournamentPlayers=TP, PlayerRedirects=PR, Players=P",
    join_on="T.OverviewPage=TP.OverviewPage, TP.Player=PR.AllName, PR.OverviewPage=P.OverviewPage",
    fields="P.Player, P.Name, P.Country, P.Birthdate, P.Residency, P.Role",
    where=f"T.Name='{torneio}'",
    group_by="P.OverviewPage"
)
df_dados_gerais = pd.DataFrame(response_dados_gerais)

# --- JOGADORES POR PARTIDA FORMATAÇÕES ---
cols_jogadores_numeric = ['Kills', 'Deaths', 'Assists', 'Gold', 'CS', 'DamageToChampions', 'VisionScore']
for col in cols_jogadores_numeric:
    if col in df_jogadores_partida.columns:
        df_jogadores_partida[col] = pd.to_numeric(df_jogadores_partida[col], errors='coerce')

side_map = {1: 'Red', 2: 'Blue', '1': 'Red', '2': 'Blue', 1.0: 'Red', 2.0: 'Blue'}
if 'Side' in df_jogadores_partida.columns:
    df_jogadores_partida['Side'] = df_jogadores_partida['Side'].replace(side_map)

if 'Link' in df_jogadores_partida.columns:
    df_jogadores_partida['Link'] = df_jogadores_partida['Link'].astype(str).str.replace(r'\s*\(.*?\)', '', regex=True).str.strip()
    df_jogadores_partida = df_jogadores_partida.rename(columns={'Link': 'Player Nick'})

# --- NOVAS MÉTRICAS DE PERFORMANCE PARA O LOOKER STUDIO ---
# 1. MÉTRICA DE BASE (CONVERSÃO DE TEMPO)
def converter_duracao(d):
    try:
        partes = str(d).split(':')
        if len(partes) == 2:
            return int(partes[0]) + int(partes[1]) / 60.0
        elif len(partes) == 3:
            return int(partes[0])*60 + int(partes[1]) + int(partes[2]) / 60.0
        return float(d)
    except:
        return pd.NA

df_jogadores_partida['Duracao_Minutos'] = df_jogadores_partida['Gamelength'].apply(converter_duracao)

# 2. MÉTRICAS DE RITMO (POR MINUTO)
df_jogadores_partida['DPM'] = df_jogadores_partida['DamageToChampions'] / df_jogadores_partida['Duracao_Minutos']
df_jogadores_partida['GPM'] = df_jogadores_partida['Gold'] / df_jogadores_partida['Duracao_Minutos']
df_jogadores_partida['CSM'] = df_jogadores_partida['CS'] / df_jogadores_partida['Duracao_Minutos']
df_jogadores_partida['VSPM'] = df_jogadores_partida['VisionScore'] / df_jogadores_partida['Duracao_Minutos']
df_jogadores_partida['KPM'] = df_jogadores_partida['Kills'] / df_jogadores_partida['Duracao_Minutos']

# 3. MÉTRICAS DE COMBATE, SOBREVIVÊNCIA E EFICIÊNCIA INDIVIDUAL
df_jogadores_partida['KDA_Ratio'] = (df_jogadores_partida['Kills'] + df_jogadores_partida['Assists']) / df_jogadores_partida['Deaths'].replace(0, 1)
df_jogadores_partida['Dano_Por_Ouro'] = df_jogadores_partida['DamageToChampions'] / df_jogadores_partida['Gold'].replace(0, 1)
df_jogadores_partida['Mortes_Por_Minuto'] = df_jogadores_partida['Deaths'] / df_jogadores_partida['Duracao_Minutos']

# 4. MÉTRICAS DE IMPACTO NO TIME (WINDOW FUNCTIONS / SHARE)
df_jogadores_partida['DMG_Share'] = df_jogadores_partida['DamageToChampions'] / df_jogadores_partida.groupby(['DateTime UTC', 'Team'])['DamageToChampions'].transform('sum')
df_jogadores_partida['Gold_Share'] = df_jogadores_partida['Gold'] / df_jogadores_partida.groupby(['DateTime UTC', 'Team'])['Gold'].transform('sum')
df_jogadores_partida['KP_Percent'] = (df_jogadores_partida['Kills'] + df_jogadores_partida['Assists']) / df_jogadores_partida.groupby(['DateTime UTC', 'Team'])['Kills'].transform('sum').replace(0, 1)
df_jogadores_partida['Vision_Share'] = df_jogadores_partida['VisionScore'] / df_jogadores_partida.groupby(['DateTime UTC', 'Team'])['VisionScore'].transform('sum')


# --- TIMES POR PARTIDA FORMATAÇÕES ---
if 'Side' in df_times_partida.columns:
    df_times_partida['Side'] = df_times_partida['Side'].replace(side_map)

cols_times_numeric = [
    'Kills', 'Gold', 'Towers', 'Dragons', 'Clouds', 'Infernals', 
    'Mountains', 'Oceans', 'Chemtechs', 'Hextechs', 'Elders', 
    'RiftHeralds', 'Barons'
]
for col in cols_times_numeric:
    if col in df_times_partida.columns:
        df_times_partida[col] = pd.to_numeric(df_times_partida[col], errors='coerce')

is_winner_map = {
    0: 'Derrota', 1: 'Vitória',
    '0': 'Derrota', '1': 'Vitória',
    0.0: 'Derrota', 1.0: 'Vitória',
    False: 'Derrota', True: 'Vitória'
}
if 'IsWinner' in df_times_partida.columns:
    df_times_partida['IsWinner'] = df_times_partida['IsWinner'].replace(is_winner_map)


torneio_formatado = torneio.replace(" ", "_")
nome_arquivo = f"{torneio_formatado}_Estatísticas_Completas.xlsx"

with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
    df_jogadores_partida.to_excel(writer, sheet_name="Jogadores por Partida", index=False)
    df_times_partida.to_excel(writer, sheet_name="Times por Partida", index=False)
    df_dados_gerais.to_excel(writer, sheet_name="Dados Gerais Jogadores", index=False)

print(f"\nExtração concluída com sucesso! Verifique o arquivo: {nome_arquivo}")