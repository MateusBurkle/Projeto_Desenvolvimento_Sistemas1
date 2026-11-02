# Módulo 6 – Relatórios (UC22, UC23, UC24)

Fonte: `docs/Projeto_LEAF_TI.docx`
## Casos de uso

UC22 Emitir relatório de vendas
Identificação
Objetivo: Gerar um relatório gerencial de vendas confirmadas para um período selecionado.
Atores: Administrador ou Funcionário
Pré-condições: Usuário interno autenticado; período informado.
Pós-condições: Relatório apresenta vendas confirmadas, itens, quantidades e valor total do período.
Relacionamentos: —
Requisitos e regras: RF16; RN16; RNF05
Fluxo principal
1. O ator abre Relatórios e seleciona Vendas.
2. O sistema solicita o período.
3. O ator informa o período e solicita a emissão.
4. O sistema seleciona vendas confirmadas dentro do período.
5. O sistema apresenta os equipamentos, quantidades e valor total correspondente.
Fluxos alternativos
FA1 Período sem vendas confirmadas. O sistema apresenta relatório sem resultados e total igual a zero.
Fluxos de exceção
FE1 Período inválido. O sistema informa a inconsistência e solicita correção.
UC23 Emitir relatório de equipamentos
Identificação
Objetivo: Consultar equipamentos cadastrados por categoria, situação e período de cadastro.
Atores: Administrador ou Funcionário
Pré-condições: Usuário interno autenticado.
Pós-condições: Relatório de equipamentos apresentado conforme os filtros selecionados.
Relacionamentos: —
Requisitos e regras: RF17; RN17; RNF05
Fluxo principal
1. O ator abre Relatórios e seleciona Equipamentos.
2. O sistema apresenta filtros por categoria, situação e período de cadastro.
3. O ator seleciona os filtros e solicita o relatório.
4. O sistema apresenta os equipamentos correspondentes, incluindo origem e destinação quando registradas.
Fluxos alternativos
FA1 Sem filtros. O sistema apresenta todos os equipamentos que o ator está autorizado a consultar.
Fluxos de exceção
FE1 Filtros inválidos. O sistema informa o problema e solicita correção.
UC24 Emitir relatório de Empresas Doadoras, empresas e ONGs
Identificação
Objetivo: Acompanhar os equipamentos informados por Empresas Doadoras, as avaliações e as destinações para venda, doação ou reciclagem.
Atores: Administrador ou Funcionário
Pré-condições: Usuário interno autenticado.
Pós-condições: Relatório de solicitações, condições avaliadas e destinações apresentado.
Relacionamentos: —
Requisitos e regras: RF18, RF21; RN18, RN21; RNF05
Fluxo principal
1. O ator abre Relatórios e seleciona Organizações e destinações.
2. O sistema apresenta solicitações das Empresas Doadoras e os equipamentos informados.
3. O sistema apresenta quantidade, condição avaliada e situação da solicitação.
4. Quando houver doação, o sistema apresenta a ONG beneficiada e a data correspondente.
5. O ator consulta os resultados do relatório.
Fluxos alternativos
FA1 Solicitação sem destinação final. O sistema inclui a solicitação e identifica a avaliação ou destinação ainda pendente.
FA2 Equipamento destinado à reciclagem. O sistema apresenta essa destinação sem associar venda ou doação.
Fluxos de exceção
FE1 Dados da avaliação incompletos. O sistema sinaliza os campos pendentes e não apresenta uma destinação não registrada como concluída.

## Requisitos e regras citados

