/* Tela app/categorias/index.html. UC05; RF07, RF08; RN07, RN08; RNF04, RNF05.
   Rotas do contrato modulo-3: GET/POST /categorias, PUT /categorias/{id}, PATCH /categorias/{id}/situacao.
   Tudo via Api (js/api.js). Sem exclusão: "excluir" é desativar (RN07). Mostrar/esconder é conveniência;
   a segurança real é do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, E = EquipUi;
  var TAMANHO = 10;
  var $ = function (id) { return document.getElementById(id); };
  var msgPagina = $('mensagem');
  var form = $('form-cat'), campoNome = $('f-nome');
  var modalForm = new bootstrap.Modal($('modal-form'));
  var modalSituacao = new bootstrap.Modal($('modal-situacao'));
  var estado = { pagina: 1, filtros: {}, editando: null, alvo: null, itens: {} };

  Layout.iniciar({ chave: 'categorias' }).then(function () {
    if (!$('area-cat')) { return; } /* sem permissão: o layout já mostrou a mensagem */
    carregar(1);
  });

  /* ---------- listagem (UC05 FA1) ---------- */
  function botoes(c) {
    var nome = E.escAttr(c.nome), id = c.id_categoria;
    if (c.protegida) { /* UC05 passo 6 / FE4: sem renomear nem desativar */
      return '<span class="texto-sem-acao">Categoria base: não pode ser renomeada nem desativada.</span>';
    }
    var desativar = c.ativa;
    return '<div class="grupo-acoes">' +
      '<button type="button" class="btn btn-outline-leaf" data-acao="renomear" data-id="' + id + '" aria-label="Renomear ' + nome + '">Renomear</button>' +
      '<button type="button" class="btn btn-acao-situacao" data-acao="situacao" data-id="' + id + '" aria-label="' + (desativar ? 'Desativar ' : 'Reativar ') + nome + '">' + (desativar ? 'Desativar' : 'Reativar') + '</button></div>';
  }
  function linhaHtml(c) {
    return '<tr role="row">' +
      '<td role="cell" data-rotulo="Categoria"><strong>' + U.esc(c.nome) + '</strong>' + (c.protegida ? ' ' + E.seloProtegida() : '') + '</td>' +
      '<td role="cell" data-rotulo="Situação">' + E.seloCategoria(c.ativa) + '</td>' +
      '<td role="cell" data-rotulo="Equipamentos">' + U.esc(c.total_equipamentos) + '</td>' +
      '<td role="cell" class="acoes">' + botoes(c) + '</td></tr>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO], fl = estado.filtros;
    if (fl.ativa) { q.push('ativa=' + fl.ativa); }
    if (fl.q) { q.push('q=' + encodeURIComponent(fl.q)); }
    $('estado-lista').textContent = 'Carregando...';
    $('estado-lista').hidden = false;
    try {
      var p = await Api.get('/categorias?' + q.join('&'));
      if (p.items.length === 0 && p.total > 0 && pagina > 1) { return carregar(pagina - 1); }
      estado.pagina = p.page;
      estado.itens = {};
      p.items.forEach(function (c) { estado.itens[c.id_categoria] = c; });
      $('corpo-tabela').innerHTML = p.items.map(linhaHtml).join('');
      $('tabela').hidden = p.items.length === 0;
      $('paginacao').hidden = p.total === 0;
      if (p.items.length === 0) {
        $('estado-lista').textContent = 'Nenhuma categoria encontrada' + (fl.ativa || fl.q ? ' para os filtros informados.' : '.');
      } else {
        $('estado-lista').hidden = true;
      }
      $('texto-pagina').textContent = E.textoPagina(p, 'categoria', 'categorias');
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
    estado.filtros = { q: $('filtro-q').value.trim(), ativa: $('filtro-ativa').value };
    U.ocultar(msgPagina);
    carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () {
    $('form-filtros').reset(); estado.filtros = {}; U.ocultar(msgPagina); carregar(1); $('filtro-q').focus();
  });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });

  $('corpo-tabela').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-acao]');
    if (!b) { return; }
    var id = Number(b.getAttribute('data-id'));
    if (b.getAttribute('data-acao') === 'situacao') { abrirSituacao(id); } else { abrirRenomear(id); }
  });

  /* ---------- foco devolvido ao elemento que abriu o modal (RNF06) ---------- */
  var abridor = null;
  function guardarAbridor(el) { abridor = el || document.activeElement; }
  function devolverFoco() {
    var el = abridor; abridor = null;
    if (!el || !document.body.contains(el) || el.disabled || el.offsetParent === null) {
      var a = el && el.getAttribute && el.getAttribute('data-acao'), i = el && el.getAttribute && el.getAttribute('data-id');
      var alt = a && i ? document.querySelector('button[data-acao="' + a + '"][data-id="' + i + '"]') : null;
      el = alt || $('btn-novo');
    }
    el.focus();
  }
  $('modal-form').addEventListener('hidden.bs.modal', devolverFoco);
  $('modal-situacao').addEventListener('hidden.bs.modal', devolverFoco);

  /* ---------- formulário (UC05 passos 2 e 3, FA1) ---------- */
  function prepararForm(cat) {
    estado.editando = cat || null;
    form.reset();
    U.limparErros(form);
    U.ocultar($('msg-form'));
    $('btn-salvar').disabled = false; $('btn-salvar').textContent = 'Salvar';
    $('modal-form-titulo').textContent = cat ? 'Renomear categoria' : 'Nova categoria';
    if (cat) { campoNome.value = cat.nome; }
  }
  $('btn-novo').addEventListener('click', function () {
    guardarAbridor(this); U.ocultar(msgPagina); prepararForm(null); modalForm.show();
  });
  $('modal-form').addEventListener('shown.bs.modal', function () { campoNome.focus(); });

  async function abrirRenomear(id) {
    guardarAbridor(); U.ocultar(msgPagina);
    try {
      var c = await Api.get('/categorias/' + id); /* FA1: dados atuais */
      if (c.protegida) { /* FE4 antes de abrir o formulário */
        U.mostrar(msgPagina, 'erro', U.esc(E.MSG.CATEGORIA_PROTEGIDA)); msgPagina.focus(); return;
      }
      prepararForm(c); modalForm.show();
    } catch (err) {
      U.mostrar(msgPagina, 'erro', U.esc(E.msgErro(err))); msgPagina.focus();
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    U.limparErros(form); U.ocultar($('msg-form'));
    var nome = campoNome.value.trim();
    /* Validação no cliente (RNF04; UC05 FE1 e FE3) */
    var erro = !nome ? 'Informe o nome da categoria.' : (nome.length > 80 ? 'O nome deve ter no máximo 80 caracteres.' : '');
    if (erro) {
      U.erroCampo(campoNome, erro);
      U.mostrar($('msg-form'), 'erro', 'Corrija o campo indicado e tente novamente.');
      campoNome.focus(); return;
    }
    var btn = $('btn-salvar'), editando = estado.editando;
    btn.disabled = true; btn.textContent = 'Salvando...';
    try {
      var salvo = editando ? await Api.put('/categorias/' + editando.id_categoria, { nome: nome })
                           : await Api.post('/categorias', { nome: nome });
      modalForm.hide();
      U.mostrar(msgPagina, 'sucesso', 'Categoria <strong>' + U.esc(salvo.nome) + '</strong> ' + (editando ? 'atualizada' : 'cadastrada e disponível para novos equipamentos') + ' com sucesso.');
      await carregar(editando ? estado.pagina : 1);
    } catch (err) {
      btn.disabled = false; btn.textContent = 'Salvar';
      var marcou = U.aplicarCamposDaApi(err, { nome: campoNome });
      if (err.codigo === 'NOME_CATEGORIA_DUPLICADO') { U.erroCampo(campoNome, 'Já existe uma categoria com este nome.'); marcou = true; }
      /* UC05 FE2: falha ao salvar -> mensagem clara; FE4: CATEGORIA_PROTEGIDA */
      var texto = err.codigo === 'REDE' || err.status >= 500 ? 'A alteração não foi concluída. ' + E.msgErro(err) : E.msgErro(err);
      U.mostrar($('msg-form'), 'erro', U.esc(texto));
      if (marcou) { campoNome.focus(); } else { $('msg-form').focus(); }
      if (err.codigo === 'NAO_ENCONTRADO' || err.codigo === 'CATEGORIA_PROTEGIDA') { carregar(estado.pagina); }
    }
  });

  /* ---------- desativar / reativar com confirmação (UC05 FA2; RN07) ---------- */
  function abrirSituacao(id) {
    guardarAbridor(); U.ocultar(msgPagina);
    var c = estado.itens[id];
    if (!c) { return; }
    var desativar = c.ativa;
    estado.alvo = { id: id, nova: !desativar, nome: c.nome };
    $('modal-situacao-titulo').textContent = desativar ? 'Desativar categoria' : 'Reativar categoria';
    $('modal-situacao-texto').innerHTML = desativar
      ? 'Deseja realmente desativar <strong>' + U.esc(c.nome) + '</strong>? Ela deixa de aparecer para novos equipamentos, mas os ' + U.esc(c.total_equipamentos) + ' equipamento(s) vinculado(s) são preservados.'
      : 'Deseja reativar <strong>' + U.esc(c.nome) + '</strong>? Ela volta a poder ser escolhida em novos equipamentos.';
    U.ocultar($('msg-situacao'));
    $('btn-confirmar-situacao').disabled = false;
    $('btn-confirmar-situacao').textContent = desativar ? 'Sim, desativar' : 'Sim, reativar';
    modalSituacao.show();
  }
  $('modal-situacao').addEventListener('shown.bs.modal', function () { $('btn-nao-situacao').focus(); });

  $('btn-confirmar-situacao').addEventListener('click', async function () {
    var btn = this, alvo = estado.alvo, rotulo = btn.textContent;
    btn.disabled = true; btn.textContent = 'Aguarde...';
    try {
      await Api.patch('/categorias/' + alvo.id + '/situacao', { ativa: alvo.nova });
      modalSituacao.hide();
      U.mostrar(msgPagina, 'sucesso', 'Categoria <strong>' + U.esc(alvo.nome) + '</strong> ' + (alvo.nova ? 'reativada' : 'desativada') + ' com sucesso.');
      await carregar(estado.pagina);
    } catch (err) {
      btn.disabled = false; btn.textContent = rotulo;
      U.mostrar($('msg-situacao'), 'erro', U.esc(E.msgErro(err)));
      $('msg-situacao').focus();
      if (err.codigo === 'NAO_ENCONTRADO' || err.codigo === 'CATEGORIA_PROTEGIDA') { carregar(estado.pagina); }
    }
  });
});
