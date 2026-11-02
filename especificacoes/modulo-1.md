# Módulo 1 – Acesso e usuários (UC02, UC03, UC26, UC27)

Fonte: `Projeto_LEAF_TI.docx` (`docs/Projeto_LEAF_TI.docx`), seções 3.1, 3.2, 3.3 e 4. Texto copiado do documento.

## Casos de uso

### UC02 Gerenciar usuários e atribuir perfis
**Identificação**
- Objetivo: **[M1]** Criar, consultar, alterar e excluir contas internas e as contas iniciais de organizações, atribuindo permissões compatíveis com o perfil e vinculando a conta à organização correspondente.
- Atores: Administrador
- Pré-condições: Administrador autenticado; organização ativa previamente cadastrada quando a conta representa uma organização.
- Pós-condições: **[M1]** Conta criada, alterada ou excluída, mantendo perfil e vínculo válidos nas contas existentes.
- Relacionamentos: «include» UC26 Verificar disponibilidade do e-mail; «include» UC27 Atribuir perfil.
- Requisitos e regras: **[M1]** RF01, RF02, RF03; RN01, RN02, RN03

**Fluxo principal**
1. O Administrador abre Usuários e seleciona Novo usuário.
2. O sistema solicita nome, e-mail, senha, perfil e, para contas organizacionais, a organização vinculada.
3. O Administrador informa os dados e seleciona um perfil permitido.
4. O sistema executa UC26 Verificar disponibilidade do e-mail e UC27 Atribuir perfil.
5. O sistema valida o vínculo organizacional quando aplicável, protege a senha e salva a conta.
6. O sistema confirma o cadastro e as permissões atribuídas.

**Fluxos alternativos**
FA1 Alterar perfil ou vínculo. O Administrador seleciona uma conta existente, altera o perfil ou vínculo e confirma. O sistema valida a nova configuração antes de salvar.
**[M1]** FA2 Alterar dados da conta. O Administrador seleciona uma conta existente e altera nome, e-mail ou senha, e confirma. Se o e-mail mudar, o sistema executa UC26 desconsiderando a própria conta. A nova senha é protegida antes de salvar.
**[M1]** FA3 Excluir conta. O Administrador seleciona uma conta existente, solicita a exclusão e confirma. O sistema remove a conta e confirma a operação.
**[M1]** FA4 Consultar usuários. O Administrador lista as contas e filtra por perfil, organização ou texto (nome ou e-mail), e seleciona uma conta para consulta.

**Fluxos de exceção**
- FE1 E-mail já utilizado ou dados inválidos. O sistema informa o problema e retorna aos dados da conta.
- FE2 Organização inexistente ou inativa. O sistema impede a criação ou alteração do vínculo.
- FE3 Perfil não autorizado. O sistema rejeita a atribuição e mantém a conta sem alterações.
- **[M1]** FE4 Alteração ou exclusão bloqueada. Tentativa de excluir a própria conta, de alterar o próprio perfil, ou de excluir ou alterar o perfil da última conta Administrador. O sistema nega a operação e mantém a conta sem alterações.

### UC03 Cadastrar usuário da própria organização
**Identificação**
- Objetivo: Permitir que um usuário autorizado crie uma conta adicional vinculada à própria organização, sem conceder permissões administrativas nem acesso a terceiros.
- Atores: Cliente Empresa ou Cliente ONG
- Pré-condições: Usuário autenticado como Cliente Empresa ou Cliente ONG; organização ativa e vinculada à conta.
- Pós-condições: Nova conta vinculada à mesma organização, com permissões do tipo de cliente.
- Relacionamentos: «include» UC26 Verificar disponibilidade do e-mail. O perfil e a organização são herdados da conta que realiza o cadastro.
- Requisitos e regras: RF02, RF04, RF09; RN02, RN04, RN09

**Fluxo principal**
1. O Cliente abre Usuários da organização e seleciona Adicionar usuário.
2. O sistema solicita os dados necessários para a nova conta.
3. O Cliente informa os dados e confirma.
4. O sistema executa UC26 Verificar disponibilidade do e-mail.
5. O sistema associa a nova conta à mesma organização e aplica as permissões correspondentes a Cliente Empresa ou Cliente ONG.
6. O sistema salva a conta e confirma a operação.

