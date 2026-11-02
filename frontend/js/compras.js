/* Tela app/compras/index.html. UC18 (RF04, RF15; RN04, RN15; RNF05) e UC13 FA1 (DP-47); link para UC17.
   Rotas do contrato modulo-5: GET /vendas, GET /vendas/{id}, PUT /vendas/{id}/itens, POST /vendas/{id}/cancelar,
   GET /catalogo (para adicionar itens ao pedido pendente), GET /notas-fiscais/{id}/download (via Api.baixar).
   A segurança real (404 para venda de outra organização) é do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, E = EquipUi, S = SolUi, V = VendasUi;
  var TAMANHO = 10;
  var $ = function (id) { return document.getElementById(id); };
  var VISTAS = ['vista-lista', 'vista-detalhe'];
  var msgPagina = $('mensagem'), msgDetalhe = $('msg-detalhe');
  var estado = { pagina: 1, filtros: {}, venda: null };

  Layout.iniciar({ chave: 'minhas_compras' }).then(function () {
    if (!$('area-compras')) { return; }
    V.SITUACOES.forEach(function (s) { var o = document.createElement('option'); o.value = s; o.textContent = s; $('filtro-situacao').appendChild(o); });
    $('cab-tabela').innerHTML = V.cabecalhoVendas(false);
    var id = S.idDaUrl();
    carregar(1);
    if (id) { abrirDetalhe(id); }
  });

  function vista(id, titulo) { S.mostrarVista(VISTAS, id, titulo); }

  /* ---------- lista (UC18 passos 2-3) ---------- */
  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO];
    if (estado.filtros.situacao) { q.push('situacao=' + encodeURIComponent(estado.filtros.situacao)); }
    $('estado-lista').hidden = false; $('estado-lista').textContent = 'Carregando...';
    try {
      var r = await Api.get('/vendas?' + q.join('&'));
      estado.pagina = r.page;
      $('tabela').hidden = r.items.length === 0;
      $('paginacao').hidden = r.total <= r.size;
      $('corpo-tabela').innerHTML = r.items.map(function (v) { return V.linhaVenda(v, false); }).join('');
      var vazio = $('vazio-lista');
      if (!r.items.length) {
        $('estado-lista').hidden = true; vazio.hidden = false;
        vazio.innerHTML = estado.filtros.situacao
          ? '<p class="titulo-vazio">Nenhum pedido encontrado</p><p class="mb-0">Nenhum registro atende ao filtro. Limpe o filtro para ver todos.</p>'
          : '<p class="titulo-vazio">Você ainda não fez pedidos</p><p class="mb-0">Escolha equipamentos no <a href="../../hardware.html">marketplace</a> para fazer o primeiro pedido.</p>';
      } else {
        vazio.hidden = true;
        $('estado-lista').textContent = r.total + (r.total === 1 ? ' registro encontrado.' : ' registros encontrados.');
      }
      $('texto-pagina').textContent = E.textoPagina(r, 'registro', 'registros');
      $('btn-anterior').disabled = r.page <= 1;
      $('btn-proxima').disabled = r.page * r.size >= r.total;
    } catch (err) {
      $('tabela').hidden = true; $('paginacao').hidden = true; $('vazio-lista').hidden = true;
      $('estado-lista').hidden = false; $('estado-lista').textContent = 'Não foi possível carregar suas compras.';
      U.mostrar(msgPagina, 'erro', U.esc(V.msgErro(err)));
    }
  }
  $('form-filtros').addEventListener('submit', function (ev) {
    ev.preventDefault(); U.ocultar(msgPagina);
    estado.filtros = { situacao: $('filtro-situacao').value }; carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () {
    $('form-filtros').reset(); estado.filtros = {}; U.ocultar(msgPagina); carregar(1);
  });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });
  $('corpo-tabela').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-acao="ver"]');
    if (b) { U.ocultar(msgPagina); abrirDetalhe(Number(b.dataset.id)); }
  });

  /* ---------- detalhe (UC18 passo 4; FE1) ---------- */
  function fecharPaineis() { $('painel-editor').hidden = true; $('painel-editor').innerHTML = ''; $('painel-cancelar').hidden = true; }

  function desenharDetalhe(v) {
    estado.venda = v;
    fecharPaineis();
    $('titulo-detalhe').textContent = 'Pedido nº ' + v.id_venda;
    $('corpo-detalhe').innerHTML = V.detalheHtml(v, false);
    var acoes = '';
    if (v.situacao === 'Pendente') { /* UC13 FA1: só enquanto pendente */
      acoes += '<button type="button" class="btn btn-success fw-semibold" id="btn-alterar">Alterar equipamentos</button>' +
        '<button type="button" class="btn btn-excluir" id="btn-cancelar">Cancelar pedido</button>';
    } else {
      $('corpo-detalhe').insertAdjacentHTML('beforeend', '<p class="aviso-info mt-3 mb-0" role="status"><span aria-hidden="true">○ </span>Este pedido está ' +
        U.esc(v.situacao.toLowerCase()) + ' e não pode mais ser alterado (somente leitura).</p>');
    }
    if (v.nota_fiscal) { /* UC17 */
      acoes += '<button type="button" class="btn btn-outline-leaf fw-semibold" id="btn-baixar">Baixar nota fiscal</button>' +
        '<a class="btn btn-outline-leaf fw-semibold" href="../notas-fiscais/index.html?id=' + v.nota_fiscal.id_nota + '">Ver nota fiscal</a>';
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
      /* UC18 FE1: venda de outra organização -> 404, acesso negado sem revelar dados */
      U.mostrar(msgPagina, 'erro', err.status === 404
        ? 'Pedido não encontrado. Ele não existe ou não pertence à sua organização.' : U.esc(V.msgErro(err)));
    }
  }
  $('btn-voltar').addEventListener('click', function () { vista('vista-lista', 'titulo-lista'); carregar(estado.pagina); });

  /* Recarrega o pedido quando ele deixou de estar pendente (VENDA_NAO_PENDENTE) */
  async function atualizarAposErro(err) {
    if (err.codigo === 'VENDA_NAO_PENDENTE' || err.status === 404) {
      try { desenharDetalhe(await Api.get('/vendas/' + estado.venda.id_venda)); } catch (e) { /* mantém a tela */ }
    }
  }

  $('acoes-detalhe').addEventListener('click', async function (ev) {
    var b = ev.target.closest('button');
    if (!b) { return; }
    U.ocultar(msgDetalhe);
    if (b.id === 'btn-baixar') { V.baixarNota(estado.venda.nota_fiscal.id_nota, estado.venda.nota_fiscal.numero, msgDetalhe); }
    if (b.id === 'btn-cancelar') { $('painel-editor').hidden = true; $('painel-cancelar').hidden = false; $('btn-confirmar-cancelar').focus(); }
    if (b.id === 'btn-alterar') { /* UC13 FA1: alterar itens, oferecendo o catálogo para acrescentar */
      $('painel-cancelar').hidden = true;
      var cat = [];
      try { cat = (await Api.get('/catalogo?size=100')).items; } catch (err) { cat = []; }
      V.editorItens($('painel-editor'), estado.venda, {
        catalogo: cat,
        salvar: function (ids) { return Api.put('/vendas/' + estado.venda.id_venda + '/itens', { ids_equipamento: ids }); },
        aoConcluir: function (v) {
          desenharDetalhe(v);
          U.mostrar(msgDetalhe, 'sucesso', 'Pedido atualizado. Ele continua pendente, aguardando a confirmação da LEAF TI.'); msgDetalhe.focus();
        },
        aoFechar: function () { fecharPaineis(); $('btn-alterar').focus(); }
      });
      $('painel-editor').hidden = false;
      $('painel-editor').querySelector('input').focus();
    }
  });

  $('btn-desistir-cancelar').addEventListener('click', function () { $('painel-cancelar').hidden = true; $('btn-cancelar').focus(); });
  $('btn-confirmar-cancelar').addEventListener('click', async function () {
    var btn = this; btn.disabled = true; btn.textContent = 'Cancelando...';
    try {
      var v = await Api.post('/vendas/' + estado.venda.id_venda + '/cancelar');
      desenharDetalhe(v);
      U.mostrar(msgDetalhe, 'sucesso', 'Pedido cancelado. Os equipamentos foram liberados.');
    } catch (err) {
      U.mostrar(msgDetalhe, 'erro', U.esc(V.msgErro(err)));
      await atualizarAposErro(err);
    } finally {
      btn.disabled = false; btn.textContent = 'Sim, cancelar pedido'; msgDetalhe.focus();
    }
  });
});
