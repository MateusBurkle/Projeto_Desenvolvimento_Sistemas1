"""Regras de negócio do módulo 3 - equipamentos: UC07, UC08 (reaproveitado por UC10/UC11 no Módulo 4).
RF11, RF12; RN08, RN11, RN12; RN13/RN14/RN21 como regras de borda; RNF04.

Ponto de reuso para o Módulo 4: `mudar_situacao(...)`, que aplica TODAS as regras de transição e, para 'Doado',
grava a DOACAO na mesma transação.
"""
import sqlite3
from datetime import date

from app.equipamentos import imagens, repository
from app.equipamentos.schemas import converter_data_iso
from app.erros import ErroApi

# RF12 / DP-35
SIT_RECEBIDO = "Recebido"
SIT_EM_AVALIACAO = "Em avaliação"
SIT_DISPONIVEL = "Disponível"
SIT_VENDIDO = "Vendido"
SIT_DOADO = "Doado"
SIT_RECICLAGEM = "Destinado à reciclagem"
COND_A_AVALIAR = "A avaliar"
COND_SEM_REUSO = "Sem condições de reuso"
TIPO_ONG = "Cliente ONG"
SITUACAO_ORG_ATIVA = "Ativa"

_FINALIZADAS = (SIT_VENDIDO, SIT_DOADO)  # somente leitura (histórico)
_FINAIS = (SIT_VENDIDO, SIT_DOADO, SIT_RECICLAGEM)  # a situação não muda depois delas
_PERMITIDAS_SEM_REUSO = (SIT_RECEBIDO, SIT_EM_AVALIACAO, SIT_RECICLAGEM)  # RN12, UC08 FE2


def _para_dict(linha) -> dict:
    d = {k: linha[k] for k in ("id_equipamento", "identificacao", "id_categoria", "nome_categoria", "modelo",
                               "condicao", "origem", "situacao", "data_recebimento", "id_item_solicitacao")}
    d["categoria_ativa"] = bool(linha["categoria_ativa"])
    d["ativo"] = bool(linha["ativo"])
    d["imagem"] = linha["imagem"]
    d["imagem_url"] = imagens.url_publica(linha["imagem"])  # DP-90
    d["valor"] = None if linha["valor"] is None else float(linha["valor"])
    d["doacao"] = None if linha["id_doacao"] is None else {
        "id_doacao": linha["id_doacao"], "id_organizacao_ong": linha["id_organizacao_ong"],
        "nome_ong": linha["nome_ong"], "data_doacao": linha["data_doacao"],
    }
    return d


def _obter_ou_404(conexao, id_equipamento: int):
    linha = repository.buscar_por_id(conexao, id_equipamento)
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Equipamento não encontrado.")
    return linha


def _erro_identificacao_duplicada() -> ErroApi:
    return ErroApi(409, "IDENTIFICACAO_DUPLICADA", "Esta identificação já está em uso.", {"identificacao": "duplicada"})


def _exigir_nao_finalizado(linha) -> None:
    """Contrato: Vendido/Doado são somente leitura -> 422 EQUIPAMENTO_FINALIZADO."""
    if linha["situacao"] in _FINALIZADAS:
        raise ErroApi(422, "EQUIPAMENTO_FINALIZADO",
                      "Equipamento vendido ou doado não pode mais ser alterado (histórico preservado).",
                      {"situacao": linha["situacao"]})


