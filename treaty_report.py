import pandas as pd

PATH_ORIGIN = "RelatorioHorasExtras.xls"
PATH_DESTINATION = "Treated report.xlsx"

if PATH_ORIGIN.split(".")[-1] == "xls":
    dftotal = pd.read_excel(PATH_ORIGIN, usecols=[3, 8, 9, 10, 11, 12, 14], engine="xlrd", header=None)
else:
    dftotal = pd.read_excel(PATH_ORIGIN, usecols=[3, 8, 9, 10, 11, 12, 14], header=None)

indice_cabecalho = dftotal[dftotal.iloc[:,0] == "Colaborador"].index[0]

dftotal.columns = dftotal.iloc[indice_cabecalho]

df = dftotal.iloc[indice_cabecalho + 1:].copy()

df_limpo = df[
    (df["Colaborador"] != "Colaborador") &
    (df["Colaborador"].notna())
].copy()

cols = list(df_limpo)

cols.insert(3, cols.pop(cols.index("Extras 01")))

df_limpo = df_limpo[cols]

df_limpo.loc[df_limpo["Abonadas"] == "08:48", "Trabalhadas"] = "ATESTADO"

df_limpo.loc[df_limpo["Atrasos"] == "-08:48", "Trabalhadas"] = "FALTA"

df_limpo["Trabalhadas"] = df_limpo["Trabalhadas"].astype(str).str.replace(":", ",")

df_limpo = df_limpo.drop(columns=["Abonadas", "Atrasos"])

df_limpo["Data"] = pd.to_datetime(df_limpo["Data"], format="%d/%m/%Y")

df_limpo.reset_index(drop=True, inplace=True)

df_limpo.to_excel(PATH_DESTINATION, index=False)