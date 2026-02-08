import pandas as pd
from pathlib import Path
from typing import List, Optional, Tuple

# --- CONFIGURAÇÕES E CONSTANTES ---
ARQUIVO_SAIDA = Path("Relatorio_Tratado.xlsx")
JORNADA_PADRAO = pd.to_timedelta('08:48:00')

# Configurações de Leitura
INDICES_COLUNAS_HORAS = [3, 8, 9, 10, 14]
INDICES_COLUNAS_AJUSTES = [0, 5, 7]

# Filtros
NOMES_PARA_EXCLUIR = [
    "Colaborador", 
    "Gustavo Andregtoni Puel", 
    "Thais Carlini", 
    "Lucas Brasil Silva"
]

NOMES_PARA_SUBSTITUIR = {
    "ATESTADO MÉDICO":"ATESTADO",
    "FALTA NÃO JUSTIFICADA":"FALTA",
    "Folga NR":"FOLGA",
    "FALTA JUSTIFICADA":"FOLGA"
}

def carregar_dados(path: Path, colunas: List[int]) -> pd.DataFrame:
    """Carrega Excel verificando engine baseada na extensão."""
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    
    try:
        return pd.read_excel(path, usecols=colunas, engine=engine, header=None)
    except Exception as e:
        raise ValueError(f"Erro ao ler o arquivo {path.name}: {e}")

def higienizar_dataframe(df: pd.DataFrame, tipo_arquivo: str) -> pd.DataFrame:
    """
    Localiza o cabeçalho dinamicamente, define as colunas e limpa linhas inválidas.
    """
    try:
        # Localiza a linha onde a primeira coluna é "Colaborador"
        idx_cabecalho = df[df.iloc[:, 0] == "Colaborador"].index[0]
    except IndexError:
        raise ValueError("Cabeçalho 'Colaborador' não encontrado no arquivo.")

    # Promove a linha de cabeçalho e ajusta o DF
    df.columns = df.iloc[idx_cabecalho]
    df = df.iloc[idx_cabecalho + 1:].copy()

    # Filtros específicos por tipo
    if tipo_arquivo == "horas":
        # Remove nomes indesejados e linhas onde Colaborador é nulo
        mask_validos = (
            (~df["Colaborador"].isin(NOMES_PARA_EXCLUIR)) & 
            (df["Colaborador"].notna())
        )
        df_limpo = df[mask_validos].copy()
    else:
        # Para arquivo de ajustes, queremos apenas linhas com Tipo preenchido
        df_limpo = df[df["Tipo"].notna()].copy()
        df_limpo["Tipo"] = df_limpo["Tipo"].replace(NOMES_PARA_SUBSTITUIR)

    return df_limpo.reset_index(drop=True)

def converter_colunas_para_timedelta(df: pd.DataFrame, colunas: List[str]) -> pd.DataFrame:
    """Converte colunas de string (HH:MM) para Timedelta pandas."""
    for col in colunas:
        # O .strip() remove espaços, e adicionamos :00 para formato HH:MM:SS
        df[f"{col}_td"] = pd.to_timedelta(
            df[col].astype(str).str.strip() + ":00", 
            errors="coerce"
        )
    return df