RF16 – Relatório de vendas
Descrição: O sistema deve permitir que o Administrador ou Funcionário emita relatórios gerenciais de vendas.
Critério de aceitação: Para o período selecionado, o relatório deve apresentar as vendas confirmadas, os equipamentos vendidos, as quantidades e o valor total. Vendas pendentes ou canceladas não devem compor os resultados.
Regra de negócio: RN16: O relatório deve considerar somente vendas confirmadas cuja data esteja no período selecionado. O valor total deve corresponder à soma das vendas incluídas no relatório.
História de usuário: Como Administrador ou Funcionário, quero emitir um relatório de vendas confirmadas por período, para acompanhar os equipamentos vendidos e o valor total das vendas.
RF17 – Relatório de equipamentos
Descrição: O sistema deve permitir que o Administrador ou Funcionário emita relatórios gerenciais sobre os equipamentos cadastrados.
Critério de aceitação: O relatório deve permitir visualizar equipamentos por categoria, situação e período de cadastro, incluindo origem e destinação quando registradas.
Regra de negócio: RN17: Somente Administrador e Funcionário podem consultar relatórios gerenciais de equipamentos.
História de usuário: Como Administrador ou Funcionário, quero consultar os equipamentos por categoria, situação e período, para acompanhar os itens disponíveis e em processamento.
RF18 – Relatório de empresas, ONGs e doações
Descrição: O sistema deve permitir que o Administrador ou Funcionário emita relatórios sobre equipamentos oferecidos por Empresas Doadoras e suas destinações.
Critério de aceitação: O relatório deve apresentar Empresa Doadora, equipamentos informados, quantidade, condição avaliada e situação da solicitação. Quando um equipamento for destinado a uma ONG, o relatório deve apresentar a ONG beneficiada e a data da doação.
Regra de negócio: RN18: As solicitações devem constar no relatório mesmo quando ainda não houver destinação final. As informações de condição e destinação devem corresponder aos registros da avaliação pela LEAF TI.
História de usuário: Como Administrador ou Funcionário, quero consultar os equipamentos informados por Empresas Doadoras e suas destinações, para acompanhar avaliação, reaproveitamento, doações e reciclagem.
RF21 – Solicitação, avaliação e destinação de equipamentos
Descrição: O sistema deve permitir o registro de solicitações de Empresas Doadoras e o registro, pela LEAF TI, da avaliação e da destinação dos equipamentos para venda, doação ou reciclagem.
Critério de aceitação: A solicitação só pode ser registrada por Empresa Doadora com vínculo de parceria ativo (RN10) e deve registrar a Empresa Doadora e os tipos, modelos e quantidades informados. O Administrador ou Funcionário deve registrar a condição avaliada de cada equipamento, atualizar sua situação durante eventual recondicionamento e definir sua destinação. Equipamentos aptos ao reuso podem ser disponibilizados para venda ou destinados à doação. Aqueles sem condições de reuso devem ser registrados como destinados à reciclagem, sem disponibilização para compra ou doação. A solicitação tem as situações Aguardando avaliação, Em avaliação e Avaliada, e não pode ser editada nem cancelada depois de registrada. Cada item informa tipo e modelo de 1 a 100 caracteres e quantidade de 1 a 9.999. A avaliação é feita por equipamento: para cada item, o Administrador ou Funcionário cadastra equipamentos vinculados ao item, em número não superior à quantidade informada. O item está avaliado quando possui tantos equipamentos quantos informados, todos com condição diferente de A avaliar e situação disponível, doado, vendido ou destinado à reciclagem; a solicitação é Avaliada quando todos os seus itens estão avaliados. A destinação só pode ser registrada depois de avaliada a condição do equipamento.
Regra de negócio: RN21: O registro da solicitação não disponibiliza automaticamente os equipamentos no catálogo. A avaliação e a definição da destinação são realizadas pelo Administrador ou Funcionário. Equipamentos de uma mesma solicitação podem receber destinações diferentes conforme suas condições. A impossibilidade de reuso determina o encaminhamento à reciclagem, não a recusa. O registro não inclui coleta ou transporte.
RNF05 – Controle de acesso
Descrição: As funcionalidades devem ser acessíveis somente a usuários autenticados e autorizados conforme os perfis Administrador, Funcionário, Cliente Empresa, Cliente ONG e Empresa Doadora.
Critério de aceitação: Um usuário sem autorização que tente acessar uma funcionalidade deve ter o acesso negado. Cada organização cliente e cada Empresa Doadora pode consultar somente seus próprios registros, observadas as permissões específicas de cada perfil.
Regra de negócio: Aplicam-se as regras de acesso de RF01, RF02, RF03, RF04 e RF05.

RN03 (trecho): O Funcionário pode executar as operações internas definidas para seu perfil... consultar relatórios (RF03).
RN21: ver RF21 acima.
