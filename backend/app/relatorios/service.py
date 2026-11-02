"""Regras dos relatórios (somente leitura). UC22, UC23, UC24; RN16, RN17, RN18, RN21; DP-57 a DP-60."""
import re
from datetime import date

from app.erros import ErroApi
from app.relatorios import repository, schemas

_ISO = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

# Situações sem destinação registrada (UC24 FE1; DP-60)
_SEM_DESTINACAO = {"Recebido", "Em avaliação", "Em manutenção", "Recondicionado"}
_DESTINACAO = {"Vendido": "Venda", "Doado": "Doação", "Destinado à reciclagem": "Reciclagem",
               "Disponível": "Venda (disponível)"}  # DP-59


def _data(valor: str | None) -> str | None:
    """Valida AAAA-MM-DD; None se ausente; levanta ValueError se inválida."""
    if valor is None or valor == "":
        return None
    if not _ISO.match(valor):
        raise ValueError(valor)
    date.fromisoformat(valor)
    return valor


def _periodos(de, ate):
    """Valida data_de/data_ate. Devolve (de, ate, campos_com_erro)."""
    campos, valores = {}, {}
    for nome, bruto in (("data_de", de), ("data_ate", ate)):
        try:
            valores[nome] = _data(bruto)
        except ValueError:
            campos[nome] = "data inválida (use AAAA-MM-DD)"
    if not campos and valores["data_de"] and valores["data_ate"] and valores["data_de"] > valores["data_ate"]:
        campos["data_de"] = "posterior à data final"
    return valores.get("data_de"), valores.get("data_ate"), campos


def _dinheiro(v) -> float:
    return round(float(v or 0), 2)


def relatorio_vendas(conexao, data_de, data_ate) -> dict:
    """UC22 fluxo principal, FA1, FE1; RF16; RN16."""
    campos = {n: "obrigatório" for n, v in (("data_de", data_de), ("data_ate", data_ate)) if not v}
    if campos:
        raise ErroApi(400, "PERIODO_INVALIDO", "Informe o período do relatório.", campos)  # UC22 passo 2-3
    de, ate, campos = _periodos(data_de, data_ate)
    if campos:
        raise ErroApi(400, "PERIODO_INVALIDO", "Período inválido. Corrija as datas informadas.", campos)  # FE1
    vendas: dict[int, dict] = {}
    for r in repository.vendas_confirmadas(conexao, de, ate):  # RN16: somente Confirmada
        v = vendas.setdefault(r["id_venda"], {
            "id_venda": r["id_venda"], "data_venda": r["data_venda"],
            "id_organizacao_cliente": r["id_organizacao_cliente"], "cliente": r["cliente"],
            "forma_pagamento": r["forma_pagamento"], "quantidade": 0, "valor_total": 0.0, "itens": []})
        if r["id_equipamento"] is not None:
            v["itens"].append({"id_equipamento": r["id_equipamento"], "identificacao": r["identificacao"],
                               "modelo": r["modelo"], "categoria": r["categoria"], "valor": _dinheiro(r["valor"])})
            v["quantidade"] += 1
            v["valor_total"] += float(r["valor"] or 0)
    lista = list(vendas.values())
    for v in lista:
        v["valor_total"] = _dinheiro(v["valor_total"])
    return {"data_de": de, "data_ate": ate, "vendas": lista, "total_vendas": len(lista),
            "total_equipamentos": sum(v["quantidade"] for v in lista),
            "valor_total": _dinheiro(sum(v["valor_total"] for v in lista))}  # RN16: soma das vendas listadas


def _validar_filtros(situacao, validas, data_de, data_ate):
    campos = {}
    if situacao is not None and situacao not in validas:
        campos["situacao"] = "situação inválida"
    de, ate, erros = _periodos(data_de, data_ate)
    campos.update(erros)
    if campos:
        raise ErroApi(400, "FILTRO_INVALIDO", "Filtros inválidos. Corrija os campos indicados.", campos)  # FE1
    return de, ate


