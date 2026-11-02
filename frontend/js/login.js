/* Tela de login. UC04 (Acessar o sistema) e UC28 (Validar credenciais); RF01, RN01, RNF04.
   Fluxo principal: valida campos, POST /auth/login via Api.login, abre app/inicio.html.
   FE1 (CREDENCIAIS_INVALIDAS) e FE2 (CONTA_INATIVA): mostra mensagem e não inicia sessão.
   DADOS_INVALIDOS: erro por campo (RNF04).
   Marketplace (DP-68): ?retorno=<caminho relativo> leva de volta ao produto após o login; só caminho relativo
   de página .html (Publico.retornoSeguro rejeita http://, //, javascript:, barra invertida: open redirect). */
document.addEventListener('DOMContentLoaded', function () {
  var form = document.getElementById('login-form');
  var aviso = document.getElementById('aviso');
  var btn = document.getElementById('btn-entrar');
  var campos = { email: document.getElementById('email'), senha: document.getElementById('senha') };

  var MSG = {
    CREDENCIAIS_INVALIDAS: 'Não foi possível entrar. Verifique o e-mail e a senha.',
    CONTA_INATIVA: 'Acesso negado. A conta ou a organização está inativa.',
    DADOS_INVALIDOS: 'Informe um e-mail válido e a senha.'
  };

  /* tipo 'erro' (padrão): .alert-danger vermelho escuro; 'aviso': .alert-warning amarelo (não crítico). */
  function mostrarAviso(texto, tipo) {
    aviso.classList.remove('alert-danger', 'alert-warning');
    aviso.classList.add(tipo === 'aviso' ? 'alert-warning' : 'alert-danger');
    aviso.textContent = texto;
    aviso.classList.remove('d-none');
    aviso.focus();
  }
  function limpar() {
    aviso.classList.add('d-none');
    aviso.textContent = '';
    Object.keys(campos).forEach(function (k) {
      campos[k].classList.remove('is-invalid');
      campos[k].removeAttribute('aria-invalid');
      document.getElementById(k + '-erro').textContent = '';
    });
  }
  function erroCampo(nome, texto) {
    campos[nome].classList.add('is-invalid');
    campos[nome].setAttribute('aria-invalid', 'true');
    document.getElementById(nome + '-erro').textContent = texto;
  }

  /* Aviso deixado por sessão expirada (401). */
  var guardado = sessionStorage.getItem('leafti.aviso');
  if (guardado) { sessionStorage.removeItem('leafti.aviso'); mostrarAviso(guardado, 'aviso'); }

  /* Destino após o login: o retorno validado ou a área logada. */
  var retorno = Publico.retornoSeguro(new URLSearchParams(window.location.search).get('retorno'));
  var destino = retorno || 'app/inicio.html';

  /* Já logado: vai direto para o destino. */
  if (Api.sessao.ativa()) { window.location.replace(destino); return; }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    limpar();

    var email = campos.email.value.trim();
    var senha = campos.senha.value;

    /* Validação local (RNF04): cada erro diz o que corrigir. */
    var ok = true;
    if (!email) { erroCampo('email', 'Informe o e-mail.'); ok = false; }
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { erroCampo('email', 'Informe um e-mail válido, por exemplo nome@empresa.com.br.'); ok = false; }
    if (!senha) { erroCampo('senha', 'Informe a senha.'); ok = false; }
    if (!ok) {
      (form.querySelector('.is-invalid') || campos.email).focus();
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Entrando...';
    try {
      await Api.login(email, senha);
      window.location.href = destino;
    } catch (err) {
      Api.sessao.limpar(); /* garante que nada fica salvo em caso de falha */
      if (err.codigo === 'DADOS_INVALIDOS') {
        var nomes = Object.keys(err.campos || {});
        nomes.forEach(function (n) { if (campos[n]) { erroCampo(n, 'Campo ' + (n === 'email' ? 'e-mail' : n) + ': ' + err.campos[n] + '.'); } });
        mostrarAviso(err.mensagem || MSG.DADOS_INVALIDOS);
      } else {
        mostrarAviso(err.mensagem || MSG[err.codigo] || 'Não foi possível entrar.');
      }
      btn.disabled = false;
      btn.textContent = 'Entrar';
    }
  });
});
