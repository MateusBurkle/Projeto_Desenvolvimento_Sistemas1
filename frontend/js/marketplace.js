/* Marketplace: lista pública (hardware.html). UC12 (RF04, RF13; RN12, RN13, RN04), Solicitar doação (ONG), DP-68 a DP-74, DP-78.
   Rotas do contrato modulo-7: GET /marketplace/categorias, GET /marketplace/produtos (token opcional, via Api.getPublico) e
   POST /doacoes/solicitacoes (Cliente ONG, vários produtos). Sem produtos fixos: tudo vem da API. Sem alert().
   O valor só vem da API para Cliente Empresa; nos demais perfis a tela mostra o texto de convite (DP-74).
   A segurança real (perfil, reserva, organização ativa) é do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var P = Publico, esc = P.esc;
  var TAMANHO = 12, LIMITE = 20;
  var CHAVE_SEL = 'leafti.selecao_doacao'; /* ids marcados pela ONG, mantidos entre páginas e filtros */
  var $ = function (id) { return document.getElementById(id); };
  var estado = { pagina: 1, filtros: {}, itens: {} };

  function lerSelecao() { try { return JSON.parse(sessionStorage.getItem(CHAVE_SEL)) || {}; } catch (e) { return {}; } }
  function gravarSelecao(s) { sessionStorage.setItem(CHAVE_SEL, JSON.stringify(s)); }
  var selecionados = lerSelecao(); /* id_equipamento -> modelo */
  function ehOng() { return P.perfil() === 'Cliente ONG'; }
  function qtdSel() { return Object.keys(selecionados).length; }

  function mensagem(el, tipo, html) {
    el.className = 'alert ' + (tipo === 'erro' ? 'alert-danger' : tipo === 'aviso' ? 'alert-warning' : 'alert-success');
    el.innerHTML = html;
    el.setAttribute('role', tipo === 'erro' ? 'alert' : 'status');
    el.setAttribute('tabindex', '-1');
  }
  function limpar(el) { el.className = 'alert d-none'; el.innerHTML = ''; }
  function textoErro(err) { return esc((err && err.mensagem) || 'Ocorreu um erro inesperado. Tente novamente.'); }

  /* ---------- categorias (filtro) ---------- */
  async function carregarCategorias() {
    try {
      var cats = await Api.getPublico('/marketplace/categorias');
      cats.forEach(function (c) {
        var o = document.createElement('option'); o.value = c.id_categoria; o.textContent = c.nome; $('filtro-categoria').appendChild(o);
      });
    } catch (err) { $('filtro-categoria').disabled = true; } /* a lista segue funcionando sem o filtro */
  }

  /* ---------- lista (UC12 passos 1-2) ---------- */
  function precoHtml(i) {
    return i.valor != null ? '<span class="preco">' + P.formatarValor(i.valor) + '</span>'
      : (P.textoSemValor() ? '<span class="sem-valor">' + esc(P.textoSemValor()) + '</span>' : '');
  }
  function cartaoHtml(i) {
    var sel = !!selecionados[i.id_equipamento];
    var acaoOng = ehOng()
      ? '<button type="button" class="btn ' + (sel ? 'btn-success' : 'btn-outline-leaf') + ' fw-semibold" data-acao="sel" data-id="' + i.id_equipamento +
        '" aria-pressed="' + sel + '" aria-label="' + (sel ? 'Retirar ' : 'Adicionar ') + esc(i.modelo) + (sel ? ' da solicitação' : ' à solicitação') + '">' +
        (sel ? '&#10004;&#xFE0E; Na solicitação' : 'Adicionar à solicitação') + '</button>' : '';
    return '<li><article class="produto-mkt' + (sel ? ' selecionado' : '') + '" aria-labelledby="p-' + i.id_equipamento + '-t">' +
      '<span class="icone-produto-caixa" data-img-id="' + i.id_equipamento + '" aria-hidden="true"><span class="icone-produto"><i class="fas fa-microchip"></i></span></span>' +
      '<h2 id="p-' + i.id_equipamento + '-t">' + esc(i.modelo) + '</h2>' +
      '<span>' + esc(i.categoria) + '</span>' +
      '<span>Condição: <strong>' + esc(i.condicao) + '</strong></span>' + precoHtml(i) +
      '<div class="grupo-acoes"><a class="btn btn-outline-leaf fw-semibold" href="compra.html?id=' + i.id_equipamento +
      '" aria-label="Ver detalhes de ' + esc(i.modelo) + '">Ver detalhes</a>' + acaoOng + '</div></article></li>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO], fl = estado.filtros;
    if (fl.cat) { q.push('id_categoria=' + encodeURIComponent(fl.cat)); }
    if (fl.q) { q.push('busca=' + encodeURIComponent(fl.q)); }
    $('estado-lista').hidden = false; $('estado-lista').textContent = 'Carregando...';
    try {
      var r = await Api.getPublico('/marketplace/produtos?' + q.join('&'));
      P.cabecalho(); /* o token pode ter sido descartado (sessão vencida) */
      estado.pagina = r.page;
      r.items.forEach(function (i) { estado.itens[i.id_equipamento] = i; });
      $('grade').hidden = r.items.length === 0;
      $('paginacao').hidden = r.total <= r.size;
      $('grade').innerHTML = r.items.map(cartaoHtml).join('');
      /* UC12 (DP-84): imagem do produto, montada por DOM (nunca innerHTML com dados); sem imagem fica o ícone padrão */
      r.items.forEach(function (i) {
        var url = Api.urlImagem(i.imagem_url), caixa = $('grade').querySelector('[data-img-id="' + i.id_equipamento + '"]');
        if (!url || !caixa) { return; }
        var img = document.createElement('img');
        img.className = 'imagem-produto'; img.src = url; img.alt = i.modelo; img.loading = 'lazy'; img.width = 320; img.height = 160;
        img.addEventListener('error', function () { img.remove(); caixa.hidden = false; });
        caixa.parentNode.insertBefore(img, caixa); caixa.hidden = true;
      });
      var vazio = $('vazio-lista');
      if (!r.items.length) { /* UC12 FE1 */
        $('estado-lista').hidden = true; vazio.hidden = false;
        vazio.innerHTML = (fl.cat || fl.q)
          ? '<p class="fw-semibold mb-1">Nenhum produto encontrado</p><p class="mb-0">Nenhum produto atende aos filtros. Ajuste ou limpe os filtros.</p>'
          : '<p class="fw-semibold mb-1">Não há produtos disponíveis no momento</p><p class="mb-0">Volte mais tarde: novos equipamentos aparecem aqui quando ficam disponíveis.</p>';
      } else {
        vazio.hidden = true;
        $('estado-lista').textContent = r.total + (r.total === 1 ? ' produto disponível.' : ' produtos disponíveis.');
      }
      var paginas = Math.max(1, Math.ceil(r.total / r.size));
      $('texto-pagina').textContent = 'Página ' + r.page + ' de ' + paginas + ' (' + r.total + (r.total === 1 ? ' produto)' : ' produtos)');
      $('btn-anterior').disabled = r.page <= 1;
      $('btn-proxima').disabled = r.page * r.size >= r.total;
    } catch (err) {
      $('grade').hidden = true; $('paginacao').hidden = true; $('vazio-lista').hidden = true;
      $('estado-lista').textContent = 'Não foi possível carregar os produtos.';
      mensagem($('mensagem'), 'erro', textoErro(err));
    }
  }

  $('form-filtros').addEventListener('submit', function (ev) {
    ev.preventDefault(); limpar($('mensagem'));
    estado.filtros = { cat: $('filtro-categoria').value, q: $('filtro-q').value.trim() };
    carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () {
    $('form-filtros').reset(); estado.filtros = {}; limpar($('mensagem')); carregar(1);
  });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });

  /* ---------- seleção da ONG (solicitar doação com vários produtos) ---------- */
  function atualizarBarra() {
    var n = ehOng() ? qtdSel() : 0;
    $('barra-solicitacao').hidden = n === 0;
    $('resumo-solicitacao').textContent = n + (n === 1 ? ' produto selecionado' : ' produtos selecionados');
  }
  $('grade').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-acao="sel"]');
    if (!b) { return; }
    limpar($('mensagem'));
    var id = b.dataset.id;
    if (selecionados[id]) { delete selecionados[id]; }
    else if (qtdSel() >= LIMITE) {
      mensagem($('mensagem'), 'aviso', 'Uma solicitação aceita no máximo ' + LIMITE + ' produtos. Retire algum para adicionar outro.');
      return;
    } else { selecionados[id] = estado.itens[id] ? estado.itens[id].modelo : 'Produto ' + id; }
    gravarSelecao(selecionados); atualizarBarra();
    b.closest('li').outerHTML = cartaoHtml(estado.itens[id]);
    var novo = $('grade').querySelector('button[data-acao="sel"][data-id="' + id + '"]');
    if (novo) { novo.focus(); }
  });

  function desenharRevisao() {
    var ids = Object.keys(selecionados);
    $('itens-solicitacao').innerHTML = ids.map(function (id) {
      return '<li class="mb-1">' + esc(selecionados[id]) + ' <button type="button" class="btn btn-excluir btn-sm" data-retirar="' + id +
        '" aria-label="Retirar ' + esc(selecionados[id]) + ' da solicitação">Retirar</button></li>';
    }).join('');
    $('btn-enviar-solicitacao').disabled = ids.length === 0;
  }
  $('btn-revisar').addEventListener('click', function () {
    limpar($('msg-solicitacao')); desenharRevisao();
    $('painel-solicitacao').hidden = false; $('titulo-solicitacao').focus();
  });
  $('btn-voltar-lista').addEventListener('click', function () { $('painel-solicitacao').hidden = true; carregar(estado.pagina); });
  $('itens-solicitacao').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-retirar]');
    if (!b) { return; }
    delete selecionados[b.dataset.retirar]; gravarSelecao(selecionados); atualizarBarra(); desenharRevisao();
    $('btn-enviar-solicitacao').focus();
  });
  $('btn-enviar-solicitacao').addEventListener('click', async function () {
    var msg = $('msg-solicitacao'), btn = this;
    limpar(msg);
    var ids = Object.keys(selecionados).map(Number);
    if (!ids.length) { mensagem(msg, 'erro', 'Selecione ao menos um produto.'); msg.focus(); return; }
    btn.disabled = true; btn.textContent = 'Enviando...';
    try {
      var s = await Api.post('/doacoes/solicitacoes', { ids_equipamentos: ids });
      selecionados = {}; gravarSelecao(selecionados); atualizarBarra(); desenharRevisao();
      mensagem(msg, 'sucesso', 'Solicitação nº ' + esc(s.id_solicitacao_doacao) + ' enviada. Ela está <strong>pendente</strong> e os produtos ficam reservados até a decisão da LEAF TI. ' +
        '<a href="app/doacoes/solicitacoes.html">Acompanhar minhas solicitações</a>.');
    } catch (err) {
      /* EQUIPAMENTO_RESERVADO / EQUIPAMENTO_INDISPONIVEL / ORGANIZACAO_INVALIDA: a API explica em português */
      mensagem(msg, 'erro', textoErro(err) + (err.status === 422 ? ' Retire os produtos indisponíveis e envie novamente.' : ''));
    } finally {
      btn.disabled = qtdSel() === 0; btn.textContent = 'Enviar solicitação';
      msg.focus();
    }
  });

  if (!ehOng()) { selecionados = {}; gravarSelecao(selecionados); } /* seleção é só da ONG */
  atualizarBarra();
  carregarCategorias();
  carregar(1);
});
