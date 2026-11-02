/* Tela app/parceiros/index.html (somente Administrador). UC06; RF10; RN03, RN10; RNF04, RNF05.
   Rotas do contrato modulo-2: GET/POST /parceiros, GET/PUT /parceiros/{id}, PATCH /parceiros/{id}/situacao,
   GET /organizacoes?situacao=Ativa&sem_parceria=true (escolha da organização). Tudo via Api (js/api.js).
   Não há exclusão: "excluir" é desativar o vínculo (UC06 FA2). A organização não é trocada após criada (DP-27). */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, O = OrgUi;
  var TAMANHO = 10;

  var $ = function (id) { return document.getElementById(id); };
  var msgPagina = $('mensagem');
  var f = { org: $('f-org'), atuacao: $('f-atuacao'), situacao: $('f-situacao') };
  var mapaApi = { id_organizacao: f.org, tipo_parceria: f.atuacao, situacao_parceria: f.situacao };
  var form = $('form-parceiro');
  var modalForm = new bootstrap.Modal($('modal-form'));
  var modalSituacao = new bootstrap.Modal($('modal-situacao'));

  var estado = { pagina: 1, filtros: {}, editando: null, itens: {}, orgs: {}, alvo: null };

  Layout.iniciar({ chave: 'parceiros' }).then(function () {
    if (!$('area-parceiros')) { return; } /* sem permissão (RN03): o layout já mostrou a mensagem */
    carregar(1);
  });

  function dadosOrgHtml(o) { /* somente leitura; vem da junção, nunca duplicado no PARCEIRO (RF10) */
    function linha(r, v) { return '<dt>' + r + '</dt><dd>' + U.esc(v) + '</dd>'; }
    return linha('Nome / razão social', o.nome_razao_social) + linha('CNPJ', O.formatarCnpj(o.cnpj)) +
      linha('Tipo', o.tipo) + linha('Telefone', O.formatarTelefone(o.telefone)) + linha('E-mail', o.email) +
      linha('Endereço', o.endereco) + '<dt>Situação da organização</dt><dd>' + O.seloSituacao(o.situacao) + '</dd>';
  }

  /* ---------- listagem (UC06 FA1) ---------- */
  function linhaHtml(p) {
    var nome = U.esc(p.nome_razao_social), id = p.id_parceiro, ativa = p.situacao_parceria === 'Ativa';
    return '<tr>' +
      '<td data-rotulo="Organização"><strong>' + nome + '</strong><span class="sub">' + U.esc(p.tipo_organizacao) + ' &middot; organização ' + U.esc(p.situacao_organizacao.toLowerCase()) + '</span></td>' +
      '<td data-rotulo="CNPJ">' + U.esc(O.formatarCnpj(p.cnpj)) + '</td>' +
      '<td data-rotulo="Atuação">' + U.esc(p.tipo_parceria) + '</td>' +
      '<td data-rotulo="Situação">' + O.seloSituacao(p.situacao_parceria) + '</td>' +
      '<td class="acoes">' +
        '<button type="button" class="btn btn-outline-leaf" data-acao="editar" data-id="' + id + '" aria-label="Editar atuação de ' + nome + '">Editar</button>' +
        '<button type="button" class="btn btn-acao-situacao" data-acao="situacao" data-id="' + id + '" aria-label="' + (ativa ? 'Desativar' : 'Reativar') + ' parceria de ' + nome + '">' + (ativa ? 'Desativar' : 'Reativar') + '</button>' +
      '</td></tr>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO];
    var fl = estado.filtros;
    if (fl.atuacao) { q.push('tipo_parceria=' + encodeURIComponent(fl.atuacao)); }
    if (fl.situacao) { q.push('situacao_parceria=' + encodeURIComponent(fl.situacao)); }
    if (fl.q) { q.push('q=' + encodeURIComponent(fl.q)); }
    $('estado-lista').textContent = 'Carregando...';
    $('estado-lista').hidden = false;
    try {
      var p = await Api.get('/parceiros?' + q.join('&'));
      if (p.items.length === 0 && p.total > 0 && pagina > 1) { return carregar(pagina - 1); }
      estado.pagina = p.page;
      estado.itens = {};
      p.items.forEach(function (x) { estado.itens[x.id_parceiro] = x; });
      $('corpo-tabela').innerHTML = p.items.map(linhaHtml).join('');
      $('tabela').hidden = p.items.length === 0;
      $('paginacao').hidden = p.total === 0;
      if (p.items.length === 0) {
        $('estado-lista').textContent = 'Nenhum parceiro encontrado' + (fl.atuacao || fl.situacao || fl.q ? ' para os filtros informados.' : '.');
      } else {
        $('estado-lista').hidden = true;
      }
      $('texto-pagina').textContent = O.textoPagina(p, 'parceiro', 'parceiros');
      $('btn-anterior').disabled = p.page <= 1;
      $('btn-proxima').disabled = p.page * p.size >= p.total;
    } catch (err) {
      $('tabela').hidden = true; $('paginacao').hidden = true;
      $('estado-lista').textContent = 'Não foi possível carregar a lista.';
      U.mostrar(msgPagina, 'erro', U.esc(O.msgErro(err)));
    }
  }

  $('form-filtros').addEventListener('submit', function (e) {
    e.preventDefault();
    estado.filtros = { q: $('filtro-q').value.trim(), atuacao: $('filtro-atuacao').value, situacao: $('filtro-situacao').value };
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
    if (b.getAttribute('data-acao') === 'editar') { abrirEdicao(id); } else { abrirSituacao(id); }
  });

  /* ---------- foco devolvido ao abridor (RNF06) ---------- */
  var abridor = null;
  function guardarAbridor(el) { abridor = el || document.activeElement; }
  function devolverFoco() {
    var el = abridor; abridor = null;
    if (!el || !document.body.contains(el) || el.disabled || el.offsetParent === null) {
      var a = el && el.getAttribute && el.getAttribute('data-acao'), i = el && el.getAttribute && el.getAttribute('data-id');
      el = (a && i ? document.querySelector('button[data-acao="' + a + '"][data-id="' + i + '"]') : null) || $('btn-novo');
    }
    el.focus();
  }
  $('modal-form').addEventListener('hidden.bs.modal', devolverFoco);
  $('modal-situacao').addEventListener('hidden.bs.modal', devolverFoco);

  /* ---------- formulário (UC06 passos 2 a 4, FA1) ---------- */
  function opcao(valor, texto) { var o = document.createElement('option'); o.value = valor; o.textContent = texto; return o; }

  /* UC06 pré-condição: organizações ativas e sem parceria */
  async function carregarOrgs(busca) {
    f.org.innerHTML = ''; f.org.appendChild(opcao('', 'Carregando...'));
    try {
      var url = '/organizacoes?situacao=Ativa&sem_parceria=true&size=100' + (busca ? '&q=' + encodeURIComponent(busca) : '');
      var p = await Api.get(url);
      estado.orgs = {};
      f.org.innerHTML = '';
      f.org.appendChild(opcao('', p.items.length ? 'Selecione a organização' : 'Nenhuma organização disponível'));
      p.items.forEach(function (o) {
        estado.orgs[o.id_organizacao] = o;
        f.org.appendChild(opcao(o.id_organizacao, o.nome_razao_social + ' (' + o.tipo + ', ' + O.formatarCnpj(o.cnpj) + ')'));
      });
      $('f-busca-dica').textContent = p.total > p.items.length
        ? 'Mostrando as ' + p.items.length + ' primeiras de ' + p.total + ' organizações. Use a busca para filtrar.'
        : 'Aparecem apenas organizações ativas que ainda não têm parceria.';
    } catch (err) {
      f.org.innerHTML = ''; f.org.appendChild(opcao('', 'Não foi possível carregar'));
      U.mostrar($('msg-form'), 'erro', U.esc(O.msgErro(err)));
    }
  }
  $('btn-buscar-org').addEventListener('click', function () { U.ocultar($('msg-form')); carregarOrgs($('f-busca-org').value.trim()); });
  $('f-busca-org').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); $('btn-buscar-org').click(); }
  });
  f.org.addEventListener('change', function () { /* mostra os dados da organização escolhida (somente leitura) */
    var o = estado.orgs[f.org.value];
    $('bloco-dados-org').hidden = !o;
    if (o) { $('dados-org').innerHTML = dadosOrgHtml(o); }
  });

  function prepararForm(parceiro) {
    estado.editando = parceiro || null;
    form.reset();
    U.limparErros(form);
    U.ocultar($('msg-form'));
    $('btn-salvar').disabled = false; $('btn-salvar').textContent = 'Salvar';
    var edit = !!parceiro;
    $('modal-form-titulo').textContent = edit ? 'Editar parceiro' : 'Novo parceiro';
    $('bloco-busca-org').hidden = edit; $('bloco-org').hidden = edit;
    $('bloco-situacao-nova').hidden = edit; $('bloco-situacao-atual').hidden = !edit;
    $('bloco-dados-org').hidden = !edit;
    $('dica-dados-org').hidden = false;
    if (edit) {
      $('dados-org').innerHTML = dadosOrgHtml({
        nome_razao_social: parceiro.nome_razao_social, cnpj: parceiro.cnpj, tipo: parceiro.tipo_organizacao,
        telefone: parceiro.telefone, email: parceiro.email, endereco: parceiro.endereco, situacao: parceiro.situacao_organizacao });
      f.atuacao.value = parceiro.tipo_parceria;
      $('situacao-atual').innerHTML = O.seloSituacao(parceiro.situacao_parceria);
    } else {
      $('f-busca-org').value = '';
      f.situacao.value = 'Ativa';
      carregarOrgs('');
    }
  }

  $('btn-novo').addEventListener('click', function () {
    guardarAbridor(this);
    U.ocultar(msgPagina);
    prepararForm(null);
    modalForm.show();
  });
  $('modal-form').addEventListener('shown.bs.modal', function () { (estado.editando ? f.atuacao : $('f-busca-org')).focus(); });

  async function abrirEdicao(id) {
    guardarAbridor();
    U.ocultar(msgPagina);
    try {
      var p = await Api.get('/parceiros/' + id);
      prepararForm(p);
      modalForm.show();
    } catch (err) {
      U.mostrar(msgPagina, 'erro', U.esc(O.msgErro(err)));
      msgPagina.focus();
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    U.limparErros(form); U.ocultar($('msg-form'));
    var edit = !!estado.editando;

    /* Validação no cliente (RNF04; UC06 FE1, FE2). A API revalida tudo. */
    var erros = {};
    if (!edit && !f.org.value) { erros.id_organizacao = 'Selecione a organização.'; }
    if (!f.atuacao.value) { erros.tipo_parceria = 'Selecione a atuação na parceria.'; }
    var tipoOrg = edit ? estado.editando.tipo_organizacao : (estado.orgs[f.org.value] || {}).tipo;
    if (f.atuacao.value === 'Empresa Doadora' && tipoOrg && tipoOrg !== 'Empresa Doadora') {
      erros.tipo_parceria = O.MSG.ATUACAO_INCOMPATIVEL;
    }
    var chaves = Object.keys(erros);
    if (chaves.length) {
      chaves.forEach(function (k) { U.erroCampo(mapaApi[k], erros[k]); });
      U.mostrar($('msg-form'), 'erro', 'Corrija os campos indicados e tente novamente.');
      form.querySelector('.is-invalid').focus();
      return;
    }

    var btn = $('btn-salvar');
    btn.disabled = true; btn.textContent = 'Salvando...';
    try {
      var salvo, texto;
      if (edit) {
        salvo = await Api.put('/parceiros/' + estado.editando.id_parceiro, { tipo_parceria: f.atuacao.value });
        texto = 'Atuação de <strong>' + U.esc(salvo.nome_razao_social) + '</strong> atualizada com sucesso.';
      } else {
        salvo = await Api.post('/parceiros', { id_organizacao: Number(f.org.value), tipo_parceria: f.atuacao.value, situacao_parceria: f.situacao.value });
        texto = 'Parceiro <strong>' + U.esc(salvo.nome_razao_social) + '</strong> cadastrado com sucesso.';
      }
      modalForm.hide();
      U.mostrar(msgPagina, 'sucesso', texto);
      await carregar(edit ? estado.pagina : 1);
    } catch (err) {
      btn.disabled = false; btn.textContent = 'Salvar';
      /* PARCERIA_DUPLICADA, ORGANIZACAO_INVALIDA -> campo da organização; ATUACAO_INCOMPATIVEL -> atuação */
      var marcou = U.aplicarCamposDaApi(err, mapaApi);
      if (!marcou && !edit && (err.codigo === 'PARCERIA_DUPLICADA' || err.codigo === 'ORGANIZACAO_INVALIDA')) {
        U.erroCampo(f.org, O.msgErro(err)); marcou = true;
      }
      if (!marcou && err.codigo === 'ATUACAO_INCOMPATIVEL') { U.erroCampo(f.atuacao, O.MSG.ATUACAO_INCOMPATIVEL); marcou = true; }
      U.mostrar($('msg-form'), 'erro', U.esc(O.msgErro(err)));
      var inv = form.querySelector('.is-invalid');
      if (inv && marcou) { inv.focus(); } else { $('msg-form').focus(); }
      if (!edit && (err.codigo === 'PARCERIA_DUPLICADA' || err.codigo === 'ORGANIZACAO_INVALIDA')) { carregarOrgs($('f-busca-org').value.trim()); }
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  });

  /* ---------- desativar / reativar com confirmação (UC06 FA2, RN10) ---------- */
  function abrirSituacao(id) {
    guardarAbridor();
    U.ocultar(msgPagina);
    var p = estado.itens[id];
    if (!p) { return; }
    var desativar = p.situacao_parceria === 'Ativa';
    estado.alvo = { id: id, nova: desativar ? 'Inativa' : 'Ativa', nome: p.nome_razao_social };
    $('modal-situacao-titulo').textContent = desativar ? 'Desativar parceria' : 'Reativar parceria';
    $('modal-situacao-texto').innerHTML = desativar
      ? 'Deseja realmente desativar a parceria de <strong>' + U.esc(p.nome_razao_social) + '</strong>? Os registros anteriores são preservados, mas novas solicitações ficam bloqueadas até a reativação.'
      : 'Deseja reativar a parceria de <strong>' + U.esc(p.nome_razao_social) + '</strong>? A organização precisa estar ativa.';
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
      await Api.patch('/parceiros/' + alvo.id + '/situacao', { situacao_parceria: alvo.nova });
      modalSituacao.hide();
      U.mostrar(msgPagina, 'sucesso', 'Parceria de <strong>' + U.esc(alvo.nome) + '</strong> ' + (alvo.nova === 'Inativa' ? 'desativada' : 'reativada') + ' com sucesso.');
      await carregar(estado.pagina);
    } catch (err) {
      btn.disabled = false; btn.textContent = rotulo;
      U.mostrar($('msg-situacao'), 'erro', U.esc(O.msgErro(err))); /* ex.: ORGANIZACAO_INVALIDA ao reativar */
      $('msg-situacao').focus();
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  });
});
