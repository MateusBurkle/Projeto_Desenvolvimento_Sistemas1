# Convenções compartilhadas (todos os agentes seguem)

## API
- Prefixo `/api/v1`, JSON, autenticação `Authorization: Bearer <token>`.
- Datas em ISO 8601. Nomes de campos iguais às colunas do banco.
- Listagens: parâmetros `page` e `size`; resposta `{ "items": [...], "total": N, "page": 1, "size": 20 }`.
- Erro padrão: `{ "codigo": "CNPJ_DUPLICADO", "mensagem": "texto em português", "campos": { "cnpj": "duplicado" } }`.
- Status: 400 dados inválidos, 401 não autenticado, 403 sem permissão, 404 não encontrado, 409 conflito (duplicidade), 422 regra de negócio violada.
- Sem exclusão física por padrão: desativar preserva o histórico e bloqueia novas operações. **Exceções aprovadas (DP-63 a DP-66):** (1) `USUARIO` pode ser excluída fisicamente pelo Administrador (DELETE /usuarios/{id}) e por ela mesma, com senha atual (DELETE /usuarios/me); a última conta Administrador é protegida; (2) o Administrador exclui `ORGANIZACAO` e a `PARCEIRO` dela (DELETE /organizacoes/{id}) somente sem histórico (422 ORGANIZACAO_EM_USO) e, havendo usuários, só com confirmação explícita (`excluir_usuarios=true`, senão 422 ORGANIZACAO_COM_USUARIOS). Desativar continua disponível.

## Perfis
Administrador, Funcionário, Cliente Empresa, Cliente ONG, Empresa Doadora. A matriz de permissões por rota fica em cada contrato e deve bater com o documento.

## Código
- Back-end: `backend/app/<modulo>/{router,schemas,service,repository}.py`. Regra de negócio somente no service.
- Front-end: base existente do grupo em `frontend/` (ver `docs/FRONTEND_EXISTENTE.md`). Adicionar `css/identidade.css` (variáveis da marca), `js/api.js` (único acesso à API) e as telas logadas em `frontend/app/<modulo>/`. Não recriar o que já funciona.
- Rastreabilidade: todo trecho cita o UC e a RN de origem.

## Decisões já tomadas (vêm do documento)
- Login: por **e-mail e senha** (e-mail único, tabela USUARIO). O campo "Usuário" da tela atual vira "E-mail". Senha só armazenada como hash. Sem redefinição de senha (fora do escopo do documento).
- Parceria: somente Empresa Doadora com vínculo de parceria ativo pode registrar solicitação (RN10, UC09). Atuação como Empresa Doadora na parceria exige organização do tipo Empresa Doadora. Patrocinador em Potencial só é registrado e consultado.
- Organização: tipos Cliente Empresa, Cliente ONG, Empresa Doadora. CNPJ com 14 dígitos e único.
- Venda: situação Pendente, Confirmada ou Cancelada. Cada item de venda é uma unidade física única (quantidade 1).