def calcular_horas_extras(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica regra de negócio para ajuste de horas extras em feriados/folgas."""
    
    # Regra 1: Se Trabalhadas == Extras (dia 100% extra) E trabalhou mais que a jornada
    # Devemos subtrair a jornada padrão do total de extras
    mask_excesso = (
        (df["Trabalhadas_td"] == df["Extras 01_td"]) & 
        (df["Trabalhadas_td"] > JORNADA_PADRAO)
    )
    df.loc[mask_excesso, "Extras 01_td"] = df.loc[mask_excesso, "Trabalhadas_td"] - JORNADA_PADRAO
    
    # Regra 2: Se trabalhou MENOS que a jornada padrão, zera a hora extra
    mask_menor_jornada = df["Trabalhadas_td"] < JORNADA_PADRAO
    df.loc[mask_menor_jornada, "Extras 01_td"] = pd.NaT 
    
    return df

def processar_arquivo_ajustes(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara o dataframe de ajustes (férias, atestados) para o merge."""
    # Garante formato de data correto
    df["Ínicio"] = pd.to_datetime(df["Ínicio"], dayfirst=True, errors='coerce').dt.date
    
    # Remove duplicatas mantendo a primeira ocorrência
    df = df.drop_duplicates(subset=["Colaborador", "Ínicio"], keep="first")
    
    # Renomeia para facilitar o merge
    return df.rename(columns={"Ínicio": "Data"})

def converter_timedelta_para_decimal(series: pd.Series) -> pd.Series:
    """
    Converte Timedelta diretamente para float (horas decimais).
    Ex: 01:30:00 -> 1.5
    """
    # total_seconds() / 3600 é a forma matemática correta de converter
    valores_float = series.dt.total_seconds().div(3600).round(2)

    return valores_float.astype(str).str.replace(".", ",", regex=False)

def preencher_dias_faltantes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria linhas para os dias que não existem no arquivo original.
    Mantém apenas Colaborador e Data preenchidos, o resto fica vazio (NaN/NaT).
    """
    # 1. Identifica o intervalo de datas do arquivo (do primeiro ao último dia registrado)
    # Se quiser forçar o mês inteiro (ex: 01 a 30), pode fixar as datas aqui manualmente.
    data_min = df["Data"].min()
    data_max = df["Data"].max()
    
    # Gera uma lista com TODOS os dias desse intervalo
    todas_datas = pd.date_range(start=data_min, end=data_max, freq='D')
    
    # 2. Pega a lista de todos os colaboradores únicos
    colaboradores = df["Colaborador"].unique()
    
    # 3. Cria o "Produto Cartesiano" (Todos os Colaboradores x Todas as Datas)
    # Isso cria um DataFrame vazio com o índice correto
    idx = pd.MultiIndex.from_product([colaboradores, todas_datas], names=["Colaborador", "Data"])
    df_completo = pd.DataFrame(index=idx).reset_index()
    
    # Garante que a coluna Data esteja no mesmo formato para o merge
    df_completo["Data"] = df_completo["Data"].dt.date
    df["Data"] = pd.to_datetime(df["Data"]).dt.date
    
    # 4. Faz o Merge: Pega o quadro completo e preenche com as informações que temos
    # O 'how="left"' garante que todas as datas vazias permaneçam
    df_final = pd.merge(df_completo, df, on=["Colaborador", "Data"], how="left")
    
    return df_final

def unir_e_formatar_final(df_horas: pd.DataFrame, df_ajustes: pd.DataFrame) -> pd.DataFrame:
    """Realiza o merge e formata as colunas finais."""
    
    # 1. Preparar data base para o merge
    df_horas["Data"] = pd.to_datetime(df_horas["Data"], dayfirst=True, errors='coerce')
    
    # --- NOVO PASSO: PREENCHER DIAS FALTANTES ---
    # Aqui criamos as linhas vazias para os dias que o colaborador não bateu ponto
    df_horas = preencher_dias_faltantes(df_horas)
    # --------------------------------------------

    # 2. Converter Timedeltas para Decimal (Apenas para fins de cálculo/visualização se houver dados)
    # Precisamos tratar erros agora, pois as novas linhas terão valores NaT (nulos)
    df_horas["Trabalhadas"] = converter_timedelta_para_decimal(df_horas["Trabalhadas_td"].fillna(pd.Timedelta(0)))

    df_horas["Extras 01"] = converter_timedelta_para_decimal(df_horas["Extras 01_td"].fillna(pd.Timedelta(0)))

    
    # Se a linha foi criada agora (vazia), 'Trabalhadas' vai ficar como "0,00". 
    # Se você quiser que fique TOTALMENTE vazia visualmente:
    mask_vazios = df_horas["Trabalhadas_td"].isna()
    
    # 3. Merge com Ajustes (Left Join)
    # Atenção: df_horas agora tem TODOS os dias, então o merge vai casar certinho
    df_merged = pd.merge(
        left=df_horas,
        right=df_ajustes[["Colaborador", "Tipo", "Data"]],
        on=["Colaborador", "Data"], # Já normalizamos para .date no passo anterior
        how="left",
        suffixes=("", "_ajuste")
    )
    
    # 4. Limpeza visual (Opcional)
    # Se for uma linha criada artificialmente e não tiver ajuste, deixamos campos em branco
    if mask_vazios.any():
         df_merged.loc[mask_vazios, "Trabalhadas"] = ""

    # Lógica anterior de preencher com o Tipo (Férias/Atestado)
    mask_substituicao = (df_merged["Tipo"].notna()) & ((df_merged["Trabalhadas"] == "") | (df_merged["Trabalhadas"] == "0,00"))
    df_merged.loc[mask_substituicao, "Trabalhadas"] = df_merged.loc[mask_substituicao, "Tipo"]

    df_merged.loc[df_merged["Extras 01"] == "0,0", ["Extras 01"]] = ""
    
    # 5. Seleção de Colunas Finais
    # Removemos colunas auxiliares
    cols_to_keep = [c for c in df_merged.columns if not c.endswith("_td") and c != "Tipo"]
    
    return df_merged[cols_to_keep]

def identificar_arquivos(paths: List[str]) -> Tuple[Optional[Path], Optional[Path]]:
    """Identifica qual arquivo é qual baseado no nome."""
    path_horas = None
    path_ajustes = None
    
    for p in paths:
        if "RelatorioHorasExtras" in p:
            path_horas = Path(p)
        else:
            path_ajustes = Path(p)
            
    return path_horas, path_ajustes

def main(paths: List[str]):
    try:
        # 1. Identificação dos Arquivos
        path_horas, path_ajustes = identificar_arquivos(paths)
        
        if not path_horas or not path_ajustes:
            raise FileNotFoundError("É necessário fornecer ambos os arquivos: Horas e Ajustes.")

        # 2. Processamento do Arquivo de Horas
        df_horas = carregar_dados(path_horas, INDICES_COLUNAS_HORAS)
        df_horas = higienizar_dataframe(df_horas, tipo_arquivo="horas")
        df_horas = converter_colunas_para_timedelta(df_horas, ["Trabalhadas", "Extras 01"])
        df_horas = calcular_horas_extras(df_horas)

        # 3. Processamento do Arquivo de Ajustes
        df_ajustes = carregar_dados(path_ajustes, INDICES_COLUNAS_AJUSTES)
        df_ajustes = higienizar_dataframe(df_ajustes, tipo_arquivo="ajuste")
        df_ajustes = processar_arquivo_ajustes(df_ajustes)

        # 4. Unificação e Saída
        df_final = unir_e_formatar_final(df_horas, df_ajustes)
        
        # Reordenação de segurança (garantir que Extras 01 fique onde você queria)
        cols = list(df_final.columns)
        if "Extras 01" in cols:
            cols.insert(3, cols.pop(cols.index("Extras 01")))
        df_final = df_final[cols]

        df_final.to_excel(ARQUIVO_SAIDA, index=False)

    except Exception as e:
        # Em interfaces, é bom imprimir o erro para logs, mas o 'raise' joga para a UI tratar
        raise e

if __name__ == "__main__":
    # Exemplo de teste (comente ao usar na interface real)
    # main(["C:/Docs/RelatorioHorasExtras.xls", "C:/Docs/Ajustes.xlsx"])
    pass