def _exigir_regras_de_situacao(condicao: str, valor: float | None, situacao: str) -> None:
    """RN12, UC08 FE2 e DP-35: 'Sem condições de reuso' só em Recebido/Em avaliação/Destinado à reciclagem;
    'Disponível' exige condição apta e valor > 0."""
    if condicao == COND_SEM_REUSO and situacao not in _PERMITIDAS_SEM_REUSO:
        raise ErroApi(422, "SEM_CONDICOES_DE_REUSO",
                      "Equipamento sem condições de reuso só pode ser encaminhado à reciclagem.",
                      {"situacao": "não permitida para este equipamento"})
    if situacao == SIT_DISPONIVEL:
        faltando = {}
        if condicao == COND_A_AVALIAR:
            faltando["condicao"] = "deve ser avaliada antes de disponibilizar"
        if valor is None or valor <= 0:
            faltando["valor"] = "deve ser maior que zero para disponibilizar"
        if faltando:
            raise ErroApi(422, "TRANSICAO_INVALIDA",
                          "Para ficar Disponível o equipamento precisa de condição avaliada e valor maior que zero.",
                          faltando)


def _exigir_categoria_ativa(conexao, id_categoria: int) -> None:
    """RN08, UC07: a categoria precisa existir e estar Ativa."""
    categoria = repository.buscar_categoria(conexao, id_categoria)
    if categoria is None or not categoria["ativa"]:
        raise ErroApi(422, "CATEGORIA_INVALIDA", "Selecione uma categoria ativa.",
                      {"id_categoria": "inexistente ou inativa"})


def _exigir_item_solicitacao(conexao, id_item_solicitacao: int | None) -> None:
    """UC07 passo 4 (DP-33): se informado, deve existir."""
    if id_item_solicitacao is not None and not repository.item_solicitacao_existe(conexao, id_item_solicitacao):
        raise ErroApi(422, "ITEM_SOLICITACAO_INVALIDO", "O item de solicitação informado não existe.",
                      {"id_item_solicitacao": "inexistente"})


def _exigir_item_com_vaga(conexao, id_item_solicitacao: int | None) -> None:
    """DP-52, UC07 passo 4, UC10: o vínculo não pode deixar o item com mais equipamentos que a sua `quantidade`.
    Mesma contagem usada em solicitacoes.service.avaliar_item (todos os equipamentos vinculados ao item)."""
    if id_item_solicitacao is None:
        return
    from app.solicitacoes import repository as solicitacoes_repository  # import tardio (evita ciclo)
    quantidade = repository.buscar_quantidade_item(conexao, id_item_solicitacao)
    if quantidade is not None and solicitacoes_repository.contar_equipamentos_do_item(
            conexao, id_item_solicitacao) >= quantidade:
        raise ErroApi(422, "ITEM_COMPLETO", "Todas as unidades deste item já foram cadastradas.",
                      {"id_item_solicitacao": f"limite de {quantidade} unidade(s) já atingido"})


def _recalcular_solicitacoes(conexao, *ids_item) -> None:
    """UC10 passo 7, DP-40: recalcula a situação da solicitação na MESMA transação (sem commit).
    Import tardio: solicitacoes.service importa este módulo (evita ciclo)."""
    from app.solicitacoes import service as solicitacoes_service
    for id_item in {i for i in ids_item if i is not None}:
        solicitacoes_service.recalcular_situacao(conexao, id_item)


def listar(conexao, page, size, filtros: dict) -> dict:
    """UC07 FA1, RF11."""
    linhas, total = repository.listar(conexao, page, size, {
        **filtros,
        "data_recebimento_de": filtros["data_recebimento_de"].isoformat() if filtros.get("data_recebimento_de") else None,
        "data_recebimento_ate": filtros["data_recebimento_ate"].isoformat() if filtros.get("data_recebimento_ate") else None,
    })
    return {"items": [_para_dict(l) for l in linhas], "total": total, "page": page, "size": size}


def obter(conexao, id_equipamento: int) -> dict:
    """UC07 FA1: 404 se inexistente; traz a doação quando houver."""
    return _para_dict(_obter_ou_404(conexao, id_equipamento))


