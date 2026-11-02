/* Tela app/notas-fiscais/index.html. UC17 (RF20; RN20; RNF05), DP-49.
   Rotas do contrato modulo-5: GET /notas-fiscais, GET /notas-fiscais/{id}, GET /notas-fiscais/{id}/download (Api.baixar, fetch com blob);
   auxiliar GET /organizacoes (módulo 2) para o filtro de cliente do Administrador.
   A segurança real (404 para nota de outra organização; 403 ao Funcionário) é do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, E = EquipUi, S = SolUi, V = VendasUi;
  var TAMANHO = 10;
  var $ = function (id) { return document.getElementById(id); };
  var VISTAS = ['vista-lista', 'vista-detalhe'];
  var msgPagina = $('mensagem'), msgDetalhe = $('msg-detalhe');
  var estado = { pagina: 1, filtros: {}, admin: false, nota: null };

  /* Cliente Empresa usa `minhas_notas_fiscais`; o Administrador usa `notas_fiscais` (outros perfis recebem o acesso negado do layout). */
  var cliente0 = (Api.sessao.usuario() || {}).perfil === 'Cliente Empresa';

  Layout.iniciar({ chave: cliente0 ? 'minhas_notas_fiscais' : 'notas_fiscais' }).then(function (usuario) {
    if (!$('area-notas')) { return; }
    estado.admin = usuario.perfil === 'Administrador';
    if (estado.admin) {
      $('bloco-filtro-cliente').hidden = false;
      carregarClientes();
    } else {
      $('titulo-lista').textContent = 'Minhas notas fiscais';
      $('dica-lista').textContent = 'Notas fiscais simuladas das compras da sua organização. Sem valor fiscal.';
    }
    $('cab-tabela').innerHTML = '<th scope="col">Número</th>' + (estado.admin ? '<th scope="col">Cliente</th>' : '') +
      '<th scope="col">Emissão</th><th scope="col">Pedido</th><th scope="col">Valor total</th><th scope="col">Ações</th>';
    var id = S.idDaUrl();
    carregar(1);
    if (id) { abrirDetalhe(id); }
  });

  function vista(id, titulo) { S.mostrarVista(VISTAS, id, titulo); }
  function opcao(valor, texto) { var o = document.createElement('option'); o.value = valor; o.textContent = texto; return o; }
  async function carregarClientes() {
    try {
      var r = await Api.get('/organizacoes?tipo=' + encodeURIComponent('Cliente Empresa') + '&size=100');
      r.items.forEach(function (o) { $('filtro-cliente').appendChild(opcao(o.id_organizacao, o.nome_razao_social)); });
    } catch (err) { $('filtro-cliente').disabled = true; }
  }

  /* ---------- lista (UC17 passos 1-2) ---------- */
  function linhaHtml(n) {
    return '<tr><td data-rotulo="Número"><strong>' + U.esc(n.numero) + '</strong></td>' +
      (estado.admin ? '<td data-rotulo="Cliente">' + U.esc(n.nome_organizacao) + '</td>' : '') +
      '<td data-rotulo="Emissão">' + E.formatarData(n.data_emissao) + '</td>' +
      '<td data-rotulo="Pedido">nº ' + n.id_venda + '</td>' +
      '<td data-rotulo="Valor">' + E.formatarValor(n.valor_total) + '</td>' +
      '<td class="acoes" data-rotulo="Ações"><div class="grupo-acoes">' +
        '<button type="button" class="btn btn-outline-leaf" data-acao="ver" data-id="' + n.id_nota + '" aria-label="Consultar a nota ' + E.escAttr(n.numero) + '">Consultar</button>' +
        '<button type="button" class="btn btn-outline-leaf" data-acao="baixar" data-id="' + n.id_nota + '" data-numero="' + E.escAttr(n.numero) + '" aria-label="Baixar a nota ' + E.escAttr(n.numero) + '">Baixar</button>' +
      '</div></td></tr>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO], fl = estado.filtros;
    if (estado.admin && fl.cliente) { q.push('id_organizacao_cliente=' + encodeURIComponent(fl.cliente)); }
    if (fl.de) { q.push('data_de=' + fl.de); }
    if (fl.ate) { q.push('data_ate=' + fl.ate); }
    $('estado-lista').hidden = false; $('estado-lista').textContent = 'Carregando...';
    try {
      var r = await Api.get('/notas-fiscais?' + q.join('&'));
      estado.pagina = r.page;
      $('tabela').hidden = r.items.length === 0;
      $('paginacao').hidden = r.total <= r.size;
      $('corpo-tabela').innerHTML = r.items.map(linhaHtml).join('');
      var vazio = $('vazio-lista');
      if (!r.items.length) {
        var filtrando = !!((estado.admin && fl.cliente) || fl.de || fl.ate);
        $('estado-lista').hidden = true; vazio.hidden = false;
        vazio.innerHTML = filtrando
          ? '<p class="titulo-vazio">Nenhuma nota encontrada</p><p class="mb-0">Nenhum registro atende aos filtros. Ajuste ou limpe os filtros.</p>'
          : '<p class="titulo-vazio">Ainda não há notas fiscais</p><p class="mb-0">' + (estado.admin
            ? 'Emita a nota de uma venda confirmada na tela Vendas.'
            : 'Quando a LEAF TI emitir a nota de uma compra confirmada, ela aparecerá aqui.') + '</p>';
      } else {
        vazio.hidden = true;
        $('estado-lista').textContent = r.total + (r.total === 1 ? ' nota encontrada.' : ' notas encontradas.');
      }
      $('texto-pagina').textContent = E.textoPagina(r, 'nota', 'notas');
      $('btn-anterior').disabled = r.page <= 1;
      $('btn-proxima').disabled = r.page * r.size >= r.total;
    } catch (err) {
      $('tabela').hidden = true; $('paginacao').hidden = true; $('vazio-lista').hidden = true;
      $('estado-lista').hidden = false; $('estado-lista').textContent = 'Não foi possível carregar as notas fiscais.';
      U.mostrar(msgPagina, 'erro', U.esc(V.msgErro(err)));
    }
  }
  $('form-filtros').addEventListener('submit', function (ev) {
    ev.preventDefault();
    U.limparErros($('form-filtros')); U.ocultar(msgPagina);
    var de = $('filtro-de').value, ate = $('filtro-ate').value;
    var erro = S.validarPeriodo(de, ate);
    if (erro) { U.erroCampo((de && !E.dataValida(de)) || (de && ate && de > ate) ? $('filtro-de') : $('filtro-ate'), erro); return; }
    estado.filtros = { cliente: $('filtro-cliente').value, de: de, ate: ate };
    carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () {
    $('form-filtros').reset(); U.limparErros($('form-filtros')); estado.filtros = {}; U.ocultar(msgPagina); carregar(1);
  });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });
  $('corpo-tabela').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-acao]');
    if (!b) { return; }
    U.ocultar(msgPagina);
    if (b.dataset.acao === 'ver') { abrirDetalhe(Number(b.dataset.id)); }
    else { V.baixarNota(Number(b.dataset.id), b.dataset.numero, msgPagina); }
  });

  /* ---------- nota (UC17 passos 3-4; FA1; FE1) ---------- */
  async function abrirDetalhe(id) {
    U.ocultar(msgDetalhe);
    try {
      var n = await Api.get('/notas-fiscais/' + id), v = n.venda || {};
      estado.nota = n;
      $('titulo-detalhe').textContent = 'Nota ' + n.numero;
      $('corpo-detalhe').innerHTML = '<dl class="dados-sol">' +
        '<dt>Número</dt><dd>' + U.esc(n.numero) + '</dd>' +
        '<dt>Data de emissão</dt><dd>' + E.formatarData(n.data_emissao) + '</dd>' +
        '<dt>Cliente Empresa</dt><dd>' + U.esc(v.nome_organizacao) + '</dd>' +
        '<dt>Pedido</dt><dd>nº ' + v.id_venda + ' (data ' + E.formatarData(v.data_venda) + ')</dd>' +
        '<dt>Forma de pagamento</dt><dd>' + U.esc(v.forma_pagamento) + '</dd></dl>' +
        '<h3 class="h5 mt-3">Equipamentos</h3>' + V.tabelaItens(v);
      var link = $('link-venda');
      link.href = (estado.admin ? '../vendas/index.html?id=' : '../compras/index.html?id=') + v.id_venda;
      link.textContent = 'Ver ' + (estado.admin ? 'a venda' : 'o pedido');
      link.hidden = false;
      vista('vista-detalhe', 'titulo-detalhe');
    } catch (err) {
      vista('vista-lista', 'titulo-lista');
      /* UC17 FE1: nota inexistente ou de outra organização -> 404 */
      U.mostrar(msgPagina, 'erro', err.status === 404
        ? 'Nota não encontrada. Ela não existe ou não está vinculada a você.' : U.esc(V.msgErro(err)));
    }
  }
  $('btn-baixar').addEventListener('click', function () {
    U.ocultar(msgDetalhe);
    V.baixarNota(estado.nota.id_nota, estado.nota.numero, msgDetalhe);
  });
  $('btn-voltar').addEventListener('click', function () { vista('vista-lista', 'titulo-lista'); carregar(estado.pagina); });
});