def relatorio_equipamentos(conexao, id_categoria, situacao, data_de, data_ate, page, size) -> dict:
    """UC23 fluxo principal, FA1, FE1; RF17; RN17."""
    de, ate = _validar_filtros(situacao, schemas.SITUACOES_EQUIPAMENTO, data_de, data_ate)
    if id_categoria is not None and not 0 < id_categoria <= schemas.ID_MAX:
        id_categoria = 0  # nunca existe -> 200 vazio (RNF04)
    linhas, total, resumo = repository.equipamentos(
        conexao, {"id_categoria": id_categoria, "situacao": situacao, "data_de": de, "data_ate": ate}, page, size)
    items = []
    for r in linhas:
        sit = r["situacao"]
        detalhe = data = None
        if sit == "Vendido" and r["cliente_venda"]:
            detalhe, data = r["cliente_venda"], r["data_venda"]
        elif sit == "Doado" and r["ong"]:
            detalhe, data = r["ong"], r["data_doacao"]
        items.append({"id_equipamento": r["id_equipamento"], "identificacao": r["identificacao"],
                      "modelo": r["modelo"], "id_categoria": r["id_categoria"], "categoria": r["categoria"],
                      "condicao": r["condicao"], "situacao": sit, "ativo": bool(r["ativo"]),
                      "valor": None if r["valor"] is None else _dinheiro(r["valor"]),
                      "data_recebimento": r["data_recebimento"], "origem": r["origem"],
                      "destinacao": _DESTINACAO.get(sit),  # DP-59
                      "destino_detalhe": detalhe, "data_destinacao": data})
    return {"items": items, "total": total, "page": page, "size": size, "resumo_por_situacao": resumo}


def relatorio_organizacoes(conexao, id_doadora, situacao, data_de, data_ate, page, size) -> dict:
    """UC24 fluxo principal, FA1, FA2, FE1; RF18, RF21; RN18, RN21."""
    de, ate = _validar_filtros(situacao, schemas.SITUACOES_SOLICITACAO, data_de, data_ate)
    if id_doadora is not None and not 0 < id_doadora <= schemas.ID_MAX:
        id_doadora = 0
    linhas, total = repository.solicitacoes(
        conexao, {"id_organizacao_doadora": id_doadora, "situacao": situacao, "data_de": de, "data_ate": ate},
        page, size)
    itens_db = repository.itens_das_solicitacoes(conexao, [r["id_solicitacao"] for r in linhas])
    equips_db = repository.equipamentos_dos_itens(conexao, [i["id_item_solicitacao"] for i in itens_db])
    por_item: dict[int, list] = {}
    for e in equips_db:
        por_item.setdefault(e["id_item_solicitacao"], []).append(e)
    items = []
    for s in linhas:
        itens, pendencias = [], []
        for i in (x for x in itens_db if x["id_solicitacao"] == s["id_solicitacao"]):
            equipamentos = []
            for e in por_item.get(i["id_item_solicitacao"], []):
                doado = e["situacao"] == "Doado"  # FA2: reciclagem nunca associa venda/doação
                equipamentos.append({
                    "id_equipamento": e["id_equipamento"], "identificacao": e["identificacao"],
                    "condicao": e["condicao"], "situacao": e["situacao"],
                    "destinacao": _DESTINACAO.get(e["situacao"]),  # DP-59
                    "ong_beneficiada": e["ong"] if doado else None,
                    "data_doacao": e["data_doacao"] if doado else None})
                if e["condicao"] == "A avaliar":  # FE1
                    pendencias.append(f"Equipamento {e['id_equipamento']}: condição a avaliar")
                if e["situacao"] in _SEM_DESTINACAO:  # FE1: nunca apresentada como concluída
                    pendencias.append(f"Equipamento {e['id_equipamento']}: destinação não registrada")
            faltam = i["quantidade"] - len(equipamentos)
            if faltam > 0:
                pendencias.append(f"Item {i['id_item_solicitacao']}: faltam {faltam} equipamentos a cadastrar")
            itens.append({"id_item_solicitacao": i["id_item_solicitacao"], "tipo": i["tipo"], "modelo": i["modelo"],
                          "quantidade": i["quantidade"], "equipamentos_cadastrados": len(equipamentos),
                          "equipamentos": equipamentos})
        items.append({"id_solicitacao": s["id_solicitacao"], "id_organizacao_doadora": s["id_organizacao_doadora"],
                      "empresa_doadora": s["empresa_doadora"], "data_solicitacao": s["data_solicitacao"],
                      "situacao": s["situacao"], "avaliacao_pendente": bool(pendencias),
                      "pendencias": pendencias, "itens": itens})  # RN18: inclui mesmo sem destinação final
    return {"items": items, "total": total, "page": page, "size": size}
