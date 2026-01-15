import fitz  # PyMuPDF

def apagar_area_em_todas_paginas(arquivo_entrada, arquivo_saida):
    
    doc = fitz.open(arquivo_entrada)

    for pagina in doc:
        area = pagina.search_for("Total:")[0].y1
        pagina.add_redact_annot(fitz.Rect((390, 240, 580, area + 10)))
        pagina.add_redact_annot(fitz.Rect((0, area + 10, 600, area + 110)))
        if pagina.search_for("manualmente") != []:
            area2 = pagina.search_for("manualmente")[0].y0
            pagina.add_redact_annot(fitz.Rect((0, area2 - 5, 600, area2 + 55)))
        
        pagina.apply_redactions(images=0, graphics=0)
        
    doc.save(arquivo_saida, garbage=4, deflate=True)
    doc.close()
    print(f"Documento '{arquivo_entrada}' processado com sucesso!")

apagar_area_em_todas_paginas("relatorio-geral-pdf.pdf", "folha_editada.pdf")