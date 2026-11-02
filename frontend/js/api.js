/* js/api.js - ÚNICO ponto de acesso à API (docs/CONVENCOES.md).
   UC04 (Acessar o sistema), UC28 (Validar credenciais); RN01, RNF04, RNF05.
   Uso: Api.login(email, senha), Api.me(), Api.get/post/put/patch/delete(caminho, corpo),
        Api.baixar(caminho) (download autenticado em blob), Api.sessao.* (token e usuário), Api.sair().
   Erros: lança ApiErro { status, codigo, mensagem, campos } sempre em português.
   Segurança real é do back-end; o front só guarda o token e esconde o que não é permitido. */
(function (global) {
  'use strict';

  var BASE = '/api/v1';
  var CHAVE_TOKEN = 'leafti.token';
  var CHAVE_USUARIO = 'leafti.usuario';

  /* Mensagens padrão por código (usadas se a API não enviar "mensagem"). */
  var MENSAGENS = {
    DADOS_INVALIDOS: 'Há dados inválidos. Corrija os campos indicados.',
    SENHA_INVALIDA: 'Senha incorreta. Informe a senha atual da sua conta.',
    NAO_AUTENTICADO: 'Sessão inválida ou expirada. Entre novamente.',
    CREDENCIAIS_INVALIDAS: 'Não foi possível entrar. Verifique o e-mail e a senha.',
    SEM_PERMISSAO: 'Você não tem permissão para realizar esta ação.',
    CONTA_INATIVA: 'Acesso negado. A conta ou a organização está inativa.',
    REDE: 'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.',
    ERRO_INESPERADO: 'Ocorreu um erro inesperado. Tente novamente em instantes.'
  };

  function ApiErro(status, codigo, mensagem, campos) {
    this.name = 'ApiErro';
    this.status = status;
    this.codigo = codigo;
    this.mensagem = mensagem;
    this.message = mensagem;
    this.campos = campos || {};
  }
  ApiErro.prototype = Object.create(Error.prototype);

  /* Sessão: sessionStorage (some ao fechar a aba). Logout = descartar o token. */
  var sessao = {
    token: function () { return sessionStorage.getItem(CHAVE_TOKEN); },
    usuario: function () {
      try { return JSON.parse(sessionStorage.getItem(CHAVE_USUARIO)); } catch (e) { return null; }
    },
    salvar: function (token, usuario) {
      sessionStorage.setItem(CHAVE_TOKEN, token);
      sessionStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario));
    },
    salvarUsuario: function (usuario) {
      sessionStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario));
    },
    limpar: function () {
      sessionStorage.removeItem(CHAVE_TOKEN);
      sessionStorage.removeItem(CHAVE_USUARIO);
    },
    ativa: function () { return !!sessao.token(); }
  };

  /* Caminho da tela de login, de qualquer pasta (frontend/ ou frontend/app/...). */
  function urlLogin() {
    var p = global.location.pathname;
    var i = p.indexOf('/app/');
    return (i >= 0 ? p.substring(0, i + 1) : p.substring(0, p.lastIndexOf('/') + 1)) + 'login.html';
  }

  function irParaLogin(aviso) {
    sessao.limpar();
    if (aviso) { sessionStorage.setItem('leafti.aviso', aviso); }
    global.location.replace(urlLogin());
  }

  async function requisicao(metodo, caminho, corpo, opcoes) {
    opcoes = opcoes || {};
    var cabecalhos = { 'Accept': 'application/json' };
    var init = { method: metodo, headers: cabecalhos };
    if (typeof FormData !== 'undefined' && corpo instanceof FormData) {
      init.body = corpo; /* multipart (UC07, DP-84): sem Content-Type manual, o navegador define o boundary */
    } else if (corpo !== undefined && corpo !== null) {
      cabecalhos['Content-Type'] = 'application/json';
      init.body = JSON.stringify(corpo);
    }
    var token = sessao.token();
    if (token && !opcoes.semToken) { cabecalhos['Authorization'] = 'Bearer ' + token; }

    var resp;
    try {
      resp = await fetch(BASE + caminho, init);
    } catch (e) {
      throw new ApiErro(0, 'REDE', MENSAGENS.REDE, {});
    }

    var dados = null;
    if (resp.status !== 204) {
      try { dados = await resp.json(); } catch (e) { dados = null; }
    }
    if (resp.ok) { return dados; }

    var codigo = (dados && dados.codigo) || (resp.status === 401 ? 'NAO_AUTENTICADO' : 'ERRO_INESPERADO');
    var mensagem = (dados && typeof dados.mensagem === 'string' && dados.mensagem) ||
                   MENSAGENS[codigo] || MENSAGENS.ERRO_INESPERADO;
    var campos = (dados && dados.campos && typeof dados.campos === 'object') ? dados.campos : {};
    var erro = new ApiErro(resp.status, codigo, mensagem, campos);

    /* 401 fora do login: sessão vencida/inválida -> limpa e volta ao login. */
    if (resp.status === 401 && !opcoes.semRedirecionar) {
      irParaLogin(mensagem);
    }
    throw erro;
  }

  /* UC17 passo 5: download autenticado (fetch + blob). Devolve { blob, nome }. Erros no formato padrão. */
  async function baixarArquivo(caminho) {
    var cab = { 'Accept': 'text/html, application/json' };
    var token = sessao.token();
    if (token) { cab['Authorization'] = 'Bearer ' + token; }
    var resp;
    try { resp = await fetch(BASE + caminho, { method: 'GET', headers: cab }); }
    catch (e) { throw new ApiErro(0, 'REDE', MENSAGENS.REDE, {}); }
    if (!resp.ok) {
      var dados = null;
      try { dados = await resp.json(); } catch (e) { dados = null; }
      var codigo = (dados && dados.codigo) || (resp.status === 401 ? 'NAO_AUTENTICADO' : 'ERRO_INESPERADO');
      var mensagem = (dados && typeof dados.mensagem === 'string' && dados.mensagem) || MENSAGENS[codigo] || MENSAGENS.ERRO_INESPERADO;
      var erro = new ApiErro(resp.status, codigo, mensagem, (dados && dados.campos) || {});
      if (resp.status === 401) { irParaLogin(mensagem); }
      throw erro;
    }
    var disp = resp.headers.get('Content-Disposition') || '';
    var m = /filename="?([^";]+)"?/i.exec(disp);
    return { blob: await resp.blob(), nome: m ? m[1] : null };
  }

  var Api = {
    BASE: BASE,
    baixar: baixarArquivo,
    ApiErro: ApiErro,
    sessao: sessao,
    urlLogin: urlLogin,
    get: function (c) { return requisicao('GET', c); },
    post: function (c, b) { return requisicao('POST', c, b); },
    put: function (c, b) { return requisicao('PUT', c, b); },
    patch: function (c, b) { return requisicao('PATCH', c, b); },
    /* UC12/Marketplace (DP-68): leitura pública com token OPCIONAL. Com token válido a API pode devolver `valor`
       (Cliente Empresa); se o token estiver vencido (401), descarta a sessão e repete como visitante, sem redirecionar. */
    getPublico: async function (c) {
      try { return await requisicao('GET', c, null, { semRedirecionar: true }); }
      catch (e) {
        if (e.status === 401) { sessao.limpar(); return requisicao('GET', c, null, { semToken: true, semRedirecionar: true }); }
        throw e;
      }
    },
    /* UC07 (DP-84): envio de arquivo (multipart, campo `arquivo`) com PUT; mesmo tratamento de 401 e de erros. */
    enviarArquivo: function (c, formData) { return requisicao('PUT', c, formData); },
    /* UC07/UC12: só aceita imagem_url da API no formato /imagens/equipamentos/<nome>; senão '' (usa o ícone padrão). */
    urlImagem: function (u) {
      return (typeof u === 'string' && /^\/imagens\/equipamentos\/[0-9a-f]{32}\.(jpg|png|webp)$/.test(u)) ? BASE + u : '';
    },
    delete: function (c, b, o) { return requisicao('DELETE', c, b, o); }, /* DP-64: DELETE /usuarios/me leva a senha no corpo */

    /* UC04 / UC28: POST /auth/login. Só inicia a sessão se der certo (FE1/FE2 não iniciam). */
    login: async function (email, senha) {
      var r = await requisicao('POST', '/auth/login', { email: email, senha: senha },
                               { semToken: true, semRedirecionar: true });
      sessao.salvar(r.access_token, r.usuario);
      return r.usuario;
    },

    /* UC04 passo 4: GET /auth/me (reavalia a conta a cada chamada; RN06, RN09). */
    me: async function () {
      var u = await requisicao('GET', '/auth/me');
      sessao.salvarUsuario(u);
      return u;
    },

    /* Logout: descarta o token e volta ao login. */
    sair: function () { irParaLogin(); }
  };

  global.Api = Api;
})(window);
