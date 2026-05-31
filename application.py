import os
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
os.environ["PYTHONHTTPSVERIFY"] = "0"

import flet as ft
import asyncio
import tkinter as tk
from tkinter import filedialog
import sys

try:
    import treating_pdf
    import treaty_report
except ImportError as e:
    print(f"Aviso: Scripts de processamento não encontrados. Erro: {e}")
    print("Usando modo simulação.")

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    sys.path.append(bundle_dir)

def processar_relatorio_horas(caminho_arquivo):
    if "treaty_report" not in globals():
        raise Exception("Módulo 'treaty_report' não foi importado corretamente.")
    
    try:
        # Tenta executar a função principal do seu módulo
        treaty_report.main(caminho_arquivo)
        return "Relatório de Horas gerado com sucesso!"
    except Exception as e:
        raise Exception(f"Falha no processamento do Relatório: {str(e)}")

def processar_folha_ponto(caminho_arquivo):
    if 'treating_pdf' not in globals():
        raise Exception("Módulo 'treating_pdf' não foi importado corretamente.")
        
    try:
        treating_pdf.main(caminho_arquivo)
        return "Folha ponto processada!"
    except Exception as e:
        raise Exception(f"Falha na edição do PDF: {str(e)}")

# --- CLASSE DA INTERFACE ---

class AutomacaoApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Painel de Automação"
        self.page.window_width = 400
        self.page.window_height = 500
        self.page.window_resizable = False
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        # Variável para saber qual botão foi clicado (estado)
        self.acao_atual = None 

        # Componentes da Interface
        self.criar_interface()

    def criar_interface(self):
        # Título Moderno
        titulo = ft.Text(
            "Painel de Automação", 
            size=24, 
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE
        )
        
        subtitulo = ft.Text(
            "Selecione a operação desejada", 
            size=12, 
            color=ft.Colors.GREY_400
        )

        # Botão 1: Relatório de Horas
        self.btn_horas = self.criar_botao_moderno(
            texto="Tratar Folha de Horas",
            icone=ft.Icons.TABLE_CHART,
            cor=ft.Colors.INDIGO,
            acao="horas"
        )

        # Botão 2: Outra Funcionalidade
        self.btn_folha = self.criar_botao_moderno(
            texto="Processar Folha Ponto",
            icone=ft.Icons.PICTURE_AS_PDF,
            cor=ft.Colors.TEAL,
            acao="folha"
        )

        # Barra de Progresso (Indeterminada) - Inicialmente invisível
        self.progress_ring = ft.ProgressRing(visible=False, color=ft.Colors.BLUE_400)
        self.status_text = ft.Text("", color=ft.Colors.GREY_400, size=12)

        # Container Principal (Cartão)
        card = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.AUTO_MODE, size=40, color=ft.Colors.BLUE_200),
                    titulo,
                    subtitulo,
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    self.btn_horas,
                    ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                    self.btn_folha,
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    self.progress_ring,
                    self.status_text
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=30,
            bgcolor=ft.Colors.GREY_900,
            border_radius=20,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            )
        )

        self.page.add(card)

    def criar_botao_moderno(self, texto, icone, cor, acao):
        return ft.Button( # Usa o botão genérico
            style=ft.ButtonStyle(
                bgcolor=cor,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=20,
            ),
            # Monta o conteúdo manualmente (Ícone + Texto)
            content=ft.Row(
                [
                    ft.Icon(icone, color=ft.Colors.WHITE),
                    ft.Text(texto, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            width=280,
            data=acao,
            on_click=self.preparar_selecao
        )

    def preparar_selecao(self, e):
        """Define qual ação será executada e abre o seletor."""
        self.acao_atual = e.control.data
        
        # Abrir diálogo de seleção de arquivo usando tkinter
        root = tk.Tk()
        root.withdraw()  # Esconde a janela principal
        root.attributes('-topmost', True)  # Coloca a janela na frente
        
        caminho_arquivo = None
        if self.acao_atual == "folha":
            caminho_arquivo = filedialog.askopenfilename(
                title="Selecione um arquivo",
                filetypes=[
                    ("PDF", "*.pdf*")
                ]
            )
            
        else:
            caminho_arquivo = filedialog.askopenfilenames(
                title="Selecione os arquivos",
                filetypes=[
                    ("XLS", "*.xls*")
                ]
            )
        
        root.destroy()
        
        if caminho_arquivo:
            # Executa o processamento em thread separada
            self.page.run_task(self.apos_selecionar_arquivo_interno, caminho_arquivo)
    
    async def apos_selecionar_arquivo_interno(self, caminho_arquivo):
        """Processa o arquivo selecionado."""
        # --- INÍCIO DO PROCESSAMENTO ---
        self.alternar_loading(True, "Processando arquivo... Aguarde.")
        
        try:
            mensagem = ""
            # Verifica qual botão foi clicado anteriormente
            if self.acao_atual == "horas":
                mensagem = await asyncio.to_thread(processar_relatorio_horas, caminho_arquivo)
            elif self.acao_atual == "folha":
                mensagem = await asyncio.to_thread(processar_folha_ponto, caminho_arquivo)
            
            # Feedback de Sucesso
            self.mostrar_snackbar(mensagem, ft.Colors.GREEN)

        except Exception as erro:
            # Feedback de Erro
            self.mostrar_snackbar(str(erro), ft.Colors.RED)
        
        finally:
            # --- FIM DO PROCESSAMENTO ---
            self.alternar_loading(False)
            self.acao_atual = None

    def alternar_loading(self, esta_carregando, text=""):
        """Controla a visibilidade do loader e desativa botões."""
        self.progress_ring.visible = esta_carregando
        self.status_text.value = text
        self.btn_horas.disabled = esta_carregando
        self.btn_folha.disabled = esta_carregando
        self.page.update()

    def mostrar_snackbar(self, text, cor):
        """Exibe mensagem no rodapé."""
        snack = ft.SnackBar(ft.Text(text), bgcolor=cor)
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

def main(page: ft.Page):
    app = AutomacaoApp(page)

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP)