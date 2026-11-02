/* Tela app/equipamentos/index.html. UC07 (RF08, RF11; RN08, RN11; RNF04) e UC08 (RF12; RN12); RNF05.
   Rotas do contrato modulo-3: GET /categorias, GET/POST /equipamentos, GET/PUT /equipamentos/{id},
   PATCH /equipamentos/{id}/situacao, PATCH /equipamentos/{id}/ativo; e GET /organizacoes (módulo 2) para a ONG da doação.
   Imagem do produto (DP-84 a DP-86, opcional): PUT /equipamentos/{id}/imagem (multipart, campo `arquivo`) e DELETE na mesma rota,
   chamados depois de salvar o equipamento por JSON. Tudo via Api (js/api.js). Sem exclusão: "excluir" é desativar (UC07 FA2).
   Mostrar/esconder é conveniência; a segurança real é do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, E = EquipUi;
  var TAMANHO = 10;
  var $ = function (id) { return document.getElementById(id); };
  var msgPagina = $('mensagem');

  var f = { identificacao: $('f-identificacao'), categoria: $('f-categoria'), modelo: $('f-modelo'), condicao: $('f-condicao'),
            origem: $('f-origem'), data: $('f-data'), valor: $('f-valor'), item: $('f-item'), solicitacao: $('f-solicitacao'), situacao: $('f-situacao') };
  /* nomes dos campos da API (= colunas do banco) -> inputs */
  var mapaApi = { identificacao: f.identificacao, id_categoria: f.categoria, modelo: f.modelo, condicao: f.condicao,
                  origem: f.origem, data_recebimento: f.data, valor: f.valor, id_item_solicitacao: f.item, situacao: f.situacao };
  var form = $('form-eq'), formSit = $('form-sit');
  var s = { situacao: $('s-situacao'), busca: $('s-busca-ong'), ong: $('s-ong'), data: $('s-data') };
  var mapaSit = { situacao: s.situacao, id_organizacao_ong: s.ong, data_doacao: s.data };
  var modalForm = new bootstrap.Modal($('modal-form'));
  var modalSit = new bootstrap.Modal($('modal-sit'));
  var modalAtivo = new bootstrap.Modal($('modal-ativo'));

  /* modo do formulário: 'criar' | 'editar' | 'leitura' (vendido ou doado) */
  var estado = { pagina: 1, filtros: {}, modo: 'criar', editando: null, itens: {}, catsTodas: [], catsAtivas: [], eqSit: null, alvoAtivo: null, seqOng: 0 };

  Layout.iniciar({ chave: 'equipamentos' }).then(function () {
    if (!$('area-eq')) { return; } /* sem permissão: o layout já mostrou a mensagem */
    preencherSelects();
    carregarCategorias().then(function () { preencherFiltroCategoria(); });
    carregar(1);
  });

  function opcao(valor, texto) { var o = document.createElement('option'); o.value = valor; o.textContent = texto; return o; }
  function preencher(select, placeholder, lista) {
    select.innerHTML = '';
    if (placeholder != null) { select.appendChild(opcao('', placeholder)); }
    lista.forEach(function (v) { select.appendChild(opcao(v, v)); });
  }
  function preencherSelects() {
    E.SITUACOES.forEach(function (v) { $('filtro-situacao').appendChild(opcao(v, v)); });
    E.CONDICOES.forEach(function (v) { $('filtro-condicao').appendChild(opcao(v, v)); });
    preencher(f.condicao, 'Selecione a condição', E.CONDICOES);
    /* UC07 passo 3: situação inicial; Vendido e Doado não são aceitos na criação (contrato) */
    preencher(f.situacao, null, E.SITUACOES.filter(function (v) { return v !== 'Vendido' && v !== 'Doado'; }));
  }

  /* ---------- categorias (UC07 passo 2; RN08) ---------- */
  async function carregarCategorias() {
    try {
      var todas = await Api.get('/categorias?size=100');
      estado.catsTodas = todas.items;
      estado.catsAtivas = todas.items.filter(function (c) { return c.ativa; });
    } catch (err) {
      U.mostrar(msgPagina, 'erro', 'Não foi possível carregar as categorias. ' + U.esc(E.msgErro(err)));
    }
  }
  function preencherFiltroCategoria() {
    var sel = $('filtro-categoria'), atual = sel.value;
    sel.innerHTML = ''; sel.appendChild(opcao('', 'Todas as categorias'));
    estado.catsTodas.forEach(function (c) { sel.appendChild(opcao(c.id_categoria, c.nome + (c.ativa ? '' : ' (desativada)'))); });
    sel.value = atual;
  }
  /* Só categorias ativas para escolher; a categoria desativada já vinculada continua listada (UC07 FA1). */
  function preencherCategoriaForm(eq) {
    f.categoria.innerHTML = '';
    f.categoria.appendChild(opcao('', 'Selecione a categoria'));
    var ids = {};
    estado.catsAtivas.forEach(function (c) { ids[c.id_categoria] = true; });
    if (eq && !ids[eq.id_categoria]) { f.categoria.appendChild(opcao(eq.id_categoria, eq.nome_categoria + ' (desativada, mantida neste registro)')); }
    estado.catsAtivas.forEach(function (c) { f.categoria.appendChild(opcao(c.id_categoria, c.nome)); });
    f.categoria.value = eq ? String(eq.id_categoria) : '';
    $('f-categoria-dica').textContent = eq && !ids[eq.id_categoria]
      ? 'A categoria atual está desativada e permanece no registro. Para trocá-la, escolha uma categoria ativa.'
      : 'Somente categorias ativas podem ser escolhidas.';
  }

  /* ---------- listagem (UC07 FA1) ---------- */
  function botoes(eq) {
    var nome = E.escAttr(eq.identificacao), id = eq.id_equipamento;
    if (E.finalizado(eq)) { /* FE2: vendido/doado = somente leitura */
      return '<div class="grupo-acoes"><button type="button" class="btn btn-outline-leaf" data-acao="ver" data-id="' + id + '" aria-label="Consultar ' + nome + ' (somente leitura)">Consultar</button></div>';
    }
    var h = '<div class="grupo-acoes"><button type="button" class="btn btn-outline-leaf" data-acao="editar" data-id="' + id + '" aria-label="Editar ' + nome + '">Editar</button>';
    if (eq.situacao !== 'Destinado à reciclagem') { /* situação final: sem novas transições */
      h += '<button type="button" class="btn btn-outline-leaf" data-acao="situacao" data-id="' + id + '" aria-label="Atualizar situação de ' + nome + '">Atualizar situação</button>';
    }
    h += '<button type="button" class="btn btn-acao-situacao" data-acao="ativo" data-id="' + id + '" aria-label="' + (eq.ativo ? 'Desativar ' : 'Reativar ') + nome + '">' + (eq.ativo ? 'Desativar' : 'Reativar') + '</button></div>';
    return h;
  }
  function linhaHtml(eq) {
    var doacao = eq.doacao
      ? '<span class="sub doacao-linha">ONG: ' + U.esc(eq.doacao.nome_ong) + ' em ' + E.formatarData(eq.doacao.data_doacao) + '</span>' : '';
    var url = Api.urlImagem(eq.imagem_url);
    var mini = url ? '<img class="miniatura-eq" src="' + U.esc(url) + '" alt="' + E.escAttr(eq.modelo) + '" width="56" height="56" loading="lazy">'
      : '<span class="texto-sem-acao">Sem imagem</span>';
    return '<tr role="row">' +
      '<td role="cell" data-rotulo="Imagem">' + mini + '</td>' +
      '<td role="cell" data-rotulo="Identificação"><strong>' + U.esc(eq.identificacao) + '</strong><span class="sub">' + U.esc(eq.nome_categoria) + (eq.categoria_ativa ? '' : ' (desativada)') + '</span></td>' +
      '<td role="cell" data-rotulo="Modelo">' + U.esc(eq.modelo) + '<span class="sub">Origem: ' + U.esc(eq.origem) + '</span></td>' +
      '<td role="cell" data-rotulo="Condição">' + U.esc(eq.condicao) + '</td>' +
      '<td role="cell" data-rotulo="Situação">' + E.seloSituacao(eq.situacao) + ' ' + E.seloAtivo(eq.ativo) + doacao + '</td>' +
      '<td role="cell" data-rotulo="Valor">' + E.formatarValor(eq.valor) + '</td>' +
      '<td role="cell" data-rotulo="Recebimento">' + E.formatarData(eq.data_recebimento) + '</td>' +
      '<td role="cell" class="acoes">' + botoes(eq) + '</td></tr>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO], fl = estado.filtros;
    if (fl.id_categoria) { q.push('id_categoria=' + encodeURIComponent(fl.id_categoria)); }
    if (fl.situacao) { q.push('situacao=' + encodeURIComponent(fl.situacao)); }
    if (fl.condicao) { q.push('condicao=' + encodeURIComponent(fl.condicao)); }
    if (fl.ativo) { q.push('ativo=' + fl.ativo); }
    if (fl.q) { q.push('q=' + encodeURIComponent(fl.q)); }
    if (fl.de) { q.push('data_recebimento_de=' + fl.de); }
    if (fl.ate) { q.push('data_recebimento_ate=' + fl.ate); }
    var filtrado = !!(fl.id_categoria || fl.situacao || fl.condicao || fl.ativo || fl.q || fl.de || fl.ate);
    $('estado-lista').textContent = 'Carregando...';
    $('estado-lista').hidden = false;
    try {
      var p = await Api.get('/equipamentos?' + q.join('&'));
      if (p.items.length === 0 && p.total > 0 && pagina > 1) { return carregar(pagina - 1); }
      estado.pagina = p.page;
      estado.itens = {};
      p.items.forEach(function (eq) { estado.itens[eq.id_equipamento] = eq; });
      $('corpo-tabela').innerHTML = p.items.map(linhaHtml).join('');
      $('tabela').hidden = p.items.length === 0;
      $('paginacao').hidden = p.total === 0;
      if (p.items.length === 0) {
        $('estado-lista').textContent = 'Nenhum equipamento encontrado' + (filtrado ? ' para os filtros informados.' : '.');
      } else {
        $('estado-lista').hidden = true;
      }
      $('texto-pagina').textContent = E.textoPagina(p, 'equipamento', 'equipamentos');
      $('btn-anterior').disabled = p.page <= 1;
      $('btn-proxima').disabled = p.page * p.size >= p.total;
    } catch (err) {
      $('tabela').hidden = true; $('paginacao').hidden = true;
      $('estado-lista').textContent = 'Não foi possível carregar a lista.';
      U.mostrar(msgPagina, 'erro', U.esc(E.msgErro(err)));
    }
  }

  $('form-filtros').addEventListener('submit', function (e) {
    e.preventDefault();
    U.limparErros($('form-filtros')); U.ocultar(msgPagina);
    var de = $('filtro-de').value, ate = $('filtro-ate').value;
    if (de && ate && de > ate) { /* RNF04: período coerente */
      U.erroCampo($('filtro-ate'), 'A data final não pode ser anterior à data inicial.');
      $('filtro-ate').focus(); return;
    }
    estado.filtros = { q: $('filtro-q').value.trim(), id_categoria: $('filtro-categoria').value, situacao: $('filtro-situacao').value,
                       condicao: $('filtro-condicao').value, ativo: $('filtro-ativo').value, de: de, ate: ate };
    carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () {
    $('form-filtros').reset(); U.limparErros($('form-filtros')); estado.filtros = {}; U.ocultar(msgPagina); carregar(1); $('filtro-q').focus();
  });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });

  $('corpo-tabela').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-acao]');
    if (!b) { return; }
    var id = Number(b.getAttribute('data-id')), acao = b.getAttribute('data-acao');
    if (acao === 'situacao') { abrirSituacao(id); }
    else if (acao === 'ativo') { abrirAtivo(id); }
    else { abrirEdicao(id, acao === 'ver'); }
  });

  /* ---------- foco devolvido ao elemento que abriu o modal (RNF06) ---------- */
  var abridor = null;
  function guardarAbridor(el) { abridor = el || document.activeElement; }
  function devolverFoco() {
    var el = abridor; abridor = null;
    if (!el || !document.body.contains(el) || el.disabled || el.offsetParent === null) {
      var a = el && el.getAttribute && el.getAttribute('data-acao'), i = el && el.getAttribute && el.getAttribute('data-id');
      var alt = a && i ? document.querySelector('button[data-acao="' + a + '"][data-id="' + i + '"]') : null;
      if (!alt && i) { alt = document.querySelector('button[data-id="' + i + '"]'); } /* a linha pode ter mudado de botões */
      el = alt || $('btn-novo');
    }
    el.focus();
  }
  ['modal-form', 'modal-sit', 'modal-ativo'].forEach(function (id) { $(id).addEventListener('hidden.bs.modal', devolverFoco); });

  /* Detalhes do erro que não têm campo na tela (ex.: TRANSICAO_INVALIDA indica o que falta) */
  var ROTULOS = { valor: 'Valor', condicao: 'Condição', ativo: 'Cadastro', situacao: 'Situação', id_categoria: 'Categoria',
                  id_organizacao_ong: 'ONG', data_doacao: 'Data da doação', data_recebimento: 'Data de recebimento' };
  function textoErro(err, mapa) {
    var extra = Object.keys(err.campos || {}).filter(function (k) { return !mapa[k]; })
      .map(function (k) { return (ROTULOS[k] || k) + ': ' + err.campos[k]; });
    return U.esc(E.msgErro(err)) + (extra.length ? ' (' + U.esc(extra.join('; ')) + ')' : '');
  }
  /* Marca os campos do erro: primeiro os campos da API, depois o campo do código quando nada foi marcado */
  function marcarErro(err, mapa, porCodigo) {
    var marcou = U.aplicarCamposDaApi(err, mapa);
    var c = porCodigo[err.codigo]; /* c[2] = true: só se a API não indicou campo */
    if (c && !(c[2] && marcou)) { U.erroCampo(c[0], c[1]); marcou = true; }
    return marcou;
  }

  /* ---------- formulário (UC07 passos 1 a 6, FA1) ---------- */
  function definirModo(modo, eq) {
    estado.modo = modo;
    var leitura = modo === 'leitura';
    ['identificacao', 'modelo', 'origem', 'data', 'valor'].forEach(function (k) { f[k].readOnly = leitura; });
    ['categoria', 'condicao', 'solicitacao', 'item'].forEach(function (k) { f[k].disabled = leitura; });
    $('bloco-situacao-nova').hidden = modo !== 'criar';
    $('bloco-situacao-atual').hidden = modo === 'criar';
    if (eq) { $('situacao-atual').innerHTML = E.seloSituacao(eq.situacao); $('ativo-atual').innerHTML = E.seloAtivo(eq.ativo); }
    $('bloco-doacao-leitura').hidden = !(eq && eq.doacao);
    if (eq && eq.doacao) { $('leitura-ong').textContent = eq.doacao.nome_ong; $('leitura-data-doacao').textContent = E.formatarData(eq.doacao.data_doacao); }
    $('btn-salvar').hidden = leitura;
    $('btn-escolher-imagem').hidden = leitura; /* somente leitura: apenas mostra a imagem */
    atualizarBotaoRemover();
    /* UC08 passo 1: atalho só na edição de equipamento não finalizado e sem situação final */
    $('btn-situacao-form').hidden = !(modo === 'editar' && eq && !E.finalizado(eq) && eq.situacao !== 'Destinado à reciclagem');
    $('btn-cancelar').textContent = leitura ? 'Fechar' : 'Cancelar';
    var dica = $('dica-form');
    dica.hidden = !leitura;
    dica.textContent = leitura ? 'Equipamento ' + (eq ? eq.situacao.toLowerCase() : '') + ': somente consulta. Vendidos e doados não podem mais ser alterados nem desativados.' : '';
    $('modal-form-titulo').textContent = modo === 'criar' ? 'Novo equipamento' : (leitura ? 'Consultar equipamento' : 'Editar equipamento');
    $('f-data').max = E.hojeIso();
  }

  /* ---------- imagem do produto (UC07; DP-84, DP-85) ---------- */
  var img = { arquivo: null, remover: false, atual: null, previa: null };
  var elImg = $('f-imagem'), elPrevia = $('previa-imagem'), elImgErro = $('f-imagem-erro');
  function liberarPrevia() { if (img.previa) { URL.revokeObjectURL(img.previa); img.previa = null; } }
  function erroImagem(texto) { elImgErro.textContent = texto || ''; elImgErro.hidden = !texto; }
  function desenharPrevia(url, alt) {
    elPrevia.innerHTML = '';
    if (!url) { var v = document.createElement('span'); v.className = 'previa-vazia'; v.textContent = 'Sem imagem'; elPrevia.appendChild(v); return; }
    var im = document.createElement('img'); im.src = url; im.alt = alt || 'Pré-visualização da imagem do produto';
    elPrevia.appendChild(im);
  }
  function atualizarBotaoRemover() {
    var tem = !!img.arquivo || (!!img.atual && !img.remover);
    $('btn-remover-imagem').hidden = !tem || estado.modo === 'leitura';
    $('btn-escolher-imagem').textContent = tem ? 'Trocar imagem' : 'Escolher imagem';
  }
  function iniciarImagem(eq) {
    liberarPrevia(); elImg.value = '';
    img.arquivo = null; img.remover = false; img.atual = eq ? Api.urlImagem(eq.imagem_url) || null : null;
    erroImagem(''); desenharPrevia(img.atual, eq ? eq.modelo : '');
    atualizarBotaoRemover();
  }
  $('btn-escolher-imagem').addEventListener('click', function () { elImg.click(); });
  elImg.addEventListener('change', function () {
    var arq = elImg.files && elImg.files[0];
    if (!arq) { return; }
    var msg = E.validarImagem(arq);
    if (msg) { elImg.value = ''; erroImagem(msg); return; } /* RNF04: mensagem clara, nada é enviado */
    erroImagem(''); liberarPrevia();
    img.arquivo = arq; img.remover = false; img.previa = URL.createObjectURL(arq);
    desenharPrevia(img.previa); atualizarBotaoRemover();
  });
  $('btn-remover-imagem').addEventListener('click', function () {
    liberarPrevia(); elImg.value = ''; img.arquivo = null; img.remover = !!img.atual; erroImagem('');
    desenharPrevia(img.remover ? null : img.atual);
    atualizarBotaoRemover(); $('btn-escolher-imagem').focus();
  });
  $('modal-form').addEventListener('hidden.bs.modal', liberarPrevia);

  function prepararForm(modo, eq) {
    estado.editando = eq || null;
    form.reset();
    U.limparErros(form); U.ocultar($('msg-form'));
    $('btn-salvar').disabled = false; $('btn-salvar').textContent = 'Salvar';
    iniciarImagem(eq);
    definirModo(modo, eq);
    preencherCategoriaForm(eq);
    if (eq) {
      f.identificacao.value = eq.identificacao; f.modelo.value = eq.modelo; f.condicao.value = eq.condicao; f.origem.value = eq.origem;
      f.data.value = eq.data_recebimento; f.valor.value = E.valorParaCampo(eq.valor);
      itemAtual(eq.id_item_solicitacao);
    } else {
      itemAtual(null);
      f.situacao.value = 'Recebido'; f.condicao.value = 'A avaliar'; /* condição ainda não avaliada: valor padrão sugerido, editável */
    }
  }

  /* ---------- vínculo opcional: solicitação -> item (UC07 passo 4; DP-52) ---------- */
  var podeListarSol = true; /* perfil sem GET /solicitacoes (403): seletor escondido, sem erro */
  async function carregarSolicitacoes() {
    if (!podeListarSol) { return; }
    try {
      var p = await Api.get('/solicitacoes?size=100');
      f.solicitacao.innerHTML = '';
      f.solicitacao.appendChild(opcao('', 'Sem solicitação'));
      p.items.forEach(function (sl) {
        f.solicitacao.appendChild(opcao(sl.id_solicitacao, 'Solicitação ' + sl.id_solicitacao + ' · ' + sl.nome_organizacao + ' · ' + E.formatarData(sl.data_solicitacao)));
      });
    } catch (err) {
      podeListarSol = false; $('bloco-item').hidden = true;
    }
  }
  /* Item atual do equipamento (solicitação desconhecida): mantém o vínculo até o usuário escolher outro. */
  function itemAtual(id) {
    f.solicitacao.value = '';
    f.item.innerHTML = '';
    f.item.appendChild(opcao('', 'Sem vínculo com item'));
    if (id != null) { f.item.appendChild(opcao(id, 'Item ' + id + ' (vínculo atual)')); f.item.value = String(id); }
  }
  f.solicitacao.addEventListener('change', async function () {
    var idSol = f.solicitacao.value, atual = estado.editando ? estado.editando.id_item_solicitacao : null;
    f.item.innerHTML = '';
    if (!idSol) { itemAtual(atual); return; }
    f.item.appendChild(opcao('', 'Carregando itens...'));
    try {
      var sol = await Api.get('/solicitacoes/' + idSol);
      if (f.solicitacao.value !== idSol) { return; }
      f.item.innerHTML = '';
      f.item.appendChild(opcao('', sol.itens.length ? 'Sem vínculo com item' : 'Esta solicitação não tem itens'));
      sol.itens.forEach(function (it) {
        var o = opcao(it.id_item_solicitacao, 'Item ' + it.id_item_solicitacao + ' · ' + it.tipo + ' ' + it.modelo + ' (' + it.quantidade_cadastrada + ' de ' + it.quantidade + ' cadastrados)');
        if (it.quantidade_cadastrada >= it.quantidade && it.id_item_solicitacao !== atual) { o.disabled = true; o.textContent += ' - completo'; }
        f.item.appendChild(o);
      });
      if (atual != null && f.item.querySelector('option[value="' + atual + '"]')) { f.item.value = String(atual); }
    } catch (err) {
      f.item.innerHTML = ''; f.item.appendChild(opcao('', 'Sem vínculo com item'));
      U.erroCampo(f.item, E.msgErro(err));
    }
  });
  $('btn-situacao-form').addEventListener('click', function () {
    var id = estado.editando.id_equipamento;
    $('modal-form').addEventListener('hidden.bs.modal', function () { abrirSituacao(id); }, { once: true });
    modalForm.hide();
  });

  $('btn-novo').addEventListener('click', async function () {
    guardarAbridor(this); U.ocultar(msgPagina);
    await carregarCategorias(); await carregarSolicitacoes(); /* UC05 passo 5: categorias novas ficam disponíveis */
    preencherFiltroCategoria();
    prepararForm('criar', null);
    modalForm.show();
  });
  $('modal-form').addEventListener('shown.bs.modal', function () {
    var primeiro = form.querySelector('input:not([readonly]):not([disabled]), select:not([disabled])');
    if (estado.modo === 'leitura') { $('btn-cancelar').focus(); } else if (primeiro) { primeiro.focus(); }
  });

  async function abrirEdicao(id, soVer) {
    guardarAbridor(); U.ocultar(msgPagina);
    try {
      await carregarCategorias(); await carregarSolicitacoes();
      var eq = await Api.get('/equipamentos/' + id); /* UC07 FA1: dados atuais */
      prepararForm(soVer || E.finalizado(eq) ? 'leitura' : 'editar', eq);
      modalForm.show();
    } catch (err) {
      U.mostrar(msgPagina, 'erro', U.esc(E.msgErro(err))); msgPagina.focus();
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (estado.modo === 'leitura') { return; }
    U.limparErros(form); U.ocultar($('msg-form'));
    var criando = estado.modo === 'criar';
    var v = { identificacao: f.identificacao.value, id_categoria: f.categoria.value, modelo: f.modelo.value, condicao: f.condicao.value,
              origem: f.origem.value, data_recebimento: f.data.value, valor: f.valor.value, id_item_solicitacao: f.item.value || '',
              situacao: criando ? f.situacao.value : '' };

    /* Validação no cliente (RNF04; UC07 FE1) */
    var erros = E.validarEquipamento(v, { criando: criando });
    var chaves = Object.keys(erros);
    if (chaves.length) {
      chaves.forEach(function (k) { if (mapaApi[k]) { U.erroCampo(mapaApi[k], erros[k]); } });
      U.mostrar($('msg-form'), 'erro', 'Corrija os campos indicados e tente novamente.');
      var primeiro = form.querySelector('.is-invalid'); if (primeiro) { primeiro.focus(); }
      return;
    }

    var corpo = { identificacao: v.identificacao.trim(), id_categoria: Number(v.id_categoria), modelo: v.modelo.trim(),
                  condicao: v.condicao, origem: v.origem.trim(), data_recebimento: v.data_recebimento, /* ISO na API */
                  valor: v.__valor, id_item_solicitacao: v.id_item_solicitacao.trim() ? Number(v.id_item_solicitacao) : null };
    if (criando) { corpo.situacao = v.situacao; }
    var msgImg = E.validarImagem(img.arquivo); /* tipo e 2 MB antes de enviar qualquer coisa */
    if (msgImg) { erroImagem(msgImg); U.mostrar($('msg-form'), 'erro', 'Corrija os campos indicados e tente novamente.'); return; }
    var btn = $('btn-salvar');
    btn.disabled = true; btn.textContent = 'Salvando...';
    var salvo;
    try {
      salvo = criando ? await Api.post('/equipamentos', corpo) : await Api.put('/equipamentos/' + estado.editando.id_equipamento, corpo);
    } catch (err) {
      btn.disabled = false; btn.textContent = 'Salvar';
      var marcou = marcarErro(err, mapaApi, {
        IDENTIFICACAO_DUPLICADA: [f.identificacao, 'Esta identificação já está em uso por outro equipamento.'],
        CATEGORIA_INVALIDA: [f.categoria, 'Escolha uma categoria ativa.'],
        ITEM_SOLICITACAO_INVALIDO: [f.item, 'Este item de solicitação não existe.'],
        SEM_CONDICOES_DE_REUSO: [criando ? f.situacao : f.condicao, 'Sem condições de reuso só combina com Recebido, Em avaliação ou Destinado à reciclagem.']
      });
      U.mostrar($('msg-form'), 'erro', textoErro(err, mapaApi));
      var inv = form.querySelector('.is-invalid');
      if (inv && marcou) { inv.focus(); } else { $('msg-form').focus(); }
      if (err.codigo === 'NAO_ENCONTRADO' || err.codigo === 'EQUIPAMENTO_FINALIZADO') { carregar(estado.pagina); }
      return;
    }
    /* Equipamento salvo. Segunda etapa (DP-90): enviar ou remover a imagem, se o usuário pediu. */
    var queriaRemover = !img.arquivo && img.remover;
    try {
      if (img.arquivo) {
        var fd = new FormData(); fd.append('arquivo', img.arquivo); /* sem Content-Type manual */
        salvo = await Api.enviarArquivo('/equipamentos/' + salvo.id_equipamento + '/imagem', fd);
      } else if (img.remover) {
        await Api.delete('/equipamentos/' + salvo.id_equipamento + '/imagem');
      }
    } catch (errImg) {
      /* O equipamento ESTÁ salvo; só a imagem falhou. Mantém o formulário aberto em modo de edição para tentar de novo. */
      estado.editando = salvo; definirModo('editar', salvo);
      liberarPrevia(); elImg.value = ''; img.arquivo = null; img.remover = false; img.atual = Api.urlImagem(salvo.imagem_url) || null;
      desenharPrevia(img.atual, salvo.modelo); atualizarBotaoRemover();
      var tipoErro = errImg.codigo === 'IMAGEM_MUITO_GRANDE' || errImg.codigo === 'IMAGEM_TIPO_INVALIDO';
      erroImagem(tipoErro ? errImg.mensagem : E.msgErro(errImg));
      btn.disabled = false; btn.textContent = 'Salvar';
      U.mostrar($('msg-form'), 'erro', 'O equipamento <strong>' + U.esc(salvo.identificacao) + '</strong> foi salvo, mas a imagem não foi ' +
        (queriaRemover ? 'removida' : 'enviada') + '. ' + U.esc(E.msgErro(errImg)));
      $('msg-form').focus();
      await carregar(criando ? 1 : estado.pagina);
      return;
    }
    modalForm.hide();
    U.mostrar(msgPagina, 'sucesso', 'Equipamento <strong>' + U.esc(salvo.identificacao) + '</strong> ' + (criando ? 'cadastrado' : 'atualizado') + ' com sucesso.');
    await carregar(criando ? 1 : estado.pagina);
  });

  /* ---------- UC08: atualizar situação ---------- */
  async function abrirSituacao(id) {
    guardarAbridor(); U.ocultar(msgPagina);
    var eq;
    try { eq = await Api.get('/equipamentos/' + id); } /* dados atuais antes de oferecer as situações */
    catch (err) {
      U.mostrar(msgPagina, 'erro', U.esc(E.msgErro(err))); msgPagina.focus();
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
      return;
    }
    var perm = E.situacoesPermitidas(eq);
    if (!perm.opcoes.length) { /* UC08 FE3: situação final */
      U.mostrar(msgPagina, 'erro', U.esc(perm.motivos.join(' '))); msgPagina.focus(); carregar(estado.pagina); return;
    }
    estado.eqSit = eq;
    formSit.reset(); U.limparErros(formSit); U.ocultar($('msg-sit'));
    $('btn-salvar-sit').disabled = false; $('btn-salvar-sit').textContent = 'Salvar situação';
    $('sit-equipamento').textContent = eq.identificacao + ' · ' + eq.modelo;
    $('sit-atual').innerHTML = E.seloSituacao(eq.situacao);
    $('sit-condicao').textContent = eq.condicao;
    s.situacao.innerHTML = '';
    s.situacao.appendChild(opcao('', 'Selecione a nova situação'));
    perm.opcoes.forEach(function (o) { s.situacao.appendChild(opcao(o, o + (o === eq.situacao ? ' (atual)' : ''))); });
    $('sit-motivos-lista').innerHTML = perm.motivos.map(function (m) { return '<li>' + U.esc(m) + '</li>'; }).join('');
    $('sit-motivos').hidden = perm.motivos.length === 0;
    $('sit-motivos').open = false;
    $('bloco-doacao').hidden = true;
    s.data.min = eq.data_recebimento; s.data.max = E.hojeIso();
    modalSit.show();
  }
  $('modal-sit').addEventListener('shown.bs.modal', function () { s.situacao.focus(); });

  s.situacao.addEventListener('change', function () {
    var doado = s.situacao.value === 'Doado'; /* UC08 passo 4 */
    $('bloco-doacao').hidden = !doado;
    if (doado && !s.ong.options.length) { s.busca.value = ''; carregarOngs(''); }
  });

  /* ONGs elegíveis: Cliente ONG ativa (RN12; GET /organizacoes do módulo 2) */
  async function carregarOngs(termo) {
    var seq = ++estado.seqOng, antes = s.ong.value;
    var url = '/organizacoes?tipo=' + encodeURIComponent('Cliente ONG') + '&situacao=Ativa&size=100' + (termo ? '&q=' + encodeURIComponent(termo) : '');
    $('s-busca-ong-dica').textContent = 'Buscando ONGs...';
    try {
      var p = await Api.get(url);
      if (seq !== estado.seqOng) { return; } /* resposta antiga */
      s.ong.innerHTML = '';
      s.ong.appendChild(opcao('', p.items.length ? 'Selecione a ONG' : 'Nenhuma ONG ativa encontrada'));
      p.items.forEach(function (o) { s.ong.appendChild(opcao(o.id_organizacao, o.nome_razao_social + ' (CNPJ ' + OrgUi.formatarCnpj(o.cnpj) + ')')); });
      if (antes && s.ong.querySelector('option[value="' + antes + '"]')) { s.ong.value = antes; }
      $('s-busca-ong-dica').textContent = p.total + (p.total === 1 ? ' ONG ativa encontrada.' : ' ONGs ativas encontradas.') +
        (p.total > p.items.length ? ' Mostrando as ' + p.items.length + ' primeiras; refine a busca.' : '');
    } catch (err) {
      if (seq !== estado.seqOng) { return; }
      $('s-busca-ong-dica').textContent = 'Não foi possível carregar as ONGs. ' + E.msgErro(err);
    }
  }
  var timerOng = null;
  s.busca.addEventListener('input', function () {
    clearTimeout(timerOng);
    timerOng = setTimeout(function () { carregarOngs(s.busca.value.trim()); }, 350);
  });
  s.busca.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); clearTimeout(timerOng); carregarOngs(s.busca.value.trim()); } });

  formSit.addEventListener('submit', async function (e) {
    e.preventDefault();
    U.limparErros(formSit); U.ocultar($('msg-sit'));
    var eq = estado.eqSit, nova = s.situacao.value, erros = {};
    if (!nova) { erros.situacao = 'Selecione a nova situação.'; }
    var corpo = { situacao: nova };
    if (nova === 'Doado') { /* UC08 FE1: sem ONG e data a doação não é registrada */
      if (!s.ong.value) { erros.id_organizacao_ong = 'Selecione a ONG beneficiada.'; }
      var d = s.data.value;
      if (!d) { erros.data_doacao = 'Informe a data da doação.'; }
      else if (!E.dataValida(d)) { erros.data_doacao = 'Informe uma data válida.'; }
      else if (d > E.hojeIso()) { erros.data_doacao = 'A data da doação não pode ser futura.'; }
      else if (d < eq.data_recebimento) { erros.data_doacao = 'A data da doação não pode ser anterior ao recebimento (' + E.formatarData(eq.data_recebimento) + ').'; }
      corpo.id_organizacao_ong = Number(s.ong.value); corpo.data_doacao = d;
    }
    var chaves = Object.keys(erros);
    if (chaves.length) {
      chaves.forEach(function (k) { U.erroCampo(mapaSit[k], erros[k]); });
      U.mostrar($('msg-sit'), 'erro', 'Corrija os campos indicados e tente novamente.');
      formSit.querySelector('.is-invalid').focus(); return;
    }
    var btn = $('btn-salvar-sit');
    btn.disabled = true; btn.textContent = 'Salvando...';
    try {
      var salvo = await Api.patch('/equipamentos/' + eq.id_equipamento + '/situacao', corpo);
      modalSit.hide();
      U.mostrar(msgPagina, 'sucesso', 'Situação de <strong>' + U.esc(salvo.identificacao) + '</strong> atualizada para <strong>' + U.esc(salvo.situacao) + '</strong>' +
        (salvo.doacao ? ' (ONG ' + U.esc(salvo.doacao.nome_ong) + ', ' + E.formatarData(salvo.doacao.data_doacao) + ')' : '') + '.');
      await carregar(estado.pagina);
    } catch (err) {
      btn.disabled = false; btn.textContent = 'Salvar situação';
      var marcou = marcarErro(err, mapaSit, {
        TRANSICAO_INVALIDA: [s.situacao, 'Esta mudança de situação não é permitida.'],
        SEM_CONDICOES_DE_REUSO: [s.situacao, 'Sem condições de reuso: escolha Recebido, Em avaliação ou Destinado à reciclagem.'],
        EQUIPAMENTO_INATIVO: [s.situacao, 'Equipamento inativo: reative-o antes.'],
        DOACAO_INVALIDA: [s.ong, 'Revise a ONG e a data da doação.', true]
      });
      U.mostrar($('msg-sit'), 'erro', textoErro(err, mapaSit));
      var inv = formSit.querySelector('.is-invalid');
      if (inv && marcou) { inv.focus(); } else { $('msg-sit').focus(); }
      if (err.codigo === 'NAO_ENCONTRADO' || err.codigo === 'EQUIPAMENTO_FINALIZADO') { carregar(estado.pagina); }
    }
  });

  /* ---------- desativar / reativar com confirmação (UC07 FA2) ---------- */
  function abrirAtivo(id) {
    guardarAbridor(); U.ocultar(msgPagina);
    var eq = estado.itens[id];
    if (!eq) { return; }
    var desativar = eq.ativo;
    estado.alvoAtivo = { id: id, novo: !desativar, nome: eq.identificacao };
    $('modal-ativo-titulo').textContent = desativar ? 'Desativar equipamento' : 'Reativar equipamento';
    $('modal-ativo-texto').innerHTML = desativar
      ? 'Deseja realmente desativar <strong>' + U.esc(eq.identificacao) + '</strong>? O histórico é preservado, mas o equipamento não poderá ser vendido nem destinado à doação até ser reativado.'
      : 'Deseja reativar <strong>' + U.esc(eq.identificacao) + '</strong>? Ele volta a poder ser vendido ou destinado à doação, conforme a situação.';
    U.ocultar($('msg-ativo'));
    $('btn-confirmar-ativo').disabled = false;
    $('btn-confirmar-ativo').textContent = desativar ? 'Sim, desativar' : 'Sim, reativar';
    modalAtivo.show();
  }
  $('modal-ativo').addEventListener('shown.bs.modal', function () { $('btn-nao-ativo').focus(); });

  $('btn-confirmar-ativo').addEventListener('click', async function () {
    var btn = this, alvo = estado.alvoAtivo, rotulo = btn.textContent;
    btn.disabled = true; btn.textContent = 'Aguarde...';
    try {
      await Api.patch('/equipamentos/' + alvo.id + '/ativo', { ativo: alvo.novo });
      modalAtivo.hide();
      U.mostrar(msgPagina, 'sucesso', 'Equipamento <strong>' + U.esc(alvo.nome) + '</strong> ' + (alvo.novo ? 'reativado' : 'desativado') + ' com sucesso.');
      await carregar(estado.pagina);
    } catch (err) {
      btn.disabled = false; btn.textContent = rotulo;
      U.mostrar($('msg-ativo'), 'erro', U.esc(E.msgErro(err)));
      $('msg-ativo').focus();
      if (err.codigo === 'NAO_ENCONTRADO' || err.codigo === 'EQUIPAMENTO_FINALIZADO') { carregar(estado.pagina); }
    }
  });
});
