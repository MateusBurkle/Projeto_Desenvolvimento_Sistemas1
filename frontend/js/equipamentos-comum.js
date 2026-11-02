/* Funções comuns às telas do Módulo 3 (categorias e equipamentos). UC05, UC07, UC08;
   RF07, RF08, RF11, RF12; RN07, RN08, RN11, RN12; RNF04, RNF06. Não faz chamadas à API (só js/api.js).
   Reaproveita UsuariosUi (js/usuarios-comum.js). Expõe o objeto global EquipUi. */
(function (global) {
  'use strict';
  var U = global.UsuariosUi;

  /* Valores exatos do contrato (modulo-3.yaml, schemas Situacao e Condicao) */
  var SITUACOES = ['Recebido', 'Em avaliação', 'Em manutenção', 'Recondicionado', 'Disponível', 'Vendido', 'Doado', 'Destinado à reciclagem'];
  var CONDICOES = ['A avaliar', 'Bom', 'Regular', 'Necessita reparo', 'Sem condições de reuso'];
  var SEM_REUSO = 'Sem condições de reuso';
  /* UC08 FE2 / RN12: com "Sem condições de reuso" só estas situações são aceitas */
  var SIT_SEM_REUSO = ['Recebido', 'Em avaliação', 'Destinado à reciclagem'];
  var FINAIS = ['Vendido', 'Doado', 'Destinado à reciclagem']; /* RF12 (M3): situações finais */

  /* Mensagens em português por código do contrato (usadas se a API não enviar "mensagem"). */
  var MSG = {
    IMAGEM_MUITO_GRANDE: 'A imagem deve ter no máximo 2 MB.',
    IMAGEM_TIPO_INVALIDO: 'Envie uma imagem JPG, PNG ou WebP.',
    DADOS_INVALIDOS: 'Há dados inválidos. Corrija os campos indicados.',
    NOME_CATEGORIA_DUPLICADO: 'Já existe uma categoria com este nome (maiúsculas e minúsculas não diferenciam).',
    IDENTIFICACAO_DUPLICADA: 'Esta identificação já está em uso por outro equipamento.',
    CATEGORIA_INVALIDA: 'A categoria escolhida não existe ou está desativada. Escolha uma categoria ativa.',
    CATEGORIA_PROTEGIDA: 'As seis categorias base não podem ser renomeadas nem desativadas.',
    ITEM_SOLICITACAO_INVALIDO: 'O item de solicitação informado não existe. Confira o número ou deixe o campo em branco.',
    ITEM_COMPLETO: 'Todas as unidades deste item de solicitação já foram cadastradas.',
    TRANSICAO_INVALIDA: 'Esta mudança de situação não é permitida para o equipamento.',
    SEM_CONDICOES_DE_REUSO: 'Equipamento sem condições de reuso só pode ficar como Recebido, Em avaliação ou Destinado à reciclagem.',
    DOACAO_INVALIDA: 'Dados da doação inválidos. Informe uma ONG ativa e uma data que não seja futura nem anterior ao recebimento.',
    EQUIPAMENTO_INATIVO: 'Equipamento inativo não pode ficar Disponível nem ser doado. Reative-o antes.',
    EQUIPAMENTO_FINALIZADO: 'Equipamentos vendidos ou doados não podem mais ser alterados nem desativados.',
    SEM_PERMISSAO: 'Você não tem permissão para realizar esta ação.',
    NAO_ENCONTRADO: 'Registro não encontrado. Ele pode ter sido removido; atualize a lista.'
  };

  /* Mensagem do erro: prefere a da API (já em português); senão a do código. */
  function msgErro(err) {
    return (err && err.mensagem) || MSG[err && err.codigo] || 'Ocorreu um erro inesperado. Tente novamente.';
  }

  function escAttr(t) { return U.esc(t).replace(/"/g, '&quot;'); }

  /* ---------- datas e valores ---------- */
  function hojeIso() {
    var d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function dataValida(iso) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || '')) { return false; }
    var p = iso.split('-'), d = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
    return d.getFullYear() === Number(p[0]) && d.getMonth() === Number(p[1]) - 1 && d.getDate() === Number(p[2]);
  }
  /* AAAA-MM-DD -> dd/mm/aaaa (a API usa ISO; a tela mostra dd/mm/aaaa) */
  function formatarData(iso) {
    if (!iso) { return '—'; }
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
    return m ? m[3] + '/' + m[2] + '/' + m[1] : String(iso);
  }
  /* R$ 1.500,00 (2 casas) */
  function formatarValor(v) {
    if (v == null || v === '') { return '—'; }
    return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function valorParaCampo(v) { return v == null ? '' : Number(v).toFixed(2).replace('.', ','); }
  /* Texto do campo -> { valor: number|null, erro: string|null }. Aceita 1500,50 / 1500.50 / 1.500,50. */
  function lerValor(texto) {
    var t = String(texto == null ? '' : texto).trim().replace(/^R\$\s*/, '');
    if (!t) { return { valor: null, erro: null }; }
    if (/^-/.test(t)) { return { valor: null, erro: 'O valor não pode ser negativo.' }; }
    var n = t.indexOf(',') !== -1 ? t.replace(/\./g, '').replace(',', '.') : t;
    if (!/^\d+(\.\d+)?$/.test(n)) { return { valor: null, erro: 'Informe um valor numérico, por exemplo 1500,00.' }; }
    if (/\.\d{3,}$/.test(n)) { return { valor: null, erro: 'O valor deve ter no máximo 2 casas decimais.' }; }
    return { valor: Number(n), erro: null };
  }

  /* ---------- selos: sempre texto + ícone (nunca só cor, RNF06) ---------- */
  var ICONE_SIT = {
    'Recebido': '▸', 'Em avaliação': '?', 'Em manutenção': '⚙', 'Recondicionado': '↻', 'Disponível': '✔',
    'Vendido': '■', 'Doado': '♥', 'Destinado à reciclagem': '♻'
  };
  function seloSituacao(s) {
    var classe = s === 'Disponível' ? 'selo-sit-ok' : (FINAIS.indexOf(s) !== -1 ? 'selo-sit-final' : 'selo-sit-proc');
    return '<span class="selo-situacao ' + classe + '">' + (ICONE_SIT[s] || '•') + '&#xFE0E; ' + U.esc(s) + '</span>';
  }
  function seloAtivo(ativo) {
    return '<span class="selo-situacao ' + (ativo ? 'selo-ativa' : 'selo-inativa') + '">' +
      (ativo ? '✔&#xFE0E; Ativo' : '–&nbsp;Inativo') + '</span>';
  }
  function seloCategoria(ativa) {
    return '<span class="selo-situacao ' + (ativa ? 'selo-ativa' : 'selo-inativa') + '">' +
      (ativa ? '✔&#xFE0E; Ativa' : '–&nbsp;Inativa') + '</span>';
  }
  function seloProtegida() {
    return '<span class="selo-situacao selo-protegida">◆&#xFE0E; Protegida</span>';
  }

  function textoPagina(p, singular, plural) {
    var total = Math.max(1, Math.ceil((p.total || 0) / (p.size || 1)));
    return 'Página ' + p.page + ' de ' + total + ' (' + p.total + ' ' + (p.total === 1 ? singular : plural) + ')';
  }

  /* Equipamento finalizado = somente leitura (vendido ou doado; contrato: EQUIPAMENTO_FINALIZADO) */
  function finalizado(eq) { return eq.situacao === 'Vendido' || eq.situacao === 'Doado'; }

  /* UC08 passos 2 e 3: situações que o contrato aceita para este equipamento.
     Devolve { opcoes: [...], motivos: [textos do que ficou de fora] }. Conveniência de tela; a API valida (RN12). */
  function situacoesPermitidas(eq) {
    var motivos = [];
    if (finalizado(eq)) { return { opcoes: [], motivos: ['Equipamento vendido ou doado não pode mais ser alterado.'] }; }
    if (eq.situacao === 'Destinado à reciclagem') { return { opcoes: [], motivos: ['Destinado à reciclagem é uma situação final e não muda mais.'] }; }
    var op = SITUACOES.filter(function (s) { return s !== 'Vendido'; });
    motivos.push('Vendido não é informado manualmente: é registrado pela confirmação da venda.');
    if (eq.condicao === SEM_REUSO) {
      op = op.filter(function (s) { return SIT_SEM_REUSO.indexOf(s) !== -1; });
      motivos.push('Condição "Sem condições de reuso": só Recebido, Em avaliação ou Destinado à reciclagem.');
    } else {
      if (eq.condicao === 'A avaliar') {
        op = op.filter(function (s) { return s !== 'Disponível' && s !== 'Doado'; });
        motivos.push('Disponível e Doado exigem que a condição já tenha sido avaliada (hoje: "A avaliar").');
      }
      if (!eq.ativo) {
        op = op.filter(function (s) { return s !== 'Disponível' && s !== 'Doado'; });
        motivos.push('Equipamento inativo não pode ficar Disponível nem ser doado. Reative-o antes.');
      }
      if (!(Number(eq.valor) > 0) && op.indexOf('Disponível') !== -1) {
        op = op.filter(function (s) { return s !== 'Disponível'; });
        motivos.push('Disponível exige valor maior que zero. Edite o equipamento e informe o valor.');
      }
    }
    return { opcoes: op, motivos: motivos };
  }

  /* Validação no cliente do cadastro/alteração (RNF04; UC07 FE1). v: campos do formulário (texto).
     opcoes.criando: valida a situação inicial. Devolve { campo: mensagem } e, em v.__valor, o número lido. */
  function validarEquipamento(v, opcoes) {
    opcoes = opcoes || {};
    var e = {};
    var ident = (v.identificacao || '').trim();
    if (!ident) { e.identificacao = 'Informe a identificação.'; }
    else if (ident.length > 50) { e.identificacao = 'A identificação deve ter no máximo 50 caracteres.'; }
    if (!v.id_categoria) { e.id_categoria = 'Selecione a categoria.'; }
    var modelo = (v.modelo || '').trim();
    if (!modelo) { e.modelo = 'Informe o modelo ou a descrição.'; }
    else if (modelo.length > 150) { e.modelo = 'O modelo deve ter no máximo 150 caracteres.'; }
    if (!v.condicao) { e.condicao = 'Selecione a condição.'; }
    var origem = (v.origem || '').trim();
    if (!origem) { e.origem = 'Informe a origem.'; }
    else if (origem.length > 100) { e.origem = 'A origem deve ter no máximo 100 caracteres.'; }
    if (!v.data_recebimento) { e.data_recebimento = 'Informe a data de recebimento.'; }
    else if (!dataValida(v.data_recebimento)) { e.data_recebimento = 'Informe uma data válida.'; }
    else if (v.data_recebimento > hojeIso()) { e.data_recebimento = 'A data de recebimento não pode ser futura.'; }
    var val = lerValor(v.valor);
    if (val.erro) { e.valor = val.erro; }
    var item = String(v.id_item_solicitacao == null ? '' : v.id_item_solicitacao).trim();
    if (item && !/^[1-9]\d*$/.test(item)) { e.id_item_solicitacao = 'Informe um número inteiro maior que zero ou deixe em branco.'; }
    if (opcoes.criando && v.situacao) {
      if (v.condicao === SEM_REUSO && SIT_SEM_REUSO.indexOf(v.situacao) === -1) {
        e.situacao = MSG.SEM_CONDICOES_DE_REUSO;
      } else if (v.situacao === 'Disponível') {
        if (v.condicao === 'A avaliar' || v.condicao === SEM_REUSO) { e.situacao = 'Disponível exige condição já avaliada e apta ao reuso.'; }
        else if (!(val.valor > 0) && !e.valor) { e.valor = 'Para ficar Disponível, informe um valor maior que zero.'; }
      }
    }
    v.__valor = val.valor;
    return e;
  }

  /* UC07 (DP-84): valida a imagem no cliente (a API valida de novo pelo conteúdo). Devolve a mensagem ou ''. */
  var IMG_TIPOS = ['image/jpeg', 'image/png', 'image/webp'], IMG_MAX = 2 * 1024 * 1024;
  function validarImagem(arq) {
    if (!arq) { return ''; }
    if (IMG_TIPOS.indexOf(arq.type) === -1) { return 'Envie uma imagem JPG, PNG ou WebP.'; }
    if (arq.size > IMG_MAX) { return 'A imagem deve ter no máximo 2 MB.'; }
    return '';
  }

  global.EquipUi = {
    validarImagem: validarImagem,
    SITUACOES: SITUACOES, CONDICOES: CONDICOES, SEM_REUSO: SEM_REUSO, SIT_SEM_REUSO: SIT_SEM_REUSO, MSG: MSG,
    msgErro: msgErro, escAttr: escAttr, hojeIso: hojeIso, dataValida: dataValida, formatarData: formatarData,
    formatarValor: formatarValor, valorParaCampo: valorParaCampo, lerValor: lerValor,
    seloSituacao: seloSituacao, seloAtivo: seloAtivo, seloCategoria: seloCategoria, seloProtegida: seloProtegida,
    textoPagina: textoPagina, finalizado: finalizado, situacoesPermitidas: situacoesPermitidas,
    validarEquipamento: validarEquipamento
  };
})(window);
