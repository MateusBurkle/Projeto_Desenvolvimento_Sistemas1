/* Tela Meu perfil: app/perfil/index.html. UC02 (conta; exclusão FA3, DP-64), UC03, UC06/UC01 (organização);
   RN02, RN04, RN05, RN09, RNF01, RNF04, RNF05. DP-93 a DP-99.
   Rotas do contrato: PATCH /usuarios/me, PUT /usuarios/me/senha (modulo-1), GET/PATCH /organizacao (modulo-2).
   Todo texto de usuário entra por .value/.textContent (nunca HTML montado com dados). */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, O = OrgUi;
  var $ = function (id) { return document.getElementById(id); };
  var msg = $('mensagem');
  var c = { nome: $('c-nome'), email: $('c-email') };
  var senhaNova = $('s-nova');
  var o = { nome_razao_social: $('o-nome'), telefone: $('o-telefone'), email: $('o-email'), endereco: $('o-endereco') };
  var org = null; /* dados carregados (CNPJ e tipo entram na validação compartilhada) */

  /* Mensagem no alto da tela (texto puro). */
  function aviso(tipo, texto) {
    msg.className = 'alert ' + (tipo === 'erro' ? 'alert-danger' : 'alert-success');
    msg.setAttribute('role', tipo === 'erro' ? 'alert' : 'status');
    msg.setAttribute('tabindex', '-1');
    msg.textContent = texto;
    msg.classList.remove('d-none');
    msg.focus();
  }
  function limparAviso() { msg.classList.add('d-none'); msg.textContent = ''; }

  Layout.iniciar({ chave: 'meu_perfil' }).then(function (me) {
    if (!$('area-perfil') || (me.funcionalidades || []).indexOf('meu_perfil') === -1) { return; }
    c.nome.value = me.nome; c.email.value = me.email;
    $('c-perfil').value = me.perfil; $('c-org').value = me.nome_organizacao || '';
    /* DP-101, DP-102: Administrador e Funcionário não têm organização (GET /organizacao daria 403): só conta e senha. */
    if (me.perfil === 'Administrador' || me.perfil === 'Funcionário') {
      ['grupo-org', 'secao-org', 'secao-excluir'].forEach(function (id) { if ($(id)) { $(id).hidden = true; } });
      $('estado').hidden = true; $('conteudo-perfil').hidden = false;
      $('secao-conta').className = 'col-12 col-lg-6';
      return;
    }
    carregarOrg();
  });

  /* GET /organizacao: falha mostra erro; a conta continua editável. */
  async function carregarOrg() {
    try {
      org = await Api.get('/organizacao');
      o.nome_razao_social.value = org.nome_razao_social; $('c-org').value = org.nome_razao_social; o.telefone.value = O.formatarTelefone(org.telefone);
      o.email.value = org.email; o.endereco.value = org.endereco;
      $('o-cnpj').value = O.formatarCnpj(org.cnpj); $('o-tipo').value = org.tipo; $('o-situacao').value = org.situacao;
    } catch (err) {
      $('form-org').hidden = true;
      aviso('erro', 'Não foi possível carregar os dados da organização. ' + O.msgErro(err));
    }
    $('estado').hidden = true;
    $('conteudo-perfil').hidden = false;
  }

  o.telefone.addEventListener('input', function () { o.telefone.value = O.mascararTelefone(o.telefone.value); });

  /* Erro da API: campo indicado (400/409) ou mensagem no alto. mapa: campo da API -> input. */
  function tratarErro(err, mapa) {
    if (err.status === 401) { return; } /* Api já redirecionou ao login */
    if (U.aplicarCamposDaApi(err, mapa)) { return; }
    aviso('erro', O.msgErro(err));
  }
  async function enviar(btn, fn) {
    btn.disabled = true;
    try { await fn(); } finally { btn.disabled = false; }
  }

  /* DP-95: nome e e-mail da conta. */
  $('form-conta').addEventListener('submit', async function (e) {
    e.preventDefault(); limparAviso(); U.limparErros(this);
    var v = { nome: c.nome.value, email: c.email.value, senha: '' };
    var er = U.validar(v, {});
    if (er.nome || er.email) {
      if (er.nome) { U.erroCampo(c.nome, er.nome); }
      if (er.email) { U.erroCampo(c.email, er.email); }
      (er.nome ? c.nome : c.email).focus(); return;
    }
    await enviar($('btn-salvar-conta'), async function () {
      try {
        var r = await Api.patch('/usuarios/me', { nome: v.nome.trim(), email: v.email.trim() });
        c.nome.value = r.nome; c.email.value = r.email;
        $('usuario-nome').textContent = r.nome;
        aviso('sucesso', 'Dados da conta atualizados.');
      } catch (err) { tratarErro(err, { nome: c.nome, email: c.email }); }
    });
  });

  /* DP-96, DP-97: troca de senha só com a senha nova. */
  $('form-senha').addEventListener('submit', async function (e) {
    e.preventDefault(); limparAviso(); U.limparErros(this);
    var t = senhaNova.value, texto = '';
    if (!t) { texto = 'Informe a nova senha (de 8 a 128 caracteres).'; }
    else if (t.length < 8 || t.length > 128) { texto = 'A senha deve ter de 8 a 128 caracteres.'; } /* P-04: sem corte silencioso */
    if (texto) { U.erroCampo(senhaNova, texto); senhaNova.focus(); return; }
    await enviar($('btn-alterar-senha'), async function () {
      try {
        await Api.put('/usuarios/me/senha', { senha_nova: t });
        senhaNova.value = '';
        aviso('sucesso', 'Senha alterada.');
      } catch (err) {
        if (err.codigo === 'SENHA_IGUAL_ATUAL') { U.erroCampo(senhaNova, 'A nova senha não pode ser igual à atual.'); senhaNova.focus(); }
        else { tratarErro(err, { senha_nova: senhaNova }); }
      }
    });
  });

  /* DP-93, DP-94: nome, telefone, e-mail e endereço da própria organização. */
  $('form-org').addEventListener('submit', async function (e) {
    e.preventDefault(); limparAviso(); U.limparErros(this);
    var v = { nome_razao_social: o.nome_razao_social.value, telefone: o.telefone.value, email: o.email.value, endereco: o.endereco.value,
      cnpj: org ? org.cnpj : '', tipo: org ? org.tipo : '' }; /* CNPJ e tipo só leitura: entram para reusar a validação */
    var er = O.validar(v), primeiro = null;
    Object.keys(o).forEach(function (k) {
      if (er[k]) { U.erroCampo(o[k], er[k]); primeiro = primeiro || o[k]; }
    });
    if (primeiro) { primeiro.focus(); return; }
    await enviar($('btn-salvar-org'), async function () {
      try {
        org = await Api.patch('/organizacao', {
          nome_razao_social: v.nome_razao_social.trim(), telefone: v.telefone.trim(),
          email: v.email.trim(), endereco: v.endereco.trim()
        });
        $('c-org').value = org.nome_razao_social;
        aviso('sucesso', 'Dados da organização atualizados.');
      } catch (err) { tratarErro(err, o); }
    });
  });

  /* DP-64, DP-99: o modal de exclusão (senha atual) é o do layout. */
  $('btn-excluir-conta-perfil').addEventListener('click', function () {
    Layout.abrirExclusaoConta(this);
  });
});
