/* Funções comuns às telas do Módulo 1 (usuários). UC02, UC03, UC26 (e-mail), UC27 (perfil); RNF04, RNF06.
   Não faz chamadas à API (isso é só em js/api.js). Expõe o objeto global UsuariosUi. */
(function (global) {
  'use strict';

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/; /* mesmo formato x@y.z do back-end (DP-09) */

  /* Mensagens em português por código do contrato (usadas quando a API não envia "mensagem"). */
  var MSG = {
    DADOS_INVALIDOS: 'Há dados inválidos. Corrija os campos indicados.',
    EMAIL_DUPLICADO: 'Este e-mail já está em uso. Informe outro e-mail.',
    ORGANIZACAO_INVALIDA: 'A organização informada não existe ou está inativa. Escolha outra.',
    VINCULO_INVALIDO: 'O perfil escolhido não corresponde à organização informada. Confira o perfil e a organização.',
    ALTERACAO_BLOQUEADA: 'Operação bloqueada: você não pode excluir a própria conta nem alterar o próprio perfil, e a última conta Administrador não pode ser excluída nem rebaixada.',
    OPERACAO_NAO_PERMITIDA: 'Você só pode cadastrar usuários da sua própria organização, com o mesmo perfil.',
    SEM_PERMISSAO: 'Você não tem permissão para realizar esta ação.',
    CONTA_INATIVA: 'Acesso negado. A conta ou a organização está inativa.',
    SENHA_IGUAL_ATUAL: 'A nova senha não pode ser igual à atual.', /* DP-97 */
    NAO_ENCONTRADO: 'Usuário não encontrado. Ele pode ter sido excluído; atualize a lista.'
  };

  function esc(t) {
    var d = document.createElement('div');
    d.textContent = t == null ? '' : String(t);
    return d.innerHTML;
  }

  function mensagemDoErro(err) {
    return (err && err.mensagem) || MSG[err && err.codigo] || 'Ocorreu um erro inesperado. Tente novamente.';
  }

  /* Mensagem no alto da tela/modal. tipo: 'erro' (.alert-danger, prefixo "Erro:" vem do CSS),
     'sucesso' (.alert-success, prefixo "Pronto:") ou 'aviso'. */
  function mostrar(el, tipo, html) {
    el.className = 'alert ' + (tipo === 'erro' ? 'alert-danger' : tipo === 'aviso' ? 'alert-warning' : 'alert-success');
    el.innerHTML = html;
    el.setAttribute('role', tipo === 'erro' ? 'alert' : 'status');
    el.setAttribute('tabindex', '-1');
    el.classList.remove('d-none');
  }
  function ocultar(el) { el.classList.add('d-none'); el.innerHTML = ''; }

  /* Erro de campo (RNF04): borda grossa + texto com ícone (via CSS) e aria-invalid. */
  function erroCampo(input, texto) {
    var alvo = document.getElementById(input.id + '-erro');
    input.classList.add('is-invalid');
    input.setAttribute('aria-invalid', 'true');
    if (alvo) { alvo.textContent = texto; }
  }
  function limparErros(form) {
    Array.prototype.forEach.call(form.querySelectorAll('.is-invalid'), function (i) {
      i.classList.remove('is-invalid'); i.removeAttribute('aria-invalid');
    });
    Array.prototype.forEach.call(form.querySelectorAll('.invalid-feedback'), function (d) { d.textContent = ''; });
  }

  /* Mostra os erros por campo vindos de DADOS_INVALIDOS/EMAIL_DUPLICADO/etc.
     mapa: { nomeDoCampoNaApi: inputElement }. Devolve true se algum campo foi marcado. */
  function aplicarCamposDaApi(err, mapa) {
    var marcou = false;
    Object.keys(err.campos || {}).forEach(function (k) {
      var input = mapa[k];
      if (!input) { return; }
      var txt = String(err.campos[k]);
      if (err.codigo === 'EMAIL_DUPLICADO' && k === 'email') { txt = 'Este e-mail já está em uso.'; }
      else if (err.codigo === 'CNPJ_DUPLICADO' && k === 'cnpj') { txt = 'Este CNPJ já está cadastrado.'; }
      else if (err.codigo === 'TIPO_EM_USO' && k === 'tipo') { txt = 'O tipo não pode ser alterado: há usuários ou parceria vinculados.'; }
      else if (/^(duplicad[oa]|invalid[oa]|obrigat[oó]ri[oa]|em uso)\.?$/i.test(txt.trim())) {
        txt = 'Valor ' + (/^duplicad/i.test(txt) ? 'já cadastrado' : 'inválido') + ' neste campo. Revise e tente novamente.';
      }
      erroCampo(input, txt.charAt(0).toUpperCase() + txt.slice(1) + (/[.!?]$/.test(txt) ? '' : '.'));
      marcou = true;
    });
    if (!marcou && err.codigo === 'EMAIL_DUPLICADO' && mapa.email) {
      erroCampo(mapa.email, 'Este e-mail já está em uso.'); marcou = true;
    }
    return marcou;
  }

  /* Validação no cliente (RNF04, UC26 formato). Devolve { campo: mensagem }. */
  function validar(v, opcoes) {
    var e = {};
    var nome = (v.nome || '').trim();
    if (!nome) { e.nome = 'Informe o nome.'; }
    else if (nome.length > 120) { e.nome = 'O nome deve ter no máximo 120 caracteres.'; }
    var email = (v.email || '').trim();
    if (!email) { e.email = 'Informe o e-mail.'; }
    else if (email.length > 254) { e.email = 'O e-mail deve ter no máximo 254 caracteres.'; }
    else if (!EMAIL_RE.test(email)) { e.email = 'Informe um e-mail válido, por exemplo nome@empresa.com.br.'; }
    var senha = v.senha || '';
    if (!senha) {
      if (opcoes.senhaObrigatoria) { e.senha = 'Informe a senha (de 8 a 128 caracteres).'; }
    } else if (senha.length < 8) { e.senha = 'A senha deve ter no mínimo 8 caracteres.'; }
    else if (senha.length > 128) { e.senha = 'A senha deve ter no máximo 128 caracteres.'; }
    if (opcoes.perfil) {
      if (!v.perfil) { e.perfil = 'Selecione um perfil.'; }
      else if (opcoes.exigeOrg && !v.id_organizacao) { e.org = 'Selecione a organização vinculada a este perfil.'; }
    }
    return e;
  }

  /* UC02 passo 6: confirma as permissões atribuídas. Rótulos vêm do menu do layout, quando existirem. */
  function rotuloFuncionalidade(chave) {
    var m = (global.Layout && Layout.MENU || []).filter(function (x) { return x.chave === chave; })[0];
    return m ? m.rotulo : String(chave).replace(/_/g, ' ');
  }
  function htmlFuncionalidades(u) {
    var f = u.funcionalidades || [];
    return '<p class="mb-1"><strong>Funcionalidades atribuídas ao perfil ' + esc(u.perfil) + ':</strong></p>' +
      (f.length ? '<ul class="mb-0">' + f.map(function (c) { return '<li>' + esc(rotuloFuncionalidade(c)) + '</li>'; }).join('') + '</ul>'
                : '<p class="mb-0">Nenhuma funcionalidade listada.</p>');
  }

  /* Paginação: botões Anterior/Próxima + "Página x de y". */
  function textoPagina(p) {
    var total = Math.max(1, Math.ceil((p.total || 0) / (p.size || 1)));
    return 'Página ' + p.page + ' de ' + total + ' (' + p.total + (p.total === 1 ? ' usuário' : ' usuários') + ')';
  }

  global.UsuariosUi = {
    MSG: MSG, esc: esc, mensagemDoErro: mensagemDoErro, mostrar: mostrar, ocultar: ocultar,
    erroCampo: erroCampo, limparErros: limparErros, aplicarCamposDaApi: aplicarCamposDaApi,
    validar: validar, htmlFuncionalidades: htmlFuncionalidades, textoPagina: textoPagina
  };
})(window);
