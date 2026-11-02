/* js/publico.js - apoio das páginas PÚBLICAS (index, quemsomos, hardware/marketplace, compra/detalhe).
   Marketplace: DP-68 (visitante vê, só logado age; volta ao produto após o login), DP-74 (valor só Cliente Empresa), DP-78.
   UC04 (acessar), UC12 (listar produtos), UC13 (comprar), RN01, RNF05, RNF01.
   - Cabeçalho: "Entrar" (visitante) ou nome do usuário + "Minha área" + "Sair" (logado), no elemento #area-usuario.
   - retornoSeguro(): o retorno pós-login só aceita CAMINHO RELATIVO de página .html (barreira contra open redirect:
     rejeita http://, //, javascript:, barra invertida, ':' e '..'). A segurança real das ações é do back-end. */
(function (global) {
  'use strict';

  /* Caminho relativo permitido: segmentos [A-Za-z0-9_-] separados por "/", terminando em .html, query opcional.
     Sem ':' (bloqueia http:, javascript:), sem '\', sem '//' no início, sem '..'. */
  var RETORNO_OK = /^[A-Za-z0-9_\-]+(\/[A-Za-z0-9_\-]+)*\.html(\?[A-Za-z0-9_=&%.\-]*)?$/;

  function retornoSeguro(valor) {
    if (typeof valor !== 'string') { return null; }
    var v = valor;
    if (!v || v.length > 300 || /[\s\x00-\x1f]/.test(v)) { return null; } /* espaços e caracteres de controle (ex.: quebra de linha) não são aceitos */
    if (v.indexOf('\\') !== -1 || v.indexOf(':') !== -1 || v.indexOf('//') !== -1 || v.indexOf('..') !== -1) { return null; }
    if (v.charAt(0) === '/') { return null; } /* só relativo ao front-end; "/x" e "//x" ficam de fora */
    if (!RETORNO_OK.test(v)) { return null; }
    return v;
  }

  function esc(t) {
    var d = document.createElement('div');
    d.textContent = t == null ? '' : String(t);
    return d.innerHTML;
  }

  /* R$ 1.500,00 */
  function formatarValor(v) {
    if (v == null || v === '') { return '—'; }
    return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  /* Página atual (relativa ao front-end, ex.: "compra.html?id=7") para voltar após o login. */
  function paginaAtual() {
    var p = global.location.pathname;
    return retornoSeguro(p.substring(p.lastIndexOf('/') + 1) + global.location.search);
  }
  function urlLogin(retorno) {
    var r = retornoSeguro(retorno === undefined ? paginaAtual() : retorno);
    return 'login.html' + (r ? '?retorno=' + encodeURIComponent(r) : '');
  }

  function perfil() {
    var u = Api.sessao.ativa() ? Api.sessao.usuario() : null;
    return u && u.perfil ? u.perfil : null;
  }

  /* Cabeçalho de sessão (todas as páginas públicas). Sair só descarta o token e recarrega a mesma página. */
  function cabecalho() {
    var el = document.getElementById('area-usuario');
    if (!el) { return; }
    var u = Api.sessao.ativa() ? Api.sessao.usuario() : null;
    if (!u) {
      el.innerHTML = '<a class="btn btn-success fw-semibold px-4" id="btn-entrar-topo" href="' + esc(urlLogin()) + '">Entrar</a>';
      return;
    }
    el.innerHTML =
      '<div class="d-flex flex-column flex-lg-row align-items-lg-center gap-2 gap-lg-3">' +
        '<span class="fw-semibold usuario-topo" title="' + esc(u.nome) + '">' + esc(u.nome) + '<span class="visually-hidden"> (' + esc(u.perfil) + ')</span></span>' +
        '<a class="btn btn-outline-leaf fw-semibold" href="app/inicio.html">Minha área</a>' +
        '<button type="button" class="btn btn-success fw-semibold" id="btn-sair-topo">Sair</button>' +
      '</div>';
    document.getElementById('btn-sair-topo').addEventListener('click', function () {
      Api.sessao.limpar();
      global.location.reload();
    });
  }

  /* DP-83: texto onde o valor não é visível, conforme o perfil (ONG: sem texto; logados não Empresa: sem convite ao login) */
  function textoSemValor() {
    var p = perfil();
    if (!p) { return 'Entre como Cliente Empresa para ver o valor e comprar'; }
    if (p === 'Cliente ONG') { return ''; }
    return 'Valor visível apenas para Cliente Empresa';
  }

  document.addEventListener('DOMContentLoaded', cabecalho);

  global.Publico = {
    retornoSeguro: retornoSeguro, urlLogin: urlLogin, paginaAtual: paginaAtual,
    cabecalho: cabecalho, perfil: perfil, esc: esc, formatarValor: formatarValor,
    textoSemValor: textoSemValor,
    TEXTO_SEM_VALOR: 'Entre como Cliente Empresa para ver o valor e comprar'
  };
})(window);
