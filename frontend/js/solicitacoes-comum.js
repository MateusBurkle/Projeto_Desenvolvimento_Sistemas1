/* Funções comuns às telas do Módulo 4 (solicitações, avaliação, doações).
   UC09, UC10, UC11, UC19, UC20; RF05, RF12, RF21; RN05, RN12, RN21; RNF04, RNF06.
   Não faz chamadas à API (só js/api.js). Reaproveita UsuariosUi e EquipUi. Expõe o objeto global SolUi. */
(function (global) {
  'use strict';
  var U = global.UsuariosUi, E = global.EquipUi;

  /* Valores exatos do contrato (modulo-4.yaml: SituacaoSolicitacao e Destinacao) */
  var SITUACOES = ['Aguardando avaliação', 'Em avaliação', 'Avaliada'];
  var DESTINACOES = ['Venda', 'Doação', 'Reciclagem'];

  /* Mensagens em português por código (usadas se a API não enviar "mensagem"). */
  var MSG = {
    ORGANIZACAO_INATIVA: 'A organização está inativa e não pode enviar novas solicitações.',
    PARCERIA_INATIVA: 'A Empresa Doadora precisa de vínculo de parceria ativo para solicitar avaliação.',
    ITEM_COMPLETO: 'Todas as unidades deste item já foram cadastradas.',
    CONDICAO_NAO_AVALIADA: 'Defina a condição avaliada antes de escolher a destinação.',
    SEM_CONDICOES_DE_REUSO: 'Equipamento sem condições de reuso só pode ser destinado à reciclagem.',
    TRANSICAO_INVALIDA: 'Esta destinação não é permitida para a situação atual do equipamento.',
    EQUIPAMENTO_INATIVO: 'Equipamento inativo não pode ser vendido nem doado. Reative-o em Equipamentos.',
    EQUIPAMENTO_FINALIZADO: 'Equipamentos vendidos ou doados não podem mais ser alterados.',
    DOACAO_INVALIDA: 'Dados da doação inválidos. Escolha uma ONG ativa e uma data que não seja futura nem anterior ao recebimento.',
    CATEGORIA_INVALIDA: 'A categoria escolhida não existe ou está desativada. Escolha uma categoria ativa.',
    IDENTIFICACAO_DUPLICADA: 'Esta identificação já está em uso por outro equipamento.',
    NAO_ENCONTRADO: 'Registro não encontrado ou sem acesso. Atualize a lista e tente novamente.'
  };
  function msgErro(err) {
    return (err && err.mensagem) || MSG[err && err.codigo] || E.MSG[err && err.codigo] || 'Ocorreu um erro inesperado. Tente novamente.';
  }

  /* ---------- selos: sempre texto + ícone (nunca só cor, RNF06) ---------- */
  var ICONE_SOL = { 'Aguardando avaliação': '○', 'Em avaliação': '◐', 'Avaliada': '✔' };
  var CLASSE_SOL = { 'Aguardando avaliação': 'selo-sol-aguardando', 'Em avaliação': 'selo-sol-andamento', 'Avaliada': 'selo-sol-avaliada' };
  function seloSolicitacao(s) {
    return '<span class="selo-situacao ' + (CLASSE_SOL[s] || 'selo-sol-andamento') + '">' + (ICONE_SOL[s] || '•') + '&#xFE0E; ' + U.esc(s) + '</span>';
  }
  var ICONE_DEST = { 'Venda': '◆', 'Doação': '♥', 'Reciclagem': '♻' };
  function seloDestinacao(d) {
    if (!d) { return '<span class="selo-situacao selo-dest-pendente">…&nbsp;Pendente</span>'; }
    return '<span class="selo-situacao selo-dest-ok">' + (ICONE_DEST[d] || '•') + '&#xFE0E; ' + U.esc(d) + '</span>';
  }
  /* UC20 passo 3: destinação registrada; para doação, ONG e data. Sem destinação = "Pendente" (nada inventado, UC20 FA1). */
  function destinacaoHtml(eq) {
    var h = seloDestinacao(eq.destinacao);
    if (eq.destinacao === 'Doação') {
      h += '<span class="sub">ONG: ' + U.esc(eq.nome_ong || '—') + ' em ' + E.formatarData(eq.data_doacao) + '</span>';
    }
    return h;
  }

  /* ---------- tabela de equipamentos de um item (UC10 passo 3-4; UC20 passo 3) ----------
     opcoes.valor: mostra a coluna Valor (nunca para Empresa Doadora; a API também omite).
     opcoes.acoes: function(eq) -> html da coluna Ações (só visão interna). */
  function tabelaEquipamentos(eqs, opcoes) {
    opcoes = opcoes || {};
    var cab = '<th scope="col">Identificação</th><th scope="col">Condição avaliada</th><th scope="col">Situação</th><th scope="col">Destinação</th>' +
      (opcoes.valor ? '<th scope="col">Valor</th>' : '') + (opcoes.acoes ? '<th scope="col">Ações</th>' : '');
    var linhas = eqs.map(function (eq) {
      return '<tr>' +
        '<td data-rotulo="Identificação"><strong>' + U.esc(eq.identificacao) + '</strong><span class="sub">' + U.esc(eq.categoria_nome || '') + '</span></td>' +
        '<td data-rotulo="Condição">' + U.esc(eq.condicao === 'A avaliar' ? 'A avaliar (ainda sem condição definida)' : eq.condicao) + '</td>' +
        '<td data-rotulo="Situação">' + E.seloSituacao(eq.situacao) + (eq.ativo === false ? ' ' + E.seloAtivo(false) : '') + '</td>' +
        '<td data-rotulo="Destinação">' + destinacaoHtml(eq) + '</td>' +
        (opcoes.valor ? '<td data-rotulo="Valor">' + E.formatarValor(eq.valor) + '</td>' : '') +
        (opcoes.acoes ? '<td class="acoes" data-rotulo="Ações">' + opcoes.acoes(eq) + '</td>' : '') +
        '</tr>';
    }).join('');
    return '<div class="table-responsive"><table class="table table-hover tabela-usuarios tabela-equip tabela-sol mb-2">' +
      '<caption class="visually-hidden">Unidades avaliadas do item</caption><thead><tr>' + cab + '</tr></thead><tbody>' + linhas + '</tbody></table></div>';
  }

  /* Cartão de um item da solicitação: o que foi informado + o que a LEAF TI já registrou.
     opcoes.rodape: html extra (ex.: botão "Cadastrar unidade"). */
  function cartaoItem(item, indice, opcoes) {
    opcoes = opcoes || {};
    var eqs = item.equipamentos || [];
    var avaliado = item.avaliado
      ? '<span class="selo-situacao selo-sol-avaliada">✔&#xFE0E; Item avaliado</span>'
      : '<span class="selo-situacao selo-sol-aguardando">○&#xFE0E; Avaliação pendente</span>';
    var corpo = eqs.length
      ? tabelaEquipamentos(eqs, opcoes)
      : '<p class="aviso-info mb-2" role="status"><span aria-hidden="true">○ </span>Nenhuma unidade deste item foi avaliada ainda. A condição e a destinação aparecerão aqui quando a LEAF TI registrá-las.</p>';
    return '<article class="cartao-item" aria-labelledby="item-' + item.id_item_solicitacao + '-t">' +
      '<h3 class="h5" id="item-' + item.id_item_solicitacao + '-t">Item ' + (indice + 1) + ': ' + U.esc(item.tipo) + ' — ' + U.esc(item.modelo) + '</h3>' +
      '<div class="meta-item"><span>Quantidade informada: <strong>' + item.quantidade + '</strong></span>' +
      '<span>Unidades cadastradas: <strong>' + (item.quantidade_cadastrada || 0) + '</strong></span>' +
      '<span>Avaliadas e destinadas: <strong>' + (item.quantidade_avaliada || 0) + '</strong></span>' + avaliado + '</div>' +
      corpo + (opcoes.rodape ? opcoes.rodape(item) : '') + '</article>';
  }

  /* UC10 FE2: pendências que impedem concluir a solicitação (texto vindo da API; nada inventado). */
  function avisoPendencias(sol) {
    if (sol.situacao === 'Avaliada') {
      return '<div class="aviso-ok" role="status"><span aria-hidden="true">✔ </span>Todos os itens foram avaliados e têm destinação registrada.</div>';
    }
    var p = sol.pendencias || [];
    if (!p.length) { return ''; }
    return '<div class="aviso-pendencias" role="status"><strong><span aria-hidden="true">… </span>Pendências para concluir a avaliação:</strong><ul>' +
      p.map(function (t) { return '<li>' + U.esc(t) + '</li>'; }).join('') + '</ul></div>';
  }

  /* Cabeçalho (lista de definição) da solicitação */
  function dadosSolicitacao(sol, comOrganizacao) {
    return '<dl class="dados-sol">' +
      (comOrganizacao ? '<dt>Empresa Doadora</dt><dd>' + U.esc(sol.nome_organizacao) + '</dd>' : '') +
      '<dt>Data da solicitação</dt><dd>' + E.formatarData(sol.data_solicitacao) + '</dd>' +
      '<dt>Situação</dt><dd>' + seloSolicitacao(sol.situacao) + '</dd></dl>';
  }

  /* ---------- filtros de período ----------
     Devolve mensagem de erro ou null (data inicial não pode ser maior que a final). */
  function validarPeriodo(de, ate) {
    if (de && !E.dataValida(de)) { return 'Informe uma data inicial válida.'; }
    if (ate && !E.dataValida(ate)) { return 'Informe uma data final válida.'; }
    if (de && ate && de > ate) { return 'A data inicial não pode ser maior que a data final.'; }
    return null;
  }

  /* Parâmetro ?id=N da URL (abre o detalhe direto); null se ausente ou inválido. */
  function idDaUrl() {
    var m = /[?&]id=(\d{1,18})(?:&|$)/.exec(global.location.search);
    return m ? Number(m[1]) : null;
  }

  /* Mostra uma vista e esconde as demais; foca o título para leitores de tela e teclado. */
  function mostrarVista(ids, mostrar, tituloId) {
    ids.forEach(function (id) { var el = document.getElementById(id); if (el) { el.hidden = id !== mostrar; } });
    var t = document.getElementById(tituloId);
    if (t) { t.setAttribute('tabindex', '-1'); t.focus(); }
  }

  global.SolUi = {
    SITUACOES: SITUACOES, DESTINACOES: DESTINACOES, MSG: MSG, msgErro: msgErro,
    seloSolicitacao: seloSolicitacao, seloDestinacao: seloDestinacao, destinacaoHtml: destinacaoHtml,
    tabelaEquipamentos: tabelaEquipamentos, cartaoItem: cartaoItem, avisoPendencias: avisoPendencias,
    dadosSolicitacao: dadosSolicitacao, validarPeriodo: validarPeriodo, idDaUrl: idDaUrl, mostrarVista: mostrarVista
  };
})(window);
