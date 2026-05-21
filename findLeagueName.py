from mwrogue.esports_client import EsportsClient
from mwrogue.auth_credentials import AuthCredentials
import pandas as pd

credentials = AuthCredentials(user_file="me")
site = EsportsClient('lol', credentials=credentials)

# Busca qualquer torneio que tenha 'LCK' no nome da página
response = site.cargo_client.query(
    tables="Tournaments=T",
    fields="T.OverviewPage, T.Name, T.League",
    where="T.OverviewPage LIKE '%LCK%'",
    limit=10
)
print(pd.DataFrame(response))