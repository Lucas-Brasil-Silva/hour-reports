import pandas as pd
from pathlib import Path
from typing import List

# --- CONFIGURAÇÕES E CONSTANTES ---
# ARQUIVO_ENTRADA = Path("RelatorioHorasExtras.xls")
ARQUIVO_SAIDA = Path("Relatorio_Tratado.xlsx")

INDICES_COLUNAS = [3, 8, 9, 10, 11, 12, 14]
JORNADA_PADRAO = pd.to_timedelta('08:48:00')

def carregar_dados(path: Path) -> pd.DataFrame:
    """Carrega o arquivo Excel verificando a extensão."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Define o motor de leitura baseado na extensão
    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    
    try:
        return pd.read_excel(path, usecols=INDICES_COLUNAS, engine=engine, header=None)
    except Exception as e:
        raise ValueError(f"Error reading excel: {e}")

def limpar_cabecalho(df: pd.DataFrame) -> pd.DataFrame:
    """Encontra o cabeçalho real e remove linhas desnecessárias."""

    try:
        idx_cabecalho = df[df.iloc[:, 0] == "Colaborador"].index[0]
    except IndexError:
        raise ValueError("A coluna 'Colaborador' não foi encontrada no arquivo.")

    # Ajusta o cabeçalho
    df.columns = df.iloc[idx_cabecalho]
    df = df.iloc[idx_cabecalho + 1:].copy()

    # Filtra linhas de repetição de cabeçalho e vazias
    df_limpo = df[
        (df["Colaborador"] != "Colaborador") & 
        (df["Colaborador"].notna())
    ].copy()
    
    return df_limpo.reset_index(drop=True)

def converter_para_tempo(df: pd.DataFrame, colunas: List[str]) -> pd.DataFrame:
    """Converte strings de hora (HH:MM) para objetos Timedelta."""
    for col in colunas:
        # Adiciona :00 e converte. 'coerce' transforma textos inválidos (como FALTAS) em NaT
        df[col + "_td"] = pd.to_timedelta(
            df[col].astype(str).str.strip() + ":00", 
            errors="coerce"
        )
    return df

def aplicar_calculos_horas(df: pd.DataFrame) -> pd.DataFrame:
    """Realiza a lógica de subtração de horas extras."""
    
    # Lógica: Se Trabalhadas == Extras (provavelmente feriado/folga trabalhada) 
    # E trabalhou mais que a jornada, subtrai a jornada.
    condicao_extra = (
        (df["Trabalhadas_td"] == df["Extras 01_td"]) & 
        (df["Trabalhadas_td"] > JORNADA_PADRAO)
    )
    
    df.loc[condicao_extra, "Extras 01_td"] = df.loc[condicao_extra, "Trabalhadas_td"] - JORNADA_PADRAO
    
    # Lógica: Se trabalhou MENOS que a jornada, zera a hora extra
    condicao_menor = df["Trabalhadas_td"] < JORNADA_PADRAO
    df.loc[condicao_menor, "Extras 01_td"] = pd.NaT  # NaT será convertido para vazio depois
    
    return df

def formatar_saida(df: pd.DataFrame) -> pd.DataFrame:
    """Formata colunas finais, aplica textos de Atestado/Falta e organiza."""
    
    # Função interna auxiliar
    def td_para_str(td):
        if pd.isnull(td): return ""
        total_seconds = int(td.total_seconds())
        horas = total_seconds // 3600
        minutos = (total_seconds % 3600) // 60
        return f"{horas:02d}:{minutos:02d}"

    # 1. Converte tempos calculados de volta para String
    df["Trabalhadas"] = df["Trabalhadas_td"].apply(td_para_str)
    df["Extras 01"] = df["Extras 01_td"].apply(td_para_str)

    # 2. Aplica regras de texto (ATESTADO/FALTA) 
    # IMPORTANTE: Fazemos isso AGORA, senão o cálculo matemático acima daria erro
    df.loc[df["Abonadas"] == "08:48", "Trabalhadas"] = "ATESTADO"
    df.loc[df["Atrasos"] == "-08:48", "Trabalhadas"] = "FALTA"

    # 3. Formatação visual (Trocar : por , e data)
    df["Trabalhadas"] = df["Trabalhadas"].str.replace(":", ",")
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors='coerce')

    # 4. Reordenar colunas
    cols = list(df.columns)
    if "Extras 01" in cols:
        cols.insert(3, cols.pop(cols.index("Extras 01")))
    
    # Remove colunas temporárias (_td) e as que não queremos mais
    cols_finais = [c for c in cols if not c.endswith("_td") and c not in ["Abonadas", "Atrasos"]]
    
    return df[cols_finais]

def main(path: str):
    print("--- Iniciando Processamento ---")
    
    # Pipeline de Execução (O fluxo lógico do script)
    try:
        path_ = Path(path)
        df_bruto = carregar_dados(path_)
        df_limpo = limpar_cabecalho(df_bruto)
        
        # Etapa de Transformação Matemática
        df_calculado = converter_para_tempo(df_limpo, ["Trabalhadas", "Extras 01"])
        df_calculado = aplicar_calculos_horas(df_calculado)
        
        # Etapa de Formatação Final
        df_final = formatar_saida(df_calculado)
        
        # Exportação
        df_final.to_excel(ARQUIVO_SAIDA, index=False)
        
    except Exception as e:
        raise Exception(f"Ocorreu um erro: {str(e)}")

if __name__ == "__main__":
    main()