def criar(conexao, dados, *, commit: bool = True) -> dict:
    """UC07 fluxo principal, RN08, RN12. Ordem: 400 (schema) -> CATEGORIA_INVALIDA -> ITEM_SOLICITACAO_INVALIDO ->
    409 -> regras de situação (422). Nada é gravado em erro (UC07 FE1).
    `commit=False` (Módulo 4, UC10 passo 3): deixa a transação aberta; o chamador faz commit/rollback.
    Se vinculado a um item de solicitação, recalcula a situação da solicitação (DP-40) na mesma transação."""
    situacao = dados.situacao or SIT_RECEBIDO
    _exigir_categoria_ativa(conexao, dados.id_categoria)
    _exigir_item_solicitacao(conexao, dados.id_item_solicitacao)
    _exigir_item_com_vaga(conexao, dados.id_item_solicitacao)  # DP-52
    if repository.buscar_id_por_identificacao(conexao, dados.identificacao) is not None:
        raise _erro_identificacao_duplicada()
    if situacao in _FINALIZADAS:  # Vendido é efeito da venda (RN14); Doado exige a ONG (use PATCH /situacao)
        raise ErroApi(422, "TRANSICAO_INVALIDA",
                      "Na criação não é possível definir Vendido ou Doado; use a atualização de situação.",
                      {"situacao": "não permitida no cadastro"})
    _exigir_regras_de_situacao(dados.condicao, dados.valor, situacao)
    valores = dados.model_dump()
    valores["situacao"] = situacao
    try:
        novo_id = repository.inserir(conexao, valores)
        _recalcular_solicitacoes(conexao, dados.id_item_solicitacao)  # UC10 passo 7, DP-40
        if commit:
            conexao.commit()
    except sqlite3.IntegrityError:  # corrida entre duas requisições com a mesma identificação
        if commit:
            conexao.rollback()
        raise _erro_identificacao_duplicada()
    return obter(conexao, novo_id)


def alterar(conexao, id_equipamento: int, dados) -> dict:
    """UC07 FA1, RN08, RN12. Ordem: 400 (schema) -> 404 -> FINALIZADO -> CATEGORIA_INVALIDA (só se mudou) ->
    ITEM_SOLICITACAO_INVALIDO -> 409 (exclui o próprio) -> regras de situação (422). Não altera situação nem ativo."""
    atual = _obter_ou_404(conexao, id_equipamento)
    _exigir_nao_finalizado(atual)
    if dados.id_categoria != atual["id_categoria"]:
        _exigir_categoria_ativa(conexao, dados.id_categoria)
    # DP-53: campo omitido preserva o vínculo atual; null explícito desvincula
    id_item = dados.id_item_solicitacao if "id_item_solicitacao" in dados.model_fields_set else atual["id_item_solicitacao"]
    _exigir_item_solicitacao(conexao, id_item)
    if id_item != atual["id_item_solicitacao"]:  # DP-52: só quando o item muda
        _exigir_item_com_vaga(conexao, id_item)
    if repository.buscar_id_por_identificacao(conexao, dados.identificacao, excluir_id=id_equipamento) is not None:
        raise _erro_identificacao_duplicada()
    _exigir_regras_de_situacao(dados.condicao, dados.valor, atual["situacao"])
    try:
        valores = dados.model_dump()
        valores["id_item_solicitacao"] = id_item  # DP-53
        repository.atualizar(conexao, id_equipamento, valores)
        # UC10 passo 7, DP-40: condição/vínculo mudaram -> recalcula o item antigo e o novo, na mesma transação
        _recalcular_solicitacoes(conexao, atual["id_item_solicitacao"], id_item)
        conexao.commit()
    except sqlite3.IntegrityError:
        conexao.rollback()
        raise _erro_identificacao_duplicada()
    return obter(conexao, id_equipamento)


def alterar_ativo(conexao, id_equipamento: int, dados) -> dict:
    """UC07 FA2 (DP-30 opção A): desativa/reativa preservando o histórico. Finalizados bloqueados. Idempotente."""
    atual = _obter_ou_404(conexao, id_equipamento)
    _exigir_nao_finalizado(atual)
    if bool(atual["ativo"]) != dados.ativo:
        repository.atualizar_ativo(conexao, id_equipamento, dados.ativo)
        _recalcular_solicitacoes(conexao, atual["id_item_solicitacao"])  # UC10 passo 7, DP-40
        conexao.commit()
    return obter(conexao, id_equipamento)


