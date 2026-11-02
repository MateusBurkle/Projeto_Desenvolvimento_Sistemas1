"""Regras de negócio do módulo 4 - solicitações: UC09, UC10, UC11 (ponto de entrada da doação), UC20.
RF05, RF10, RF11, RF12, RF21; RN03, RN04, RN05, RN10, RN11, RN12, RN21; RNF05.

Reuso do Módulo 3: `equipamentos.service.criar` (avaliar = cadastrar a unidade, DP-41) e `mudar_situacao`
(destinação, DP-42), ambos com `commit=False` para agrupar a gravação com a situação da solicitação.

Ponto de reuso inverso: `recalcular_situacao(conexao, id_item_solicitacao)` é chamada pelo Módulo 3 (e pela venda do
Módulo 5) na mesma transação, sem commit (DP-40).
"""
import sqlite3
from datetime import date

from app.equipamentos import service as equipamentos_service
from app.equipamentos.schemas import EquipamentoCriar
from app.erros import ErroApi
from app.permissoes import EMPRESA_DOADORA
from app.solicitacoes import repository

# DP-40: situações da solicitação
SIT_AGUARDANDO = "Aguardando avaliação"
SIT_EM_AVALIACAO = "Em avaliação"
SIT_AVALIADA = "Avaliada"

TIPO_ORG_ATIVA = "Ativa"

# DP-42: destinação -> situação do equipamento
_SITUACAO_POR_DESTINACAO = {"Venda": "Disponível", "Doação": "Doado", "Reciclagem": "Destinado à reciclagem"}
# situações que já correspondem a cada destinação (Vendido é consequência da venda de um item Disponível)
_SITUACOES_QUE_CORRESPONDEM = {
    "Venda": ("Disponível", "Vendido"),
    "Doação": ("Doado",),
    "Reciclagem": ("Destinado à reciclagem",),
}


def _destinacao_da_situacao(situacao: str) -> str | None:
    """UC20 passo 3 (DP-42): destinação derivada da situação; pendente (None) nas demais."""
    if situacao in ("Disponível", "Vendido"):
        return "Venda"
    if situacao == "Doado":
        return "Doação"
    if situacao == "Destinado à reciclagem":
        return "Reciclagem"
    return None


def _checar_acesso(usuario: dict, solicitacao) -> None:
    """RN05, RN04, RNF05, UC20 FE1: Empresa Doadora só acessa a própria organização; outra -> 404 (não vaza existência)."""
    if usuario["perfil"] == EMPRESA_DOADORA and usuario["id_organizacao"] != solicitacao["id_organizacao_doadora"]:
        raise ErroApi(404, "NAO_ENCONTRADO", "Solicitação não encontrada.")


def _obter_solicitacao_ou_404(conexao, id_solicitacao: int):
    solicitacao = repository.buscar_solicitacao(conexao, id_solicitacao)
    if solicitacao is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Solicitação não encontrada.")
    return solicitacao


def _equipamento_para_dict(linha, ver_valor: bool) -> dict:
    d = {
        "id_equipamento": linha["id_equipamento"], "identificacao": linha["identificacao"],
        "id_categoria": linha["id_categoria"], "categoria_nome": linha["categoria_nome"], "modelo": linha["modelo"],
        "condicao": linha["condicao"], "situacao": linha["situacao"], "ativo": bool(linha["ativo"]),
        "data_recebimento": linha["data_recebimento"], "destinacao": _destinacao_da_situacao(linha["situacao"]),
        "id_organizacao_ong": linha["id_organizacao_ong"], "nome_ong": linha["nome_ong"],
        "data_doacao": linha["data_doacao"],
    }
    if ver_valor:  # UC20: a Empresa Doadora não recebe o valor do equipamento
        d["valor"] = None if linha["valor"] is None else float(linha["valor"])
    return d


