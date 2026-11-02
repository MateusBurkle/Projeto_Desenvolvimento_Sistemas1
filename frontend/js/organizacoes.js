/* Tela app/organizacoes/index.html. UC01 (include UC25); RF03, RF06, RF09; RN03, RN06, RN09; RNF04, RNF05.
   Rotas do contrato modulo-2: GET/POST /organizacoes, GET/PUT /organizacoes/{id},
   PATCH /organizacoes/{id}/contato, PATCH /organizacoes/{id}/situacao. Tudo via Api (js/api.js).
   Exclusão (DP-63, substitui DP-25): DELETE /organizacoes/{id}, só Administrador, com confirmação explícita;
   desativar continua disponível (UC01 FA2, RN06).
   Mostrar/esconder é conveniência; a segurança real é do back-end. */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';
  var U = UsuariosUi, O = OrgUi;
  var TAMANHO = 10;

  var $ = function (id) { return document.getElementById(id); };
  var msgPagina = $('mensagem');
  var f = { nome: $('f-nome'), cnpj: $('f-cnpj'), tipo: $('f-tipo'), telefone: $('f-telefone'), email: $('f-email'),
            endereco: $('f-endereco'), situacao: $('f-situacao') };
  /* nomes dos campos da API (= colunas do banco) -> inputs */
  var mapaApi = { nome_razao_social: f.nome, cnpj: f.cnpj, tipo: f.tipo, telefone: f.telefone, email: f.email,
                  endereco: f.endereco, situacao: f.situacao };
  var form = $('form-org');
  var modalForm = new bootstrap.Modal($('modal-form'));
  var modalSituacao = new bootstrap.Modal($('modal-situacao'));
  var modalExcluir = new bootstrap.Modal($('modal-excluir'));

  /* modo do formulário: 'criar' | 'editar' (Administrador, PUT) | 'contato' (Funcionário, PATCH) | 'leitura' */
  var estado = { me: null, admin: false, pagina: 1, filtros: {}, editando: null, modo: 'criar', alvoSituacao: null, itens: {} };

  Layout.iniciar({ chave: 'organizacoes' }).then(function (me) {
    if (!$('area-org')) { return; } /* sem permissão: o layout já mostrou a mensagem */
    estado.me = me;
    estado.admin = me.perfil === 'Administrador';
    $('btn-novo').hidden = !estado.admin;          /* RF06: cadastro é do Administrador */
    $('aviso-perfil').hidden = estado.admin;
    carregar(1);
  });

  /* máscaras opcionais (UC25: CNPJ com ou sem máscara) */
  f.cnpj.addEventListener('input', function () { f.cnpj.value = O.mascararCnpj(f.cnpj.value); });
  f.telefone.addEventListener('input', function () { f.telefone.value = O.mascararTelefone(f.telefone.value); });

  /* ---------- listagem (UC01 FA1) ---------- */
  function contatoEditavelPeloFuncionario(o) { return o.tipo !== 'Empresa Doadora'; } /* RF09, DP-26 */

  function botoes(o) {
    var nome = U.esc(o.nome_razao_social), id = o.id_organizacao;
    if (estado.admin) {
      var desativar = o.situacao === 'Ativa';
      return '<button type="button" class="btn btn-outline-leaf" data-acao="editar" data-id="' + id + '" aria-label="Editar ' + nome + '">Editar</button>' +
        '<button type="button" class="btn btn-acao-situacao" data-acao="situacao" data-id="' + id + '" aria-label="' + (desativar ? 'Desativar ' : 'Reativar ') + nome + '">' + (desativar ? 'Desativar' : 'Reativar') + '</button>' +
        '<button type="button" class="btn btn-outline-leaf" data-acao="excluir" data-id="' + id + '" aria-label="Excluir ' + nome + '">Excluir</button>';
    }
    if (contatoEditavelPeloFuncionario(o)) {
      return '<button type="button" class="btn btn-outline-leaf" data-acao="editar" data-id="' + id + '" aria-label="Editar contato de ' + nome + '">Editar contato</button>';
    }
    return '<button type="button" class="btn btn-outline-leaf" data-acao="ver" data-id="' + id + '" aria-label="Consultar ' + nome + ' (somente leitura)">Consultar</button>';
  }

  function linhaHtml(o) {
    return '<tr>' +
      '<td data-rotulo="Nome"><strong>' + U.esc(o.nome_razao_social) + '</strong>' + (o.possui_parceria ? ' <span class="badge-voce">Com parceria</span>' : '') + '</td>' +
      '<td data-rotulo="CNPJ">' + U.esc(O.formatarCnpj(o.cnpj)) + '</td>' +
      '<td data-rotulo="Tipo">' + U.esc(o.tipo) + '</td>' +
      '<td data-rotulo="Contato">' + '<span class="nw">' + U.esc(O.formatarTelefone(o.telefone)) + '</span><span class="sub">' + U.esc(o.email) + '</span></td>' +
      '<td data-rotulo="Situação">' + O.seloSituacao(o.situacao) + '</td>' +
      '<td class="acoes">' + botoes(o) + '</td></tr>';
  }

  async function carregar(pagina) {
    var q = ['page=' + pagina, 'size=' + TAMANHO];
    var fl = estado.filtros;
    if (fl.tipo) { q.push('tipo=' + encodeURIComponent(fl.tipo)); }
    if (fl.situacao) { q.push('situacao=' + encodeURIComponent(fl.situacao)); }
    if (fl.q) { q.push('q=' + encodeURIComponent(fl.q)); }
    $('estado-lista').textContent = 'Carregando...';
    $('estado-lista').hidden = false;
    try {
      var p = await Api.get('/organizacoes?' + q.join('&'));
      if (p.items.length === 0 && p.total > 0 && pagina > 1) { return carregar(pagina - 1); }
      estado.pagina = p.page;
      estado.itens = {};
      p.items.forEach(function (o) { estado.itens[o.id_organizacao] = o; });
      $('corpo-tabela').innerHTML = p.items.map(linhaHtml).join('');
      $('tabela').hidden = p.items.length === 0;
      $('paginacao').hidden = p.total === 0;
      if (p.items.length === 0) {
        $('estado-lista').textContent = 'Nenhuma organização encontrada' + (fl.tipo || fl.situacao || fl.q ? ' para os filtros informados.' : '.');
      } else {
        $('estado-lista').hidden = true;
      }
      $('texto-pagina').textContent = O.textoPagina(p, 'organização', 'organizações');
      $('btn-anterior').disabled = p.page <= 1;
      $('btn-proxima').disabled = p.page * p.size >= p.total;
    } catch (err) {
      $('tabela').hidden = true; $('paginacao').hidden = true;
      $('estado-lista').textContent = 'Não foi possível carregar a lista.';
      U.mostrar(msgPagina, 'erro', U.esc(O.msgErro(err)));
    }
  }

  $('form-filtros').addEventListener('submit', function (e) {
    e.preventDefault();
    estado.filtros = { q: $('filtro-q').value.trim(), tipo: $('filtro-tipo').value, situacao: $('filtro-situacao').value };
    U.ocultar(msgPagina);
    carregar(1);
  });
  $('btn-limpar').addEventListener('click', function () {
    $('form-filtros').reset(); estado.filtros = {}; U.ocultar(msgPagina); carregar(1); $('filtro-q').focus();
  });
  $('btn-anterior').addEventListener('click', function () { carregar(estado.pagina - 1); });
  $('btn-proxima').addEventListener('click', function () { carregar(estado.pagina + 1); });

  $('corpo-tabela').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-acao]');
    if (!b) { return; }
    var id = Number(b.getAttribute('data-id'));
    var acao = b.getAttribute('data-acao');
    if (acao === 'situacao') { abrirSituacao(id); } else if (acao === 'excluir') { abrirExclusao(id); } else { abrirEdicao(id, acao === 'ver'); }
  });

  /* ---------- foco: devolvido ao elemento que abriu o modal (RNF06) ---------- */
  var abridor = null;
  function guardarAbridor(el) { abridor = el || document.activeElement; }
  function devolverFoco() {
    var el = abridor; abridor = null;
    if (!el || !document.body.contains(el) || el.disabled || el.offsetParent === null) {
      var a = el && el.getAttribute && el.getAttribute('data-acao'), i = el && el.getAttribute && el.getAttribute('data-id');
      var alt = a && i ? document.querySelector('button[data-acao="' + a + '"][data-id="' + i + '"]') : null;
      el = alt || (!$('btn-novo').hidden ? $('btn-novo') : $('filtro-q'));
    }
    el.focus();
  }
  $('modal-form').addEventListener('hidden.bs.modal', devolverFoco);
  $('modal-situacao').addEventListener('hidden.bs.modal', devolverFoco);
  $('modal-excluir').addEventListener('hidden.bs.modal', devolverFoco);

  /* ---------- formulário (UC01 passos 1 a 5, FA1, FA3) ---------- */
  function definirModo(modo, o) {
    estado.modo = modo;
    var tudoLeitura = modo === 'leitura';
    var soContato = modo === 'contato';
    ['nome', 'cnpj'].forEach(function (k) { f[k].readOnly = tudoLeitura || soContato; });
    f.tipo.disabled = tudoLeitura || soContato;
    ['telefone', 'email', 'endereco'].forEach(function (k) { f[k].readOnly = tudoLeitura; });
    $('bloco-situacao-nova').hidden = modo !== 'criar';
    $('bloco-situacao-atual').hidden = modo === 'criar';
    if (o) { $('situacao-atual').innerHTML = O.seloSituacao(o.situacao); }
    $('btn-salvar').hidden = tudoLeitura;
    $('btn-cancelar').textContent = tudoLeitura ? 'Fechar' : 'Cancelar';
    var dica = $('dica-form');
    dica.hidden = !(soContato || tudoLeitura);
    dica.textContent = tudoLeitura
      ? 'Empresa Doadora: o Funcionário apenas consulta. Alterações são feitas pelo Administrador.'
      : (soContato ? 'Você pode alterar apenas telefone, e-mail e endereço. Os demais campos são exclusivos do Administrador.' : '');
    $('modal-form-titulo').textContent = modo === 'criar' ? 'Novo cadastro' : (tudoLeitura ? 'Consultar organização' : (soContato ? 'Editar contato' : 'Editar organização'));
  }

  function prepararForm(modo, o) {
    estado.editando = o || null;
    form.reset();
    U.limparErros(form);
    U.ocultar($('msg-form'));
    $('btn-salvar').disabled = false; $('btn-salvar').textContent = 'Salvar';
    definirModo(modo, o);
    if (o) {
      f.nome.value = o.nome_razao_social; f.cnpj.value = O.formatarCnpj(o.cnpj); f.tipo.value = o.tipo;
      f.telefone.value = O.formatarTelefone(o.telefone); f.email.value = o.email; f.endereco.value = o.endereco;
    } else {
      f.situacao.value = 'Ativa';
    }
  }

  $('btn-novo').addEventListener('click', function () {
    guardarAbridor(this);
    U.ocultar(msgPagina);
    prepararForm('criar', null);
    modalForm.show();
  });
  $('modal-form').addEventListener('shown.bs.modal', function () {
    var primeiro = form.querySelector('input:not([readonly]):not([disabled]), select:not([disabled])');
    if (estado.modo === 'leitura') { $('btn-cancelar').focus(); } else if (primeiro) { primeiro.focus(); }
  });

  async function abrirEdicao(id, soVer) {
    guardarAbridor();
    U.ocultar(msgPagina);
    try {
      var o = await Api.get('/organizacoes/' + id); /* UC01 FA1: dados atuais */
      var modo = soVer ? 'leitura' : (estado.admin ? 'editar' : (contatoEditavelPeloFuncionario(o) ? 'contato' : 'leitura'));
      prepararForm(modo, o);
      modalForm.show();
    } catch (err) {
      U.mostrar(msgPagina, 'erro', U.esc(O.msgErro(err)));
      msgPagina.focus();
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (estado.modo === 'leitura') { return; }
    U.limparErros(form); U.ocultar($('msg-form'));
    var modo = estado.modo;
    var v = { nome_razao_social: f.nome.value, cnpj: f.cnpj.value, tipo: f.tipo.value, telefone: f.telefone.value,
              email: f.email.value, endereco: f.endereco.value };

    /* Validação no cliente (RNF04; UC01 FE2; UC25 formato do CNPJ) */
    var erros = O.validar(v, { soContato: modo === 'contato' });
    var chaves = Object.keys(erros);
    if (chaves.length) {
      chaves.forEach(function (k) { U.erroCampo(mapaApi[k], erros[k]); });
      U.mostrar($('msg-form'), 'erro', 'Corrija os campos indicados e tente novamente.');
      var primeiro = form.querySelector('.is-invalid'); if (primeiro) { primeiro.focus(); }
      return;
    }

    var contato = { telefone: O.digitos(v.telefone), email: v.email.trim().toLowerCase(), endereco: v.endereco.trim() };
    var completo = { nome_razao_social: v.nome_razao_social.trim(), cnpj: O.digitos(v.cnpj), tipo: v.tipo,
                     telefone: contato.telefone, email: contato.email, endereco: contato.endereco };
    var btn = $('btn-salvar');
    btn.disabled = true; btn.textContent = 'Salvando...';
    try {
      var salvo, texto;
      if (modo === 'criar') {
        completo.situacao = f.situacao.value;
        salvo = await Api.post('/organizacoes', completo);
        texto = 'Organização <strong>' + U.esc(salvo.nome_razao_social) + '</strong> cadastrada com sucesso.';
      } else if (modo === 'editar') {
        salvo = await Api.put('/organizacoes/' + estado.editando.id_organizacao, completo);
        texto = 'Organização <strong>' + U.esc(salvo.nome_razao_social) + '</strong> atualizada com sucesso.';
      } else {
        salvo = await Api.patch('/organizacoes/' + estado.editando.id_organizacao + '/contato', contato);
        texto = 'Contato de <strong>' + U.esc(salvo.nome_razao_social) + '</strong> atualizado com sucesso.';
      }
      modalForm.hide();
      U.mostrar(msgPagina, 'sucesso', texto);
      await carregar(modo === 'criar' ? 1 : estado.pagina);
    } catch (err) {
      btn.disabled = false; btn.textContent = 'Salvar';
      /* DADOS_INVALIDOS / CNPJ_DUPLICADO (campos.cnpj) / TIPO_EM_USO (campos.tipo, se vier) */
      var marcou = U.aplicarCamposDaApi(err, mapaApi);
      if (!marcou && err.codigo === 'CNPJ_DUPLICADO') { U.erroCampo(f.cnpj, 'Este CNPJ já está cadastrado.'); marcou = true; }
      if (!marcou && err.codigo === 'TIPO_EM_USO') { U.erroCampo(f.tipo, 'O tipo não pode ser alterado: há usuários ou parceria vinculados.'); marcou = true; }
      U.mostrar($('msg-form'), 'erro', U.esc(O.msgErro(err)));
      var inv = form.querySelector('.is-invalid');
      if (inv && marcou) { inv.focus(); } else { $('msg-form').focus(); }
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  });

  /* ---------- desativar / reativar com confirmação (UC01 FA2; RN06) ---------- */
  function abrirSituacao(id) {
    guardarAbridor();
    U.ocultar(msgPagina);
    var o = estado.itens[id];
    if (!o) { return; }
    var desativar = o.situacao === 'Ativa';
    estado.alvoSituacao = { id: id, nova: desativar ? 'Inativa' : 'Ativa', nome: o.nome_razao_social };
    $('modal-situacao-titulo').textContent = desativar ? 'Desativar organização' : 'Reativar organização';
    $('modal-situacao-texto').innerHTML = desativar
      ? 'Deseja realmente desativar <strong>' + U.esc(o.nome_razao_social) + '</strong>? Os dados são preservados, mas os usuários da organização perdem o acesso e novas operações ficam bloqueadas até a reativação.'
      : 'Deseja reativar <strong>' + U.esc(o.nome_razao_social) + '</strong>? Os usuários da organização voltam a ter acesso.';
    U.ocultar($('msg-situacao'));
    $('btn-confirmar-situacao').disabled = false;
    $('btn-confirmar-situacao').textContent = desativar ? 'Sim, desativar' : 'Sim, reativar';
    modalSituacao.show();
  }
  $('modal-situacao').addEventListener('shown.bs.modal', function () { $('btn-nao-situacao').focus(); });

  $('btn-confirmar-situacao').addEventListener('click', async function () {
    var btn = this, alvo = estado.alvoSituacao, rotulo = btn.textContent;
    btn.disabled = true; btn.textContent = 'Aguarde...';
    try {
      await Api.patch('/organizacoes/' + alvo.id + '/situacao', { situacao: alvo.nova });
      modalSituacao.hide();
      U.mostrar(msgPagina, 'sucesso', 'Organização <strong>' + U.esc(alvo.nome) + '</strong> ' + (alvo.nova === 'Inativa' ? 'desativada' : 'reativada') + ' com sucesso.');
      await carregar(estado.pagina);
    } catch (err) {
      btn.disabled = false; btn.textContent = rotulo;
      U.mostrar($('msg-situacao'), 'erro', U.esc(O.msgErro(err)));
      $('msg-situacao').focus();
      if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
    }
  });

  /* ---------- excluir com confirmação explícita (DP-63; UC01, UC25) ---------- */
  var alvoExcluir = null;
  function abrirExclusao(id) {
    guardarAbridor();
    U.ocultar(msgPagina);
    var o = estado.itens[id];
    if (!o) { return; }
    alvoExcluir = { id: id, nome: o.nome_razao_social, excluirUsuarios: false };
    $('modal-excluir-texto').innerHTML = 'Deseja realmente excluir <strong>' + U.esc(o.nome_razao_social) + '</strong>' +
      (o.possui_parceria ? ' e a parceria dela' : '') + '? Esta ação é definitiva e não pode ser desfeita.';
    $('bloco-lista-usuarios').hidden = true; $('lista-usuarios-excluir').textContent = '';
    $('bloco-excluir-usuarios').hidden = true; $('chk-excluir-usuarios').checked = false;
    U.ocultar($('msg-excluir'));
    $('btn-confirmar-excluir').disabled = false;
    modalExcluir.show();
  }
  $('modal-excluir').addEventListener('shown.bs.modal', function () { $('btn-nao-excluir').focus(); });

  $('btn-confirmar-excluir').addEventListener('click', async function () {
    var btn = this, alvo = alvoExcluir;
    U.ocultar($('msg-excluir'));
    if (alvo.excluirUsuarios && !$('chk-excluir-usuarios').checked) {
      U.mostrar($('msg-excluir'), 'erro', 'Marque a confirmação para excluir também os usuários.');
      $('msg-excluir').focus();
      return;
    }
    btn.disabled = true;
    try {
      await Api.delete('/organizacoes/' + alvo.id + (alvo.excluirUsuarios ? '?excluir_usuarios=true' : ''));
      modalExcluir.hide();
      U.mostrar(msgPagina, 'sucesso', 'Organização <strong>' + U.esc(alvo.nome) + '</strong> excluída com sucesso.');
      await carregar(estado.pagina);
    } catch (err) {
      btn.disabled = false;
      if (err.codigo === 'ORGANIZACAO_EM_USO') { /* histórico: Desativar continua disponível */
        U.mostrar($('msg-excluir'), 'erro', 'Esta organização tem histórico e não pode ser excluída; você pode desativá-la.');
      } else if (err.codigo === 'ORGANIZACAO_COM_USUARIOS') {
        var n = err.campos && err.campos.quantidade_usuarios;
        alvo.excluirUsuarios = true;
        var qtd = n != null ? n + (Number(n) === 1 ? ' usuário vinculado' : ' usuários vinculados') : 'os usuários vinculados';
        $('lbl-excluir-usuarios').textContent = 'Excluir também ' + qtd + ' a esta organização.';
        $('bloco-excluir-usuarios').hidden = false;
        var us = (err.campos && err.campos.usuarios) || [];
        var ul = $('lista-usuarios-excluir');
        ul.textContent = '';
        us.forEach(function (u) {
          var li = document.createElement('li');
          li.className = 'list-group-item';
          var nm = document.createElement('strong'); nm.textContent = u.nome;
          li.appendChild(nm);
          li.appendChild(document.createElement('br'));
          li.appendChild(document.createTextNode((u.email || '') + ' - ' + (u.perfil || '')));
          ul.appendChild(li);
        });
        $('titulo-lista-usuarios').textContent = 'Serão excluídos ' + (n != null ? n : us.length) + ' usuário(s):';
        $('bloco-lista-usuarios').hidden = !us.length;
        U.mostrar($('msg-excluir'), 'erro', 'Esta organização tem ' + qtd + '. Para excluí-la, confirme a exclusão deles também.');
        $('chk-excluir-usuarios').focus();
        return;
      } else if (err.codigo === 'ALTERACAO_BLOQUEADA') {
        U.mostrar($('msg-excluir'), 'erro', 'Não é possível excluir: a exclusão removeria o único Administrador.');
      } else {
        U.mostrar($('msg-excluir'), 'erro', U.esc(O.msgErro(err)));
        if (err.codigo === 'NAO_ENCONTRADO') { carregar(estado.pagina); }
      }
      $('msg-excluir').focus();
    }
  });
});
