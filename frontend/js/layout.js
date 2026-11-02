/* Layout base das telas logadas (frontend/app/). UC04 passo 4 (apresentar as funcionalidades
   autorizadas ao perfil); RN01, RNF05, RNF01, RNF06.
   Uso em cada página logada: carregar api.js e layout.js e chamar
     Layout.iniciar({ chave: 'inicio' }).then(function (usuario) { ... });
   - Guarda de rota: sem token -> login; 401 em /auth/me -> Api limpa a sessão e volta ao login.
   - Menu montado a partir de usuario.funcionalidades (GET /auth/me). A segurança real é da API.
   - Módulos ainda não implementados aparecem como itens "Em breve" (sem link). Quando um módulo
     ganhar tela, preencha o campo href do item em MENU (caminho relativo a frontend/app/).
   - Funciona em qualquer subpasta de app/ (ex.: app/usuarios/): os links são montados a partir de APP. */
(function (global) {
  'use strict';

  /* Chaves de funcionalidades do contrato (x-matriz-funcionalidades) -> rótulo e UC/RF de origem.
     href: null = tela prevista, ainda não implementada. */
  var MENU = [
    { chave: 'catalogo',              rotulo: 'Catálogo',               href: '../hardware.html' }, /* UC12, UC13: leva ao marketplace (DP-68, DP-78); app/catalogo foi aposentada */
    { chave: 'minhas_compras',        rotulo: 'Minhas compras',         href: 'compras/index.html' }, /* UC13 FA1, UC18 (Módulo 5) */
    { chave: 'minhas_notas_fiscais',  rotulo: 'Minhas notas fiscais',   href: 'notas-fiscais/index.html' }, /* UC17 (Módulo 5) */
    { chave: 'minhas_doacoes',        rotulo: 'Minhas doações',         href: 'doacoes/index.html' }, /* UC19 (Módulo 4); a tela tem o botão para as solicitações de doação (Módulo 7) */
    { chave: 'solicitacoes_doacao',  rotulo: 'Solicitações de doação', href: 'doacoes/solicitacoes.html' }, /* Módulo 7, DP-80 */
    { chave: 'minhas_solicitacoes',   rotulo: 'Minhas solicitações',    href: 'solicitacoes/index.html' }, /* UC09, UC20 (Módulo 4) */
    { chave: 'solicitacoes',          rotulo: 'Solicitações',           href: 'avaliacao/index.html' }, /* UC10, UC11 (Módulo 4) */
    { chave: 'equipamentos',          rotulo: 'Equipamentos',           href: 'equipamentos/index.html' }, /* UC07, UC08 (Módulo 3) */
    { chave: 'categorias',            rotulo: 'Categorias',             href: 'categorias/index.html' }, /* UC05 (Módulo 3) */
    { chave: 'vendas',                rotulo: 'Vendas',                 href: 'vendas/index.html' }, /* UC14 a UC16, UC21 (Módulo 5) */
    { chave: 'notas_fiscais',         rotulo: 'Notas fiscais',          href: 'notas-fiscais/index.html' }, /* UC17 (Módulo 5) */
    { chave: 'organizacoes',          rotulo: 'Organizações',           href: 'organizacoes/index.html' }, /* UC01, UC25 (Módulo 2) */
    { chave: 'parceiros',             rotulo: 'Parceiros',              href: 'parceiros/index.html' }, /* UC06 (Módulo 2) */
    { chave: 'usuarios',              rotulo: 'Usuários',               href: 'usuarios/index.html' }, /* UC02, UC26, UC27 (Módulo 1) */
    { chave: 'usuarios_organizacao',  rotulo: 'Usuários da organização', href: 'usuarios/organizacao.html' }, /* UC03, UC26 (Módulo 1) */
    { chave: 'meu_perfil',          rotulo: 'Meu perfil',             href: 'perfil/index.html' }, /* UC02, UC03, UC06, DP-93 a DP-99: todos os perfis (DP-101, DP-102) */
    { chave: 'relatorios',            rotulo: 'Relatórios',             href: 'relatorios/index.html' }  /* UC22 a UC24 (Módulo 6) */
  ];

  /* Bases absolutas no servidor: APP = .../app/ e RAIZ = .../ (independe da subpasta da tela). */
  var _p = global.location.pathname;
  var _i = _p.indexOf('/app/');
  var RAIZ = _i >= 0 ? _p.substring(0, _i + 1) : _p.substring(0, _p.lastIndexOf('/') + 1);
  var APP = RAIZ + 'app/';

  function esc(t) {
    var d = document.createElement('div');
    d.textContent = t == null ? '' : String(t);
    return d.innerHTML;
  }

  function montar(usuario, chaveAtiva) {
    var permitidas = usuario.funcionalidades || [];
    var raiz = document.getElementById('app-cabecalho');
    var itens = '<li class="nav-item"><a class="nav-link' + (chaveAtiva === 'inicio' ? ' active' : '') +
      '" href="' + APP + 'inicio.html"' + (chaveAtiva === 'inicio' ? ' aria-current="page"' : '') + '>Início</a></li>';

    /* Itens permitidos ao perfil. Com mais de LIMITE itens, o excedente vai para o menu "Mais"
       (evita estourar ou quebrar linha entre 1200 e 1400 px com o perfil Administrador). */
    var LIMITE = 3;
    var visiveis = MENU.map(function (m, i) { return { m: m, i: i }; })
      .filter(function (x) { return permitidas.indexOf(x.m.chave) !== -1; }) /* esconde o não permitido (RN01) */
      .sort(function (a, b) { return (a.m.href ? 0 : 1) - (b.m.href ? 0 : 1) || a.i - b.i; }) /* itens com tela primeiro; "Em breve" vão para "Mais" */
      .map(function (x) { return x.m; });
    /* P-03: 'Meu perfil' fica fixo ao lado do usuário, nunca em "Mais". */
    var fixo = visiveis.filter(function (m) { return m.chave === 'meu_perfil'; })[0];
    if (fixo) { visiveis = visiveis.filter(function (m) { return m !== fixo; }); }
    function item(m, emDropdown) {
      var ativo = chaveAtiva === m.chave;
      var cls = emDropdown ? 'dropdown-item' : 'nav-link';
      var html;
      if (m.href) {
        html = '<a class="' + cls + (ativo ? ' active' : '') + '" href="' + esc(APP + m.href) + '"' +
          (ativo ? ' aria-current="page"' : '') + '>' + esc(m.rotulo) + '</a>';
      } else {
        /* Selo "Em breve" só no dropdown; no nível superior fica só o texto (economiza largura). */
        html = '<span class="' + cls + ' item-em-breve" aria-disabled="true"' + (emDropdown ? '' : ' title="Em breve"') + '>' +
          esc(m.rotulo) + (emDropdown ? '&nbsp;<span class="badge badge-acento">Em breve</span>' : '<span class="visually-hidden"> (em breve)</span>') + '</span>';
      }
      return '<li' + (emDropdown ? '' : ' class="nav-item"') + '>' + html + '</li>';
    }
    var principais = visiveis.length > LIMITE + 1 ? visiveis.slice(0, LIMITE) : visiveis;
    var extras = visiveis.slice(principais.length);
    principais.forEach(function (m) { itens += item(m, false); });
    if (extras.length) {
      var algumAtivo = extras.some(function (m) { return m.chave === chaveAtiva; });
      itens += '<li class="nav-item dropdown"><a class="nav-link dropdown-toggle' + (algumAtivo ? ' active' : '') +
        '" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">Mais</a>' +
        '<ul class="dropdown-menu dropdown-menu-end">' + extras.map(function (m) { return item(m, true); }).join('') + '</ul></li>';
    }

    raiz.innerHTML =
      '<nav class="navbar navbar-expand-xl navbar-dark bg-leaf-dark" aria-label="Menu principal">' +
        '<div class="container-fluid">' +
          '<a class="navbar-brand d-flex align-items-center gap-2" href="' + APP + 'inicio.html">' +
            '<img src="' + RAIZ + 'images/logosemfundo-claro.png" alt="" width="32" height="32">' +
            '<span>LEAF TI</span></a>' +
          '<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#menu-principal" ' +
            'aria-controls="menu-principal" aria-expanded="false" aria-label="Abrir ou fechar o menu">' +
            '<span class="navbar-toggler-icon"></span></button>' +
          '<div class="collapse navbar-collapse" id="menu-principal">' +
            '<ul class="navbar-nav me-auto mb-2 mb-xl-0">' + itens + '</ul>' +
            '<div class="bloco-usuario d-flex flex-column flex-xl-row align-items-xl-center gap-2 gap-xl-3 pb-2 pb-xl-0">' +
              (fixo ? '<a class="nav-link text-white text-nowrap px-0 px-xl-2' + (chaveAtiva === 'meu_perfil' ? ' active fw-bold' : '') + '" id="link-meu-perfil" href="' + esc(APP + fixo.href) + '"' + (chaveAtiva === 'meu_perfil' ? ' aria-current="page"' : '') + '>' + esc(fixo.rotulo) + '</a>' : '') +
              '<div class="usuario-info text-xl-end">' +
                '<div class="fw-semibold text-truncate" id="usuario-nome" title="' + esc(usuario.nome) + '">' + esc(usuario.nome) + '</div>' +
                '<div class="text-truncate" id="usuario-perfil">' + esc(usuario.perfil) + '</div>' +
              '</div>' +
              /* DP-99: quem tem 'meu_perfil' exclui a conta pela tela Meu perfil; Administrador e Funcionário mantêm o botão no menu (DP-64, DP-102). */
              ((permitidas.indexOf('meu_perfil') === -1 || usuario.perfil === 'Administrador' || usuario.perfil === 'Funcionário') ? '<button type="button" class="btn btn-sair fw-semibold" id="btn-excluir-conta">Excluir minha conta</button>' : '') +
              '<button type="button" class="btn btn-sair fw-semibold" id="btn-sair">Sair</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</nav>';

    document.getElementById('btn-sair').addEventListener('click', function () { Api.sair(); });
    montarExclusaoConta();
  }

  /* Pedido 2, DP-88: componente js/senha-olho.js; carrega se a pagina nao o incluiu e aplica ao modal. */
  function carregarSenhaOlho() {
    if (global.SenhaOlho) { global.SenhaOlho.aplicar(document.body); return; }
    if (global.__senhaOlhoCarregando) { return; } /* evita carregar duas vezes */
    global.__senhaOlhoCarregando = true;
    var s = document.createElement('script');
    s.src = RAIZ + 'js/senha-olho.js';
    s.onload = function () { if (global.SenhaOlho) { global.SenhaOlho.aplicar(document.body); } };
    document.head.appendChild(s);
  }

  /* Excluir a própria conta: UC02 FA3 ampliado; DP-64, DP-65, DP-66. Todos os perfis.
     Modal pede a senha atual e confirmação explícita; DELETE /usuarios/me com { senha }. */
  function montarExclusaoConta() {
    var m = document.createElement('div');
    m.innerHTML =
      '<div class="modal fade" id="modal-excluir-conta" tabindex="-1" aria-labelledby="modal-excluir-conta-titulo" aria-hidden="true">' +
        '<div class="modal-dialog modal-dialog-centered"><div class="modal-content"><form id="form-excluir-conta" novalidate>' +
          '<div class="modal-header"><h2 class="modal-title h4" id="modal-excluir-conta-titulo">Excluir minha conta</h2>' +
            '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button></div>' +
          '<div class="modal-body">' +
            '<div id="msg-excluir-conta" class="alert alert-danger d-none" role="alert" tabindex="-1"></div>' +
            '<p>Sua conta será excluída definitivamente e você perderá o acesso. Esta ação não pode ser desfeita.</p>' +
            '<label class="form-label" for="senha-excluir-conta">Senha atual <span aria-hidden="true">*</span></label>' +
            '<input type="password" class="form-control" id="senha-excluir-conta" maxlength="128" autocomplete="current-password" aria-describedby="senha-excluir-conta-erro" required>' +
            '<div id="senha-excluir-conta-erro" class="invalid-feedback"></div>' +
            '<div class="form-check mt-3"><input class="form-check-input" type="checkbox" id="confirma-excluir-conta">' +
              '<label class="form-check-label" for="confirma-excluir-conta">Entendo que a exclusão é definitiva.</label></div>' +
          '</div>' +
          '<div class="modal-footer"><button type="button" class="btn btn-outline-leaf fw-semibold" data-bs-dismiss="modal">Cancelar</button>' +
            '<button type="submit" class="btn btn-success fw-semibold" id="btn-confirmar-excluir-conta">Sim, excluir minha conta</button></div>' +
        '</form></div></div></div>';
    document.body.appendChild(m.firstChild);
    carregarSenhaOlho(); /* Pedido 2, DP-88: olho no campo de senha do modal */
    var el = document.getElementById('modal-excluir-conta');
    var modal = new bootstrap.Modal(el);
    var senha = document.getElementById('senha-excluir-conta'), conf = document.getElementById('confirma-excluir-conta');
    var msg = document.getElementById('msg-excluir-conta'), erroSenha = document.getElementById('senha-excluir-conta-erro');
    var btn = document.getElementById('btn-confirmar-excluir-conta');
    function erro(texto, noCampo) {
      if (noCampo) { senha.classList.add('is-invalid'); erroSenha.textContent = texto; senha.focus(); }
      else { msg.textContent = texto; msg.classList.remove('d-none'); msg.focus(); }
    }
    var gatilho = null;
    function abrir(origem) {
      gatilho = origem || document.getElementById('btn-excluir-conta');
      document.getElementById('form-excluir-conta').reset();
      senha.classList.remove('is-invalid'); msg.classList.add('d-none'); btn.disabled = false;
      modal.show();
    }
    global.Layout.abrirExclusaoConta = abrir; /* usado pela tela Meu perfil (DP-99) */
    var btnMenu = document.getElementById('btn-excluir-conta');
    if (btnMenu) { btnMenu.addEventListener('click', function () { abrir(btnMenu); }); }
    el.addEventListener('shown.bs.modal', function () { senha.focus(); });
    el.addEventListener('hidden.bs.modal', function () { if (gatilho) { gatilho.focus(); } });
    document.getElementById('form-excluir-conta').addEventListener('submit', async function (e) {
      e.preventDefault();
      senha.classList.remove('is-invalid'); msg.classList.add('d-none');
      if (!senha.value) { erro('Informe a senha atual.', true); return; }
      if (!conf.checked) { erro('Marque a confirmação para excluir a conta.', false); return; }
      btn.disabled = true;
      try {
        await Api.delete('/usuarios/me', { senha: senha.value }, { semRedirecionar: true }); /* 401 aqui é SENHA_INVALIDA */
        Api.sessao.limpar();
        sessionStorage.setItem('leafti.aviso_inicio', 'Conta excluída.');
        global.location.replace(RAIZ + 'index.html');
      } catch (err) {
        btn.disabled = false;
        if (err.codigo === 'SENHA_INVALIDA') { erro('Senha incorreta. Tente novamente.', true); }
        else if (err.status === 401) { Api.sessao.limpar(); global.location.replace(Api.urlLogin()); }
        else { erro(err.mensagem, false); } /* ALTERACAO_BLOQUEADA (última conta Administrador) e demais */
      }
    });
  }

  /* Só mostra o conteúdo se o perfil tiver a funcionalidade da página (RN01); 'inicio' é livre. */
  function autorizado(usuario, chave) {
    return !chave || chave === 'inicio' || (usuario.funcionalidades || []).indexOf(chave) !== -1;
  }

  var Layout = {
    MENU: MENU,
    iniciar: async function (opcoes) {
      opcoes = opcoes || {};
      var chave = opcoes.chave || 'inicio';
      var conteudo = document.getElementById('conteudo-app');

      /* Guarda de rota (RNF05): sem token, volta ao login. */
      if (!Api.sessao.ativa()) { global.location.replace(Api.urlLogin()); return new Promise(function () {}); }

      var usuario;
      try {
        usuario = await Api.me(); /* 401 -> Api redireciona; 403 CONTA_INATIVA tratado abaixo */
      } catch (err) {
        if (err.status === 401) { return new Promise(function () {}); }
        Api.sessao.limpar();
        sessionStorage.setItem('leafti.aviso', err.mensagem);
        global.location.replace(Api.urlLogin());
        return new Promise(function () {});
      }

      montar(usuario, chave);
      if (!autorizado(usuario, chave)) {
        conteudo.innerHTML = '<div class="alert alert-danger" role="alert">Você não tem permissão para acessar esta tela.</div>';
      }
      conteudo.hidden = false;
      carregarSenhaOlho(); /* Pedido 2, DP-88: olho em TODA tela interna (usuarios/index, organizacao...) */
      return usuario;
    }
  };

  global.Layout = Layout;
})(window);