def _montar_detalhe(conexao, solicitacao, ver_valor: bool) -> dict:
    """UC09 FA1, UC10 passo 2, UC20 passo 3-4: solicitação com itens, equipamentos avaliados e pendências."""
    contagens = {c["id_item_solicitacao"]: c for c in repository.contagens_dos_itens(conexao, solicitacao["id_solicitacao"])}
    por_item: dict[int, list] = {}
    for linha in repository.listar_equipamentos(conexao, solicitacao["id_solicitacao"]):
        por_item.setdefault(linha["id_item_solicitacao"], []).append(_equipamento_para_dict(linha, ver_valor))
    itens, pendencias = [], []
    for item in repository.listar_itens(conexao, solicitacao["id_solicitacao"]):
        c = contagens[item["id_item_solicitacao"]]
        cadastrada, avaliada, quantidade = c["cadastrada"], c["avaliada"], item["quantidade"]
        avaliado = cadastrada == quantidade and avaliada == quantidade  # DP-41
        itens.append({
            "id_item_solicitacao": item["id_item_solicitacao"], "tipo": item["tipo"], "modelo": item["modelo"],
            "quantidade": quantidade, "quantidade_cadastrada": cadastrada, "quantidade_avaliada": avaliada,
            "avaliado": avaliado, "equipamentos": por_item.get(item["id_item_solicitacao"], []),
        })
        if not avaliado:  # UC10 FE2: o que falta para concluir
            rotulo = f"{item['tipo']} {item['modelo']}"
            if cadastrada < quantidade:
                pendencias.append(f"{rotulo}: faltam {quantidade - cadastrada} unidade(s) a avaliar")
            if cadastrada > avaliada:
                pendencias.append(f"{rotulo}: {cadastrada - avaliada} unidade(s) sem condição avaliada ou sem destinação")
    return {
        "id_solicitacao": solicitacao["id_solicitacao"], "id_organizacao_doadora": solicitacao["id_organizacao_doadora"],
        "nome_organizacao": solicitacao["nome_organizacao"], "data_solicitacao": solicitacao["data_solicitacao"],
        "situacao": solicitacao["situacao"], "pendencias": pendencias, "itens": itens,
    }


def recalcular_situacao(conexao: sqlite3.Connection, id_item_solicitacao: int | None) -> None:
    """UC10 passo 7, FE2, DP-40. Recalcula a situação da solicitação do item, SEM commit (mesma transação do chamador).

    Nenhum equipamento vinculado -> 'Aguardando avaliação'; algum vinculado -> 'Em avaliação'; todos os itens avaliados
    (DP-41: `quantidade` equipamentos, condição avaliada e destinação registrada) -> 'Avaliada'. Item inexistente
    ou None é ignorado (equipamento avulso)."""
    if id_item_solicitacao is None:
        return
    dono = repository.buscar_solicitacao_do_item(conexao, id_item_solicitacao)
    if dono is None:
        return
    contagens = repository.contagens_dos_itens(conexao, dono["id_solicitacao"])
    if not any(c["cadastrada"] for c in contagens):
        nova = SIT_AGUARDANDO
    elif all(c["cadastrada"] == c["quantidade"] and c["avaliada"] == c["quantidade"] for c in contagens):
        nova = SIT_AVALIADA
    else:
        nova = SIT_EM_AVALIACAO
    if nova != dono["situacao"]:
        repository.atualizar_situacao(conexao, dono["id_solicitacao"], nova)


def listar(conexao, usuario: dict, page: int, size: int, filtros: dict) -> dict:
    """UC20 passo 1-3 (Empresa Doadora: só a própria organização), UC10 passo 1 (Administrador/Funcionário: todas)."""
    filtros = dict(filtros)
    if usuario["perfil"] == EMPRESA_DOADORA:  # RN05, RN04: o filtro do cliente é ignorado
        filtros["id_organizacao_doadora"] = usuario["id_organizacao"] if usuario["id_organizacao"] is not None else -1
    for chave in ("data_de", "data_ate"):
        if filtros.get(chave) is not None:
            filtros[chave] = filtros[chave].isoformat()
    linhas, total = repository.listar(conexao, page, size, filtros)
    return {"items": [dict(l) for l in linhas], "total": total, "page": page, "size": size}


def obter(conexao, usuario: dict, id_solicitacao: int) -> dict:
    """UC09 FA1, UC10 passo 2, UC20 passo 3-4, UC20 FE1: 404 se inexistente ou de outra organização."""
    solicitacao = _obter_solicitacao_ou_404(conexao, id_solicitacao)
    _checar_acesso(usuario, solicitacao)
    return _montar_detalhe(conexao, solicitacao, ver_valor=usuario["perfil"] != EMPRESA_DOADORA)


def criar(conexao, usuario: dict, dados) -> dict:
    """UC09 fluxo principal, RN05, RN10, RN21. Ordem: 400 (schema) -> ORGANIZACAO_INATIVA (FE2) -> PARCERIA_INATIVA (FE3).
    Organização vem do token. Solicitação e itens gravados na mesma transação; não disponibiliza nada (RN21)."""
    id_organizacao = usuario["id_organizacao"]
    organizacao = repository.buscar_organizacao(conexao, id_organizacao) if id_organizacao is not None else None
    if organizacao is None or organizacao["situacao"] != TIPO_ORG_ATIVA:  # UC09 FE2, RN05
        raise ErroApi(422, "ORGANIZACAO_INATIVA", "A organização está inativa e não pode enviar novas solicitações.")
    if not repository.parceria_doadora_ativa(conexao, id_organizacao):  # UC09 FE3, RN10
        raise ErroApi(422, "PARCERIA_INATIVA",
                      "A Empresa Doadora precisa de vínculo de parceria ativo para solicitar avaliação.")
    try:
        id_solicitacao = repository.inserir_solicitacao(conexao, id_organizacao, date.today().isoformat(), SIT_AGUARDANDO)
        for item in dados.itens:  # RN11: tipo, modelo e quantidade ficam registrados
            repository.inserir_item(conexao, id_solicitacao, item.tipo, item.modelo, item.quantidade)
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    return obter(conexao, usuario, id_solicitacao)


