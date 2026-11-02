/* Tela app/avaliacao/index.html (Administrador e Funcionário). UC10 (RF03, RF05, RF11, RF12, RF21; RN03, RN05, RN11, RN12, RN21)
   e UC11 (RF12, RF21; RN12, RN21). Decisões DP-40, DP-41 e DP-42.
   Rotas do contrato modulo-4: GET /solicitacoes, GET /solicitacoes/{id}, POST /solicitacoes/{id}/itens/{item}/equipamentos,
   PUT /solicitacoes/{id}/equipamentos/{eq}/destinacao, GET /doacoes/ongs-elegiveis; auxiliares: GET /categorias (módulo 3)
   e GET /organizacoes (módulo 2, filtro). Tudo via Api (js/api.js).
   Mostrar/esconder é conveniência; as regras reais (reuso, doação, transições) são do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, E = EquipUi, S = SolUi;
  var TAMANHO = 10;
  var $ = function (id) { return document.getElementById(id); };
  var VISTAS = ['vista-lista', 'vista-detalhe'];
  var msgPagina = $('mensagem');
  var estado = { pagina: 1, filtros: {}, sol: null, cats: null, ongs: null, alvoItem: null, alvoEq: null };
  var modalUnidade = new bootstrap.Modal($('modal-unidade'));
  var modalDest = new bootstrap.Modal($('modal-dest'));

  var u = { identificacao: $('u-identificacao'), categoria: $('u-categoria'), condicao: $('u-condicao'), situacao: $('u-situacao'),
            data: $('u-data'), valor: $('u-valor'), origem: $('u-origem') };
  var mapaUnidade = { identificacao: u.identificacao, id_categoria: u.categoria, condicao: u.condicao, situacao: u.situacao,
                      data_recebimento: u.data, valor: u.valor, origem: u.origem };
  var mapaDest = { id_organizacao_ong: $('d-ong'), data_doacao: $('d-data') };

  Layout.iniciar({ chave: 'solicitacoes' }).then(function () {
    if (!$('area-ava')) { return; } /* sem permissão: o layout já mostrou a mensagem */
    S.SITUACOES.forEach(function (v) { $('filtro-situacao').appendChild(opcao(v, v)); });
    u.condicao.innerHTML = ''; u.condicao.appendChild(opcao('', 'Selecione a condição'));
    E.CONDICOES.forEach(function (v) { u.condicao.appendChild(opcao(v, v)); });
    ['Recebido', 'Em avaliação', 'Em manutenção'].forEach(function (v) { u.situacao.appendChild(opcao(v, v)); });
    carregarEmpresas();
    carregar(1);
    var idUrl = S.idDaUrl();
    if (idUrl) { abrirDetalhe(idUrl, false); }
  });

  function opcao(valor, texto) { var o = document.createElement('option'); o.value = valor; o.textContent = texto; return o; }
  function vista(id, titulo) { S.mostrarVista(VISTAS, id, titulo); }
  function limparMensagem() { U.ocultar(msgPagina); }

  /* Filtro de Empresa Doadora (UC10 passo 1); se falhar, a lista continua funcionando sem ele */
  async function carregarEmpresas() {
    try {
      var r = await Api.get('/organizacoes?tipo=' + encodeURIComponent('Empresa Doadora') + '&size=100');
      r.items.forEach(function (o) { $('filtro-org').appendChild(opcao(o.id_organizacao, o.nome_razao_social)); });
    } catch (err) { $('filtro-org').disabled = true; }
  }

  /* ---------- lista (UC10 passo 1) ---------- */
  function linhaHtml(s) {
    var aval = s.situacao === 'Aguardando avaliação' ? 'Nenhuma unidade avaliada'
      : s.unidades_avaliadas + ' de ' + s.total_unidades + (s.total_unidades === 1 ? ' unidade' : ' unidades');
    return '<tr>' +
      '<td data-rotulo="Solicitação"><strong>Nº ' + s.id_solicitacao + '</strong><span class="sub">' + s.total_itens + (s.total_itens === 1 ? ' item' : ' itens') + '</span></td>' +
      '<td data-rotulo="Empresa Doadora">' + U.esc(s.nome_organizacao) + '</td>' +
      '<td data-rotulo="Data">' + E.formatarData(s.data_solicitacao) + '</td>' +
      '<td data-rotulo="Situação">' + S.seloSolicitacao(s.situacao) + '</td>' +
      '<td data-rotulo="Avaliação">' + aval + '</td>' +
      '<td class="acoes" data-rotulo="Ações"><div class="grupo-acoes"><button type="button" class="btn btn-outline-leaf" data-acao="abrir" data-id="' + s.id_solicitacao +
        '" aria-label="' + (s.situacao === 'Avaliada' ? 'Consultar' : 'Avaliar') + ' solicitação número ' + s.id_solicitacao + '">' +
        (s.situacao === 'Avaliada' ? 'Consultar' : 'Avaliar') + '</button></div></td></tr>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO], fl = estado.filtros;
    if (fl.situacao) { q.push('situacao=' + encodeURIComponent(fl.situacao)); }
    if (fl.org) { q.push('id_organizacao_doadora=' + encodeURIComponent(fl.org)); }
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
        var filtrando = !!(fl.situacao || fl.org || fl.de || fl.ate);
        $('estado-lista').hidden = true; vazio.hidden = false;
        vazio.innerHTML = filtrando
          ? '<p class="titulo-vazio">Nenhuma solicitação encontrada</p><p class="mb-0">Nenhuma solicitação atende aos filtros. Ajuste ou limpe os filtros.</p>'
          : '<p class="titulo-vazio">Nenhuma solicitação registrada</p><p class="mb-0">Quando uma Empresa Doadora enviar equipamentos para avaliação, a solicitação aparecerá aqui.</p>';
      } else {
        vazio.hidden = true;
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
    if (erro) { U.erroCampo((de && !E.dataValida(de)) || (de && ate && de > ate) ? $('filtro-de') : $('filtro-ate'), erro); return; }
    estado.filtros = { situacao: $('filtro-situacao').value, org: $('filtro-org').value, de: de, ate: ate };
    carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () {
    $('form-filtros').reset(); U.limparErros($('form-filtros')); estado.filtros = {}; limparMensagem(); carregar(1);
  });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });
  $('corpo-tabela').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-acao="abrir"]');
    if (b) { limparMensagem(); abrirDetalhe(Number(b.dataset.id), true); }
  });

  /* ---------- detalhe e avaliação (UC10 passos 2-7) ---------- */
  var FINAIS = ['Vendido', 'Doado', 'Destinado à reciclagem'];

  function acoesEquipamento(eq) {
    if (FINAIS.indexOf(eq.situacao) !== -1) { return '<span class="texto-sem-acao">Situação final: sem ações</span>'; }
    return '<div class="grupo-acoes"><button type="button" class="btn btn-outline-leaf" data-acao="destinar" data-id="' + eq.id_equipamento +
      '" aria-label="' + (eq.destinacao ? 'Alterar' : 'Definir') + ' destinação de ' + E.escAttr(eq.identificacao) + '">' + (eq.destinacao ? 'Alterar destinação' : 'Definir destinação') + '</button></div>';
  }
  function rodapeItem(item) {
    if ((item.quantidade_cadastrada || 0) >= item.quantidade) {
      return '<p class="texto-sem-acao mb-0">Todas as ' + item.quantidade + ' unidades deste item já foram cadastradas.</p>';
    }
    var falta = item.quantidade - (item.quantidade_cadastrada || 0);
    return '<button type="button" class="btn btn-success fw-semibold" data-acao="unidade" data-item="' + item.id_item_solicitacao +
      '" aria-label="Cadastrar unidade do item ' + E.escAttr(item.tipo + ' ' + item.modelo) + '">+ Cadastrar unidade</button> ' +
      '<span class="dica-campo ms-1">Faltam ' + falta + (falta === 1 ? ' unidade' : ' unidades') + ' para cadastrar.</span>';
  }

  function mostrarDetalhe(sol) {
    estado.sol = sol;
    $('titulo-detalhe').textContent = 'Solicitação nº ' + sol.id_solicitacao;
    $('cab-detalhe').innerHTML = S.dadosSolicitacao(sol, true);
    $('aviso-detalhe').innerHTML = S.avisoPendencias(sol); /* UC10 FE2: pendências enquanto não concluir */
    $('itens-detalhe').innerHTML = (sol.itens || []).map(function (it, i) {
      return S.cartaoItem(it, i, { valor: true, acoes: acoesEquipamento, rodape: rodapeItem });
    }).join('');
  }
  async function abrirDetalhe(id, focar) {
    try {
      var sol = await Api.get('/solicitacoes/' + id);
      mostrarDetalhe(sol);
      vista('vista-detalhe', focar === false ? null : 'titulo-detalhe');
    } catch (err) {
      vista('vista-lista', 'titulo-lista-ava');
      U.mostrar(msgPagina, 'erro', err.status === 404 ? 'Solicitação não encontrada.' : U.esc(S.msgErro(err)));
    }
  }
  async function recarregarDetalhe(mensagem) {
    var sol = await Api.get('/solicitacoes/' + estado.sol.id_solicitacao);
    mostrarDetalhe(sol);
    if (mensagem) { U.mostrar(msgPagina, 'sucesso', U.esc(mensagem)); msgPagina.focus(); }
  }
  $('btn-voltar').addEventListener('click', function () { limparMensagem(); vista('vista-lista', 'titulo-lista-ava'); carregar(estado.pagina); });

  function achar(tipo, id) {
    var r = null;
    (estado.sol.itens || []).forEach(function (it) {
      if (tipo === 'item' && it.id_item_solicitacao === id) { r = it; }
      (it.equipamentos || []).forEach(function (eq) { if (tipo === 'eq' && eq.id_equipamento === id) { r = { eq: eq, item: it }; } });
    });
    return r;
  }
  $('itens-detalhe').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-acao]');
    if (!b) { return; }
    limparMensagem();
    if (b.dataset.acao === 'unidade') { abrirUnidade(achar('item', Number(b.dataset.item))); }
    else if (b.dataset.acao === 'destinar') { abrirDestinacao(achar('eq', Number(b.dataset.id))); }
  });

  /* ---------- cadastrar unidade (UC10 passo 3; DP-41) ---------- */
  async function abrirUnidade(item) {
    if (!item) { return; }
    estado.alvoItem = item;
    U.limparErros($('form-unidade')); U.ocultar($('msg-unidade'));
    $('form-unidade').reset();
    $('unidade-resumo').textContent = 'Item: ' + item.tipo + ' — ' + item.modelo + ' (unidade ' + ((item.quantidade_cadastrada || 0) + 1) + ' de ' + item.quantidade + ')';
    u.data.max = E.hojeIso(); u.data.value = E.hojeIso();
    u.origem.placeholder = 'Solicitação ' + estado.sol.id_solicitacao;
    u.situacao.value = 'Recebido';
    modalUnidade.show();
    if (!estado.cats) {
      try { estado.cats = (await Api.get('/categorias?size=100')).items.filter(function (c) { return c.ativa; }); }
      catch (err) { U.mostrar($('msg-unidade'), 'erro', 'Não foi possível carregar as categorias. ' + U.esc(S.msgErro(err))); estado.cats = []; }
    }
    u.categoria.innerHTML = ''; u.categoria.appendChild(opcao('', 'Selecione a categoria'));
    estado.cats.forEach(function (c) { u.categoria.appendChild(opcao(c.id_categoria, c.nome)); });
  }

  $('form-unidade').addEventListener('submit', async function (ev) {
    ev.preventDefault();
    U.limparErros($('form-unidade')); U.ocultar($('msg-unidade'));
    var item = estado.alvoItem, solId = estado.sol.id_solicitacao;
    var v = { identificacao: u.identificacao.value, id_categoria: u.categoria.value, modelo: item.modelo, condicao: u.condicao.value,
              origem: u.origem.value.trim() || ('Solicitação ' + solId), data_recebimento: u.data.value, valor: u.valor.value,
              situacao: u.situacao.value };
    var erros = E.validarEquipamento(v, { criando: true }); /* mesmas regras do módulo 3 (UC07 FE1, RN12) */
    var chaves = Object.keys(erros);
    if (chaves.length) {
      chaves.forEach(function (k) { if (mapaUnidade[k]) { U.erroCampo(mapaUnidade[k], erros[k]); } });
      U.mostrar($('msg-unidade'), 'erro', 'Corrija os campos indicados. A unidade não foi cadastrada.');
      (mapaUnidade[chaves[0]] || $('msg-unidade')).focus(); return;
    }
    var corpo = { identificacao: v.identificacao.trim(), id_categoria: Number(v.id_categoria), condicao: v.condicao,
                  data_recebimento: v.data_recebimento, situacao: v.situacao };
    if (u.origem.value.trim()) { corpo.origem = u.origem.value.trim(); }
    if (v.__valor != null) { corpo.valor = v.__valor; }
    var btn = $('btn-salvar-unidade');
    btn.disabled = true; btn.textContent = 'Cadastrando...';
    try {
      await Api.post('/solicitacoes/' + solId + '/itens/' + item.id_item_solicitacao + '/equipamentos', corpo);
      modalUnidade.hide();
      await recarregarDetalhe('Unidade ' + corpo.identificacao + ' cadastrada. A solicitação passa a "Em avaliação" até que todas as unidades tenham condição e destinação.');
    } catch (err) {
      var marcou = U.aplicarCamposDaApi(err, mapaUnidade);
      if (err.codigo === 'IDENTIFICACAO_DUPLICADA' && !marcou) { U.erroCampo(u.identificacao, 'Esta identificação já está em uso por outro equipamento.'); marcou = true; }
      U.mostrar($('msg-unidade'), 'erro', U.esc(S.msgErro(err)) + (marcou ? ' Corrija os campos indicados.' : ''));
      $('msg-unidade').focus();
      if (err.codigo === 'ITEM_COMPLETO') { modalUnidade.hide(); try { await recarregarDetalhe(); } catch (e) { /* mensagem já exibida */ } U.mostrar(msgPagina, 'erro', U.esc(S.msgErro(err))); }
    } finally {
      btn.disabled = false; btn.textContent = 'Cadastrar unidade';
    }
  });

  /* ---------- definir destinação (UC10 passos 4-7; UC11) ---------- */
  /* Conveniência de tela: quais destinações a regra do equipamento permite. A API valida de verdade (RN11, RN12). */
  function destinacoesPermitidas(eq) {
    var motivoReuso = null;
    if (eq.condicao === E.SEM_REUSO) { motivoReuso = 'Equipamento sem condições de reuso: só pode ser destinado à reciclagem.'; }
    else if (eq.condicao === 'A avaliar') { motivoReuso = 'Registre antes a condição avaliada (hoje: "A avaliar"). Use Equipamentos para alterar a condição.'; }
    else if (eq.ativo === false) { motivoReuso = 'Equipamento inativo não pode ser vendido nem doado. Reative-o em Equipamentos.'; }
    return {
      'Venda': motivoReuso || (Number(eq.valor) > 0 ? null : 'A venda exige valor maior que zero. Informe o valor em Equipamentos.'),
      'Doação': motivoReuso,
      'Reciclagem': null
    };
  }
  var DESC_DEST = { 'Venda': 'Disponibiliza o equipamento para venda (situação Disponível).',
                    'Doação': 'Destina o equipamento a uma ONG (situação Doado). Informe a ONG e a data.',
                    'Reciclagem': 'Encaminha à reciclagem (situação final). Não pode mais ser vendido nem doado.' };
  var ID_DEST = { 'Venda': 'dest-venda', 'Doação': 'dest-doacao', 'Reciclagem': 'dest-reciclagem' };

  function abrirDestinacao(achado) {
    if (!achado) { return; }
    var eq = achado.eq;
    estado.alvoEq = eq;
    U.limparErros($('form-dest')); U.ocultar($('msg-dest')); $('dest-erro').textContent = '';
    $('bloco-doacao').hidden = true; $('d-data').value = ''; $('d-data').max = E.hojeIso(); $('d-data').min = eq.data_recebimento || '';
    $('dest-resumo').innerHTML = 'Equipamento <strong>' + U.esc(eq.identificacao) + '</strong> (' + U.esc(eq.categoria_nome || '') + '). Condição: <strong>' + U.esc(eq.condicao) +
      '</strong>. Situação: <strong>' + U.esc(eq.situacao) + '</strong>.';
    var perm = destinacoesPermitidas(eq);
    /* DP-54: com condição "A avaliar" nenhuma destinação é aceita (CONDICAO_NAO_AVALIADA) */
    if (eq.condicao === 'A avaliar') { perm['Reciclagem'] = perm['Venda']; }
    $('dest-opcoes').innerHTML = S.DESTINACOES.map(function (d) {
      var bloq = perm[d], id = ID_DEST[d];
      return '<div class="opcao-destinacao' + (bloq ? ' desabilitada' : '') + '">' +
        '<input type="radio" name="destinacao" id="' + id + '" value="' + d + '"' + (bloq ? ' disabled' : '') + ' aria-describedby="' + id + '-desc">' +
        '<label for="' + id + '"><strong>' + d + '</strong><span class="d-block" id="' + id + '-desc">' + U.esc(bloq || DESC_DEST[d]) + '</span></label></div>';
    }).join('');
    modalDest.show();
  }
  $('dest-opcoes').addEventListener('change', async function () {
    var sel = $('form-dest').querySelector('input[name="destinacao"]:checked');
    $('dest-erro').textContent = '';
    var doacao = !!sel && sel.value === 'Doação';
    $('bloco-doacao').hidden = !doacao;
    if (doacao && !estado.ongs) { await carregarOngs(); }
  });
  /* UC11 passo 2: ONGs ativas elegíveis */
  async function carregarOngs() {
    var sel = $('d-ong');
    sel.innerHTML = ''; sel.appendChild(opcao('', 'Carregando ONGs...'));
    try {
      estado.ongs = await Api.get('/doacoes/ongs-elegiveis');
    } catch (err) {
      sel.innerHTML = ''; sel.appendChild(opcao('', 'Não foi possível carregar as ONGs'));
      U.mostrar($('msg-dest'), 'erro', U.esc(S.msgErro(err))); return;
    }
    sel.innerHTML = '';
    if (!estado.ongs.length) { /* UC11 FE1: sem ONG ativa não há como concluir a doação */
      sel.appendChild(opcao('', 'Nenhuma ONG ativa disponível'));
      U.erroCampo(sel, 'Não há ONG ativa cadastrada. Cadastre ou reative uma ONG para registrar a doação.');
      estado.ongs = null; return;
    }
    sel.appendChild(opcao('', 'Selecione a ONG beneficiária'));
    estado.ongs.forEach(function (o) { sel.appendChild(opcao(o.id_organizacao, o.nome_razao_social)); });
  }

  $('form-dest').addEventListener('submit', async function (ev) {
    ev.preventDefault();
    U.limparErros($('form-dest')); U.ocultar($('msg-dest')); $('dest-erro').textContent = '';
    var eq = estado.alvoEq, solId = estado.sol.id_solicitacao;
    var sel = $('form-dest').querySelector('input[name="destinacao"]:checked');
    if (!sel) { $('dest-erro').textContent = 'Selecione a destinação do equipamento.'; U.mostrar($('msg-dest'), 'erro', 'Escolha Venda, Doação ou Reciclagem.'); $('msg-dest').focus(); return; }
    var corpo = { destinacao: sel.value };
    if (sel.value === 'Doação') {
      var erros = 0, ong = $('d-ong').value, data = $('d-data').value;
      if (!ong) { U.erroCampo($('d-ong'), 'Selecione a ONG beneficiária.'); erros++; }
      if (!data) { U.erroCampo($('d-data'), 'Informe a data da doação.'); erros++; }
      else if (!E.dataValida(data)) { U.erroCampo($('d-data'), 'Informe uma data válida.'); erros++; }
      else if (data > E.hojeIso()) { U.erroCampo($('d-data'), 'A data da doação não pode ser futura.'); erros++; }
      else if (eq.data_recebimento && data < eq.data_recebimento) { U.erroCampo($('d-data'), 'A data da doação não pode ser anterior ao recebimento (' + E.formatarData(eq.data_recebimento) + ').'); erros++; }
      if (erros) { U.mostrar($('msg-dest'), 'erro', 'Corrija os campos indicados. A destinação não foi registrada.'); $('msg-dest').focus(); return; }
      corpo.id_organizacao_ong = Number(ong); corpo.data_doacao = data;
    }
    var btn = $('btn-salvar-dest');
    btn.disabled = true; btn.textContent = 'Registrando...';
    try {
      var sol = await Api.put('/solicitacoes/' + solId + '/equipamentos/' + eq.id_equipamento + '/destinacao', corpo);
      modalDest.hide();
      mostrarDetalhe(sol);
      U.mostrar(msgPagina, 'sucesso', 'Destinação ' + U.esc(corpo.destinacao) + ' registrada para ' + U.esc(eq.identificacao) + '. ' +
        (sol.situacao === 'Avaliada' ? 'Todos os itens foram avaliados: a solicitação está Avaliada.' : 'A solicitação continua "' + U.esc(sol.situacao) + '" enquanto houver pendências.'));
      msgPagina.focus();
    } catch (err) {
      var marcou = U.aplicarCamposDaApi(err, mapaDest);
      if (err.codigo === 'DOACAO_INVALIDA' && !marcou) { U.erroCampo($('d-ong'), 'Revise a ONG e a data da doação.'); marcou = true; }
      U.mostrar($('msg-dest'), 'erro', U.esc(S.msgErro(err)) + (marcou ? ' Corrija os campos indicados.' : ''));
      $('msg-dest').focus();
    } finally {
      btn.disabled = false; btn.textContent = 'Registrar destinação';
    }
  });
});
