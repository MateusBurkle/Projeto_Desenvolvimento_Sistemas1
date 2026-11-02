/* Mostrar/ocultar senha (Pedido 2, DP-88; UC01 login, UC02/UC03 usuarios, UC02 FA3 exclusao da propria conta, DP-64).
   Componente unico: envolve todo <input type="password"> com um botao de olho dentro do campo, a direita.
   - Comeca oculto; nao altera autocomplete nem guarda a senha.
   - Volta a ocultar no submit do formulario e no pagehide.
   - Campos inseridos depois (modais) sao tratados por MutationObserver; tambem ha SenhaOlho.aplicar(raiz). */
(function (global) {
  'use strict';

  var OLHO_ABERTO = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>';
  var OLHO_RISCADO = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M17.94 17.94A10.9 10.9 0 0 1 12 19C5 19 1 12 1 12a18.5 18.5 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

  function definir(input, botao, visivel) {
    input.type = visivel ? 'text' : 'password';
    botao.setAttribute('aria-pressed', visivel ? 'true' : 'false');
    botao.setAttribute('aria-label', visivel ? 'Ocultar senha' : 'Mostrar senha');
    botao.innerHTML = visivel ? OLHO_ABERTO : OLHO_RISCADO; /* aberto = senha visivel; riscado = oculta */
  }

  function envolver(input) {
    if (input.getAttribute('data-senha-olho') === '1') { return; }
    input.setAttribute('data-senha-olho', '1');
    var doc = input.ownerDocument;
    var wrap = doc.createElement('div');
    wrap.className = 'senha-olho';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    var botao = doc.createElement('button');
    botao.type = 'button';
    botao.className = 'senha-olho-botao';
    wrap.appendChild(botao);
    definir(input, botao, false);
    botao.addEventListener('click', function () { definir(input, botao, input.type === 'password'); });
    var form = input.form;
    if (form) { form.addEventListener('submit', function () { definir(input, botao, false); }); }
  }

  function aplicar(raiz) {
    var r = raiz || document;
    var lista = r.querySelectorAll ? r.querySelectorAll('input[type="password"]') : [];
    for (var i = 0; i < lista.length; i++) { envolver(lista[i]); }
    if (r.matches && r.matches('input[type="password"]')) { envolver(r); }
  }

  function ocultarTodos() {
    var bts = document.querySelectorAll('.senha-olho-botao');
    for (var i = 0; i < bts.length; i++) {
      var inp = bts[i].parentNode.querySelector('input');
      if (inp) { definir(inp, bts[i], false); }
    }
  }

  function iniciar() {
    aplicar(document);
    if (global.MutationObserver) {
      new MutationObserver(function (muts) {
        for (var i = 0; i < muts.length; i++) {
          for (var j = 0; j < muts[i].addedNodes.length; j++) {
            var n = muts[i].addedNodes[j];
            if (n.nodeType === 1) { aplicar(n); }
          }
        }
      }).observe(document.body, { childList: true, subtree: true });
    }
  }

  global.addEventListener('pagehide', ocultarTodos);
  global.SenhaOlho = { aplicar: aplicar, ocultarTodos: ocultarTodos };
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', iniciar); }
  else { iniciar(); }
})(window);
