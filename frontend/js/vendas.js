/* Tela app/vendas/index.html. UC21 (RF15; RN15), UC14 (RF03, RF13; RN03, RN13, RN14), UC15 (RF14; RN14), UC16 (RF19; RN19).
   Decisões DP-45 a DP-51. Administrador e Funcionário; emissão de nota só para o Administrador.
   Rotas do contrato modulo-5: GET /vendas, GET /vendas/{id}, PATCH /vendas/{id}, PUT /vendas/{id}/itens,
   POST /vendas/{id}/cancelar, POST /vendas/{id}/confirmar, POST /vendas/{id}/nota-fiscal, GET /notas-fiscais/{id}/download
   (via Api.baixar); auxiliar GET /organizacoes (módulo 2) para o filtro de cliente.
   A segurança real é do back-end; aqui só se escondem as ações que o perfil não tem. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, E = EquipUi, S = SolUi, V = VendasUi;
  var TAMANHO = 10;
  var $ = function (id) { return document.getElementById(id); };
  var VISTAS = ['vista-lista', 'vista-detalhe'];
  var PAINEIS = ['painel-confirmar', 'painel-pagamento', 'painel-editor', 'painel-cancelar', 'painel-nota'];
  var msgPagina = $('mensagem'), msgDetalhe = $('msg-detalhe');
  var estado = { pagina: 1, filtros: {}, venda: null, admin: false };

  Layout.iniciar({ chave: 'vendas' }).then(function (usuario) {
    if (!$('area-vendas')) { return; }
    estado.admin = usuario.perfil === 'Administrador';
    V.SITUACOES.forEach(function (s) { $('filtro-situacao').appendChild(opcao(s, s)); });
    [$('c-forma'), $('p-forma')].forEach(function (sel) {
      sel.appendChild(opcao('', 'Selecione a forma de pagamento'));
      V.FORMAS.forEach(function (f) { sel.appendChild(opcao(f, f)); });
    });
    $('cab-tabela').innerHTML = V.cabecalhoVendas(true);
    carregarClientes();
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

  /* ---------- histórico (UC21 passos 2-4; FA1 sem filtros) ---------- */
  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO], fl = estado.filtros;
    if (fl.cliente) { q.push('id_organizacao_cliente=' + encodeURIComponent(fl.cliente)); }
    if (fl.situacao) { q.push('situacao=' + encodeURIComponent(fl.situacao)); }
    if (fl.de) { q.push('data_de=' + fl.de); }
    if (fl.ate) { q.push('data_ate=' + fl.ate); }
    $('estado-lista').hidden = false; $('estado-lista').textContent = 'Carregando...';
    try {
      var r = await Api.get('/vendas?' + q.join('&'));
      estado.pagina = r.page;
      $('tabela').hidden = r.items.length === 0;
      $('paginacao').hidden = r.total <= r.size;
      $('corpo-tabela').innerHTML = r.items.map(function (v) { return V.linhaVenda(v, true); }).join('');
      var vazio = $('vazio-lista');
      if (!r.items.length) {
        $('estado-lista').hidden = true; vazio.hidden = false;
        vazio.innerHTML = (fl.cliente || fl.situacao || fl.de || fl.ate)
          ? '<p class="titulo-vazio">Nenhuma venda encontrada</p><p class="mb-0">Nenhum registro atende aos filtros. Ajuste ou limpe os filtros.</p>'
          : '<p class="titulo-vazio">Ainda não há vendas registradas</p><p class="mb-0">Os pedidos dos Clientes Empresa aparecerão aqui.</p>';
      } else {
        vazio.hidden = true;
        $('estado-lista').textContent = r.total + (r.total === 1 ? ' registro encontrado.' : ' registros encontrados.');
      }
      $('texto-pagina').textContent = E.textoPagina(r, 'registro', 'registros');
      $('btn-anterior').disabled = r.page <= 1;
      $('btn-proxima').disabled = r.page * r.size >= r.total;
    } catch (err) {
      $('tabela').hidden = true; $('paginacao').hidden = true; $('vazio-lista').hidden = true;
      $('estado-lista').hidden = false; $('estado-lista').textContent = 'Não foi possível carregar o histórico.';
      U.mostrar(msgPagina, 'erro', U.esc(V.msgErro(err)));
    }
  }
  $('form-filtros').addEventListener('submit', function (ev) {
    ev.preventDefault();
    U.limparErros($('form-filtros')); U.ocultar(msgPagina);
    var de = $('filtro-de').value, ate = $('filtro-ate').value;
    var erro = S.validarPeriodo(de, ate);
    if (erro) { U.erroCampo((de && !E.dataValida(de)) || (de && ate && de > ate) ? $('filtro-de') : $('filtro-ate'), erro); return; }
    estado.filtros = { cliente: $('filtro-cliente').value, situacao: $('filtro-situacao').value, de: de, ate: ate };
    carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () {
    $('form-filtros').reset(); U.limparErros($('form-filtros')); estado.filtros = {}; U.ocultar(msgPagina); carregar(1);
  });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });
  $('corpo-tabela').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-acao="ver"]');
    if (b) { U.ocultar(msgPagina); abrirDetalhe(Number(b.dataset.id)); }
  });

  /* ---------- detalhe (UC21 passo 5; UC14 passo 2) ---------- */
  function fecharPaineis() {
    PAINEIS.forEach(function (id) { $(id).hidden = true; });
    $('painel-editor').innerHTML = '';
    U.limparErros($('painel-confirmar')); U.limparErros($('painel-pagamento'));
  }
  function abrirPainel(id, foco) { fecharPaineis(); U.ocultar(msgDetalhe); $(id).hidden = false; if (foco) { foco.focus(); } }

  function desenharDetalhe(v) {
    estado.venda = v;
    fecharPaineis();
    $('titulo-detalhe').textContent = 'Venda nº ' + v.id_venda;
    $('corpo-detalhe').innerHTML = V.detalheHtml(v, true, !estado.admin);
    var acoes = '';
    if (v.situacao === 'Pendente') {
      acoes += '<button type="button" class="btn btn-success fw-semibold" data-ac="confirmar">Confirmar venda</button>' +
        '<button type="button" class="btn btn-outline-leaf fw-semibold" data-ac="pagamento">Ajustar forma de pagamento</button>' +
        '<button type="button" class="btn btn-outline-leaf fw-semibold" data-ac="itens">Trocar itens</button>' +
        '<button type="button" class="btn btn-excluir" data-ac="cancelar">Cancelar pedido</button>';
    } else if (v.situacao === 'Confirmada') {
      if (estado.admin && !v.nota_fiscal) { acoes += '<button type="button" class="btn btn-success fw-semibold" data-ac="nota">Emitir nota simulada</button>'; }
      if (estado.admin && v.nota_fiscal) { /* UC16 FA1: mostra a existente, sem duplicar */
        acoes += '<a class="btn btn-outline-leaf fw-semibold" href="../notas-fiscais/index.html?id=' + v.nota_fiscal.id_nota + '">Ver nota fiscal existente</a>' +
          '<button type="button" class="btn btn-outline-leaf fw-semibold" data-ac="baixar">Baixar nota fiscal</button>';
      }
      $('corpo-detalhe').insertAdjacentHTML('beforeend', '<p class="aviso-ok mt-3 mb-0" role="status"><span aria-hidden="true">✔ </span>Venda confirmada: os equipamentos constam como vendidos e não podem mais ser alterados.' +
        (!estado.admin ? ' A nota fiscal simulada é emitida pelo Administrador.' : '') + '</p>');
    } else {
      $('corpo-detalhe').insertAdjacentHTML('beforeend', '<p class="aviso-info mt-3 mb-0" role="status"><span aria-hidden="true">○ </span>Pedido cancelado. Não gera venda confirmada nem nota fiscal (somente leitura).</p>');
    }
    $('acoes-detalhe').innerHTML = acoes;
  }

  async function abrirDetalhe(id) {
    U.ocultar(msgDetalhe);
    try {
      desenharDetalhe(await Api.get('/vendas/' + id));
      vista('vista-detalhe', 'titulo-detalhe');
    } catch (err) {
      vista('vista-lista', 'titulo-lista');
      U.mostrar(msgPagina, 'erro', err.status === 404 ? 'Venda não encontrada.' : U.esc(V.msgErro(err)));
    }
  }
  $('btn-voltar').addEventListener('click', function () { vista('vista-lista', 'titulo-lista'); carregar(estado.pagina); });

  /* Se o estado mudou fora da tela (VENDA_NAO_PENDENTE etc.), recarrega o pedido */
  async function atualizarAposErro(err) {
    if (err.codigo === 'VENDA_NAO_PENDENTE') {
      try { var v = await Api.get('/vendas/' + estado.venda.id_venda); desenharDetalhe(v); } catch (e) { /* mantém a tela */ }
    }
  }
  function erroNoDetalhe(err) {
    var ids = V.idsIndisponiveis(err);
    var txt = U.esc(V.msgErro(err)) + (ids.length ? ' Equipamentos afetados (números): ' + ids.join(', ') + '. Use Trocar itens para retirá-los.' : '');
    U.mostrar(msgDetalhe, 'erro', txt);
    if (ids.length) { V.marcarIndisponiveis($('corpo-detalhe'), ids); }
    msgDetalhe.focus();
  }

  document.querySelectorAll('[data-fechar]').forEach(function (b) {
    b.addEventListener('click', function () { $(b.dataset.fechar).hidden = true; });
  });

  $('acoes-detalhe').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-ac]');
    if (!b) { return; }
    var v = estado.venda;
    switch (b.dataset.ac) {
      case 'confirmar':
        $('c-data').value = E.hojeIso(); $('c-data').min = v.data_venda; $('c-data').max = E.hojeIso();
        $('c-forma').value = V.FORMAS.indexOf(v.forma_pagamento) !== -1 ? v.forma_pagamento : '';
        abrirPainel('painel-confirmar', $('c-data')); break;
      case 'pagamento':
        $('p-forma').value = V.FORMAS.indexOf(v.forma_pagamento) !== -1 ? v.forma_pagamento : '';
        abrirPainel('painel-pagamento', $('p-forma')); break;
      case 'itens':
        abrirPainel('painel-editor');
        V.editorItens($('painel-editor'), v, {
          catalogo: null, /* o catálogo é do Cliente Empresa (UC12 FE2): o ator interno informa os números */
          salvar: function (ids) { return Api.put('/vendas/' + v.id_venda + '/itens', { ids_equipamento: ids }); },
          aoConcluir: function (nv) {
            desenharDetalhe(nv);
            U.mostrar(msgDetalhe, 'sucesso', 'Itens do pedido atualizados. Confira os valores antes de confirmar a venda.'); msgDetalhe.focus();
          },
          aoFechar: function () { fecharPaineis(); }
        });
        $('painel-editor').querySelector('input').focus(); break;
      case 'cancelar': abrirPainel('painel-cancelar', $('btn-confirmar-cancelar')); break;
      case 'nota': abrirPainel('painel-nota', $('btn-confirmar-nota')); break;
      case 'baixar': V.baixarNota(v.nota_fiscal.id_nota, v.nota_fiscal.numero, msgDetalhe); break;
    }
  });

  /* ---------- confirmar venda (UC14 passos 3-6; UC15; FE1) ---------- */
  $('painel-confirmar').addEventListener('submit', async function (ev) {
    ev.preventDefault();
    var form = this, v = estado.venda, ok = true;
    U.limparErros(form); U.ocultar(msgDetalhe);
    var data = $('c-data').value, forma = $('c-forma').value;
    if (!data) { U.erroCampo($('c-data'), 'Informe a data da venda.'); ok = false; }
    else if (!E.dataValida(data)) { U.erroCampo($('c-data'), 'Informe uma data válida.'); ok = false; }
    else if (data > E.hojeIso()) { U.erroCampo($('c-data'), 'A data da venda não pode ser futura.'); ok = false; }
    else if (data < v.data_venda) { U.erroCampo($('c-data'), 'A data da venda não pode ser anterior à data do pedido (' + E.formatarData(v.data_venda) + ').'); ok = false; }
    if (!forma) { U.erroCampo($('c-forma'), 'Selecione a forma de pagamento.'); ok = false; }
    if (!ok) { form.querySelector('.is-invalid').focus(); return; }
    var btn = $('btn-confirmar-venda'); btn.disabled = true; btn.textContent = 'Confirmando...';
    try {
      var nv = await Api.post('/vendas/' + v.id_venda + '/confirmar', { data_venda: data, forma_pagamento: forma });
      desenharDetalhe(nv);
      U.mostrar(msgDetalhe, 'sucesso', 'Venda confirmada. Os equipamentos foram marcados como vendidos e saíram do catálogo.'); msgDetalhe.focus();
    } catch (err) {
      if (!U.aplicarCamposDaApi(err, { data_venda: $('c-data'), forma_pagamento: $('c-forma') }) || err.codigo !== 'DADOS_INVALIDOS') { erroNoDetalhe(err); }
      else { U.mostrar(msgDetalhe, 'erro', U.esc(V.msgErro(err))); msgDetalhe.focus(); }
      await atualizarAposErro(err);
    } finally {
      btn.disabled = false; btn.textContent = 'Confirmar venda';
    }
  });

  /* ---------- ajustar forma de pagamento (UC14 FA1) ---------- */
  $('painel-pagamento').addEventListener('submit', async function (ev) {
    ev.preventDefault();
    U.limparErros(this); U.ocultar(msgDetalhe);
    var forma = $('p-forma').value;
    if (!forma) { U.erroCampo($('p-forma'), 'Selecione a forma de pagamento.'); $('p-forma').focus(); return; }
    var btn = $('btn-salvar-pagamento'); btn.disabled = true; btn.textContent = 'Salvando...';
    try {
      var nv = await Api.patch('/vendas/' + estado.venda.id_venda, { forma_pagamento: forma });
      desenharDetalhe(nv);
      U.mostrar(msgDetalhe, 'sucesso', 'Forma de pagamento atualizada.'); msgDetalhe.focus();
    } catch (err) {
      if (!U.aplicarCamposDaApi(err, { forma_pagamento: $('p-forma') })) { erroNoDetalhe(err); }
      await atualizarAposErro(err);
    } finally {
      btn.disabled = false; btn.textContent = 'Salvar';
    }
  });

  /* ---------- cancelar (UC14 FA2) ---------- */
  $('btn-confirmar-cancelar').addEventListener('click', async function () {
    var btn = this; btn.disabled = true; btn.textContent = 'Cancelando...';
    try {
      var nv = await Api.post('/vendas/' + estado.venda.id_venda + '/cancelar');
      desenharDetalhe(nv);
      U.mostrar(msgDetalhe, 'sucesso', 'Pedido cancelado. Nenhuma venda ou nota foi gerada e os equipamentos foram liberados.'); msgDetalhe.focus();
    } catch (err) {
      erroNoDetalhe(err); await atualizarAposErro(err);
    } finally {
      btn.disabled = false; btn.textContent = 'Sim, cancelar pedido';
    }
  });

  /* ---------- emitir nota simulada (UC16 passos 3-5; FA1, FE1, FE2) ---------- */
  $('btn-confirmar-nota').addEventListener('click', async function () {
    var btn = this; btn.disabled = true; btn.textContent = 'Emitindo...';
    try {
      var nota = await Api.post('/vendas/' + estado.venda.id_venda + '/nota-fiscal');
      desenharDetalhe(await Api.get('/vendas/' + estado.venda.id_venda));
      U.mostrar(msgDetalhe, 'sucesso', 'Nota fiscal simulada ' + U.esc(nota.numero) + ' disponível para esta venda (emitida em ' + E.formatarData(nota.data_emissao) + ').'); msgDetalhe.focus();
    } catch (err) {
      erroNoDetalhe(err);
    } finally {
      btn.disabled = false; btn.textContent = 'Confirmar emissão';
    }
  });
});
