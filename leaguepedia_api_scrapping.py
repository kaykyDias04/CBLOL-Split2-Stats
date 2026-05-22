from mwrogue.esports_client import EsportsClient
from mwrogue.auth_credentials import AuthCredentials
import pandas as pd


credentials = AuthCredentials(user_file="me")
site = EsportsClient('lol', credentials=credentials)


torneio = "CBLOL 2026 Split 1"


response_jogadores_partida = site.cargo_client.query(
tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Tournaments=T",
join_on="SG.GameId=SP.GameId, SG.OverviewPage=T.OverviewPage",
fields="""
SG.DateTime_UTC, SG.Gamelength, SG.Patch,
SP.Link, SP.Team, SP.Side, SP.Role, SP.Champion,
SP.Kills, SP.Deaths, SP.Assists, SP.Gold, SP.CS,
SP.DamageToChampions, SP.VisionScore,
SP.Items__full=Items, SP.SummonerSpells__full=SummonerSpells,
SP.Pentakills
""",
where=f"T.Name='{torneio}'",
limit="max"
)
df_jogadores_partida = pd.DataFrame(response_jogadores_partida)


response_times_partida = site.cargo_client.query(
tables="ScoreboardGames=SG, ScoreboardTeams=ST, Tournaments=T",
join_on="SG.GameId=ST.GameId, SG.OverviewPage=T.OverviewPage",
fields="""
SG.DateTime_UTC, SG.Gamelength,
ST.Team, ST.Side, ST.IsWinner, ST.Kills, ST.Gold, ST.Towers,
ST.Dragons, ST.Dragons, ST.Clouds, ST.Infernals, ST.Mountains, ST.Oceans, ST.Chemtechs, ST.Hextechs, ST.Elders, ST.RiftHeralds, ST.Barons, ST.Bans__full=Bans, ST.Picks__full=Picks
""",
where=f"T.Name='{torneio}'",
limit="max"
)
df_times_partida = pd.DataFrame(response_times_partida)


response_dados_gerais = site.cargo_client.query(
tables="Tournaments=T, TournamentPlayers=TP, PlayerRedirects=PR, Players=P",
join_on="T.OverviewPage=TP.OverviewPage, TP.Player=PR.AllName, PR.OverviewPage=P.OverviewPage",
fields="P.Player, P.Name, P.Country, P.Birthdate, P.Residency, P.Role",
where=f"T.Name='{torneio}'",
group_by="P.OverviewPage",
limit="max"
)
df_dados_gerais = pd.DataFrame(response_dados_gerais)


nome_arquivo = "cblol_2026_Split_1_Estatisticas_Completas_v2.xlsx"
with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
    df_jogadores_partida.to_excel(writer, sheet_name="Jogadores por Partida", index=False)
    df_times_partida.to_excel(writer, sheet_name="Times por Partida", index=False)
    df_dados_gerais.to_excel(writer, sheet_name="Dados Gerais Jogadores", index=False)


print(f"Extração concluída com sucesso! Verifique o arquivo: {nome_arquivo}")