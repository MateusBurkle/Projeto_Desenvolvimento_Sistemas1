/* Tela do Cliente Empresa/Cliente ONG: app/usuarios/organizacao.html. UC03 (inclui UC26); RN02, RN04, RN09, RNF04, RNF05.
   Rotas do contrato modulo-1: GET/POST /organizacao/usuarios (via Api). O corpo leva só nome, e-mail e senha:
   perfil e organização são herdados no back-end (UC03 passo 5). */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi;
  var TAMANHO = 10;
  var $ = function (id) { return document.getElementById(id); };
  var msgPagina = $('mensagem');
  var f = { nome: $('f-nome'), email: $('f-email'), senha: $('f-senha') };
  var form = $('form-usuario');
  var pagina = 1;

  Layout.iniciar({ chave: 'usuarios_organizacao' }).then(function (me) {
    if (!$('area-org')) { return; } /* sem permissão: o layout já mostrou a mensagem */
    $('perfil-herdado').textContent = me.perfil;
    carregar(1);
  });

  function linha(u) {
    return '<tr><td data-rotulo="Nome"><strong>' + U.esc(u.nome) + '</strong></td>' +
      '<td data-rotulo="E-mail">' + U.esc(u.email) + '</td>' +
      '<td data-rotulo="Perfil">' + U.esc(u.perfil) + '</td>' +
      '<td data-rotulo="Organização">' + U.esc(u.nome_organizacao || '') + '</td></tr>';
  }

  /* UC03 FA1: só as contas da própria organização (o filtro é feito pela API) */
  async function carregar(p) {
    $('estado-lista').hidden = false; $('estado-lista').textContent = 'Carregando...';
    try {
      var r = await Api.get('/organizacao/usuarios?page=' + p + '&size=' + TAMANHO);
      if (r.items.length === 0 && r.total > 0 && p > 1) { return carregar(p - 1); }
      pagina = r.page;
      $('corpo-tabela').innerHTML = r.items.map(linha).join('');
      $('tabela').hidden = r.items.length === 0;
      $('paginacao').hidden = r.total === 0;
      if (r.items.length === 0) { $('estado-lista').textContent = 'Nenhum usuário encontrado.'; } else { $('estado-lista').hidden = true; }
      $('texto-pagina').textContent = U.textoPagina(r);
      $('btn-anterior').disabled = r.page <= 1;
      $('btn-proxima').disabled = r.page * r.size >= r.total;
    } catch (err) {
      $('tabela').hidden = true; $('paginacao').hidden = true;
      $('estado-lista').textContent = 'Não foi possível carregar a lista.';
      U.mostrar(msgPagina, 'erro', U.esc(U.mensagemDoErro(err)));
    }
  }
  $('btn-anterior').addEventListener('click', function () { carregar(pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(pagina + 1); });

  function abrirForm() {
    form.reset(); U.limparErros(form); U.ocultar($('msg-form')); U.ocultar(msgPagina);
    $('secao-form').hidden = false;
    $('btn-adicionar').setAttribute('aria-expanded', 'true');
    f.nome.focus();
  }
  function fecharForm() {
    $('secao-form').hidden = true;
    $('btn-adicionar').setAttribute('aria-expanded', 'false');
    $('btn-adicionar').focus();
  }
  $('btn-adicionar').addEventListener('click', abrirForm);
  $('btn-cancelar').addEventListener('click', fecharForm);

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    U.limparErros(form); U.ocultar($('msg-form'));
    var erros = U.validar({ nome: f.nome.value, email: f.email.value, senha: f.senha.value }, { senhaObrigatoria: true });
    var chaves = Object.keys(erros);
    if (chaves.length) { /* UC03 FE1 (no cliente, RNF04) */
      chaves.forEach(function (k) { U.erroCampo(f[k], erros[k]); });
      U.mostrar($('msg-form'), 'erro', 'Corrija os campos indicados e tente novamente.');
      form.querySelector('.is-invalid').focus();
      return;
    }
    var btn = $('btn-salvar'); btn.disabled = true; btn.textContent = 'Salvando...';
    try {
      var novo = await Api.post('/organizacao/usuarios', { nome: f.nome.value.trim(), email: f.email.value.trim().toLowerCase(), senha: f.senha.value });
      $('secao-form').hidden = true;
      $('btn-adicionar').setAttribute('aria-expanded', 'false');
      U.mostrar(msgPagina, 'sucesso', 'Usuário <strong>' + U.esc(novo.nome) + '</strong> (' + U.esc(novo.email) + ') adicionado à sua organização com o perfil ' + U.esc(novo.perfil) + '.');
      await carregar(1);
      msgPagina.focus();
    } catch (err) {
      /* DADOS_INVALIDOS, EMAIL_DUPLICADO (FE1); OPERACAO_NAO_PERMITIDA (FE2); SEM_PERMISSAO */
      var marcou = U.aplicarCamposDaApi(err, f);
      U.mostrar($('msg-form'), 'erro', U.esc(U.mensagemDoErro(err)));
      var inv = form.querySelector('.is-invalid');
      if (marcou && inv) { inv.focus(); } else { $('msg-form').focus(); }
    } finally {
      btn.disabled = false; btn.textContent = 'Salvar';
    }
  });
});
