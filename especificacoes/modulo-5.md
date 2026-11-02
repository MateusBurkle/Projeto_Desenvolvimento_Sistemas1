# Módulo 5 – Loja e vendas (UC12 a UC18, UC21)

Fonte: `Projeto_LEAF_TI.docx` (`docs/Projeto_LEAF_TI.docx`)

## Casos de uso

UC12 Consultar catálogo de equipamentos
Identificação
Objetivo: Consultar equipamentos recondicionados disponíveis para compra.
Atores: Cliente Empresa
Pré-condições: Cliente Empresa autenticada e ativa.
Pós-condições: Lista ou detalhe dos equipamentos disponíveis apresentado.
Relacionamentos: —
Requisitos e regras: RF04, RF13; RN04, RN13
Fluxo principal
1. O Cliente Empresa abre o catálogo de equipamentos.
2. O sistema apresenta os equipamentos ativos, disponíveis e aptos para reuso.
3. O Cliente Empresa seleciona um equipamento.
4. O sistema apresenta os dados disponíveis do item, incluindo categoria, descrição ou modelo, condição e valor, quando aplicável.
Fluxos alternativos
FA1 Consultar outro item. O Cliente Empresa retorna à lista e seleciona outro equipamento.
Fluxos de exceção
FE1 Nenhum item disponível. O sistema informa que não há equipamentos disponíveis para compra.
FE2 Usuário sem perfil de Cliente Empresa. O sistema bloqueia as funções de compra.
UC13 Realizar pedido de compra
Identificação
Objetivo: Solicitar a compra de equipamentos disponíveis para a própria organização.
Atores: Cliente Empresa
Pré-condições: Cliente Empresa autenticada e ativa; equipamentos ativos e disponíveis.
Pós-condições: Pedido registrado e aguardando confirmação interna.
Relacionamentos: —
Requisitos e regras: RF04, RF13; RN04, RN13
Fluxo principal
1. O Cliente Empresa seleciona equipamentos disponíveis no catálogo.
2. O sistema apresenta os itens e seus valores.
3. O Cliente Empresa informa as quantidades e confirma o pedido.
4. O sistema verifica novamente a disponibilidade e registra o pedido vinculado à organização.
5. O sistema informa que o pedido aguarda confirmação pela LEAF TI.
Fluxos alternativos
FA1 Alterar ou cancelar antes da confirmação. O Cliente Empresa solicita alteração ou cancelamento enquanto o pedido estiver pendente; o sistema atualiza a situação e libera itens quando aplicável.
Fluxos de exceção
FE1 Equipamento indisponível ou quantidade inválida. O sistema aponta os itens afetados e não confirma o pedido.
FE2 Cliente inativo. O sistema impede a criação do pedido.
UC14 Registrar e confirmar venda
Identificação
Objetivo: Registrar os dados da venda e confirmar o pedido de compra de um Cliente Empresa.
Atores: Administrador ou Funcionário
Pré-condições: Pedido válido aguardando confirmação; Cliente Empresa ativo; itens disponíveis.
Pós-condições: Venda confirmada e vinculada ao cliente e aos equipamentos.
Relacionamentos: «include» UC15 Atualizar disponibilidade do estoque após a confirmação.
Requisitos e regras: RF03, RF13, RF14; RN03, RN13, RN14
Fluxo principal
1. O ator abre os pedidos pendentes e seleciona um pedido.
2. O sistema apresenta Cliente Empresa, equipamentos, quantidades e valores.
3. O ator verifica os dados, registra a data e a forma de pagamento e confirma a venda.
4. O sistema valida o cliente e a disponibilidade dos itens.
5. O sistema registra a venda como confirmada e executa UC15.
6. O sistema confirma a operação.
Fluxos alternativos
FA1 Ajustar pedido antes da confirmação. O ator atualiza dados permitidos do pedido e retorna à validação do passo 4.
FA2 Cancelar pedido. O ator registra o cancelamento e o sistema não gera venda confirmada nem nota fiscal.
Fluxos de exceção
FE1 Item indisponível, cliente inativo ou dados incompletos. O sistema impede a confirmação e informa o que deve ser corrigido.
UC15 Atualizar disponibilidade do estoque
Identificação
Objetivo: Marcar como vendido e indisponível cada equipamento incluído em venda confirmada.
Atores: UC14, com execução automatizada pelo sistema
Pré-condições: Venda confirmada por UC14.
Pós-condições: Equipamentos vendidos indisponíveis para novas vendas.
Relacionamentos: «include» obrigatório de UC14 após a confirmação.
Requisitos e regras: RF14; RN14
Fluxo principal
1. O sistema recebe a confirmação da venda em UC14.
2. O sistema atualiza a situação dos equipamentos para vendido.
3. O sistema remove os itens da disponibilidade para compra.
4. O sistema confirma a atualização do estoque a UC14.
Fluxos alternativos
Não há fluxo alternativo previsto para esta operação.
Fluxos de exceção
FE1 Falha na atualização. O sistema não deve apresentar a venda como concluída sem atualizar a disponibilidade; registra a falha para correção e evita nova venda dos itens.
UC16 Emitir nota fiscal simulada
Identificação
Objetivo: Gerar a nota fiscal simulada vinculada a uma venda confirmada.
Atores: Administrador
Pré-condições: Administrador autenticado; venda confirmada.
Pós-condições: Nota fiscal simulada emitida com número único e vínculo com a venda.
Relacionamentos: —
Requisitos e regras: RF02, RF19; RN02, RN19; RNF03, RNF05
Fluxo principal
1. O Administrador abre uma venda confirmada e seleciona Emitir nota simulada.
2. O sistema apresenta os dados da venda, do Cliente Empresa, dos equipamentos e dos valores.
3. O Administrador confirma a emissão.
4. O sistema gera número único, registra a data de emissão e vincula a nota à venda.
5. O sistema disponibiliza a nota para consulta e download conforme as permissões.
Fluxos alternativos
FA1 Consultar venda já documentada. Se já existir nota, o sistema apresenta a nota existente e evita emissão duplicada.
Fluxos de exceção
FE1 Venda não confirmada. O sistema impede a emissão.
FE2 Dados da venda inconsistentes. O sistema aponta a inconsistência e não emite a nota.
UC17 Consultar e baixar nota fiscal simulada
Identificação
Objetivo: Consultar ou baixar uma nota fiscal simulada, respeitando o vínculo com a venda e as permissões da organização.
Atores: Administrador ou Cliente Empresa
Pré-condições: Nota fiscal simulada emitida e vinculada a uma venda.
Pós-condições: Nota consultada ou arquivo disponibilizado ao usuário autorizado.
Relacionamentos: —
Requisitos e regras: RF20; RN20; RNF05
Fluxo principal
1. O ator abre Notas fiscais.
2. O sistema apresenta as notas permitidas ao perfil: todas para o Administrador ou somente as próprias compras para o Cliente Empresa.
3. O ator seleciona uma nota.
4. O sistema apresenta os dados e disponibiliza a opção de download.
5. Se solicitado, o sistema gera ou fornece o arquivo da nota simulada.
Fluxos alternativos
FA1 Consultar sem baixar. O ator visualiza a nota e encerra a consulta.
Fluxos de exceção
FE1 Nota inexistente ou não vinculada ao usuário. O sistema nega o acesso e não revela dados de outra organização.
UC18 Consultar histórico de compras
Identificação
Objetivo: Consultar os pedidos e as compras da própria organização.
Atores: Cliente Empresa
Pré-condições: Cliente Empresa autenticada e ativa.
Pós-condições: Histórico próprio apresentado.
Relacionamentos: —
Requisitos e regras: RF04, RF15; RN04, RN15; RNF05
Fluxo principal
1. O Cliente Empresa abre Minhas compras.
2. O sistema localiza pedidos e vendas vinculados à organização autenticada.
3. O sistema apresenta data, situação, itens e valores registrados.
4. O Cliente Empresa seleciona uma operação para consultar seus detalhes.
Fluxos alternativos
Não há fluxo alternativo previsto para esta operação.
Fluxos de exceção
FE1 Tentativa de consultar registro de outra organização. O sistema nega o acesso.
UC21 Consultar histórico geral de vendas
Identificação
Objetivo: Consultar todas as vendas registradas e localizar operações por período, Cliente Empresa ou situação.
Atores: Administrador ou Funcionário
Pré-condições: Usuário interno autenticado.
Pós-condições: Histórico geral ou detalhes de uma venda apresentados.
Relacionamentos: —
Requisitos e regras: RF15; RN15; RNF05
Fluxo principal
1. O ator abre Histórico de vendas.
2. O sistema apresenta as vendas registradas.
3. O ator informa filtros de período, Cliente Empresa ou situação.
4. O sistema apresenta os resultados correspondentes.
5. O ator seleciona uma venda para consultar seus detalhes.
Fluxos alternativos
FA1 Consulta sem filtros. O sistema apresenta todo o histórico autorizado.
Fluxos de exceção
FE1 Usuário externo tenta consultar o histórico geral. O sistema nega o acesso.