def validar_entrada_situacao(situacao: str, id_organizacao_ong, data_doacao) -> None:
    """UC08 FE1 (400): 'Doado' exige id_organizacao_ong e data_doacao; nas demais situações devem estar ausentes."""
    campos = {}
    if situacao == SIT_DOADO:
        if id_organizacao_ong is None:
            campos["id_organizacao_ong"] = "obrigatório para doação"
        if data_doacao is None:
            campos["data_doacao"] = "obrigatório para doação"
    else:
        if id_organizacao_ong is not None:
            campos["id_organizacao_ong"] = "só é aceito quando a situação é Doado"
        if data_doacao is not None:
            campos["data_doacao"] = "só é aceito quando a situação é Doado"
    if campos:
        raise ErroApi(400, "DADOS_INVALIDOS", "Dados inválidos. Corrija os campos indicados.", campos)


def _erro_doacao(campo: str, texto: str) -> ErroApi:
    return ErroApi(422, "DOACAO_INVALIDA", "Dados da doação inválidos: " + texto + ".", {campo: texto})


def _validar_doacao(conexao, equipamento, id_organizacao_ong: int, data_doacao: str) -> None:
    """UC08 FE1, UC11 FE1, RN11: ONG Cliente ONG Ativa; data ISO não futura e não anterior ao recebimento."""
    ong = repository.buscar_organizacao(conexao, id_organizacao_ong)
    if ong is None:
        raise _erro_doacao("id_organizacao_ong", "organização inexistente")
    if ong["tipo"] != TIPO_ONG:
        raise _erro_doacao("id_organizacao_ong", "a organização precisa ser do tipo Cliente ONG")
    if ong["situacao"] != SITUACAO_ORG_ATIVA:
        raise _erro_doacao("id_organizacao_ong", "a organização precisa estar ativa")
    data = converter_data_iso(data_doacao)
    if data > date.today():
        raise _erro_doacao("data_doacao", "a data não pode ser futura")
    if data < date.fromisoformat(equipamento["data_recebimento"]):
        raise _erro_doacao("data_doacao", "a data não pode ser anterior à data de recebimento")


