/* Tela app/doacoes/index.html. UC19 (RF04, RF12, RF15; RN04, RN12, RN15; RNF05), decisão DP-44.
   Cliente ONG: só as doações da própria ONG. Administrador e Funcionário: visão interna com todas e filtro por ONG.
   Rotas do contrato modulo-4: GET /doacoes e GET /doacoes/{id}; auxiliar GET /organizacoes (módulo 2) para o filtro interno.
   Somente leitura. Tudo via Api (js/api.js). A segurança real (404 para doação de outra ONG) é do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, E = EquipUi, S = SolUi;
  var TAMANHO = 10;
  var $ = function (id) { return document.getElementById(id); };
  var VISTAS = ['vista-lista', 'vista-detalhe'];
  var msgPagina = $('mensagem');
  var estado = { pagina: 1, filtros: {}, interno: false };

  /* Cliente ONG usa a funcionalidade `minhas_doacoes`; a visão interna (Administrador e Funcionário) não tem item de menu próprio,
     então a chave só é exigida dos demais perfis (qualquer outro recebe a mensagem de acesso negado do layout). */
  var perfil0 = (Api.sessao.usuario() || {}).perfil;
  var interno0 = perfil0 === 'Administrador' || perfil0 === 'Funcionário';

  Layout.iniciar({ chave: interno0 ? 'solicitacoes' : 'minhas_doacoes' }).then(function (usuario) {
    if (!$('area-doa')) { return; }
    estado.interno = usuario.perfil === 'Administrador' || usuario.perfil === 'Funcionário';
    if (estado.interno) {
      $('titulo-lista-doa').textContent = 'Doações registradas';
      $('dica-lista').textContent = 'Visão interna: todas as doações registradas pela destinação de equipamentos. Esta tela é somente para consulta; para registrar uma doação, defina a destinação "Doação" na avaliação da solicitação.';
      $('link-avaliacao').hidden = false;
      $('bloco-filtro-ong').hidden = false;
      carregarOngs();
    }
    $('cab-tabela').innerHTML = '<th scope="col">Equipamento</th>' + (estado.interno ? '<th scope="col">ONG</th>' : '') +
      '<th scope="col">Condição</th><th scope="col">Situação</th><th scope="col">Data da doação</th><th scope="col">Ações</th>';
    carregar(1);
  });

  function vista(id, titulo) { S.mostrarVista(VISTAS, id, titulo); }
  function limparMensagem() { U.ocultar(msgPagina); }
  function opcao(valor, texto) { var o = document.createElement('option'); o.value = valor; o.textContent = texto; return o; }

  async function carregarOngs() {
    try {
      var r = await Api.get('/organizacoes?tipo=' + encodeURIComponent('Cliente ONG') + '&size=100');
      r.items.forEach(function (o) { $('filtro-ong').appendChild(opcao(o.id_organizacao, o.nome_razao_social)); });
    } catch (err) { $('filtro-ong').disabled = true; }
  }

  /* ---------- lista (UC19 passos 2-3) ---------- */
  function linhaHtml(d) {
    return '<tr>' +
      '<td data-rotulo="Equipamento"><strong>' + U.esc(d.identificacao) + '</strong><span class="sub">' + U.esc(d.modelo) + ' · ' + U.esc(d.categoria_nome) + '</span></td>' +
      (estado.interno ? '<td data-rotulo="ONG">' + U.esc(d.nome_ong) + '</td>' : '') +
      '<td data-rotulo="Condição">' + U.esc(d.condicao) + '</td>' +
      '<td data-rotulo="Situação">' + E.seloSituacao(d.situacao) + '</td>' +
      '<td data-rotulo="Data da doação">' + E.formatarData(d.data_doacao) + '</td>' +
      '<td class="acoes" data-rotulo="Ações"><div class="grupo-acoes"><button type="button" class="btn btn-outline-leaf" data-acao="ver" data-id="' + d.id_doacao +
        '" aria-label="Consultar detalhes da doação de ' + E.escAttr(d.identificacao) + '">Detalhes</button></div></td></tr>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO], fl = estado.filtros;
    if (estado.interno && fl.ong) { q.push('id_organizacao_ong=' + encodeURIComponent(fl.ong)); }
    if (fl.de) { q.push('data_de=' + fl.de); }
    if (fl.ate) { q.push('data_ate=' + fl.ate); }
    $('estado-lista').hidden = false; $('estado-lista').textContent = 'Carregando...';
    try {
      var r = await Api.get('/doacoes?' + q.join('&'));
      estado.pagina = r.page;
      $('tabela').hidden = r.items.length === 0;
      $('paginacao').hidden = r.total <= r.size;
      $('corpo-tabela').innerHTML = r.items.map(linhaHtml).join('');
      var vazio = $('vazio-lista');
      if (!r.items.length) { /* UC19 FA1: sem registros */
        var filtrando = !!((estado.interno && fl.ong) || fl.de || fl.ate);
        $('estado-lista').hidden = true; vazio.hidden = false;
        vazio.innerHTML = filtrando
          ? '<p class="titulo-vazio">Nenhuma doação encontrada</p><p class="mb-0">Nenhum registro atende aos filtros. Ajuste ou limpe os filtros.</p>'
          : '<p class="titulo-vazio">Ainda não há doações ou equipamentos destinados</p><p class="mb-0">' +
            (estado.interno ? 'Quando um equipamento for destinado à doação, o registro aparecerá aqui.'
                            : 'Quando a LEAF TI destinar equipamentos à sua ONG, eles aparecerão aqui.') + '</p>';
      } else {
        vazio.hidden = true;
        $('estado-lista').textContent = r.total + (r.total === 1 ? ' registro encontrado.' : ' registros encontrados.');
      }
      $('texto-pagina').textContent = E.textoPagina(r, 'registro', 'registros');
      $('btn-anterior').disabled = r.page <= 1;
      $('btn-proxima').disabled = r.page * r.size >= r.total;
    } catch (err) {
      $('tabela').hidden = true; $('paginacao').hidden = true; $('vazio-lista').hidden = true;
      $('estado-lista').hidden = false; $('estado-lista').textContent = 'Não foi possível carregar as doações.';
      U.mostrar(msgPagina, 'erro', U.esc(S.msgErro(err)));
    }
  }

  $('form-filtros').addEventListener('submit', function (ev) {
    ev.preventDefault();
    U.limparErros($('form-filtros')); limparMensagem();
    var de = $('filtro-de').value, ate = $('filtro-ate').value;
    var erro = S.validarPeriodo(de, ate);
    if (erro) { U.erroCampo((de && !E.dataValida(de)) || (de && ate && de > ate) ? $('filtro-de') : $('filtro-ate'), erro); return; }
    estado.filtros = { ong: $('filtro-ong').value, de: de, ate: ate };
    carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () {
    $('form-filtros').reset(); U.limparErros($('form-filtros')); estado.filtros = {}; limparMensagem(); carregar(1);
  });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });
  $('corpo-tabela').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-acao="ver"]');
    if (b) { limparMensagem(); abrirDetalhe(Number(b.dataset.id)); }
  });

  /* ---------- detalhe somente leitura (UC19 passo 4; FE1) ---------- */
  async function abrirDetalhe(id) {
    try {
      var d = await Api.get('/doacoes/' + id);
      $('corpo-detalhe').innerHTML = '<dl class="dados-sol">' +
        '<dt>Equipamento</dt><dd>' + U.esc(d.identificacao) + '</dd>' +
        '<dt>Modelo</dt><dd>' + U.esc(d.modelo) + '</dd>' +
        '<dt>Categoria</dt><dd>' + U.esc(d.categoria_nome) + '</dd>' +
        '<dt>Condição</dt><dd>' + U.esc(d.condicao) + '</dd>' +
        '<dt>Situação</dt><dd>' + E.seloSituacao(d.situacao) + '</dd>' +
        '<dt>ONG beneficiária</dt><dd>' + U.esc(d.nome_ong) + '</dd>' +
        '<dt>Data da doação</dt><dd>' + E.formatarData(d.data_doacao) + '</dd>' +
        (estado.interno && d.id_solicitacao
          ? '<dt>Solicitação de origem</dt><dd><a href="../avaliacao/index.html?id=' + d.id_solicitacao + '">Solicitação nº ' + d.id_solicitacao + '</a></dd>' : '') +
        '</dl>';
      vista('vista-detalhe', 'titulo-detalhe');
    } catch (err) {
      /* FE1: doação de outra ONG -> 404, o sistema nega o acesso sem revelar o registro */
      vista('vista-lista', 'titulo-lista-doa');
      U.mostrar(msgPagina, 'erro', err.status === 404
        ? 'Registro não encontrado. Ele não existe ou não pertence à sua ONG.' : U.esc(S.msgErro(err)));
    }
  }
  $('btn-voltar').addEventListener('click', function () { vista('vista-lista', 'titulo-lista-doa'); carregar(estado.pagina); });
});
