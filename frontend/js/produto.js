/* Detalhe do produto (compra.html). UC12 passos 3-4, UC13 (comprar), Solicitar doação, UC09 (Anunciar); RN12, RN13, RN04; DP-68 a DP-78.
   Rotas do contrato: GET /marketplace/produtos/{id} (token opcional), POST /vendas (Cliente Empresa; fluxo existente: pedido pendente,
   confirmação e nota pela LEAF TI) e POST /doacoes/solicitacoes (Cliente ONG). Ações por perfil:
   visitante -> login e volta ao produto; Cliente Empresa -> Comprar; Cliente ONG -> Solicitar doação; Empresa Doadora -> Anunciar (UC09);
   Administrador e Funcionário -> só consulta. Sem alert(). A segurança real é do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var P = Publico, esc = P.esc;
  var FORMAS = ['Pix', 'Boleto', 'Transferência bancária', 'Cartão de crédito']; /* DP-46, igual ao contrato do módulo 5 */
  var $ = function (id) { return document.getElementById(id); };
  var id = new URLSearchParams(window.location.search).get('id');
  var produto = null;

  function mensagem(tipo, html) {
    var el = $('msg-acao');
    el.className = 'alert ' + (tipo === 'erro' ? 'alert-danger' : tipo === 'aviso' ? 'alert-warning' : 'alert-success');
    el.innerHTML = html; el.setAttribute('role', tipo === 'erro' ? 'alert' : 'status'); el.setAttribute('tabindex', '-1'); el.focus();
  }
  function textoErro(err) { return esc((err && err.mensagem) || 'Ocorreu um erro inesperado. Tente novamente.'); }
  function falha(texto) {
    $('estado').hidden = true; $('produto').hidden = true;
    var m = $('mensagem'); m.className = 'alert alert-danger'; m.setAttribute('role', 'alert'); m.setAttribute('tabindex', '-1');
    m.innerHTML = texto; m.focus();
  }

  if (!/^\d{1,18}$/.test(id || '')) { falha('Produto não informado ou inválido. Volte ao marketplace e escolha um produto.'); return; }

  /* ---------- ações por perfil ---------- */
  function desenharAcao() {
    var perfil = P.perfil(), el = $('conteudo-acao');
    if (!perfil) { /* visitante: vê, mas só age logado; volta a este produto depois do login (DP-68) */
      el.innerHTML = '<p>Para comprar ou solicitar este produto, entre na sua conta. Depois do login você volta a esta página.</p>' +
        '<a class="btn btn-success fw-semibold" id="btn-entrar-acao" href="' + esc(P.urlLogin()) + '">Entrar</a>';
    } else if (perfil === 'Cliente Empresa') {
      el.innerHTML = '<form id="form-compra" novalidate><div class="mb-3" style="max-width:24rem">' +
        '<label class="form-label" for="forma-pagamento">Forma de pagamento <span aria-hidden="true">*</span></label>' +
        '<select class="form-select" id="forma-pagamento" aria-describedby="forma-pagamento-erro" required><option value="">Selecione...</option>' +
        FORMAS.map(function (f) { return '<option>' + esc(f) + '</option>'; }).join('') + '</select>' +
        '<div class="invalid-feedback" id="forma-pagamento-erro"></div></div>' +
        '<button type="submit" class="btn btn-success btn-lg fw-semibold" id="btn-comprar">Comprar</button></form>';
      $('form-compra').addEventListener('submit', comprar);
    } else if (perfil === 'Cliente ONG') {
      el.innerHTML = '<p>Solicite a doação deste produto. O pedido fica <strong>pendente</strong> e o produto fica reservado até a decisão da LEAF TI.</p>' +
        '<div class="d-flex flex-wrap gap-2"><button type="button" class="btn btn-success btn-lg fw-semibold" id="btn-solicitar">Solicitar doação</button>' +
        '<a class="btn btn-outline-leaf btn-lg fw-semibold" href="hardware.html">Escolher mais produtos</a></div>';
      $('btn-solicitar').addEventListener('click', solicitar);
    } else if (perfil === 'Empresa Doadora') {
      el.innerHTML = '<p>Tem equipamentos para anunciar? Envie uma solicitação de avaliação (exige parceria ativa).</p>' +
        '<a class="btn btn-success btn-lg fw-semibold" id="btn-anunciar" href="app/solicitacoes/index.html">Anunciar</a>';
    } else { /* Administrador e Funcionário só consultam */
      el.innerHTML = '<p>Você está consultando o marketplace. A decisão das solicitações de doação é feita na ' +
        '<a href="app/doacoes/solicitacoes.html">área interna</a>.</p>';
    }
  }

  /* UC13: Cliente Empresa cria o pedido (pendente); confirmação e nota são da LEAF TI (fluxo de /vendas). */
  async function comprar(ev) {
    ev.preventDefault();
    var sel = $('forma-pagamento'), btn = $('btn-comprar');
    sel.classList.remove('is-invalid'); sel.removeAttribute('aria-invalid');
    if (!sel.value) { /* validação local */
      sel.classList.add('is-invalid'); sel.setAttribute('aria-invalid', 'true');
      $('forma-pagamento-erro').textContent = 'Selecione a forma de pagamento.'; sel.focus(); return;
    }
    btn.disabled = true; btn.textContent = 'Enviando...';
    try {
      var v = await Api.post('/vendas', { ids_equipamento: [produto.id_equipamento], forma_pagamento: sel.value });
      $('conteudo-acao').innerHTML = '<a class="btn btn-outline-leaf fw-semibold" href="app/compras/index.html?id=' + esc(v.id_venda) + '">Ver meu pedido</a> ' +
        '<a class="btn btn-outline-leaf fw-semibold" href="hardware.html">Continuar no marketplace</a>';
      mensagem('sucesso', 'Pedido nº ' + esc(v.id_venda) + ' registrado (' + P.formatarValor(v.valor_total) + '), forma de pagamento: ' + esc(sel.value) +
        '. Ele está <strong>pendente</strong> até a confirmação pela LEAF TI; a nota fiscal é emitida depois da confirmação. ' +
        'Enquanto estiver pendente você pode alterá-lo ou cancelá-lo em Minhas compras.');
    } catch (err) {
      btn.disabled = false; btn.textContent = 'Comprar';
      if (err.codigo === 'ITEM_INDISPONIVEL' || err.codigo === 'EQUIPAMENTO_RESERVADO' || err.codigo === 'EQUIPAMENTO_INDISPONIVEL') {
        mensagem('erro', 'Este produto não está mais disponível. <a href="hardware.html">Voltar ao marketplace</a>.'); btn.disabled = true;
      } else if (err.codigo === 'CLIENTE_INATIVO' || err.codigo === 'CONTA_INATIVA') {
        mensagem('erro', 'Sua organização está inativa. O pedido não pode ser criado.');
      } else { mensagem('erro', textoErro(err)); }
    }
  }

  /* Solicitar doação: ONG envia uma solicitação com este produto (nasce Pendente; produto reservado). */
  async function solicitar() {
    var btn = $('btn-solicitar');
    btn.disabled = true; btn.textContent = 'Enviando...';
    try {
      var s = await Api.post('/doacoes/solicitacoes', { ids_equipamentos: [produto.id_equipamento] });
      $('conteudo-acao').innerHTML = '<a class="btn btn-outline-leaf fw-semibold" href="app/doacoes/solicitacoes.html">Minhas solicitações</a> ' +
        '<a class="btn btn-outline-leaf fw-semibold" href="hardware.html">Continuar no marketplace</a>';
      mensagem('sucesso', 'Solicitação nº ' + esc(s.id_solicitacao_doacao) + ' enviada. Ela está <strong>pendente</strong> e o produto fica reservado até a decisão da LEAF TI.');
    } catch (err) {
      btn.disabled = false; btn.textContent = 'Solicitar doação';
      mensagem('erro', textoErro(err));
    }
  }

  /* ---------- carga do produto (UC12 passos 3-4) ---------- */
  (async function () {
    try {
      produto = await Api.getPublico('/marketplace/produtos/' + id);
    } catch (err) {
      falha(err.status === 404
        ? 'Este produto não existe ou não está mais disponível. <a href="hardware.html">Voltar ao marketplace</a>.' : textoErro(err));
      return;
    }
    P.cabecalho(); /* a sessão pode ter sido descartada se o token estava vencido */
    document.title = 'LeafTi - ' + produto.modelo;
    $('titulo-produto').textContent = produto.modelo;
    /* UC12 (DP-84): imagem do produto (alt = modelo); sem imagem mantém o ícone padrão */
    var urlImg = Api.urlImagem(produto.imagem_url);
    if (urlImg) {
      var img = document.createElement('img'), area = $('d-imagem'), icone = area.firstElementChild;
      img.className = 'imagem-detalhe'; img.src = urlImg; img.alt = produto.modelo; img.width = 360; img.height = 270;
      img.addEventListener('error', function () { img.remove(); icone.hidden = false; });
      icone.hidden = true; area.appendChild(img);
    }
    $('d-categoria').textContent = produto.categoria;
    $('d-condicao').textContent = produto.condicao;
    /* DP-74: onde o valor não é visível, o texto de convite ocupa o lugar do preço */
    $('d-valor').innerHTML = produto.valor != null ? '<span class="preco">' + P.formatarValor(produto.valor) + '</span>'
      : (P.textoSemValor() ? '<span class="sem-valor">' + esc(P.textoSemValor()) + '</span>' : '');
    $('estado').hidden = true; $('produto').hidden = false;
    desenharAcao();
  })();
});
