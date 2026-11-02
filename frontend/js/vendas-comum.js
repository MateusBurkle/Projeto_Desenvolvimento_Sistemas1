/* Funções comuns às telas do Módulo 5 (catálogo, compras, vendas, notas fiscais).
   UC12 a UC18, UC21; RF04, RF13 a RF15, RF19, RF20; RN13 a RN15, RN19, RN20; DP-45 a DP-51; RNF04, RNF06.
   Não faz chamadas à API além de Api.baixar (js/api.js). Reaproveita UsuariosUi, EquipUi e SolUi. Expõe VendasUi. */
(function (global) {
  'use strict';
  var U = global.UsuariosUi, E = global.EquipUi, S = global.SolUi;

  /* Valores exatos do contrato (modulo-5.yaml: SituacaoVenda e FormaPagamento) */
  var SITUACOES = ['Pendente', 'Confirmada', 'Cancelada'];
  var FORMAS = ['Pix', 'Boleto', 'Transferência bancária', 'Cartão de crédito'];

  /* Mensagens em português por código (usadas se a API não enviar "mensagem"). */
  var MSG = {
    ITEM_INDISPONIVEL: 'Há equipamentos indisponíveis no pedido. Retire-os e tente novamente.',
    CLIENTE_INATIVO: 'A organização compradora está inativa. A operação não pode ser concluída.',
    VENDA_NAO_PENDENTE: 'Este pedido não está mais pendente e agora é somente leitura.',
    FALHA_ESTOQUE: 'Não foi possível atualizar o estoque. A venda continua pendente; tente novamente.',
    VENDA_NAO_CONFIRMADA: 'A nota só pode ser emitida para venda confirmada.',
    VENDA_INCONSISTENTE: 'Os dados da venda estão inconsistentes. A nota não foi emitida.',
    NAO_ENCONTRADO: 'Registro não encontrado ou sem acesso. Atualize a lista e tente novamente.',
    SEM_PERMISSAO: 'Você não tem permissão para realizar esta ação.'
  };
  function msgErro(err) {
    return (err && err.mensagem) || MSG[err && err.codigo] || S.MSG[err && err.codigo] || 'Ocorreu um erro inesperado. Tente novamente.';
  }

  /* ---------- selos: texto + ícone (nunca só cor, RNF06) ---------- */
  var ICONE = { 'Pendente': '…', 'Confirmada': '✔', 'Cancelada': '–' };
  var CLASSE = { 'Pendente': 'selo-sol-aguardando', 'Confirmada': 'selo-sol-avaliada', 'Cancelada': 'selo-inativa' };
  function seloVenda(s) {
    return '<span class="selo-situacao ' + (CLASSE[s] || 'selo-sol-andamento') + '">' + (ICONE[s] || '•') + '&#xFE0E; ' + U.esc(s) + '</span>';
  }

  /* UC13 FE1: "indisponíveis: 12, 15" -> [12, 15] */
  function idsIndisponiveis(err) {
    var t = err && err.campos && err.campos.ids_equipamento;
    if (!t) { return []; }
    return (String(t).match(/\d+/g) || []).map(Number);
  }

  /* Lê uma lista de ids digitados (separados por vírgula, espaço ou ponto e vírgula). */
  function lerIds(texto) {
    var partes = String(texto || '').split(/[\s,;]+/).filter(Boolean), ids = [], ruim = [];
    partes.forEach(function (p) { if (/^[1-9]\d{0,17}$/.test(p)) { ids.push(Number(p)); } else { ruim.push(p); } });
    return { ids: ids, invalidos: ruim };
  }

  /* ---------- lista de vendas/pedidos (UC18, UC21) ---------- */
  function cabecalhoVendas(comCliente) {
    return '<th scope="col">Pedido</th>' + (comCliente ? '<th scope="col">Cliente</th>' : '') +
      '<th scope="col">Data</th><th scope="col">Situação</th><th scope="col">Itens</th><th scope="col">Valor total</th>' +
      '<th scope="col">Nota fiscal</th><th scope="col">Ações</th>';
  }
  function linhaVenda(v, comCliente) {
    return '<tr>' +
      '<td data-rotulo="Pedido"><strong>nº ' + v.id_venda + '</strong></td>' +
      (comCliente ? '<td data-rotulo="Cliente">' + U.esc(v.nome_organizacao) + '</td>' : '') +
      '<td data-rotulo="Data">' + E.formatarData(v.data_venda) + '</td>' +
      '<td data-rotulo="Situação">' + seloVenda(v.situacao) + '</td>' +
      '<td data-rotulo="Itens">' + v.quantidade + '</td>' +
      '<td data-rotulo="Valor">' + E.formatarValor(v.valor_total) + '</td>' +
      '<td data-rotulo="Nota fiscal">' + (v.possui_nota ? 'Emitida' : '—') + '</td>' +
      '<td class="acoes" data-rotulo="Ações"><div class="grupo-acoes"><button type="button" class="btn btn-outline-leaf" data-acao="ver" data-id="' + v.id_venda +
        '" aria-label="Consultar detalhes do pedido ' + v.id_venda + '">Detalhes</button></div></td></tr>';
  }

  /* ---------- detalhe ---------- */
  function dadosVenda(v, comCliente, semLinkNota) {
    var nota = v.nota_fiscal && semLinkNota
      ? U.esc(v.nota_fiscal.numero) + ' (emitida em ' + E.formatarData(v.nota_fiscal.data_emissao) + ')'
      : v.nota_fiscal
      ? '<a href="../notas-fiscais/index.html?id=' + v.nota_fiscal.id_nota + '">' + U.esc(v.nota_fiscal.numero) + '</a> (emitida em ' + E.formatarData(v.nota_fiscal.data_emissao) + ')'
      : 'Nenhuma nota emitida';
    return '<dl class="dados-sol">' +
      '<dt>Pedido</dt><dd>nº ' + v.id_venda + '</dd>' +
      (comCliente ? '<dt>Cliente Empresa</dt><dd>' + U.esc(v.nome_organizacao) + '</dd>' : '') +
      '<dt>Data</dt><dd>' + E.formatarData(v.data_venda) + '</dd>' +
      '<dt>Situação</dt><dd>' + seloVenda(v.situacao) + '</dd>' +
      '<dt>Forma de pagamento</dt><dd>' + U.esc(v.forma_pagamento === 'A definir' ? 'A definir (informada na confirmação)' : v.forma_pagamento) + '</dd>' +
      '<dt>Nota fiscal</dt><dd>' + nota + '</dd></dl>';
  }
  function tabelaItens(v) {
    var linhas = (v.itens || []).map(function (i) {
      return '<tr data-eq="' + i.id_equipamento + '"><td data-rotulo="Identificação"><strong>' + U.esc(i.identificacao) + '</strong><span class="sub">' + U.esc(i.categoria_nome) + '</span></td>' +
        '<td data-rotulo="Modelo">' + U.esc(i.modelo) + '</td>' +
        '<td data-rotulo="Condição">' + U.esc(i.condicao) + '</td>' +
        '<td data-rotulo="Valor">' + E.formatarValor(i.valor) + '</td></tr>';
    }).join('');
    return '<div class="table-responsive"><table class="table table-hover tabela-usuarios tabela-equip mb-2">' +
      '<caption class="visually-hidden">Equipamentos do pedido</caption><thead><tr><th scope="col">Equipamento</th><th scope="col">Modelo</th>' +
      '<th scope="col">Condição</th><th scope="col">Valor</th></tr></thead><tbody>' + linhas + '</tbody></table></div>' +
      '<p class="fs-5 mb-0"><strong>Quantidade: ' + v.quantidade + (v.quantidade === 1 ? ' item' : ' itens') + ' &middot; Valor total: ' + E.formatarValor(v.valor_total) + '</strong></p>';
  }
  function detalheHtml(v, comCliente, semLinkNota) {
    return dadosVenda(v, comCliente, semLinkNota) + '<h3 class="h5 mt-3">Equipamentos</h3>' + tabelaItens(v);
  }

  /* ---------- editor de itens do pedido pendente (UC13 FA1, UC14 FA1) ----------
     el: contêiner. opcoes.catalogo: itens do catálogo para adicionar (Cliente Empresa) ou null (interno: ids digitados).
     opcoes.salvar(ids) -> Promise com a venda; opcoes.aoConcluir(venda); opcoes.aoFechar(). */
  function editorItens(el, venda, opcoes) {
    var cat = opcoes.catalogo;
    var atuais = (venda.itens || []).map(function (i) {
      return '<div class="opcao-destinacao" data-eq="' + i.id_equipamento + '"><input type="checkbox" id="ed-a-' + i.id_equipamento + '" value="' + i.id_equipamento + '" data-grupo="a" checked>' +
        '<label for="ed-a-' + i.id_equipamento + '"><strong>' + U.esc(i.identificacao) + '</strong> &middot; ' + U.esc(i.modelo) + ' &middot; ' + E.formatarValor(i.valor) + '<span class="aviso-item"></span></label></div>';
    }).join('');
    var novos;
    if (cat) {
      novos = '<fieldset class="mb-3"><legend class="h6">Adicionar do catálogo</legend>' + (cat.length
        ? cat.map(function (i) {
          return '<div class="opcao-destinacao" data-eq="' + i.id_equipamento + '"><input type="checkbox" id="ed-n-' + i.id_equipamento + '" value="' + i.id_equipamento + '" data-grupo="n">' +
            '<label for="ed-n-' + i.id_equipamento + '"><strong>' + U.esc(i.identificacao) + '</strong> &middot; ' + U.esc(i.modelo) + ' &middot; ' + E.formatarValor(i.valor) + '<span class="aviso-item"></span></label></div>';
        }).join('')
        : '<p class="aviso-info mb-0" role="status"><span aria-hidden="true">○ </span>Não há outros equipamentos disponíveis no catálogo.</p>') + '</fieldset>';
    } else {
      novos = '<div class="mb-3"><label class="form-label" for="ed-novos">Adicionar equipamentos pelo número (opcional)</label>' +
        '<input type="text" class="form-control" id="ed-novos" inputmode="numeric" autocomplete="off" aria-describedby="ed-novos-dica ed-novos-erro">' +
        '<div id="ed-novos-dica" class="dica-campo">Informe os números dos equipamentos separados por vírgula, por exemplo 12, 15. Só equipamentos disponíveis são aceitos.</div>' +
        '<div id="ed-novos-erro" class="invalid-feedback"></div></div>';
    }
    el.innerHTML = '<form id="ed-form" novalidate><h3 class="h5">Alterar equipamentos do pedido nº ' + venda.id_venda + '</h3>' +
      '<div id="ed-msg" class="alert d-none" aria-live="polite"></div>' +
      '<fieldset class="mb-3"><legend class="h6">Equipamentos no pedido (desmarque para retirar)</legend>' + atuais + '</fieldset>' + novos +
      '<div class="d-flex flex-wrap gap-2"><button type="submit" class="btn btn-success fw-semibold" id="ed-salvar">Salvar alterações</button>' +
      '<button type="button" class="btn btn-outline-leaf fw-semibold" id="ed-fechar">Fechar sem salvar</button></div></form>';

    var form = el.querySelector('#ed-form'), msg = el.querySelector('#ed-msg'), campoNovos = el.querySelector('#ed-novos');
    el.querySelector('#ed-fechar').addEventListener('click', function () { opcoes.aoFechar(); });
    form.addEventListener('submit', async function (ev) {
      ev.preventDefault();
      U.ocultar(msg); U.limparErros(form);
      Array.prototype.forEach.call(form.querySelectorAll('.aviso-item'), function (s) { s.textContent = ''; });
      var ids = Array.prototype.map.call(form.querySelectorAll('input[type="checkbox"]:checked'), function (c) { return Number(c.value); });
      if (campoNovos) {
        var lido = lerIds(campoNovos.value);
        if (lido.invalidos.length) { U.erroCampo(campoNovos, 'Número inválido: ' + lido.invalidos.join(', ') + '. Use apenas números inteiros positivos.'); campoNovos.focus(); return; }
        ids = ids.concat(lido.ids);
      }
      ids = ids.filter(function (id, i) { return ids.indexOf(id) === i; });
      if (!ids.length) { U.mostrar(msg, 'erro', 'O pedido precisa ter pelo menos 1 equipamento. Para desistir da compra, use Cancelar pedido.'); msg.focus(); return; }
      if (ids.length > 50) { U.mostrar(msg, 'erro', 'O pedido aceita no máximo 50 equipamentos.'); msg.focus(); return; }
      var btn = el.querySelector('#ed-salvar'); btn.disabled = true; btn.textContent = 'Salvando...';
      try {
        var v = await opcoes.salvar(ids);
        opcoes.aoConcluir(v);
      } catch (err) {
        btn.disabled = false; btn.textContent = 'Salvar alterações';
        marcarIndisponiveis(form, idsIndisponiveis(err));
        U.mostrar(msg, 'erro', U.esc(msgErro(err)) + (idsIndisponiveis(err).length ? ' Itens afetados: ' + idsIndisponiveis(err).join(', ') + '.' : ''));
        msg.focus();
      }
    });
  }
  /* UC13 FE1: aponta no formulário os itens afetados. */
  function marcarIndisponiveis(raiz, ids) {
    ids.forEach(function (id) {
      Array.prototype.forEach.call(raiz.querySelectorAll('[data-eq="' + id + '"]'), function (linha) {
        linha.classList.add('item-indisponivel');
        var s = linha.querySelector('.aviso-item');
        if (s) { s.textContent = ' — indisponível: retire este item'; }
        else if (linha.tagName === 'TR' && linha.firstElementChild && !linha.querySelector('.aviso-tabela')) {
          linha.firstElementChild.insertAdjacentHTML('beforeend', '<span class="aviso-item aviso-tabela d-block">Indisponível</span>');
        }
      });
    });
  }

  /* ---------- download autenticado da nota (UC17 passo 5) ---------- */
  async function baixarNota(idNota, numero, msgEl) {
    try {
      var r = await Api.baixar('/notas-fiscais/' + idNota + '/download');
      var url = URL.createObjectURL(r.blob), a = document.createElement('a');
      a.href = url; a.download = r.nome || ((numero || 'nota-fiscal') + '.html');
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
      U.mostrar(msgEl, 'sucesso', 'Download da nota ' + U.esc(numero || '') + ' iniciado.');
    } catch (err) {
      U.mostrar(msgEl, 'erro', U.esc(msgErro(err)));
    }
  }

  global.VendasUi = {
    SITUACOES: SITUACOES, FORMAS: FORMAS, MSG: MSG, msgErro: msgErro, seloVenda: seloVenda,
    idsIndisponiveis: idsIndisponiveis, lerIds: lerIds, cabecalhoVendas: cabecalhoVendas, linhaVenda: linhaVenda,
    dadosVenda: dadosVenda, tabelaItens: tabelaItens, detalheHtml: detalheHtml, editorItens: editorItens,
    marcarIndisponiveis: marcarIndisponiveis, baixarNota: baixarNota
  };
})(window);
