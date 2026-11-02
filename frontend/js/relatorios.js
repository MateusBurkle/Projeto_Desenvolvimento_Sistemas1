/* Relatórios - UC22 (RF16, RN16), UC23 (RF17, RN17), UC24 (RF18, RF21, RN18, RN21); RNF05.
   Rotas: GET /relatorios/vendas, /relatorios/equipamentos, /relatorios/organizacoes-destinacoes.
   Somente leitura. Todo dado vindo da API passa por esc() antes de entrar no HTML. */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var SITUACOES_EQUIP = ['Recebido', 'Em avaliação', 'Em manutenção', 'Recondicionado', 'Disponível', 'Vendido', 'Doado', 'Destinado à reciclagem'];
  var SITUACOES_SOL = ['Aguardando avaliação', 'Em avaliação', 'Avaliada'];
  var TAM = 20;
  var estado = { equip: {}, org: {} };

  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function data(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
    return m ? m[3] + '/' + m[2] + '/' + m[1] : '-';
  }
  function moeda(v) { return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }); }
  function opcao(valor, texto) { var o = document.createElement('option'); o.value = valor; o.textContent = texto; return o; }
  function hoje() { var d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }

  function mostrarMsg(id, texto, tipo) {
    var el = $(id); el.textContent = texto; el.className = 'alert alert-' + (tipo || 'danger'); el.classList.remove('d-none');
  }
  function limparMsg(id) { $(id).classList.add('d-none'); }
  function marcarErro(campo, texto) {
    var el = $(campo); if (!el) { return; }
    el.classList.add('is-invalid'); var f = $(campo + '-erro'); if (f) { f.textContent = texto; }
  }
  function limparErros(form) { form.querySelectorAll('.is-invalid').forEach(function (e) { e.classList.remove('is-invalid'); }); }

  /* Mapeia erro da API (campos) para os inputs do formulário; devolve true se algum foi marcado */
  function erroApi(err, prefixo, mapa, idMsg) {
    var marcou = false;
    Object.keys(err.campos || {}).forEach(function (k) {
      if (mapa[k]) { marcarErro(prefixo + mapa[k], err.campos[k]); marcou = true; }
    });
    var texto = err.mensagem || 'Não foi possível emitir o relatório.';
    if (err.codigo === 'PERIODO_INVALIDO' && !marcou) { texto = err.mensagem || 'Período inválido. Corrija as datas.'; }
    mostrarMsg(idMsg, texto, 'danger');
    $(idMsg).focus && $(idMsg).setAttribute('tabindex', '-1');
    $(idMsg).focus();
  }

  function totais(lista) {
    return '<div class="totais-rel" role="group" aria-label="Totais do relatório">' + lista.map(function (t) {
      return '<div class="total-rel"><span class="rotulo">' + esc(t[0]) + '</span><span class="numero">' + esc(t[1]) + '</span></div>';
    }).join('') + '</div>';
  }
  function vazio(texto) {
    return '<div class="estado-vazio cartao-app" role="status"><div class="titulo-vazio">Nenhum resultado</div><p class="mb-0">' + esc(texto) + '</p></div>';
  }
  function paginacao(tipo, total, pagina) {
    var paginas = Math.max(1, Math.ceil(total / TAM));
    if (paginas <= 1) { return ''; }
    return '<nav class="d-flex flex-wrap align-items-center gap-2 mt-2" aria-label="Paginação do relatório">' +
      '<button type="button" class="btn btn-outline-leaf fw-semibold" data-pag="' + tipo + '" data-ir="' + (pagina - 1) + '"' + (pagina <= 1 ? ' disabled' : '') + '>Anterior</button>' +
      '<span aria-live="polite">Página ' + pagina + ' de ' + paginas + '</span>' +
      '<button type="button" class="btn btn-outline-leaf fw-semibold" data-pag="' + tipo + '" data-ir="' + (pagina + 1) + '"' + (pagina >= paginas ? ' disabled' : '') + '>Próxima</button></nav>';
  }

  /* ---------- UC22 vendas ---------- */
  async function emitirVendas(ev) {
    ev.preventDefault();
    var form = $('form-vendas'); limparErros(form); limparMsg('msg-vendas');
    var de = $('v-de').value, ate = $('v-ate').value, ok = true;
    if (!de) { marcarErro('v-de', 'Informe a data inicial.'); ok = false; }
    if (!ate) { marcarErro('v-ate', 'Informe a data final.'); ok = false; }
    if (ok && de > ate) { marcarErro('v-de', 'A data inicial não pode ser posterior à data final.'); ok = false; } /* FE1 */
    if (!ok) { mostrarMsg('msg-vendas', 'Período inválido. Corrija as datas e emita novamente.'); return; }
    $('res-vendas').innerHTML = '<p role="status">Carregando...</p>';
    try {
      var r = await Api.get('/relatorios/vendas?data_de=' + encodeURIComponent(de) + '&data_ate=' + encodeURIComponent(ate));
      renderVendas(r, de, ate);
    } catch (err) {
      $('res-vendas').innerHTML = '';
      erroApi(err, 'v-', { data_de: 'de', data_ate: 'ate' }, 'msg-vendas');
    }
  }
  function renderVendas(r, de, ate) {
    var vendas = r.vendas || [];
    var h = '<p class="dica-campo" role="status">Período: ' + data(r.data_de || de) + ' a ' + data(r.data_ate || ate) + '</p>' +
      totais([['Vendas confirmadas', r.total_vendas || 0], ['Equipamentos vendidos', r.total_equipamentos || 0], ['Valor total', moeda(r.valor_total)]]);
    if (!vendas.length) { /* FA1 */
      $('res-vendas').innerHTML = h + vazio('Nenhuma venda confirmada neste período. Total igual a ' + moeda(0) + '.'); return;
    }
    h += '<div class="cartao-app"><div class="table-responsive"><table class="table table-hover tabela-usuarios tabela-rel mb-0">' +
      '<caption class="visually-hidden">Vendas confirmadas no período</caption>' +
      '<thead><tr><th scope="col">Venda</th><th scope="col">Data</th><th scope="col">Cliente</th><th scope="col">Pagamento</th><th scope="col">Equipamentos</th><th scope="col">Quantidade</th><th scope="col">Total</th></tr></thead><tbody>' +
      vendas.map(function (v) {
        var itens = (v.itens || []).map(function (i) {
          return '<li>' + esc(i.identificacao) + ' - ' + esc(i.modelo) + ' <span class="rel-sub">' + esc(i.categoria) + ' &middot; ' + moeda(i.valor) + '</span></li>';
        }).join('');
        return '<tr><td data-rotulo="Venda"><strong>Nº ' + esc(v.id_venda) + '</strong></td>' +
          '<td data-rotulo="Data">' + data(v.data_venda) + '</td>' +
          '<td data-rotulo="Cliente">' + esc(v.cliente) + '</td>' +
          '<td data-rotulo="Pagamento">' + esc(v.forma_pagamento) + '</td>' +
          '<td data-rotulo="Equipamentos"><ul class="lista-itens-rel">' + itens + '</ul></td>' +
          '<td data-rotulo="Quantidade">' + esc(v.quantidade) + '</td>' +
          '<td data-rotulo="Total"><strong>' + moeda(v.valor_total) + '</strong></td></tr>';
      }).join('') + '</tbody></table></div></div>';
    $('res-vendas').innerHTML = h;
  }

  /* ---------- UC23 equipamentos ---------- */
  function consultaEquip(pagina) {
    var q = ['page=' + pagina, 'size=' + TAM];
    var f = estado.equip;
    if (f.cat) { q.push('id_categoria=' + encodeURIComponent(f.cat)); }
    if (f.sit) { q.push('situacao=' + encodeURIComponent(f.sit)); }
    if (f.de) { q.push('data_de=' + encodeURIComponent(f.de)); }
    if (f.ate) { q.push('data_ate=' + encodeURIComponent(f.ate)); }
    return q.join('&');
  }
  async function emitirEquip(ev, pagina) {
    if (ev) { ev.preventDefault(); }
    var form = $('form-equip'); limparMsg('msg-equip');
    if (ev) {
      limparErros(form);
      estado.equip = { cat: $('e-cat').value, sit: $('e-sit').value, de: $('e-de').value, ate: $('e-ate').value };
      if (estado.equip.de && estado.equip.ate && estado.equip.de > estado.equip.ate) { /* FE1 */
        marcarErro('e-de', 'A data inicial não pode ser posterior à data final.');
        mostrarMsg('msg-equip', 'Filtros inválidos. Corrija o período de cadastro.'); return;
      }
    }
    $('res-equip').innerHTML = '<p role="status">Carregando...</p>';
    try {
      var r = await Api.get('/relatorios/equipamentos?' + consultaEquip(pagina || 1));
      renderEquip(r);
    } catch (err) {
      $('res-equip').innerHTML = '';
      erroApi(err, 'e-', { id_categoria: 'cat', situacao: 'sit', data_de: 'de', data_ate: 'ate' }, 'msg-equip');
    }
  }
  function renderEquip(r) {
    var itens = r.items || [], resumo = r.resumo_por_situacao || {};
    var t = [['Total de equipamentos', r.total || 0]];
    Object.keys(resumo).forEach(function (s) { t.push([s, resumo[s]]); });
    var h = totais(t);
    if (!itens.length) { $('res-equip').innerHTML = h + vazio('Nenhum equipamento encontrado para os filtros selecionados.'); return; }
    h += '<div class="cartao-app"><div class="table-responsive"><table class="table table-hover tabela-usuarios tabela-rel mb-0">' +
      '<caption class="visually-hidden">Equipamentos cadastrados</caption>' +
      '<thead><tr><th scope="col">Equipamento</th><th scope="col">Categoria</th><th scope="col">Condição</th><th scope="col">Situação</th><th scope="col">Valor</th><th scope="col">Recebimento</th><th scope="col">Origem</th><th scope="col">Destinação</th></tr></thead><tbody>' +
      itens.map(function (e) {
        var dest = e.destinacao ? '<span class="selo-dest">' + esc(e.destinacao) + '</span>' +
          (e.destino_detalhe ? '<span class="rel-sub">' + esc(e.destino_detalhe) + '</span>' : '') +
          (e.data_destinacao ? '<span class="rel-sub">' + data(e.data_destinacao) + '</span>' : '') : 'Não registrada';
        return '<tr><td data-rotulo="Equipamento"><strong>' + esc(e.identificacao) + '</strong><span class="rel-sub">' + esc(e.modelo) + (e.ativo === false ? ' &middot; Inativo' : '') + '</span></td>' +
          '<td data-rotulo="Categoria">' + esc(e.categoria) + '</td>' +
          '<td data-rotulo="Condição">' + esc(e.condicao) + '</td>' +
          '<td data-rotulo="Situação">' + esc(e.situacao) + '</td>' +
          '<td data-rotulo="Valor">' + (e.valor == null ? '-' : moeda(e.valor)) + '</td>' +
          '<td data-rotulo="Recebimento">' + data(e.data_recebimento) + '</td>' +
          '<td data-rotulo="Origem">' + esc(e.origem || '-') + '</td>' +
          '<td data-rotulo="Destinação">' + dest + '</td></tr>';
      }).join('') + '</tbody></table></div>' + paginacao('equip', r.total || 0, r.page || 1) + '</div>';
    $('res-equip').innerHTML = h;
  }

  /* ---------- UC24 organizações e destinações ---------- */
  function consultaOrg(pagina) {
    var q = ['page=' + pagina, 'size=' + TAM], f = estado.org;
    if (f.emp) { q.push('id_organizacao_doadora=' + encodeURIComponent(f.emp)); }
    if (f.sit) { q.push('situacao=' + encodeURIComponent(f.sit)); }
    if (f.de) { q.push('data_de=' + encodeURIComponent(f.de)); }
    if (f.ate) { q.push('data_ate=' + encodeURIComponent(f.ate)); }
    return q.join('&');
  }
  async function emitirOrg(ev, pagina) {
    if (ev) { ev.preventDefault(); }
    var form = $('form-org'); limparMsg('msg-org');
    if (ev) {
      limparErros(form);
      estado.org = { emp: $('o-emp').value, sit: $('o-sit').value, de: $('o-de').value, ate: $('o-ate').value };
      if (estado.org.de && estado.org.ate && estado.org.de > estado.org.ate) { /* FE1 */
        marcarErro('o-de', 'A data inicial não pode ser posterior à data final.');
        mostrarMsg('msg-org', 'Filtros inválidos. Corrija o período.'); return;
      }
    }
    $('res-org').innerHTML = '<p role="status">Carregando...</p>';
    try {
      var r = await Api.get('/relatorios/organizacoes-destinacoes?' + consultaOrg(pagina || 1));
      renderOrg(r);
    } catch (err) {
      $('res-org').innerHTML = '';
      erroApi(err, 'o-', { id_organizacao_doadora: 'emp', situacao: 'sit', data_de: 'de', data_ate: 'ate' }, 'msg-org');
    }
  }
  /* FE1/FA1: destinação nula nunca vira "concluída"; mostra "Pendente" */
  function destinacaoEq(e) {
    if (!e.destinacao) { return '<span class="selo-pendente">Destinação pendente</span>'; }
    var h = '<span class="selo-dest">' + esc(e.destinacao) + '</span>';
    if (e.destinacao === 'Doação') { /* FA2: só doação mostra ONG e data */
      h += '<span class="rel-sub">ONG: ' + esc(e.ong_beneficiada || 'não informada') + '</span><span class="rel-sub">Data: ' + data(e.data_doacao) + '</span>';
    }
    return h;
  }
  function renderOrg(r) {
    var itens = r.items || [];
    var pend = itens.filter(function (s) { return s.avaliacao_pendente; }).length;
    var h = totais([['Solicitações', r.total || 0], ['Com pendência (nesta página)', pend]]);
    if (!itens.length) { $('res-org').innerHTML = h + vazio('Nenhuma solicitação encontrada para os filtros selecionados.'); return; }
    h += itens.map(function (s) {
      var pendencias = (s.pendencias || []);
      var aviso = s.avaliacao_pendente
        ? '<div class="aviso-pendente" role="status"><strong>Avaliação ou destinação pendente.</strong>' +
          (pendencias.length ? '<ul class="mb-0">' + pendencias.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul>' : '') + '</div>' : '';
      var itensHtml = (s.itens || []).map(function (i) {
        var linhas = (i.equipamentos || []).map(function (e) {
          return '<tr><td data-rotulo="Equipamento">' + esc(e.identificacao) + '</td>' +
            '<td data-rotulo="Condição">' + esc(e.condicao) + '</td>' +
            '<td data-rotulo="Situação">' + esc(e.situacao) + '</td>' +
            '<td data-rotulo="Destinação">' + destinacaoEq(e) + '</td></tr>';
        }).join('');
        return '<h4 class="h6 mt-3">' + esc(i.tipo) + ' - ' + esc(i.modelo) + ' <span class="rel-sub">Quantidade informada: ' + esc(i.quantidade) + ' &middot; Equipamentos cadastrados: ' + esc(i.equipamentos_cadastrados) + '</span></h4>' +
          (linhas ? '<div class="table-responsive"><table class="table tabela-usuarios tabela-rel mb-0"><caption class="visually-hidden">Equipamentos do item ' + esc(i.tipo) + '</caption>' +
            '<thead><tr><th scope="col">Equipamento</th><th scope="col">Condição</th><th scope="col">Situação</th><th scope="col">Destinação</th></tr></thead><tbody>' + linhas + '</tbody></table></div>'
            : '<p class="aviso-pendente mb-0">Nenhum equipamento cadastrado para este item (avaliação pendente).</p>');
      }).join('');
      return '<article class="cartao-solicitacao' + (s.avaliacao_pendente ? ' com-pendencia' : '') + '" aria-labelledby="sol-' + esc(s.id_solicitacao) + '">' +
        '<h3 id="sol-' + esc(s.id_solicitacao) + '">Solicitação Nº ' + esc(s.id_solicitacao) + ' - ' + esc(s.empresa_doadora) + '</h3>' +
        '<p class="mb-2">Data: ' + data(s.data_solicitacao) + ' &middot; Situação: <strong>' + esc(s.situacao) + '</strong></p>' +
        aviso + itensHtml + '</article>';
    }).join('') + paginacao('org', r.total || 0, r.page || 1);
    $('res-org').innerHTML = h;
  }

  /* ---------- apoio: listas dos filtros ---------- */
  async function carregarApoio() {
    SITUACOES_EQUIP.forEach(function (s) { $('e-sit').appendChild(opcao(s, s)); });
    SITUACOES_SOL.forEach(function (s) { $('o-sit').appendChild(opcao(s, s)); });
    try {
      var c = await Api.get('/categorias?size=100');
      c.items.forEach(function (x) { $('e-cat').appendChild(opcao(x.id_categoria, x.nome)); });
    } catch (e) { $('e-cat').disabled = true; }
    try {
      var o = await Api.get('/organizacoes?tipo=' + encodeURIComponent('Empresa Doadora') + '&size=100');
      o.items.forEach(function (x) { $('o-emp').appendChild(opcao(x.id_organizacao, x.nome_razao_social)); });
    } catch (e) { $('o-emp').disabled = true; }
  }

  Layout.iniciar({ chave: 'relatorios' }).then(function (usuario) {
    if (!usuario || (usuario.funcionalidades || []).indexOf('relatorios') === -1) { $('area-relatorios').hidden = true; return; }
    $('v-ate').value = hoje();
    var d = new Date(); $('v-de').value = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-01';
    $('form-vendas').addEventListener('submit', emitirVendas);
    $('form-equip').addEventListener('submit', function (ev) { emitirEquip(ev, 1); });
    $('form-org').addEventListener('submit', function (ev) { emitirOrg(ev, 1); });
    $('e-limpar').addEventListener('click', function () { $('form-equip').reset(); limparErros($('form-equip')); limparMsg('msg-equip'); estado.equip = {}; emitirEquip(null, 1); });
    $('o-limpar').addEventListener('click', function () { $('form-org').reset(); limparErros($('form-org')); limparMsg('msg-org'); estado.org = {}; emitirOrg(null, 1); });
    $('area-relatorios').addEventListener('click', function (ev) {
      var b = ev.target.closest('[data-pag]'); if (!b || b.disabled) { return; }
      var p = parseInt(b.getAttribute('data-ir'), 10);
      if (b.getAttribute('data-pag') === 'equip') { emitirEquip(null, p); } else { emitirOrg(null, p); }
    });
    carregarApoio();
    /* FA1 do UC23/UC24: sem filtros, carrega tudo ao abrir a aba pela primeira vez */
    var carregado = {};
    $('abas').addEventListener('shown.bs.tab', function (ev) {
      var alvo = ev.target.id;
      if (carregado[alvo]) { return; }
      if (alvo === 'aba-equip') { carregado[alvo] = true; emitirEquip(null, 1); }
      if (alvo === 'aba-org') { carregado[alvo] = true; emitirOrg(null, 1); }
    });
  });
})();
