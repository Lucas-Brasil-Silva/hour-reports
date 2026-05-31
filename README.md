# 📊 Painel de Automação - Relatório de Horas

**Uma aplicação desktop moderna para automação de processamento de folhas de ponto e relatórios de horas trabalhadas.**

## ✨ Funcionalidades

### 1. 📄 **Processar Folha Ponto (PDF)**
- Extrai dados de PDFs de folha de ponto automaticamente
- Identifica o nome do funcionário e localiza informações-chave
- Aplica redações automáticas em áreas sensíveis (coordenadas específicas)
- Separa e salva cada página em um PDF individual por funcionário
- Filtra funcionários conforme configuração
- Mantém histórico de processamento em pasta dedicada

### 2. 📊 **Tratar Folha de Horas (Excel)**
- Carrega arquivos Excel com dados de horas trabalhadas
- Normaliza e limpa dados (remove linhas inválidas, padroniza formatos)
- Calcula automaticamente horas extras com regras de negócio
- Preenche dias faltantes do mês com dados estruturados
- Processa ajustes (férias, atestados, faltas)
- Substitui termos e categorias conforme configuração
- Gera relatório Excel final formatado

### 3. 🎨 **Interface Gráfica Moderna**
- Design limpo e intuitivo com tema escuro
- Dois botões principais com ícones
- Indicador de progresso durante processamento
- Notificações de status ao usuário
- Seletor de arquivos integrado
- Totalmente responsiva e acessível

## 🛠️ Tecnologias Utilizadas

- **Python 3.x** - Linguagem principal
- **Flet** - Framework para interface gráfica moderna e multiplataforma
- **pandas** - Processamento e análise de dados Excel
- **PyMuPDF (fitz)** - Manipulação e processamento de PDFs
- **openpyxl** - Suporte para arquivos Excel modernos
- **PyInstaller** - Empacotamento como executável Windows

## 📋 Requisitos do Sistema

- Windows 7+
- Python 3.8+ (para desenvolvimento)
- ~100 MB de espaço em disco

## 🚀 Como Usar

### Versão Desenvolvimento
```bash
# Clonar repositório
git clone https://github.com/seu-usuario/hour-reports.git
cd hour-reports

# Criar ambiente virtual (opcional, mas recomendado)
python -m venv venv
venv\Scripts\activate  # Windows
# ou
source venv/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Executar aplicação
python application.py
```

## 📁 Estrutura de Arquivos

```
hour-reports/
├── application.py           # Interface gráfica principal (Flet)
├── treaty_report.py         # Processamento de folha de horas (Excel)
├── treating_pdf.py          # Processamento de folha ponto (PDF)
├── grade.py                 # Utilitário para gerar grade de referência
├── requirements.txt         # Dependências do projeto
├── README.md               # Este arquivo
├── LICENSE                 # Licença do projeto
├── relatorio2.ipynb        # Notebook com análises/testes
└── pdfs_processados/       # Pasta de saída para PDFs processados
```

## ⚙️ Configuração

Edite as constantes nos arquivos de processamento conforme necessário:

### `treaty_report.py`
- `JORNADA_PADRAO` - Quantidade de horas diárias (padrão: 8:48)
- `NOMES_PARA_EXCLUIR` - Lista de colaboradores a filtrar
- `NOMES_PARA_SUBSTITUIR` - Dicionário de termos a padronizar

### `treating_pdf.py`
- `NOMES_PARA_EXCLUIR` - Funcionários cujos PDFs não serão salvos
- Coordenadas das áreas de redação (personalizável conforme layout do PDF)

## 📝 Licença

[Especifique a licença do seu projeto - MIT, Apache, etc.]