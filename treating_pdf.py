import fitz
from pathlib import Path
import re

# INPUT_PDF = "C:/Users/lucas/Downloads/relatorio-geral-pdf.pdf"
TERMO_NOME = "Nome:"
TERMO_TOTAL = "Total:"
TERMO_MANUALMENTE = "manualmente"
OUTPUT_FOLDER = Path("pdfs_processados")

def sanitize_filenamme(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos."""
    # Mantém apenas letras, números, espaços, hífens e underlines
    return re.sub(r'[^\w\s-]', '', name).strip()

def get_employee_name(page: fitz.Page) -> str:
    """Busca o nome do funcionário na segunda ocorrência de 'Nome:'."""
    rects = page.search_for(TERMO_NOME)

    if len(rects) < 2:
        return "Nome_Nao_Encontrado"
    
    target_rect = rects[1]

    read_rect = fitz.Rect(
        target_rect.x1 + 5 ,
        target_rect.y0 - 2,
        target_rect.x1 + 120,
        target_rect.y1 + 2
    )
    raw_name = page.get_text("text", clip=read_rect).strip()
    clean_name = sanitize_filenamme(raw_name)
    return f"{clean_name}-" if clean_name else "Funcionario_sem_Nome"

def apply_redactions(page: fitz.Page, y_ref: float):
    """Aplica todas as tarjas de redação baseadas na coordenada Y de referência."""

    areas_to_redact = [
        fitz.Rect(432, 240, 580, y_ref + 10),
        # Lateral Direita Inferior (Metade)
        fitz.Rect(350, y_ref + 10, 600, y_ref + 110),
        # Área Central Inferior
        fitz.Rect(0, y_ref + 21, 600, y_ref + 110)
    ]

    for rect in areas_to_redact:
        page.add_redact_annot(rect)
    
    manual_occurrences = page.search_for(TERMO_MANUALMENTE)
    if manual_occurrences:
        y_manual = manual_occurrences[0].y0
        footer_rect = fitz.Rect(0, y_manual - 5, 600, y_manual + 55)
        page.add_redact_annot(footer_rect)
    
    page.apply_redactions(images=0, graphics=0)

def save_single_page(doc_origin: fitz.Document, page_idx: int, file_name: str):
    """Cria e salva um novo PDF contendo apenas a página especificada."""
    try:
        
        OUTPUT_FOLDER.mkdir(exist_ok=True)
        # Garante nome único caso já exista arquivo
        final_path = OUTPUT_FOLDER / f"{file_name}.pdf"
        counter = 2
        while final_path.exists():
            final_path = OUTPUT_FOLDER / f"{file_name}_v{counter}.pdf"
            counter += 1

        with fitz.open() as new_doc:
            new_doc.insert_pdf(doc_origin, from_page=page_idx, to_page=page_idx)
            new_doc.save(final_path)
        
    except Exception as e:
        raise Exception(f"Erro ao salvar {file_name}: {str(e)}")

def main(input_pdf: str):
    if not Path(input_pdf).exists():
        return

    try:
        # 'with' garante que o arquivo original seja fechado ao final
        with fitz.open(input_pdf) as doc:
            
            for index, page in enumerate(doc):

                # 1. Encontra a âncora principal (Total)
                search_total = page.search_for(TERMO_TOTAL)
                
                if not search_total:
                    continue
                
                # Pega a coordenada base (y1 = fundo do texto "Total")
                y_anchor = search_total[0].y1

                # 2. Aplica as redações
                apply_redactions(page, y_anchor)

                # 3. Identifica o nome
                employee_name = get_employee_name(page)

                # 4. Salva o novo arquivo
                save_single_page(doc, index, employee_name)

    except Exception as e:
        raise Exception(f"Erro fatal: {str(e)}")
        
if __name__ == "__main__":
    main()
