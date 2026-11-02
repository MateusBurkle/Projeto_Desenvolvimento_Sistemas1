/* Tela do Administrador: app/usuarios/index.html. UC02 (e includes UC26, UC27); RN01, RN02, RN03, RNF03, RNF04, RNF05.
   Rotas do contrato modulo-1: GET /usuarios/perfis-atribuiveis, GET /usuarios/opcoes-organizacao,
   GET/POST /usuarios, GET/PUT/DELETE /usuarios/{id}. Todas via Api (js/api.js).
   Mostrar/esconder é conveniência; a segurança real é do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi;
  var TAMANHO = 10;

  var $ = function (id) { return document.getElementById(id); };
  var msgPagina = $('mensagem');
  var f = { nome: $('f-nome'), email: $('f-email'), senha: $('f-senha'), perfil: $('f-perfil'), org: $('f-org') };
  var mapaApi = { nome: f.nome, email: f.email, senha: f.senha, perfil: f.perfil, id_organizacao: f.org };
  var formUsuario = $('form-usuario');
  var modalForm = new bootstrap.Modal($('modal-form'));
  var modalExcluir = new bootstrap.Modal($('modal-excluir'));

  var estado = { me: null, perfis: [], orgs: [], pagina: 1, filtros: {}, editando: null, excluindo: null, ultimoPagina: null };

  /* ---------- carga inicial ---------- */
  Layout.iniciar({ chave: 'usuarios' }).then(async function (me) {
    if (!$('area-admin')) { return; } /* sem permissão: o layout já mostrou a mensagem */
    estado.me = me;
    try {
      var r = await Promise.all([Api.get('/usuarios/perfis-atribuiveis'), Api.get('/usuarios/opcoes-organizacao')]);
      estado.perfis = r[0]; estado.orgs = r[1];
    } catch (err) {
      U.mostrar(msgPagina, 'erro', U.esc(U.mensagemDoErro(err)));
    }
    preencherFiltros();
    preencherPerfisForm();
    carregar(1);
  });

  function opcao(valor, texto) { var o = document.createElement('option'); o.value = valor; o.textContent = texto; return o; }

  function preencherFiltros() {
    estado.perfis.forEach(function (p) { $('filtro-perfil').appendChild(opcao(p.perfil, p.perfil)); });
    estado.orgs.forEach(function (o) { $('filtro-org').appendChild(opcao(o.id_organizacao, o.nome_razao_social + ' (' + o.tipo + ')')); });
  }
  function preencherPerfisForm() { /* UC27 passo 1: perfis que o Administrador pode atribuir */
    estado.perfis.forEach(function (p) { f.perfil.appendChild(opcao(p.perfil, p.perfil)); });
  }

  /* ---------- listagem (UC02 FA4) ---------- */
  function linhaHtml(u) {
    var eu = estado.me && u.id_usuario === estado.me.id_usuario;
    return '<tr>' +
      '<td data-rotulo="Nome"><strong>' + U.esc(u.nome) + '</strong>' + (eu ? ' <span class="badge-voce">você</span>' : '') + '</td>' +
      '<td data-rotulo="E-mail">' + U.esc(u.email) + '</td>' +
      '<td data-rotulo="Perfil">' + U.esc(u.perfil) + '</td>' +
      '<td data-rotulo="Organização">' + (u.nome_organizacao ? U.esc(u.nome_organizacao) : 'Sem organização') + '</td>' +
      '<td class="acoes">' +
        '<button type="button" class="btn btn-outline-leaf" data-acao="editar" data-id="' + u.id_usuario + '" aria-label="Editar ' + U.esc(u.nome) + '">Editar</button>' +
        (eu ? '<button type="button" class="btn btn-excluir" disabled title="Você não pode excluir a própria conta." aria-label="Excluir ' + U.esc(u.nome) + ' (indisponível: é a sua conta)">Excluir</button>'
            : '<button type="button" class="btn btn-excluir" data-acao="excluir" data-id="' + u.id_usuario + '" aria-label="Excluir ' + U.esc(u.nome) + '">Excluir</button>') +
      '</td></tr>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO];
    var fl = estado.filtros;
    if (fl.perfil) { q.push('perfil=' + encodeURIComponent(fl.perfil)); }
    if (fl.org) { q.push('id_organizacao=' + encodeURIComponent(fl.org)); }
    if (fl.q) { q.push('q=' + encodeURIComponent(fl.q)); }
    $('estado-lista').textContent = 'Carregando...';
    $('estado-lista').hidden = false;
    try {
      var p = await Api.get('/usuarios?' + q.join('&'));
      /* página além do fim (ex.: após excluir o último item): volta uma */
      if (p.items.length === 0 && p.total > 0 && pagina > 1) { return carregar(pagina - 1); }
      estado.pagina = p.page;
      $('corpo-tabela').innerHTML = p.items.map(linhaHtml).join('');
      $('tabela').hidden = p.items.length === 0;
      $('paginacao').hidden = p.total === 0;
      if (p.items.length === 0) {
        $('estado-lista').textContent = 'Nenhum usuário encontrado' + (fl.perfil || fl.org || fl.q ? ' para os filtros informados.' : '.');
      } else {
        $('estado-lista').hidden = true;
      }
      $('texto-pagina').textContent = U.textoPagina(p);
      $('btn-anterior').disabled = p.page <= 1;
      $('btn-proxima').disabled = p.page * p.size >= p.total;
    } catch (err) {
      $('tabela').hidden = true; $('paginacao').hidden = true;
      $('estado-lista').textContent = 'Não foi possível carregar a lista.';
      U.mostrar(msgPagina, 'erro', U.esc(U.mensagemDoErro(err)));
    }
  }

  $('form-filtros').addEventListener('submit', function (e) {
    e.preventDefault();
    estado.filtros = { q: $('filtro-q').value.trim(), perfil: $('filtro-perfil').value, org: $('filtro-org').value };
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
    if (b.getAttribute('data-acao') === 'editar') { abrirEdicao(id); } else { abrirExclusao(id); }
  });

  /* ---------- formulário: criar e editar (UC02 passos 1 a 6, FA1, FA2; UC27) ---------- */
  function perfilInfo(nome) { return estado.perfis.filter(function (p) { return p.perfil === nome; })[0] || null; }

  /* UC27 passo 2/3: organização depende do perfil (tipo igual ao do perfil; bloqueada para Administrador/Funcionário). */
  function atualizarOrganizacao(manter) {
    var info = perfilInfo(f.perfil.value);
    var atual = manter !== undefined ? String(manter == null ? '' : manter) : f.org.value;
    f.org.innerHTML = '';
    $('asterisco-org').hidden = !(info && info.exige_organizacao);
    if (!info) {
      f.org.appendChild(opcao('', 'Selecione primeiro o perfil'));
      f.org.disabled = true; $('f-org-dica').textContent = '';
    } else if (!info.exige_organizacao) {
      f.org.appendChild(opcao('', 'Não se aplica a este perfil'));
      f.org.disabled = true;
      $('f-org-dica').textContent = 'Administrador e Funcionário não têm organização.';
    } else {
      f.org.appendChild(opcao('', 'Selecione a organização'));
      estado.orgs.filter(function (o) { return o.tipo === info.tipo_organizacao; }).forEach(function (o) {
        f.org.appendChild(opcao(o.id_organizacao, o.nome_razao_social));
      });
      f.org.disabled = false;
      $('f-org-dica').textContent = 'Apenas organizações ativas do tipo ' + info.tipo_organizacao + '.';
      if (atual && Array.prototype.some.call(f.org.options, function (o) { return o.value === atual; })) { f.org.value = atual; }
    }
    if (estado.editando && estado.me && estado.editando.id_usuario === estado.me.id_usuario) { f.org.disabled = true; }
  }
  f.perfil.addEventListener('change', function () { atualizarOrganizacao(''); });

  function prepararForm(usuario) {
    estado.editando = usuario;
    formUsuario.reset();
    U.limparErros(formUsuario);
    U.ocultar($('msg-form')); U.ocultar($('resultado'));
    $('campos-form').classList.remove('d-none');
    $('btn-salvar').classList.remove('d-none'); $('btn-salvar').disabled = false; $('btn-salvar').textContent = 'Salvar';
    $('btn-cancelar').textContent = 'Cancelar';
    var edit = !!usuario;
    $('modal-form-titulo').textContent = edit ? 'Editar usuário' : 'Novo usuário';
    $('rotulo-senha').textContent = edit ? 'Nova senha' : 'Senha';
    $('asterisco-senha').hidden = edit; /* obrigatória só ao criar */
    $('f-senha-dica').textContent = edit ? 'Deixe em branco para manter a senha atual. Se preencher: de 8 a 128 caracteres.' : 'De 8 a 128 caracteres.';
    f.perfil.disabled = false; f.org.disabled = false; $('f-perfil-dica').textContent = '';
    if (edit) {
      f.nome.value = usuario.nome; f.email.value = usuario.email; f.perfil.value = usuario.perfil;
      atualizarOrganizacao(usuario.id_organizacao);
      if (estado.me && usuario.id_usuario === estado.me.id_usuario) { /* RN02, UC02 FE4: não altera o próprio perfil */
        f.perfil.disabled = true; f.org.disabled = true;
        $('f-perfil-dica').textContent = 'Você não pode alterar o seu próprio perfil nem a sua organização.';
      }
    } else {
      atualizarOrganizacao('');
    }
  }

  /* Devolve o foco ao elemento que abriu o modal (RNF06); se sumiu (linha recarregada), vai ao botão Novo usuário. */
  var abridor = null;
  function guardarAbridor(el) { abridor = el || document.activeElement; }
  function devolverFoco() {
    var el = abridor;
    abridor = null;
    if (!el || !document.body.contains(el) || el.disabled || el.offsetParent === null) {
      var porId = el && el.getAttribute && el.getAttribute('data-id') && el.getAttribute('data-acao')
        ? document.querySelector('button[data-acao="' + el.getAttribute('data-acao') + '"][data-id="' + el.getAttribute('data-id') + '"]') : null;
      el = porId || $('btn-novo');
    }
    el.focus();
  }
  $('modal-form').addEventListener('hidden.bs.modal', devolverFoco);
  $('modal-excluir').addEventListener('hidden.bs.modal', function () {
    if (estado.excluido) { estado.excluido = false; abridor = null; $('btn-novo').focus(); return; }
    devolverFoco();
  });

  $('btn-novo').addEventListener('click', function () {
    guardarAbridor(this);
    U.ocultar(msgPagina);
    prepararForm(null);
    modalForm.show();
  });
  $('modal-form').addEventListener('shown.bs.modal', function () {
    if (!$('campos-form').classList.contains('d-none')) { f.nome.focus(); }
  });

  async function abrirEdicao(id) {
    guardarAbridor();
    U.ocultar(msgPagina);
    try {
      var u = await Api.get('/usuarios/' + id);
      prepararForm(u);
      modalForm.show();
    } catch (err) {
      U.mostrar(msgPagina, 'erro', U.esc(U.mensagemDoErro(err)));
      msgPagina.focus();
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  }

  formUsuario.addEventListener('submit', async function (e) {
    e.preventDefault();
    U.limparErros(formUsuario); U.ocultar($('msg-form'));
    var edit = !!estado.editando;
    var info = perfilInfo(f.perfil.value);
    var valores = { nome: f.nome.value, email: f.email.value, senha: f.senha.value, perfil: f.perfil.value, id_organizacao: f.org.value };

    /* Validação no cliente (RNF04) */
    var erros = U.validar(valores, { senhaObrigatoria: !edit, perfil: true, exigeOrg: info && info.exige_organizacao });
    var chaves = Object.keys(erros);
    if (chaves.length) {
      chaves.forEach(function (k) { U.erroCampo(f[k], erros[k]); });
      U.mostrar($('msg-form'), 'erro', 'Corrija os campos indicados e tente novamente.');
      var primeiro = formUsuario.querySelector('.is-invalid'); if (primeiro) { primeiro.focus(); }
      return;
    }

    var corpo = {
      nome: valores.nome.trim(),
      email: valores.email.trim().toLowerCase(),
      perfil: valores.perfil,
      id_organizacao: info && info.exige_organizacao ? Number(valores.id_organizacao) : null
    };
    if (valores.senha) { corpo.senha = valores.senha; } /* ao editar, senha ausente mantém a atual */

    var btn = $('btn-salvar');
    btn.disabled = true; btn.textContent = 'Salvando...';
    try {
      var salvo = edit ? await Api.put('/usuarios/' + estado.editando.id_usuario, corpo) : await Api.post('/usuarios', corpo);
      mostrarResultado(salvo, edit);
      carregar(estado.pagina);
    } catch (err) {
      btn.disabled = false; btn.textContent = 'Salvar';
      var marcou = U.aplicarCamposDaApi(err, mapaApi);
      U.mostrar($('msg-form'), 'erro', U.esc(U.mensagemDoErro(err)));
      var inv = formUsuario.querySelector('.is-invalid');
      if (inv && marcou) { inv.focus(); } else { $('msg-form').focus(); }
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  });

  /* UC02 passo 6: confirma o cadastro e as permissões atribuídas */
  function mostrarResultado(u, edit) {
    $('campos-form').classList.add('d-none');
    $('btn-salvar').classList.add('d-none');
    $('btn-cancelar').textContent = 'Fechar';
    U.ocultar($('msg-form'));
    var r = $('resultado');
    U.mostrar(r, 'sucesso',
      '<p class="mb-2">Usuário <strong>' + U.esc(u.nome) + '</strong> (' + U.esc(u.email) + ') ' + (edit ? 'atualizado.' : 'cadastrado.') + '</p>' +
      '<p class="mb-2">Perfil: <strong>' + U.esc(u.perfil) + '</strong>' + (u.nome_organizacao ? ' &middot; Organização: <strong>' + U.esc(u.nome_organizacao) + '</strong>' : '') + '</p>' +
      '<div class="lista-funcionalidades">' + U.htmlFuncionalidades(u) + '</div>');
    $('modal-form-titulo').textContent = edit ? 'Usuário atualizado' : 'Usuário cadastrado';
    r.focus();
  }

  /* ---------- exclusão com confirmação (UC02 FA3, FE4) ---------- */
  async function abrirExclusao(id) {
    guardarAbridor();
    U.ocultar(msgPagina);
    var linha = document.querySelector('button[data-acao="excluir"][data-id="' + id + '"]');
    var tr = linha && linha.closest('tr');
    estado.excluindo = { id: id, nome: tr ? tr.children[0].textContent : '', email: tr ? tr.children[1].textContent : '' };
    $('modal-excluir-texto').innerHTML = 'Deseja realmente excluir o usuário <strong>' + U.esc(estado.excluindo.nome.replace(/\s*você$/, '')) +
      '</strong> (' + U.esc(estado.excluindo.email) + ')? Esta ação não pode ser desfeita.';
    U.ocultar($('msg-excluir'));
    $('btn-confirmar-excluir').disabled = false; $('btn-confirmar-excluir').textContent = 'Sim, excluir';
    modalExcluir.show();
  }
  $('modal-excluir').addEventListener('shown.bs.modal', function () { $('btn-nao-excluir').focus(); });

  $('btn-confirmar-excluir').addEventListener('click', async function () {
    var btn = this; var alvo = estado.excluindo;
    btn.disabled = true; btn.textContent = 'Excluindo...';
    try {
      await Api.delete('/usuarios/' + alvo.id);
      estado.excluido = true; /* a linha deixou de existir: o foco vai ao botão Novo usuário (hidden.bs.modal) */
      modalExcluir.hide();
      U.mostrar(msgPagina, 'sucesso', 'Usuário excluído com sucesso.');
      await carregar(estado.pagina);
    } catch (err) {
      btn.disabled = false; btn.textContent = 'Sim, excluir';
      /* ALTERACAO_BLOQUEADA, NAO_ENCONTRADO, SEM_PERMISSAO: nada foi removido (UC02 FE4) */
      U.mostrar($('msg-excluir'), 'erro', U.esc(U.mensagemDoErro(err)));
      $('msg-excluir').focus();
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  });
});