## Requisitos e regras citados

RF13 – Gestão de vendas
Descrição: O sistema deve permitir que o Administrador ou Funcionário registre e acompanhe vendas de equipamentos recondicionados para Clientes Empresa.
Critério de aceitação: Cada venda deve registrar Cliente Empresa, equipamentos, quantidades, valores, data, forma de pagamento e situação. O sistema deve permitir que o Cliente Empresa acompanhe suas próprias compras.
Regra de negócio: RN13: Uma venda deve estar vinculada a um Cliente Empresa ativo e a pelo menos um equipamento. Somente equipamentos ativos, disponíveis e aptos ao reuso podem ser incluídos em nova venda. Cliente ONG não realiza compra, conforme o escopo definido para este perfil.
História de usuário: Como Administrador ou Funcionário, quero registrar e acompanhar vendas de equipamentos recondicionados para Empresas, para controlar as operações e seus dados.
RF14 – Atualização de estoque
Descrição: O sistema deve atualizar a disponibilidade do equipamento após a confirmação da venda.
Critério de aceitação: Ao confirmar uma venda, o sistema deve marcar o equipamento como vendido e indisponível e impedir sua inclusão em outra venda.
Regra de negócio: RN14: Após a confirmação da venda, o equipamento deve ser considerado vendido e indisponível para novas vendas.
História de usuário: Como Administrador ou Funcionário, quero que a confirmação da venda torne o equipamento indisponível automaticamente, para evitar que seja vendido novamente.
RF15 – Histórico de vendas
Descrição: O sistema deve permitir que o Administrador ou Funcionário consulte o histórico geral de vendas.
Critério de aceitação: A consulta deve permitir filtrar as vendas por período, Cliente Empresa e situação. O Cliente Empresa pode consultar somente as próprias compras.
Regra de negócio: RN15: Somente Administrador e Funcionário podem consultar o histórico geral. O Cliente Empresa pode consultar apenas suas próprias compras. Cliente ONG consulta seus próprios registros de doação, não o histórico geral de vendas.
RF19 – Emissão de nota fiscal simulada
Descrição: O sistema deve permitir a emissão de uma nota fiscal simulada referente à venda de equipamentos recondicionados para Cliente Empresa.
Critério de aceitação: Após a confirmação da venda, o Administrador deve conseguir gerar uma nota fiscal simulada com número próprio e único, Cliente Empresa, equipamentos, valores e data de emissão.
Regra de negócio: RN19: A nota fiscal simulada somente pode ser emitida para venda confirmada. Cliente, equipamentos e valores devem corresponder à venda vinculada. Cada nota fiscal simulada deve possuir número único e data de emissão. Somente o Administrador pode emitir notas fiscais simuladas.
História de usuário: Como Administrador, quero emitir uma nota fiscal simulada após a confirmação da venda, para registrar os dados da operação no projeto acadêmico.
RF20 – Consulta de nota fiscal simulada
Descrição: O sistema deve permitir que o Administrador e o Cliente Empresa vinculado à venda consultem e baixem as notas fiscais simuladas emitidas.
Critério de aceitação: A nota fiscal simulada deve permanecer vinculada à venda. O Administrador pode consultar todas as notas emitidas; o Cliente Empresa pode consultar e baixar somente as notas de suas próprias compras.
Regra de negócio: RN20: A nota fiscal simulada deve permanecer vinculada à venda correspondente após sua emissão. Somente o Administrador e o Cliente Empresa da venda podem consultar e baixar a respectiva nota.
História de usuário: Como Cliente Empresa, quero consultar e baixar as notas fiscais simuladas das minhas compras, para guardar os documentos dessas operações. Como Administrador, quero consultar e baixar as notas emitidas, para conferir os documentos das vendas.
