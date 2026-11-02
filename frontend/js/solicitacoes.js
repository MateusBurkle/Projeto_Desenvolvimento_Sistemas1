/* Tela app/solicitacoes/index.html (Empresa Doadora). UC09 (RF05, RF10, RF21; RN05, RN10, RN21; RNF04) e
   UC20 (RF05, RF21; RN05, RN21; RNF05). Decisões DP-40 e DP-43.
   Rotas do contrato modulo-4: GET/POST /solicitacoes e GET /solicitacoes/{id}. Tudo via Api (js/api.js).
   Mostrar/esconder é conveniência; a segurança real (só a própria organização) é do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, E = EquipUi, S = SolUi;
  var TAMANHO = 10, MAX_ITENS = 50;
  var $ = function (id) { return document.getElementById(id); };
  var VISTAS = ['vista-lista', 'vista-nova', 'vista-detalhe'];
  var msgPagina = $('mensagem');
  var estado = { pagina: 1, filtros: {}, seq: 0 };

  Layout.iniciar({ chave: 'minhas_solicitacoes' }).then(function () {
    if (!$('area-sol')) { return; } /* sem permissão: o layout já mostrou a mensagem */
    S.SITUACOES.forEach(function (v) { var o = document.createElement('option'); o.value = v; o.textContent = v; $('filtro-situacao').appendChild(o); });
    var idUrl = S.idDaUrl();
    carregar(1);
    if (idUrl) { abrirDetalhe(idUrl, false); }
  });

  function vista(id, titulo) { S.mostrarVista(VISTAS, id, titulo); }
  function limparMensagem() { U.ocultar(msgPagina); }

  /* ---------- lista (UC20 passos 1-3) ---------- */
  function linhaHtml(s) {
    var aval = s.situacao === 'Aguardando avaliação'
      ? 'Ainda não avaliada'
      : s.unidades_avaliadas + ' de ' + s.total_unidades + (s.total_unidades === 1 ? ' unidade' : ' unidades');
    return '<tr>' +
      '<td data-rotulo="Solicitação"><strong>Nº ' + s.id_solicitacao + '</strong></td>' +
      '<td data-rotulo="Data">' + E.formatarData(s.data_solicitacao) + '</td>' +
      '<td data-rotulo="Situação">' + S.seloSolicitacao(s.situacao) + '</td>' +
      '<td data-rotulo="Itens">' + s.total_itens + (s.total_itens === 1 ? ' item' : ' itens') + ' (' + s.total_unidades + (s.total_unidades === 1 ? ' unidade' : ' unidades') + ')</td>' +
      '<td data-rotulo="Avaliação">' + aval + '</td>' +
      '<td class="acoes" data-rotulo="Ações"><div class="grupo-acoes"><button type="button" class="btn btn-outline-leaf" data-acao="ver" data-id="' + s.id_solicitacao +
        '" aria-label="Consultar solicitação número ' + s.id_solicitacao + '">Consultar</button></div></td></tr>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO], fl = estado.filtros;
    if (fl.situacao) { q.push('situacao=' + encodeURIComponent(fl.situacao)); }
    if (fl.de) { q.push('data_de=' + fl.de); }
    if (fl.ate) { q.push('data_ate=' + fl.ate); }
    $('estado-lista').hidden = false; $('estado-lista').textContent = 'Carregando...';
    try {
      var r = await Api.get('/solicitacoes?' + q.join('&'));
      estado.pagina = r.page;
      $('tabela').hidden = r.items.length === 0;
      $('paginacao').hidden = r.total <= r.size;
      $('corpo-tabela').innerHTML = r.items.map(linhaHtml).join('');
      var vazio = $('vazio-lista');
      if (!r.items.length) {
        var filtrando = !!(fl.situacao || fl.de || fl.ate);
        $('estado-lista').hidden = true; vazio.hidden = false;
        vazio.innerHTML = filtrando
          ? '<p class="titulo-vazio">Nenhuma solicitação encontrada</p><p class="mb-0">Nenhuma solicitação atende aos filtros. Ajuste ou limpe os filtros.</p>'
          : '<p class="titulo-vazio">Você ainda não enviou solicitações</p><p>Use <strong>Nova solicitação</strong> para informar os equipamentos que deseja enviar para avaliação.</p>';
      } else {
        vazio.hidden = true;
        $('estado-lista').hidden = false;
        $('estado-lista').textContent = r.total + (r.total === 1 ? ' solicitação encontrada.' : ' solicitações encontradas.');
      }
      $('texto-pagina').textContent = E.textoPagina(r, 'solicitação', 'solicitações');
      $('btn-anterior').disabled = r.page <= 1;
      $('btn-proxima').disabled = r.page * r.size >= r.total;
    } catch (err) {
      $('tabela').hidden = true; $('paginacao').hidden = true; $('vazio-lista').hidden = true;
      $('estado-lista').hidden = false; $('estado-lista').textContent = 'Não foi possível carregar as solicitações.';
      U.mostrar(msgPagina, 'erro', U.esc(S.msgErro(err)));
    }
  }

  $('form-filtros').addEventListener('submit', function (ev) {
    ev.preventDefault();
    U.limparErros($('form-filtros')); limparMensagem();
    var de = $('filtro-de').value, ate = $('filtro-ate').value;
    var erro = S.validarPeriodo(de, ate);
    if (erro) { U.erroCampo(de > ate || !E.dataValida(de) && de ? $('filtro-de') : $('filtro-ate'), erro); return; }
    estado.filtros = { situacao: $('filtro-situacao').value, de: de, ate: ate };
    carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () {
    $('form-filtros').reset(); U.limparErros($('form-filtros')); estado.filtros = {}; limparMensagem(); carregar(1);
  });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });
  $('corpo-tabela').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-acao="ver"]');
    if (b) { limparMensagem(); abrirDetalhe(Number(b.dataset.id), true); }
  });

  /* ---------- detalhe somente leitura (UC09 FA1; UC20 passos 3-4, FA1, FE1) ---------- */
  function mostrarDetalhe(sol) {
    $('titulo-detalhe').textContent = 'Solicitação nº ' + sol.id_solicitacao;
    $('cab-detalhe').innerHTML = S.dadosSolicitacao(sol, false);
    var aviso = '';
    if (sol.situacao === 'Aguardando avaliação') { /* UC20 FA1: situação pendente, sem inventar avaliação ou destinação */
      aviso = '<div class="aviso-info" role="status"><span aria-hidden="true">○ </span><strong>Aguardando avaliação pela LEAF TI.</strong> Ainda não há condição avaliada nem destinação registrada para os itens desta solicitação.</div>';
    } else {
      aviso = S.avisoPendencias(sol);
    }
    $('aviso-detalhe').innerHTML = aviso;
    /* Empresa Doadora não vê valor (a API também omite) e não tem ações: somente leitura */
    $('itens-detalhe').innerHTML = (sol.itens || []).map(function (it, i) { return S.cartaoItem(it, i, {}); }).join('');
  }

  async function abrirDetalhe(id, focar) {
    try {
      var sol = await Api.get('/solicitacoes/' + id);
      mostrarDetalhe(sol);
      vista('vista-detalhe', focar === false ? null : 'titulo-detalhe');
    } catch (err) {
      /* FE1 (UC20): solicitação de outra empresa -> 404, sem revelar existência */
      vista('vista-lista', 'titulo-lista-sol');
      U.mostrar(msgPagina, 'erro', err.status === 404
        ? 'Solicitação não encontrada. Ela não existe ou não pertence à sua organização.' : U.esc(S.msgErro(err)));
    }
  }
  $('btn-voltar-detalhe').addEventListener('click', function () { vista('vista-lista', 'titulo-lista-sol'); carregar(estado.pagina); });

  /* ---------- nova solicitação (UC09 passos 1-5) ---------- */
  function linhaItemHtml(n) {
    return '<fieldset class="linha-item" data-linha>' +
      '<legend>Item <span class="num-item"></span></legend>' +
      '<div class="row g-3 align-items-start">' +
        '<div class="col-12 col-md-6 col-xl-4"><label class="form-label" for="it-tipo-' + n + '">Tipo <span aria-hidden="true">*</span></label>' +
          '<input type="text" class="form-control" id="it-tipo-' + n + '" data-campo="tipo" maxlength="100" autocomplete="off" required aria-describedby="it-tipo-' + n + '-erro" placeholder="Ex.: Notebook">' +
          '<div id="it-tipo-' + n + '-erro" class="invalid-feedback"></div></div>' +
        '<div class="col-12 col-md-6 col-xl-4"><label class="form-label" for="it-modelo-' + n + '">Modelo <span aria-hidden="true">*</span></label>' +
          '<input type="text" class="form-control" id="it-modelo-' + n + '" data-campo="modelo" maxlength="100" autocomplete="off" required aria-describedby="it-modelo-' + n + '-erro" placeholder="Ex.: Dell Latitude 5420">' +
          '<div id="it-modelo-' + n + '-erro" class="invalid-feedback"></div></div>' +
        '<div class="col-6 col-md-4 col-xl-2"><label class="form-label" for="it-qtd-' + n + '">Quantidade <span aria-hidden="true">*</span></label>' +
          '<input type="number" class="form-control" id="it-qtd-' + n + '" data-campo="quantidade" min="1" max="9999" step="1" inputmode="numeric" required aria-describedby="it-qtd-' + n + '-erro">' +
          '<div id="it-qtd-' + n + '-erro" class="invalid-feedback"></div></div>' +
        '<div class="col-6 col-md-4 col-xl-2 align-self-end"><button type="button" class="btn btn-outline-leaf fw-semibold w-100" data-acao="remover">Remover</button></div>' +
      '</div></fieldset>';
  }
  function linhas() { return Array.prototype.slice.call($('itens-form').querySelectorAll('[data-linha]')); }
  function atualizarLinhas() {
    var ls = linhas();
    ls.forEach(function (l, i) {
      l.querySelector('.num-item').textContent = i + 1;
      var rem = l.querySelector('[data-acao="remover"]');
      rem.disabled = ls.length === 1;
      rem.setAttribute('aria-label', 'Remover item ' + (i + 1));
    });
    $('btn-add-item').disabled = ls.length >= MAX_ITENS;
    $('msg-limite').hidden = ls.length < MAX_ITENS;
  }
  function adicionarLinha(focar) {
    $('itens-form').insertAdjacentHTML('beforeend', linhaItemHtml(++estado.seq));
    atualizarLinhas();
    if (focar) { var ls = linhas(); ls[ls.length - 1].querySelector('input').focus(); }
  }
  function abrirNova() {
    limparMensagem(); U.ocultar($('msg-nova'));
    $('itens-form').innerHTML = '';
    adicionarLinha(false);
    vista('vista-nova', 'titulo-nova');
  }
  $('btn-nova').addEventListener('click', abrirNova);
  $('btn-add-item').addEventListener('click', function () { adicionarLinha(true); });
  $('itens-form').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-acao="remover"]');
    if (!b || linhas().length === 1) { return; }
    var l = b.closest('[data-linha]'), ls = linhas(), i = ls.indexOf(l);
    l.remove(); atualizarLinhas();
    var resto = linhas(); (resto[Math.min(i, resto.length - 1)].querySelector('input')).focus();
  });
  function voltarLista() { vista('vista-lista', 'titulo-lista-sol'); }
  $('btn-voltar-nova').addEventListener('click', voltarLista);
  $('btn-cancelar-nova').addEventListener('click', voltarLista);

  /* Validação no cliente (UC09 FE1; RNF04). A API valida de novo. */
  function validarItens() {
    var erros = 0, primeiro = null, itens = [];
    linhas().forEach(function (l) {
      var tipo = l.querySelector('[data-campo="tipo"]'), modelo = l.querySelector('[data-campo="modelo"]'), qtd = l.querySelector('[data-campo="quantidade"]');
      function falha(campo, texto) { U.erroCampo(campo, texto); erros++; if (!primeiro) { primeiro = campo; } }
      var t = tipo.value.trim(), m = modelo.value.trim(), q = qtd.value.trim();
      if (!t) { falha(tipo, 'Informe o tipo do equipamento.'); } else if (t.length > 100) { falha(tipo, 'O tipo deve ter no máximo 100 caracteres.'); }
      if (!m) { falha(modelo, 'Informe o modelo do equipamento.'); } else if (m.length > 100) { falha(modelo, 'O modelo deve ter no máximo 100 caracteres.'); }
      if (!q) { falha(qtd, 'Informe a quantidade.'); }
      else if (!/^\d+$/.test(q) || Number(q) < 1 || Number(q) > 9999) { falha(qtd, 'A quantidade deve ser um número inteiro de 1 a 9999.'); }
      itens.push({ tipo: t, modelo: m, quantidade: /^\d+$/.test(q) ? Number(q) : null });
    });
    return { erros: erros, primeiro: primeiro, itens: itens };
  }
  /* Erros por campo da API: "itens.N.campo" (N-ésima linha) ou só a chave curta "campo"
     (esclarecimento 1 do contrato). Sem índice, marca a primeira linha cujo campo falha
     na checagem local; se nenhuma falhar, a primeira linha. */
  function aplicarCamposApi(err) {
    var ls = linhas(), marcou = false;
    Object.keys(err.campos || {}).forEach(function (k) {
      var m = /^(?:itens\.(\d+)\.)?(tipo|modelo|quantidade)$/.exec(k);
      if (!m) { return; }
      var alvo;
      if (m[1] !== undefined) { alvo = ls[Number(m[1])]; }
      else {
        alvo = ls.filter(function (l) {
          var v = l.querySelector('[data-campo="' + m[2] + '"]').value.trim();
          if (m[2] === 'quantidade') { return !/^\d+$/.test(v) || Number(v) < 1 || Number(v) > 9999; }
          return !v || v.length > 100;
        })[0] || ls[0];
      }
      if (!alvo) { return; }
      var campo = alvo.querySelector('[data-campo="' + m[2] + '"]');
      var t = String(err.campos[k]);
      U.erroCampo(campo, t.charAt(0).toUpperCase() + t.slice(1) + (/[.!?]$/.test(t) ? '' : '.'));
      marcou = true;
    });
    return marcou;
  }

  $('form-nova').addEventListener('submit', async function (ev) {
    ev.preventDefault();
    U.limparErros($('form-nova')); U.ocultar($('msg-nova'));
    var v = validarItens();
    if (v.erros) { /* FE1: não registra e pede correção */
      U.mostrar($('msg-nova'), 'erro', 'Corrija os campos indicados e envie novamente. A solicitação ainda não foi registrada.');
      $('msg-nova').focus(); return;
    }
    var btn = $('btn-enviar');
    btn.disabled = true; btn.textContent = 'Enviando...';
    try {
      var sol = await Api.post('/solicitacoes', { itens: v.itens });
      mostrarDetalhe(sol);
      vista('vista-detalhe', 'titulo-detalhe');
      U.mostrar(msgPagina, 'sucesso', 'Solicitação nº ' + sol.id_solicitacao + ' enviada. Ela está aguardando avaliação da LEAF TI.');
      msgPagina.focus();
      estado.pagina = 1;
    } catch (err) {
      /* FE2 ORGANIZACAO_INATIVA, FE3 PARCERIA_INATIVA (422), FE1 DADOS_INVALIDOS (400): nada foi registrado */
      var marcou = err.codigo === 'DADOS_INVALIDOS' && aplicarCamposApi(err);
      U.mostrar($('msg-nova'), 'erro', U.esc(S.msgErro(err)) + (marcou ? ' Corrija os campos indicados.' : '') + ' A solicitação não foi registrada.');
      $('msg-nova').focus();
    } finally {
      btn.disabled = false; btn.textContent = 'Confirmar e enviar solicitação';
    }
  });
});