**Fluxos alternativos**
FA1 Consultar usuários da organização. O Cliente visualiza as contas vinculadas à própria organização, sem acesso a contas de terceiros. **[M1]** Alterar e excluir contas não faz parte deste caso de uso; essas operações são do Administrador (UC02).

**Fluxos de exceção**
- FE1 E-mail já utilizado ou dados inválidos. O sistema informa o problema e solicita correção.
- FE2 Tentativa de vincular outra organização ou conceder perfil administrativo. O sistema nega a operação **[M1]**, informa que a operação não é permitida e não cria a conta.

### UC26 Verificar disponibilidade do e-mail
**Identificação**
- Objetivo: Verificar se o e-mail pode ser usado em uma nova conta.
- Atores: UC02 ou UC03, processado pelo sistema
- Pré-condições: Criação ou alteração de conta iniciada em UC02 ou UC03**[M1]**, inclusive alteração de e-mail (UC02 FA2).
- Pós-condições: E-mail considerado disponível ou duplicidade informada.
- Relacionamentos: «include» de UC02 e UC03.
- Requisitos e regras: RF02, RF04; RN02, RN04; RNF04

**Fluxo principal**
1. O sistema recebe o e-mail informado para a conta.
2. **[M1]** O sistema normaliza o e-mail (sem espaços nas pontas e sem diferenciar maiúsculas de minúsculas) e verifica se ele já está associado a outra conta, desconsiderando a própria conta em caso de alteração.
3. Se estiver disponível, o sistema permite continuar o cadastro.

**Fluxos alternativos**
Não há fluxo alternativo previsto para esta operação.

**Fluxos de exceção**
- FE1 E-mail já utilizado ou em formato inválido. O sistema informa o problema e retorna ao cadastro da conta.

### UC27 Atribuir perfil
**Identificação**
- Objetivo: Definir o perfil e as permissões autorizadas para uma conta criada pelo Administrador.
- Atores: Administrador
- Pré-condições: Cadastro ou alteração de conta iniciado por Administrador em UC02.
- Pós-condições: Conta com perfil válido atribuído.
- Relacionamentos: «include» de UC02.
- Requisitos e regras: RF01, RF02; RN01, RN02

**Fluxo principal**
1. O sistema apresenta os perfis que o Administrador está autorizado a atribuir.
2. O Administrador seleciona o perfil correspondente à conta e, quando necessário, a organização vinculada.
3. O sistema valida que o perfil é permitido e que o vínculo organizacional corresponde à conta**[M1]**: Administrador e Funcionário não têm organização; Cliente Empresa, Cliente ONG e Empresa Doadora exigem organização ativa do tipo correspondente ao perfil.
4. O sistema aplica as permissões do perfil ao usuário.

**Fluxos alternativos**
Não há fluxo alternativo previsto para esta operação.

**Fluxos de exceção**
- FE1 Nenhum perfil selecionado ou perfil sem autorização. O sistema impede a conclusão do cadastro.

## Requisitos funcionais e regras relacionados

### RF01 – Controle de acesso por perfil
Descrição: O sistema deve autenticar usuários por e-mail e senha e controlar o acesso conforme o perfil atribuído: Administrador, Funcionário, Cliente Empresa, Cliente ONG ou Empresa Doadora.
Critério de aceitação: O login deve validar as credenciais antes de iniciar a sessão. Após a autenticação, o usuário deve acessar somente as funcionalidades permitidas ao seu perfil. A conta deve estar previamente cadastrada; o login não realiza cadastro.
Regra de negócio: RN01: O acesso deve limitar-se às operações autorizadas para o perfil do usuário.

