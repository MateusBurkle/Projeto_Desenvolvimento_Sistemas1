# LEAF TI

E-commerce de reuso e descarte correto de equipamentos eletrônicos. O sistema cobre cadastro de organizações e equipamentos, avaliação de solicitações, vendas com nota fiscal simulada, doações e relatórios, para cinco perfis de usuário.

**Stack:** FastAPI (Python), SQLite, autenticação JWT, front-end em HTML/CSS/JavaScript com Bootstrap 5 (sem etapa de build).

## Sobre o projeto
Projeto acadêmico do curso de Sistemas de Informação (Projeto e Desenvolvimento de Sistemas), Universidade Presbiteriana Mackenzie.

## Requisitos
- Python 3.11 ou superior (desenvolvido e testado com 3.14)
- Git

## Como rodar (com dados de demonstração)

```
git clone <URL-do-repositorio>

# criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate.bat              # Windows cmd
# .\.venv\Scripts\Activate.ps1          # PowerShell
# source .venv/bin/activate             # Linux, macOS
# source .venv/Scripts/activate         # Git Bash no Windows

pip install -r requirements.txt

# variável de ambiente (desenvolvimento local): um texto longo e aleatório
set LEAF_JWT_SECRET=troque-por-um-texto-longo-e-aleatorio            # Windows cmd
# $env:LEAF_JWT_SECRET="troque-por-um-texto-longo-e-aleatorio"       # PowerShell
# export LEAF_JWT_SECRET="troque-por-um-texto-longo-e-aleatorio"     # Git Bash, Linux, macOS

# carregar os dados de demonstração
python -m scripts.popular_demonstracao

# subir o servidor (API + telas)
uvicorn app.main:app --reload
```

A aplicação lê as variáveis do terminal (não carrega `.env` sozinha); veja `.env.example` para a lista completa.

## Onde abrir
- Telas: http://127.0.0.1:8000/
- Documentação interativa da API: http://127.0.0.1:8000/docs

## Logins de demonstração
Senha de todos: `Demo@Folha2026`

| Perfil | E-mail |
|---|---|
| Administrador | admin@leafti.test |
| Administrador (extra) | admin2@leafti.test |
| Funcionário | funcionario@leafti.test |
| Cliente Empresa | empresa@leafti.test |
| Cliente ONG | ong@leafti.test |
| Empresa Doadora | doadora@leafti.test |

**Aviso:** logins, senha e dados são fictícios e existem só para demonstração local. Não use em produção (a carga se recusa a rodar com `LEAF_AMBIENTE=producao`).

## Testes
Dentro de `backend/`, com o ambiente virtual ativo: `pytest`

## Problemas comuns
- **Porta 8000 ocupada:** use `uvicorn app.main:app --reload --port 8001`.
- **`ModuleNotFoundError` / comando não encontrado:** o ambiente virtual não está ativo; repita o passo de ativação.
- **Banco antigo ou carga interrompida:** defina `LEAF_DB_PATH` com o caminho do banco e rode `python -m scripts.popular_demonstracao --reiniciar` (apaga só esse arquivo, depois de você digitar `SIM`).
- **Site parou de abrir:** o servidor encerra ao fechar o terminal; abra de novo, ative o ambiente e rode o `uvicorn`.
- A carga pode ser repetida: o que já existe é pulado.

## Autores

Projeto de Desenvolvimento de Sistemas, Curso de Sistemas de Informação, Universidade Presbiteriana Mackenzie (Alphaville, 2026). Orientadora: Dra. Sandra Bozolan.

| Nome | RA |
|---|---|
| Ana Beatriz dos Santos | 10434439 |
| Carlos Eduardo da Costa Oliveira | 10434492 |
| Cassio Silva Melo | 10434493 |
| Debora Farinelli Salvador | 10434463 |
| Isabela Siqueira da Silva | 10372156 |
| Mateus Burkle Nascimento | 10434370 |

## Licença
MIT (arquivo `LICENSE`).