def avaliar_item(conexao, id_solicitacao: int, id_item_solicitacao: int, dados) -> dict:
    """UC10 passo 3 (DP-41), RN03, RN11, RN21. Ordem: 400 -> 404 (item de outra solicitação também) -> ITEM_COMPLETO ->
    regras do Módulo 3 (CATEGORIA_INVALIDA, 409 IDENTIFICACAO_DUPLICADA, regras de situação). Cria o equipamento
    vinculado e recalcula a situação da solicitação na mesma transação."""
    _obter_solicitacao_ou_404(conexao, id_solicitacao)
    item = repository.buscar_item(conexao, id_item_solicitacao)
    if item is None or item["id_solicitacao"] != id_solicitacao:
        raise ErroApi(404, "NAO_ENCONTRADO", "Item de solicitação não encontrado.")
    if repository.contar_equipamentos_do_item(conexao, id_item_solicitacao) >= item["quantidade"]:
        raise ErroApi(422, "ITEM_COMPLETO", "Todas as unidades deste item já foram cadastradas.",
                      {"quantidade": f"limite de {item['quantidade']} unidade(s)"})
    entrada = EquipamentoCriar(
        identificacao=dados.identificacao, id_categoria=dados.id_categoria, modelo=item["modelo"],
        condicao=dados.condicao, origem=dados.origem or f"Solicitação {id_solicitacao}",
        data_recebimento=dados.data_recebimento, valor=dados.valor, id_item_solicitacao=id_item_solicitacao,
        situacao=dados.situacao,
    )
    try:
        equipamento = equipamentos_service.criar(conexao, entrada, commit=False)  # recalcula a solicitação internamente
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    linha = next(l for l in repository.listar_equipamentos(conexao, id_solicitacao)
                 if l["id_equipamento"] == equipamento["id_equipamento"])
    return _equipamento_para_dict(linha, ver_valor=True)


def validar_destinacao(dados) -> None:
    """UC11 FE1 (400): Doação exige ONG e data; Venda e Reciclagem rejeitam esses campos."""
    campos = {}
    if dados.destinacao == "Doação":
        if dados.id_organizacao_ong is None:
            campos["id_organizacao_ong"] = "obrigatório para doação"
        if dados.data_doacao is None:
            campos["data_doacao"] = "obrigatório para doação"
    else:
        if dados.id_organizacao_ong is not None:
            campos["id_organizacao_ong"] = "só é aceito para doação"
        if dados.data_doacao is not None:
            campos["data_doacao"] = "só é aceito para doação"
    if campos:
        raise ErroApi(400, "DADOS_INVALIDOS", "Dados inválidos. Corrija os campos indicados.", campos)


def definir_destinacao(conexao, usuario: dict, id_solicitacao: int, id_equipamento: int, dados) -> dict:
    """UC10 passo 4-7, UC11, FE1, FA1, RN11, RN12, RN21 (DP-42). Ordem: 400 -> 404 (solicitação / equipamento fora dela) ->
    CONDICAO_NAO_AVALIADA (DP-54) -> idempotência -> regras do Módulo 3 em `mudar_situacao` (EQUIPAMENTO_FINALIZADO, TRANSICAO_INVALIDA,
    SEM_CONDICOES_DE_REUSO, EQUIPAMENTO_INATIVO, DOACAO_INVALIDA). Situação do equipamento, DOACAO e situação da
    solicitação são gravadas na mesma transação."""
    validar_destinacao(dados)
    _obter_solicitacao_ou_404(conexao, id_solicitacao)
    vinculado = repository.buscar_equipamento_vinculado(conexao, id_solicitacao, id_equipamento)
    if vinculado is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Equipamento não encontrado nesta solicitação.")
    if vinculado["condicao"] == "A avaliar":  # DP-54, UC10 passo 3-4, FE2: avalie a condição antes da destinação
        raise ErroApi(422, "CONDICAO_NAO_AVALIADA", "Avalie a condição do equipamento antes de definir a destinação.",
                      {"condicao": "A avaliar"})
    if vinculado["situacao"] not in _SITUACOES_QUE_CORRESPONDEM[dados.destinacao]:  # idempotente se já corresponde
        try:
            equipamentos_service.mudar_situacao(
                conexao, id_equipamento, _SITUACAO_POR_DESTINACAO[dados.destinacao],
                dados.id_organizacao_ong, dados.data_doacao, commit=False,  # recalcula a solicitação internamente
            )
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
    return obter(conexao, usuario, id_solicitacao)
