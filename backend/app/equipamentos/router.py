"""Rotas do módulo 3 - equipamentos (contrato modulo-3.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, UploadFile

from app.db import get_conexao
from app.dependencias import exigir_perfis
from app.equipamentos import imagens, schemas, service
from app.erros import ErroApi
from app.permissoes import ADMINISTRADOR, FUNCIONARIO

router = APIRouter(tags=["Equipamentos"])


def _checar_id(id_equipamento: int) -> None:
    # RNF04: id acima de 2^63-1 não existe no banco; devolve 404 em vez de estourar o sqlite3
    if id_equipamento > schemas.ID_MAX:
        raise ErroApi(404, "NAO_ENCONTRADO", "Equipamento não encontrado.")

_admin_ou_funcionario = exigir_perfis(ADMINISTRADOR, FUNCIONARIO)


@router.get("/equipamentos", response_model=schemas.PaginaEquipamentos, operation_id="listarEquipamentos")
def listar(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), id_categoria: int | None = Query(None, le=schemas.ID_MAX),
           situacao: schemas.Situacao | None = None, condicao: schemas.Condicao | None = None,
           ativo: bool | None = None, q: str | None = Query(None, max_length=150),
           data_recebimento_de: date | None = None, data_recebimento_ate: date | None = None,
           _: dict = Depends(_admin_ou_funcionario), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC07 FA1, RF11: lista com filtros (Administrador e Funcionário)
    filtros = {"id_categoria": id_categoria, "situacao": situacao, "condicao": condicao, "ativo": ativo, "q": q,
               "data_recebimento_de": data_recebimento_de, "data_recebimento_ate": data_recebimento_ate}
    return service.listar(conexao, page, size, filtros)


@router.post("/equipamentos", response_model=schemas.Equipamento, status_code=201, operation_id="criarEquipamento")
def criar(dados: schemas.EquipamentoCriar, _: dict = Depends(_admin_ou_funcionario),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC07, RF11, RN08, RN12, RNF04: cadastra equipamento (Administrador e Funcionário)
    return service.criar(conexao, dados)


@router.get("/equipamentos/{id_equipamento}", response_model=schemas.Equipamento, operation_id="obterEquipamento")
def obter(id_equipamento: int, _: dict = Depends(_admin_ou_funcionario),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC07 FA1, RF11: consulta um equipamento (com a doação, se houver)
    _checar_id(id_equipamento)
    return service.obter(conexao, id_equipamento)


@router.put("/equipamentos/{id_equipamento}", response_model=schemas.Equipamento, operation_id="alterarEquipamento")
def alterar(id_equipamento: int, dados: schemas.EquipamentoAlterar, _: dict = Depends(_admin_ou_funcionario),
            conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC07 FA1, RN08, RN12: altera dados descritivos; Vendido/Doado são somente leitura
    _checar_id(id_equipamento)
    return service.alterar(conexao, id_equipamento, dados)


@router.patch("/equipamentos/{id_equipamento}/situacao", response_model=schemas.Equipamento,
              operation_id="atualizarSituacaoEquipamento")
def atualizar_situacao(id_equipamento: int, dados: schemas.SituacaoEntrada,
                       _: dict = Depends(_admin_ou_funcionario), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC08, RF12, RN11, RN12 (UC08 FE1/FE2; reaproveitado por UC10/UC11): atualiza a situação; Doado grava DOACAO
    _checar_id(id_equipamento)
    return service.atualizar_situacao(conexao, id_equipamento, dados)


@router.patch("/equipamentos/{id_equipamento}/ativo", response_model=schemas.Equipamento,
              operation_id="alterarAtivoEquipamento")
def alterar_ativo(id_equipamento: int, dados: schemas.AtivoEntrada, _: dict = Depends(_admin_ou_funcionario),
                  conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC07 FA2 (DP-30 opção A): desativa ou reativa, sem exclusão física
    _checar_id(id_equipamento)
    return service.alterar_ativo(conexao, id_equipamento, dados)


@router.put("/equipamentos/{id_equipamento}/imagem", response_model=schemas.Equipamento,
            operation_id="enviarImagemEquipamento")
def enviar_imagem(id_equipamento: int, arquivo: UploadFile, _: dict = Depends(_admin_ou_funcionario),
                  conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC07, DP-84 a DP-87: anexa/substitui a imagem (lê no máximo 2 MB + 1 byte; tipo pelo conteúdo)
    _checar_id(id_equipamento)
    conteudo = arquivo.file.read(imagens.TAMANHO_MAX + 1)
    return service.enviar_imagem(conexao, id_equipamento, conteudo)


@router.delete("/equipamentos/{id_equipamento}/imagem", status_code=204, operation_id="removerImagemEquipamento")
def remover_imagem(id_equipamento: int, _: dict = Depends(_admin_ou_funcionario),
                   conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC07, DP-84, DP-86: remove a imagem (204 idempotente)
    _checar_id(id_equipamento)
    service.remover_imagem(conexao, id_equipamento)
    return Response(status_code=204)


@router.get("/imagens/equipamentos/{nome_arquivo}", tags=["Imagens"], operation_id="obterArquivoImagemEquipamento")
def obter_arquivo_imagem(nome_arquivo: str):
    # UC12, DP-86 (público): serve só o arquivo, como imagem estática; nome fora do padrão -> 404
    return imagens.resposta_arquivo(nome_arquivo)