def mudar_situacao(conexao, id_equipamento: int, nova_situacao: str, id_organizacao_ong: int | None = None,
                   data_doacao: str | None = None, *, permitir_vendido: bool = False, commit: bool = True) -> dict:
    """UC08 (reaproveitável por UC10/UC11 no Módulo 4), RF12, RN11, RN12.

    Ordem das validações: 404 -> FINALIZADO -> TRANSICAO_INVALIDA (final / Vendido) -> idempotência ->
    SEM_CONDICOES_DE_REUSO -> condição/valor -> EQUIPAMENTO_INATIVO -> DOACAO_INVALIDA. Nada é gravado em erro.
    'Doado' grava a DOACAO na MESMA transação da mudança de situação (rollback se algo falhar).

    Parâmetros para o Módulo 4: `permitir_vendido=True` é o único caminho para 'Vendido' (efeito da confirmação da
    venda, RN14); `commit=False` deixa a transação aberta para o chamador agrupar com outras gravações (o chamador é
    quem faz commit/rollback). Os campos 400 (Doado sem ONG/data) são conferidos com `validar_entrada_situacao`.
    """
    atual = _obter_ou_404(conexao, id_equipamento)
    _exigir_nao_finalizado(atual)
    if atual["situacao"] == SIT_RECICLAGEM:  # final: não muda mais (DP-35)
        raise ErroApi(422, "TRANSICAO_INVALIDA", "Equipamento destinado à reciclagem não muda mais de situação.",
                      {"situacao": "situação final"})
    if nova_situacao == SIT_VENDIDO and not permitir_vendido:  # RN14: efeito da venda confirmada (Módulo 5)
        raise ErroApi(422, "TRANSICAO_INVALIDA", "A situação Vendido só é definida pela confirmação da venda.",
                      {"situacao": "não pode ser definida diretamente"})
    if nova_situacao == atual["situacao"]:  # idempotente (200)
        return _para_dict(atual)
    _exigir_regras_de_situacao(atual["condicao"], atual["valor"], nova_situacao)
    if nova_situacao == SIT_DOADO and atual["condicao"] == COND_A_AVALIAR:
        raise ErroApi(422, "TRANSICAO_INVALIDA", "Para ser doado o equipamento precisa de condição avaliada.",
                      {"condicao": "deve ser avaliada antes de doar"})
    if nova_situacao in (SIT_DISPONIVEL, SIT_DOADO) and not atual["ativo"]:  # UC07 FA2, DP-30
        raise ErroApi(422, "EQUIPAMENTO_INATIVO", "Equipamento inativo não pode ser disponibilizado nem doado.",
                      {"ativo": "equipamento inativo"})
    if nova_situacao == SIT_DOADO:
        _validar_doacao(conexao, atual, id_organizacao_ong, data_doacao)
    try:
        repository.atualizar_situacao(conexao, id_equipamento, nova_situacao)
        if nova_situacao == SIT_DOADO:
            repository.inserir_doacao(conexao, id_equipamento, id_organizacao_ong, data_doacao)  # mesma transação
        _recalcular_solicitacoes(conexao, atual["id_item_solicitacao"])  # UC10 passo 7, DP-40 (mesma transação)
        if commit:
            conexao.commit()
    except sqlite3.IntegrityError:
        if commit:
            conexao.rollback()
        raise _erro_doacao("id_organizacao_ong", "não foi possível registrar a doação")
    except Exception:
        if commit:
            conexao.rollback()
        raise
    return obter(conexao, id_equipamento)


def atualizar_situacao(conexao, id_equipamento: int, dados) -> dict:
    """UC08 (rota PATCH). Ordem: 400 -> 404 -> 422 (em `mudar_situacao`)."""
    validar_entrada_situacao(dados.situacao, dados.id_organizacao_ong, dados.data_doacao)
    return mudar_situacao(conexao, id_equipamento, dados.situacao, dados.id_organizacao_ong, dados.data_doacao)


def enviar_imagem(conexao, id_equipamento: int, conteudo: bytes) -> dict:
    """UC07, DP-84 a DP-87. Ordem: 404 -> EQUIPAMENTO_FINALIZADO -> IMAGEM_MUITO_GRANDE -> IMAGEM_TIPO_INVALIDO.
    Grava o arquivo novo (atômico), atualiza o banco e só então apaga o antigo; se o banco falhar, apaga o novo."""
    atual = _obter_ou_404(conexao, id_equipamento)
    _exigir_nao_finalizado(atual)
    novo = imagens.salvar(conteudo)  # levanta 422 (tamanho/tipo) sem gravar nada
    try:
        repository.atualizar_imagem(conexao, id_equipamento, novo)
        conexao.commit()
    except Exception:
        conexao.rollback()
        imagens.apagar(novo)
        raise
    imagens.apagar(atual["imagem"])  # DP-86
    return obter(conexao, id_equipamento)


def remover_imagem(conexao, id_equipamento: int) -> None:
    """UC07, DP-84/DP-86: apaga o arquivo e zera a coluna. Idempotente. Mesmo bloqueio de Vendido/Doado do PUT."""
    atual = _obter_ou_404(conexao, id_equipamento)
    _exigir_nao_finalizado(atual)
    if atual["imagem"] is None:
        return
    repository.atualizar_imagem(conexao, id_equipamento, None)
    conexao.commit()
    imagens.apagar(atual["imagem"])
