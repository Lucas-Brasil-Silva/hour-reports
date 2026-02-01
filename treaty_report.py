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
    return series.dt.total_seconds().div(3600).round(2)

def converter_timedelta_para_string(td):
    """Auxiliar para formatar HH:MM para exibição (se necessário em outra coluna)."""
    if pd.isnull(td): return ""
    total_seconds = int(td.total_seconds())
    horas = total_seconds // 3600
    minutos = (total_seconds % 3600) // 60
    return f"{horas:02d}:{minutos:02d}"

def unir_e_formatar_final(df_horas: pd.DataFrame, df_ajustes: pd.DataFrame) -> pd.DataFrame:
    """Realiza o merge e formata as colunas finais."""
    
    # 1. Converter colunas de tempo para Decimal (Float)
    # ATENÇÃO: Convertemos direto do Timedelta, sem passar por string intermediária
    df_horas["Trabalhadas"] = converter_timedelta_para_decimal(df_horas["Trabalhadas_td"])
    
    # Se quiser manter a coluna de Extras formatada visualmente (HH:MM), use a função string
    # Se quiser decimal, use a função decimal. Mantive a lógica original (HH:MM para Extras)
    df_horas["Extras 01"] = df_horas["Extras 01_td"].apply(converter_timedelta_para_string)

    # 2. Preparar chaves para o Merge
    df_horas["Data_Merge"] = pd.to_datetime(df_horas["Data"], dayfirst=True, errors='coerce').dt.date
    
    # 3. Merge (Left Join)
    df_merged = pd.merge(
        left=df_horas,
        right=df_ajustes[["Colaborador", "Tipo", "Data"]],
        left_on=["Colaborador", "Data_Merge"],
        right_on=["Colaborador", "Data"],
        how="left",
        suffixes=("", "_ajuste")
    )
    
    # 4. Preencher "Trabalhadas" com o "Tipo" (Férias/Atestado) quando vazio
    # Converte para string para aceitar texto "FÉRIAS" junto com números
    df_merged["Trabalhadas"] = df_merged["Trabalhadas"].fillna("")
    
    mask_substituicao = (df_merged["Tipo"].notna()) & (df_merged["Trabalhadas"] == "")
    df_merged.loc[mask_substituicao, "Trabalhadas"] = df_merged.loc[mask_substituicao, "Tipo"]
    
    # 5. Limpeza Final de Colunas
    colunas_finais = ["Colaborador", "Data_Merge", "Trabalhadas", "Extras 01"] # Adicione outras se necessário
    # Se quiser manter todas exceto as temporárias:
    cols_to_keep = [c for c in df_merged.columns if not c.endswith("_td") and c not in ["Data_ajuste", "Data_Merge", "Tipo"]]
    
    # Atualiza a coluna Data original com o formato datetime correto
    df_merged["Data"] = pd.to_datetime(df_merged["Data_Merge"])
    
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