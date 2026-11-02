# Módulo 0 – Fundação (UC04, UC28)

Fonte: `Projeto_LEAF_TI.docx` (versão em `Entrega/DOCUMENTO PARTE 2/`), seções 3.1, 3.2, 3.3, 4.1 e 4. Texto copiado sem alteração; numeração original.

## Perfis (seção 3.1)
Os requisitos definem cinco perfis de interação: Administrador, Funcionário, Cliente Empresa, Cliente ONG e Empresa Doadora. Cliente Empresa e Cliente ONG são tratados como variações do perfil Cliente, com permissões diferentes. O Administrador mantém os cadastros e configurações gerais; o Funcionário realiza operações internas autorizadas; os clientes consultam somente os registros de sua organização; e a Empresa Doadora acompanha suas próprias solicitações e resultados.

## Casos de uso

### UC04 Acessar o sistema
**Identificação**
- Objetivo: Autenticar uma conta e apresentar as funções permitidas ao perfil e ao vínculo organizacional.
- Atores: Administrador, Funcionário, Cliente Empresa, Cliente ONG ou Empresa Doadora
- Pré-condições: Conta cadastrada e ativa.
- Pós-condições: Sessão autenticada ou acesso negado.
- Relacionamentos: «include» UC28 Validar credenciais.
- Requisitos e regras: RF01; RN01; RNF03, RNF05

**Fluxo principal**
1. O usuário abre a tela de acesso.
2. O usuário informa e-mail e senha e seleciona Entrar.
3. O sistema executa UC28 Validar credenciais e confirma que a conta está ativa.
4. O sistema inicia a sessão e apresenta as funcionalidades autorizadas ao perfil.

**Fluxos alternativos**
Não há fluxo alternativo previsto para esta operação.

**Fluxos de exceção**
- FE1 Credenciais inválidas. O sistema informa que não foi possível entrar e retorna à tela de acesso, sem iniciar sessão.
- FE2 Conta ou organização inativa. O sistema nega o acesso e informa o impedimento.

### UC28 Validar credenciais
**Identificação**
- Objetivo: Validar e-mail e senha para autenticar a conta.
- Atores: UC04, processado pelo sistema
- Pré-condições: Usuário enviou e-mail e senha em UC04.
- Pós-condições: Credenciais aceitas ou acesso negado.
- Relacionamentos: «include» de UC04.
- Requisitos e regras: RF01; RN01; RNF03, RNF05

**Fluxo principal**
1. O sistema consulta a conta associada ao e-mail informado.
2. O sistema compara a senha informada com a senha protegida armazenada.
3. Se as credenciais forem válidas e a conta estiver ativa, o sistema retorna sucesso a UC04.

**Fluxos alternativos**
Não há fluxo alternativo previsto para esta operação.

**Fluxos de exceção**
- FE1 Conta não encontrada, senha incorreta ou conta inativa. O sistema retorna falha a UC04 sem iniciar sessão.

## Requisitos funcionais relacionados

### RF01 – Controle de acesso por perfil
Descrição: O sistema deve autenticar usuários por e-mail e senha e controlar o acesso conforme o perfil atribuído: Administrador, Funcionário, Cliente Empresa, Cliente ONG ou Empresa Doadora.
Critério de aceitação: O login deve validar as credenciais antes de iniciar a sessão. Após a autenticação, o usuário deve acessar somente as funcionalidades permitidas ao seu perfil. A conta deve estar previamente cadastrada; o login não realiza cadastro.
Regra de negócio: RN01: O acesso deve limitar-se às operações autorizadas para o perfil do usuário.
História de usuário: Como usuário cadastrado, quero acessar o sistema conforme meu perfil, para realizar somente as atividades autorizadas.

### RF02 – Perfil de administrador (somente trechos de perfis; o cadastro de usuários é do Módulo 1)
Regra de negócio: RN02: O Administrador é o único perfil autorizado a cadastrar usuários para terceiros, criar contas de Funcionário e Administrador e atribuir ou alterar os perfis gerais do sistema. Clientes Empresa e Cliente ONG podem cadastrar usuários vinculados à própria organização, limitados às permissões de seu tipo de cliente. Não podem criar usuários de outras organizações nem cadastrar Administradores ou Funcionários. Somente o Administrador pode emitir notas fiscais simuladas. Todo usuário deve receber um perfil válido.

### RF03, RF04, RF05 (regras de perfil que alimentam a matriz de permissões)
- RN03: O Funcionário pode executar as operações internas definidas para seu perfil, mas não pode cadastrar usuários, atribuir perfis, gerenciar permissões ou emitir notas fiscais simuladas.
- RN04: Cliente Empresa pode consultar somente seus pedidos, compras e documentos correspondentes. Cliente ONG pode consultar somente suas doações, solicitações e equipamentos vinculados. Cada cliente pode cadastrar usuários somente para sua própria organização, sem conceder permissões administrativas nem acessar dados de terceiros.
- RN05: A solicitação deve estar vinculada a uma Empresa Doadora cadastrada e ativa. (...) A Empresa Doadora pode consultar somente as próprias solicitações e os resultados correspondentes (RF05, critério de aceitação).

### RF06 / RF09 (situação da organização, que afeta o acesso – UC04 FE2)
- RN06: (...) Uma organização desativada não pode realizar novas operações no sistema.
- RN09: (...) Um cliente desativado não pode realizar novas compras nem participar de novas operações como cliente.

## Requisitos não funcionais relacionados
- **RNF03 – Proteção de senhas.** Descrição: As senhas dos usuários devem ser armazenadas utilizando hash seguro e nunca em texto simples. Critério de aceitação: A consulta direta ao banco de dados não deve revelar a senha original de nenhum usuário.
- **RNF04 – Validação de dados.** Descrição: O sistema deve validar os campos obrigatórios e apresentar mensagens claras quando os dados informados forem inválidos. Critério de aceitação: Formulários não devem ser enviados com campos obrigatórios vazios ou formatos inválidos, e cada erro deve indicar o que precisa ser corrigido.
- **RNF05 – Controle de acesso.** Descrição: As funcionalidades devem ser acessíveis somente a usuários autenticados e autorizados conforme os perfis Administrador, Funcionário, Cliente Empresa, Cliente ONG e Empresa Doadora. Critério de aceitação: Um usuário sem autorização que tente acessar uma funcionalidade deve ter o acesso negado. Cada organização cliente e cada Empresa Doadora pode consultar somente seus próprios registros, observadas as permissões específicas de cada perfil. Regra de negócio: Aplicam-se as regras de acesso de RF01, RF02, RF03, RF04 e RF05.
- **RNF01 / RNF06** (layout base): fonte principal de no mínimo 16 px, contraste adequado, navegação por teclado, textos alternativos em imagens informativas.

## Modelo de dados usado (banco/Codigo_Modelo_Fisico.sql)
`USUARIO(id_usuario, id_organizacao NULL, email UNIQUE, perfil CHECK em 5 valores, senha_hash, nome)` e `ORGANIZACAO(..., situacao)`.
Observação: `USUARIO` não possui coluna de situação; ver `docs/DECISOES_PENDENTES.md`.