### RF02 – Perfil de administrador
Descrição: O sistema deve permitir que o Administrador cadastre usuários, atribua perfis e gerencie as informações e operações gerais da LEAF TI.
Critério de aceitação: O Administrador deve poder cadastrar contas de Funcionário, Cliente Empresa, Cliente ONG e Empresa Doadora, além de criar contas administrativas e atribuir os perfis correspondentes. Clientes Empresa e Cliente ONG podem cadastrar usuários adicionais vinculados à própria organização, sem acesso a funções administrativas ou dados de terceiros. O Administrador também deve gerenciar organizações, categorias, parceiros, equipamentos, solicitações de equipamentos, vendas, relatórios e notas fiscais simuladas. **[M1]** O Administrador também deve consultar, alterar e excluir contas de usuário. Nenhum usuário pode excluir a própria conta.
Regra de negócio: RN02: O Administrador é o único perfil autorizado a cadastrar usuários para terceiros, criar contas de Funcionário e Administrador e atribuir ou alterar os perfis gerais do sistema. Clientes Empresa e Cliente ONG podem cadastrar usuários vinculados à própria organização, limitados às permissões de seu tipo de cliente. Não podem criar usuários de outras organizações nem cadastrar Administradores ou Funcionários. Somente o Administrador pode emitir notas fiscais simuladas. Todo usuário deve receber um perfil válido. **[M1]** A senha deve ter de 8 a 128 caracteres. O perfil deve corresponder ao vínculo organizacional: Administrador e Funcionário não têm organização; Cliente Empresa, Cliente ONG e Empresa Doadora exigem organização ativa do tipo correspondente ao perfil. O Administrador não pode alterar o próprio perfil nem excluir a própria conta, e a última conta Administrador não pode ser excluída nem ter o perfil alterado.
História de usuário: Como Administrador, quero cadastrar usuários e gerenciar as operações da LEAF TI, para manter os acessos e as informações organizados.

### RF03 – Perfil de funcionário
Regra de negócio: RN03: O Funcionário pode executar as operações internas definidas para seu perfil, mas não pode cadastrar usuários, atribuir perfis, gerenciar permissões ou emitir notas fiscais simuladas. **[M1]** O Funcionário e a Empresa Doadora não acessam o cadastro de usuários.

### RF04 – Perfil de cliente — Empresa ou ONG
Critério de aceitação: (...) Ambos podem consultar somente os registros vinculados à própria organização e cadastrar usuários adicionais da própria organização.
Regra de negócio: RN04: Cliente Empresa pode consultar somente seus pedidos, compras e documentos correspondentes. Cliente ONG pode consultar somente suas doações, solicitações e equipamentos vinculados. Cada cliente pode cadastrar usuários somente para sua própria organização, sem conceder permissões administrativas nem acessar dados de terceiros.

### RF05 – Perfil de Empresa Doadora
Regra de negócio: RN05: A solicitação deve estar vinculada a uma Empresa Doadora cadastrada e ativa. (...) A Empresa Doadora pode consultar somente as próprias solicitações e os resultados correspondentes.

### RF06 e RF09 (organização ativa)
- RN06: (...) Uma organização desativada não pode realizar novas operações no sistema.
- RN09: (...) Um cliente desativado não pode realizar novas compras nem participar de novas operações como cliente. Clientes Empresa e Cliente ONG podem cadastrar usuários vinculados à própria organização conforme RF02.
- Tipos de organização (RF06): Cliente Empresa, Cliente ONG ou Empresa Doadora.

## Requisitos não funcionais relacionados
- **RNF03 – Proteção de senhas.** As senhas dos usuários devem ser armazenadas utilizando hash seguro e nunca em texto simples. Critério: A consulta direta ao banco de dados não deve revelar a senha original de nenhum usuário.
- **RNF04 – Validação de dados.** O sistema deve validar os campos obrigatórios e apresentar mensagens claras quando os dados informados forem inválidos. Critério: Formulários não devem ser enviados com campos obrigatórios vazios ou formatos inválidos, e cada erro deve indicar o que precisa ser corrigido.
- **RNF05 – Controle de acesso.** As funcionalidades devem ser acessíveis somente a usuários autenticados e autorizados conforme os perfis. Critério: Um usuário sem autorização que tente acessar uma funcionalidade deve ter o acesso negado. Cada organização cliente e cada Empresa Doadora pode consultar somente seus próprios registros.
- **RNF01, RNF06:** legibilidade (16 px) e acessibilidade nas telas.

## Observações do coordenador (não fazem parte do documento)
- `USUARIO` não tem coluna de situação (DP-02). **Exclusão de conta é física** (aprovada pelo usuário): nenhuma tabela referencia USUARIO; exceção à regra "sem exclusão física" de `docs/CONVENCOES.md`, restrita a essa tabela.
- Do módulo 0 (já decidido): e-mail normalizado (strip + minúsculas) e regex simples (DP-09); senha mínima de 8 caracteres definida neste módulo; checar duplicidade sem diferenciar caixa (UNIQUE do SQLite diferencia); perfil de cliente/doadora sem organização é conta inativa (DP-08); `ORGANIZACAO.situacao` = `Ativa`/`Inativa` (DP-03).
- Dependência: a criação de organizações é do Módulo 2; aqui as organizações só são lidas.
