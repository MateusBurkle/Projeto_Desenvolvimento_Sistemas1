/* Funções comuns às telas do Módulo 2 (organizações e parceiros). UC01, UC25 (formato do CNPJ), UC06;
   RF06, RF09, RF10; RN06, RN09, RN10; RNF04, RNF06. Não faz chamadas à API (só js/api.js).
   Reaproveita UsuariosUi (js/usuarios-comum.js) para mensagens, erros de campo e escape de HTML.
   Expõe o objeto global OrgUi. */
(function (global) {
  'use strict';
  var U = global.UsuariosUi;
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  /* Mensagens em português por código do contrato (usadas se a API não enviar "mensagem"). */
  var MSG = {
    DADOS_INVALIDOS: 'Há dados inválidos. Corrija os campos indicados.',
    CNPJ_DUPLICADO: 'Este CNPJ já está cadastrado em outra organização.',
    TIPO_EM_USO: 'O tipo não pode ser alterado enquanto a organização tiver usuários vinculados ou vínculo de parceria como Empresa Doadora.',
    OPERACAO_NAO_PERMITIDA: 'Operação não permitida. O Funcionário só altera telefone, e-mail e endereço de Cliente Empresa e Cliente ONG.',
    SEM_PERMISSAO: 'Você não tem permissão para realizar esta ação.',
    NAO_ENCONTRADO: 'Registro não encontrado. Ele pode ter sido removido; atualize a lista.',
    ORGANIZACAO_EM_USO: 'Esta organização tem histórico e não pode ser excluída; você pode desativá-la.',
    ALTERACAO_BLOQUEADA: 'Não é possível excluir: a exclusão removeria o único Administrador.',
    ORGANIZACAO_COM_USUARIOS: 'Esta organização tem usuários vinculados. Confirme a exclusão deles para excluí-la.',
    PARCERIA_DUPLICADA: 'Esta organização já possui um vínculo de parceria.',
    ATUACAO_INCOMPATIVEL: 'A atuação Empresa Doadora exige uma organização do tipo Empresa Doadora.',
    ORGANIZACAO_INVALIDA: 'A organização está inativa. Reative a organização antes de registrar ou reativar o vínculo.'
  };

  /* Mensagem do erro: prefere a da API (já em português); senão a do código. */
  function msgErro(err) {
    return (err && err.mensagem) || MSG[err && err.codigo] || 'Ocorreu um erro inesperado. Tente novamente.';
  }

  function digitos(t) { return String(t == null ? '' : t).replace(/\D/g, ''); }

  /* 00.000.000/0000-00 (UC25: exibição); se não tiver 14 dígitos, mostra como veio. */
  function formatarCnpj(c) {
    var d = digitos(c);
    if (d.length !== 14) { return String(c == null ? '' : c); }
    return d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
  }
  function formatarTelefone(t) {
    var d = digitos(t);
    if (d.length === 11) { return d.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3'); }
    if (d.length === 10) { return d.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3'); }
    return String(t == null ? '' : t);
  }
  /* Máscara opcional de digitação do CNPJ (aplicada no evento input). */
  function mascararCnpj(v) {
    var d = digitos(v).slice(0, 14), s = d;
    if (d.length > 12) { s = d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{0,2}).*/, '$1.$2.$3/$4-$5'); }
    else if (d.length > 8) { s = d.replace(/^(\d{2})(\d{3})(\d{3})(\d{0,4}).*/, '$1.$2.$3/$4'); }
    else if (d.length > 5) { s = d.replace(/^(\d{2})(\d{3})(\d{0,3}).*/, '$1.$2.$3'); }
    else if (d.length > 2) { s = d.replace(/^(\d{2})(\d{0,3}).*/, '$1.$2'); }
    return s;
  }
  function mascararTelefone(v) {
    var d = digitos(v).slice(0, 11);
    if (d.length > 10) { return d.replace(/^(\d{2})(\d{5})(\d{0,4}).*/, '($1) $2-$3'); }
    if (d.length > 6) { return d.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3'); }
    if (d.length > 2) { return d.replace(/^(\d{2})(\d{0,5}).*/, '($1) $2'); }
    return d.length ? '(' + d : '';
  }

  /* Validação no cliente (RNF04; UC01 FE2, UC25 passo 2). v: { nome_razao_social, cnpj, tipo, telefone, email, endereco }.
     opcoes.soContato: valida só telefone, e-mail e endereço (Funcionário, UC01 FA3). Devolve { campo: mensagem }. */
  function validar(v, opcoes) {
    opcoes = opcoes || {};
    var e = {};
    if (!opcoes.soContato) {
      var nome = (v.nome_razao_social || '').trim();
      if (!nome) { e.nome_razao_social = 'Informe o nome ou a razão social.'; }
      else if (nome.length > 150) { e.nome_razao_social = 'O nome ou a razão social deve ter no máximo 150 caracteres.'; }
      var c = (v.cnpj || '').trim();
      if (!c) { e.cnpj = 'Informe o CNPJ.'; }
      else if (/[^\d.\/\-\s]/.test(c) || digitos(c).length !== 14) { e.cnpj = 'O CNPJ deve ter 14 dígitos, com ou sem máscara.'; }
      if (!v.tipo) { e.tipo = 'Selecione o tipo da organização.'; }
    }
    var t = (v.telefone || '').trim();
    if (!t) { e.telefone = 'Informe o telefone.'; }
    else if (/[^\d()\-\s+.]/.test(t) || [10, 11].indexOf(digitos(t).length) === -1) { e.telefone = 'O telefone deve ter 10 ou 11 dígitos, com DDD.'; }
    var em = (v.email || '').trim();
    if (!em) { e.email = 'Informe o e-mail.'; }
    else if (em.length > 254) { e.email = 'O e-mail deve ter no máximo 254 caracteres.'; }
    else if (!EMAIL_RE.test(em)) { e.email = 'Informe um e-mail válido, por exemplo contato@empresa.com.br.'; }
    var en = (v.endereco || '').trim();
    if (!en) { e.endereco = 'Informe o endereço.'; }
    else if (en.length > 255) { e.endereco = 'O endereço deve ter no máximo 255 caracteres.'; }
    return e;
  }

  /* Selo de situação: texto + ícone (nunca só cor, RNF06). */
  function seloSituacao(s) {
    var ativa = s === 'Ativa';
    return '<span class="selo-situacao ' + (ativa ? 'selo-ativa' : 'selo-inativa') + '">' +
      (ativa ? '✔︎' : '–') + ' ' + U.esc(s) + '</span>';
  }

  function textoPagina(p, singular, plural) {
    var total = Math.max(1, Math.ceil((p.total || 0) / (p.size || 1)));
    return 'Página ' + p.page + ' de ' + total + ' (' + p.total + ' ' + (p.total === 1 ? singular : plural) + ')';
  }

  global.OrgUi = {
    MSG: MSG, msgErro: msgErro, digitos: digitos, formatarCnpj: formatarCnpj, formatarTelefone: formatarTelefone,
    mascararCnpj: mascararCnpj, mascararTelefone: mascararTelefone, validar: validar,
    seloSituacao: seloSituacao, textoPagina: textoPagina
  };
})(window);
