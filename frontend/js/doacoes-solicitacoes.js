/* Tela app/doacoes/solicitacoes.html. Novo UC "Solicitar doação", UC11 (aprovar), UC19 ampliado; RN04, RN12, RN15; RNF05; DP-69 a DP-73, DP-77.
   Rotas do contrato modulo-7: GET /doacoes/solicitacoes, GET /doacoes/solicitacoes/{id}, PATCH .../aprovar, .../recusar ({motivo}), .../cancelar.
   Cliente ONG: só as próprias; vê situação, motivo da recusa e Cancelar enquanto Pendente. Administrador e Funcionário: veem todas,
   Aprovam ou Recusam (motivo obrigatório, 3 a 500). A segurança real (404 de outra ONG, só Pendente muda) é do back-end. Sem alert(). */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, E = EquipUi;
  var TAMANHO = 10;
  var $ = function (id) { return document.getElementById(id); };
  var VISTAS = ['vista-lista', 'vista-detalhe'];
  var msgPagina = $('mensagem'), msgDet = $('msg-detalhe');
  var estado = { pagina: 1, situacao: '', interno: false, atual: null };

  var ICONE = { 'Pendente': '○', 'Aprovada': '✔', 'Recusada': '✖', 'Cancelada': '–' };
  var MSG = {
    SOLICITACAO_NAO_PENDENTE: 'Esta solicitação já foi decidida ou cancelada e não pode mais ser alterada.',
    ORGANIZACAO_INVALIDA: 'A organização da solicitação está inativa. Não foi possível aprovar.',
    EQUIPAMENTO_INDISPONIVEL: 'Algum produto da solicitação não está mais disponível. Não foi possível aprovar.',
    NAO_ENCONTRADO: 'Solicitação não encontrada. Ela não existe ou não pertence à sua ONG.'
  };
  function msgErro(err) { return (err && err.mensagem) || MSG[err && err.codigo] || 'Ocorreu um erro inesperado. Tente novamente.'; }

  /* Mesma regra da doacoes.js: Cliente ONG usa `minhas_doacoes`; Administrador e Funcionário usam `solicitacoes`. */
  var perfil0 = (Api.sessao.usuario() || {}).perfil;
  var interno0 = perfil0 === 'Administrador' || perfil0 === 'Funcionário';

  Layout.iniciar({ chave: interno0 ? 'solicitacoes' : 'minhas_doacoes' }).then(function (usuario) {
    if (!$('area-sd')) { return; }
    estado.interno = usuario.perfil === 'Administrador' || usuario.perfil === 'Funcionário';
    $('dica-lista').textContent = estado.interno
      ? 'Visão interna: aprove ou recuse as solicitações de doação das ONGs. Ao aprovar, a doação é registrada (UC11).'
      : 'Acompanhe as solicitações de doação da sua ONG. Você pode cancelar enquanto estiverem pendentes.';
    $('link-marketplace').hidden = estado.interno;
    $('cab-tabela').innerHTML = '<th scope="col">Solicitação</th>' + (estado.interno ? '<th scope="col">ONG</th>' : '') +
      '<th scope="col">Data</th><th scope="col">Situação</th><th scope="col">Ações</th>';
    carregar(1);
  });

  function vista(id, titulo) {
    VISTAS.forEach(function (v) { $(v).hidden = v !== id; });
    var t = $(titulo); t.setAttribute('tabindex', '-1'); t.focus();
  }
  function selo(s) { return '<span class="selo-situacao selo-doa selo-doa-' + String(s).toLowerCase() + '">' + (ICONE[s] || '•') + '&#xFE0E; ' + U.esc(s) + '</span>'; }
  function nomeOng(s) { return s.nome_organizacao || s.nome_ong || s.nome_razao_social || ''; }

  /* ---------- lista ---------- */
  function linhaHtml(s) {
    var id = s.id_solicitacao_doacao;
    return '<tr><td data-rotulo="Solicitação"><strong>Nº ' + U.esc(id) + '</strong>' +
      (s.motivo_recusa ? '<span class="sub">Motivo da recusa: ' + U.esc(s.motivo_recusa) + '</span>' : '') + '</td>' +
      (estado.interno ? '<td data-rotulo="ONG">' + U.esc(nomeOng(s)) + '</td>' : '') +
      '<td data-rotulo="Data">' + E.formatarData(s.data_solicitacao) + '</td>' +
      '<td data-rotulo="Situação">' + selo(s.situacao) + '</td>' +
      '<td class="acoes" data-rotulo="Ações"><div class="grupo-acoes"><button type="button" class="btn btn-outline-leaf" data-acao="ver" data-id="' + U.esc(id) +
      '" aria-label="Ver detalhes da solicitação ' + U.esc(id) + '">Detalhes</button></div></td></tr>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO];
    if (estado.situacao) { q.push('situacao=' + encodeURIComponent(estado.situacao)); }
    $('estado-lista').hidden = false; $('estado-lista').textContent = 'Carregando...';
    try {
      var r = await Api.get('/doacoes/solicitacoes?' + q.join('&'));
      estado.pagina = r.page;
      $('tabela').hidden = r.items.length === 0;
      $('paginacao').hidden = r.total <= r.size;
      $('corpo-tabela').innerHTML = r.items.map(linhaHtml).join('');
      var vazio = $('vazio-lista');
      if (!r.items.length) { /* FA: sem solicitações */
        $('estado-lista').hidden = true; vazio.hidden = false;
        vazio.innerHTML = estado.situacao
          ? '<p class="titulo-vazio">Nenhuma solicitação encontrada</p><p class="mb-0">Nenhuma solicitação atende ao filtro. Limpe o filtro.</p>'
          : '<p class="titulo-vazio">Ainda não há solicitações de doação</p><p class="mb-0">' +
            (estado.interno ? 'Quando uma ONG solicitar um produto, a solicitação aparecerá aqui.' : 'Escolha produtos no marketplace e use "Solicitar doação".') + '</p>';
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
      U.mostrar(msgPagina, 'erro', U.esc(msgErro(err)));
    }
  }

  $('form-filtros').addEventListener('submit', function (ev) {
    ev.preventDefault(); U.ocultar(msgPagina); estado.situacao = $('filtro-situacao').value; carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () { $('form-filtros').reset(); estado.situacao = ''; U.ocultar(msgPagina); carregar(1); });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });
  $('corpo-tabela').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-acao="ver"]');
    if (b) { U.ocultar(msgPagina); abrirDetalhe(Number(b.dataset.id)); }
  });

  /* ---------- detalhe e ações ---------- */
  function fecharPaineis() { $('painel-recusa').hidden = true; $('painel-cancelar').hidden = true; }

  function desenharDetalhe(s) {
    estado.atual = s; fecharPaineis(); U.ocultar(msgDet);
    var itens = (s.itens || []).map(function (i) {
      return '<li>' + U.esc(i.modelo) + ' &middot; ' + U.esc(i.categoria) + ' &middot; ' + U.esc(i.condicao) + '</li>';
    }).join('');
    $('corpo-detalhe').innerHTML = '<dl class="dados-sol">' +
      '<dt>Solicitação</dt><dd>Nº ' + U.esc(s.id_solicitacao_doacao) + '</dd>' +
      (nomeOng(s) ? '<dt>ONG</dt><dd>' + U.esc(nomeOng(s)) + '</dd>' : '') +
      '<dt>Data da solicitação</dt><dd>' + E.formatarData(s.data_solicitacao) + '</dd>' +
      '<dt>Situação</dt><dd>' + selo(s.situacao) + '</dd>' +
      '<dt>Produtos</dt><dd><ul class="lista-itens-doa">' + (itens || '<li>Sem itens informados.</li>') + '</ul></dd>' +
      (s.motivo_recusa ? '<dt>Motivo da recusa</dt><dd><div class="motivo-recusa">' + U.esc(s.motivo_recusa) + '</div></dd>' : '') +
      (s.decidido_por ? '<dt>Decidido por</dt><dd>' + U.esc(s.decidido_por) + (s.data_decisao ? ' em ' + E.formatarData(s.data_decisao) : '') + '</dd>' : '') +
      '</dl>';
    var acoes = '';
    if (s.situacao === 'Pendente') { /* só Pendente muda de estado (DP-70) */
      acoes = estado.interno
        ? '<button type="button" class="btn btn-success fw-semibold" id="btn-aprovar">Aprovar</button>' +
          '<button type="button" class="btn btn-excluir fw-semibold" id="btn-recusar">Recusar</button>'
        : '<button type="button" class="btn btn-excluir fw-semibold" id="btn-cancelar">Cancelar solicitação</button>';
    }
    $('acoes-detalhe').innerHTML = acoes;
  }

  async function abrirDetalhe(id) {
    try { desenharDetalhe(await Api.get('/doacoes/solicitacoes/' + id)); vista('vista-detalhe', 'titulo-detalhe'); }
    catch (err) { vista('vista-lista', 'titulo-lista-sd'); U.mostrar(msgPagina, 'erro', U.esc(msgErro(err))); }
  }
  $('btn-voltar').addEventListener('click', function () { vista('vista-lista', 'titulo-lista-sd'); carregar(estado.pagina); });

  /* Erro de ação: se a solicitação já não está Pendente, recarrega o detalhe e avisa (FE) */
  async function falhaAcao(err) {
    var id = estado.atual.id_solicitacao_doacao, texto = U.esc(msgErro(err));
    if (err.codigo === 'SOLICITACAO_NAO_PENDENTE') {
      try { desenharDetalhe(await Api.get('/doacoes/solicitacoes/' + id)); } catch (e) { /* mantém a tela */ }
    }
    U.mostrar(msgDet, 'erro', texto); msgDet.focus();
  }

  $('acoes-detalhe').addEventListener('click', async function (ev) {
    var b = ev.target.closest('button');
    if (!b) { return; }
    U.ocultar(msgDet);
    if (b.id === 'btn-recusar') { $('painel-recusa').hidden = false; $('motivo').focus(); }
    else if (b.id === 'btn-cancelar') { $('painel-cancelar').hidden = false; $('titulo-cancelar').focus(); }
    else if (b.id === 'btn-aprovar') {
      b.disabled = true;
      try { /* UC11: cria a doação de cada item no back-end */
        var s = await Api.patch('/doacoes/solicitacoes/' + estado.atual.id_solicitacao_doacao + '/aprovar');
        desenharDetalhe(s && s.situacao ? s : await Api.get('/doacoes/solicitacoes/' + estado.atual.id_solicitacao_doacao));
        U.mostrar(msgDet, 'sucesso', 'Solicitação aprovada. A doação foi registrada.'); msgDet.focus();
      } catch (err) { b.disabled = false; falhaAcao(err); }
    }
  });

  $('btn-desistir-recusa').addEventListener('click', function () { $('painel-recusa').hidden = true; });
  $('btn-desistir-cancelar').addEventListener('click', function () { $('painel-cancelar').hidden = true; });

  $('painel-recusa').addEventListener('submit', async function (ev) {
    ev.preventDefault();
    var campo = $('motivo'), motivo = campo.value.trim(), btn = $('btn-confirmar-recusa');
    U.limparErros($('painel-recusa'));
    if (!motivo) { U.erroCampo(campo, 'Informe o motivo da recusa.'); campo.focus(); return; }
    if (motivo.length < 3) { U.erroCampo(campo, 'O motivo deve ter pelo menos 3 caracteres.'); campo.focus(); return; }
    if (motivo.length > 500) { U.erroCampo(campo, 'O motivo deve ter no máximo 500 caracteres.'); campo.focus(); return; }
    btn.disabled = true;
    try {
      var id = estado.atual.id_solicitacao_doacao;
      var s = await Api.patch('/doacoes/solicitacoes/' + id + '/recusar', { motivo: motivo });
      campo.value = '';
      desenharDetalhe(s && s.situacao ? s : await Api.get('/doacoes/solicitacoes/' + id));
      U.mostrar(msgDet, 'sucesso', 'Solicitação recusada. A ONG verá o motivo informado e os produtos voltam ao marketplace.'); msgDet.focus();
    } catch (err) {
      if (err.codigo === 'DADOS_INVALIDOS' && !U.aplicarCamposDaApi(err, { motivo: campo })) { falhaAcao(err); }
      else if (err.codigo !== 'DADOS_INVALIDOS') { falhaAcao(err); }
    } finally { btn.disabled = false; }
  });

  $('btn-confirmar-cancelar').addEventListener('click', async function () {
    var btn = this, id = estado.atual.id_solicitacao_doacao;
    btn.disabled = true;
    try {
      var s = await Api.patch('/doacoes/solicitacoes/' + id + '/cancelar');
      desenharDetalhe(s && s.situacao ? s : await Api.get('/doacoes/solicitacoes/' + id));
      U.mostrar(msgDet, 'sucesso', 'Solicitação cancelada. Os produtos voltaram ao marketplace.'); msgDet.focus();
    } catch (err) { falhaAcao(err); }
    finally { btn.disabled = false; }
  });
});
