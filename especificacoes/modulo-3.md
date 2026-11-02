# Módulo 3 – Equipamentos e categorias (UC05, UC07, UC08)

Fonte: `Projeto_LEAF_TI.docx` (`docs/Projeto_LEAF_TI.docx`)
## Casos de uso

### UC05 Manter categorias de equipamentos
**Identificação**
- Objetivo: Cadastrar e manter categorias, incluindo as seis categorias mínimas exigidas para classificar equipamentos.
- Atores: Administrador
- Pré-condições: Administrador autenticado.
- Pós-condições: Categorias cadastradas ou atualizadas; equipamentos existentes preservados.
- Relacionamentos: —
- Requisitos e regras: RF07, RF08; RN07, RN08

**Fluxo principal**
1. O Administrador abre Categorias e seleciona Nova categoria.
2. O sistema solicita o nome da categoria.
3. O Administrador informa o nome e confirma.
4. O sistema valida o campo e salva a categoria como ativa.
5. O sistema disponibiliza a categoria para o cadastro de equipamentos.
6. O sistema deve manter pelo menos estas seis categorias: computadores, notebooks, monitores, periféricos, placas de vídeo e placas-mãe.

**Fluxos alternativos**
- FA1 Consultar ou alterar categoria. O Administrador seleciona uma categoria, consulta ou altera seu nome e confirma. O sistema preserva os vínculos com equipamentos existentes.
- FA2 Desativar categoria. O Administrador confirma a desativação. O sistema impede novas seleções e preserva os vínculos existentes.

**Fluxos de exceção**
- FE1 Nome ausente. O sistema solicita o preenchimento antes de salvar.
- FE2 Falha ao salvar. O sistema informa que a alteração não foi concluída.
- FE3 Nome inválido ou duplicado. O sistema informa o problema e retorna ao formulário sem salvar. **[M3]**
- FE4 Categoria protegida. O Administrador tenta desativar ou renomear uma das seis categorias iniciais. O sistema nega a operação e mantém a categoria sem alterações. **[M3]**

### UC07 Manter cadastro de equipamentos
**Identificação**
- Objetivo: Registrar e atualizar os equipamentos controlados pela LEAF TI, vinculando categoria, origem, condição e situação.
- Atores: Administrador ou Funcionário
- Pré-condições: Usuário interno autenticado e autorizado; categoria ativa disponível.
- Pós-condições: Equipamento registrado ou atualizado com identificação única.
- Relacionamentos: —
- Requisitos e regras: RF08, RF11; RN08, RN11; RNF04

**Fluxo principal**
1. O ator abre Equipamentos e seleciona Novo equipamento.
2. O sistema apresenta as categorias ativas e os campos do cadastro.
3. O ator informa identificação, categoria, descrição ou modelo, condição, origem, data de recebimento, valor quando aplicável e situação.
4. Se o equipamento veio de uma solicitação de Empresa Doadora, o ator vincula o registro à solicitação correspondente.
5. O sistema valida os campos, a identificação única e a categoria ativa.
6. O sistema salva o equipamento e confirma a operação.

**Fluxos alternativos**
- FA1 Consultar ou alterar. O ator seleciona um equipamento e consulta ou atualiza os dados autorizados. Uma categoria desativada já vinculada pode permanecer no registro, mas não pode ser escolhida como nova categoria.
- FA2 Desativar. O ator confirma a desativação. O sistema preserva o histórico e impede novas vendas do item.

**Fluxos de exceção**
- FE1 Identificação duplicada, categoria inativa ou dados inválidos. O sistema explica o problema e retorna ao formulário sem salvar.

### UC08 Atualizar situação do equipamento
**Identificação**
- Objetivo: Registrar a situação atual do equipamento durante avaliação, recondicionamento e destinação.
- Atores: Administrador ou Funcionário
- Pré-condições: Equipamento cadastrado.
- Pós-condições: Situação atualizada e histórico do equipamento consistente.
- Relacionamentos: Pode ser executado por UC10 e UC11 para registrar as mudanças decorrentes da avaliação e da doação.
- Requisitos e regras: RF12; RN12

**Fluxo principal**
1. O ator abre o cadastro de um equipamento e seleciona Atualizar situação.
2. O sistema apresenta as situações permitidas.
3. O ator seleciona a situação correspondente: recebido, em avaliação, em manutenção, recondicionado, disponível, vendido, doado ou destinado à reciclagem.
4. Se selecionar doado, o ator informa a ONG beneficiada e a data da doação.
5. O sistema valida os dados e atualiza a situação atual.

**Fluxos alternativos**
- FA1 Atualizar durante processamento. O ator registra uma nova situação após avaliação ou recondicionamento; o sistema mantém a situação atualizada.

**Fluxos de exceção**
- FE1 Dados da doação ausentes. O sistema não registra a situação “doado” sem ONG beneficiada e data.
- FE2 Equipamento destinado à reciclagem. O sistema impede que o item seja disponibilizado para venda ou doação.

## Requisitos funcionais e regras relacionados

### RF07 – Cadastro de categorias
Descrição: O sistema deve permitir que o Administrador cadastre, altere e desative categorias de equipamentos.
Critério de aceitação: O Administrador deve conseguir gerenciar categorias sem excluir equipamentos já vinculados a elas.
Regra de negócio: RN07: Uma categoria desativada não pode ser selecionada para novos equipamentos. A desativação deve preservar os equipamentos e os vínculos existentes.
História de usuário: Como Administrador, quero gerenciar categorias de equipamentos, para organizar o catálogo e preservar os registros existentes.

### RF08 – Categorias de equipamentos
Descrição: O sistema deve disponibilizar no mínimo seis categorias para classificar os equipamentos: computadores, notebooks, monitores, periféricos, placas de vídeo e placas-mãe.
Critério de aceitação: O sistema deve disponibilizar pelo menos seis categorias. Cada equipamento cadastrado deve estar associado a uma categoria ativa. As seis categorias iniciais são computadores, notebooks, monitores, periféricos, placas de vídeo e placas-mãe. Outras categorias podem ser incluídas pelo Administrador.
Regra de negócio: RN08: Todo equipamento deve estar associado a uma categoria ativa. Categorias inativas não podem ser selecionadas para novos equipamentos nem para alteração de categoria.
História de usuário: Como Administrador ou Funcionário, quero classificar cada equipamento em uma categoria ativa, para manter o catálogo organizado.

### RF11 – Gestão de equipamentos
Descrição: O sistema deve permitir que o Administrador e o Funcionário cadastrem, consultem e alterem os equipamentos registrados pela LEAF TI.
Critério de aceitação: Cada equipamento deve possuir identificação, categoria, descrição ou modelo, condição avaliada, origem, data de recebimento, valor quando aplicável e situação. O equipamento deve estar associado a uma categoria ativa. Quando sua origem for uma solicitação de uma Empresa Doadora, deve ser possível vinculá-lo à solicitação correspondente.
Regra de negócio: RN11: Todo equipamento deve estar associado a uma categoria ativa. O tipo, modelo e quantidade informados pela Empresa Doadora devem ficar registrados na solicitação correspondente. A avaliação da condição e a destinação são responsabilidades do Administrador ou Funcionário. Equipamentos aptos ao reuso podem ser disponibilizados para venda ou destinados à doação. Equipamentos sem condições de reuso devem ser registrados como destinados à reciclagem. O registro não inclui coleta ou transporte.
História de usuário: Como Administrador ou Funcionário, quero registrar e atualizar os equipamentos, incluindo categoria, condição, origem e situação, para controlar seu processamento e sua destinação.

### RF12 – Situação do equipamento
Descrição: O sistema deve permitir que o Administrador ou Funcionário atualize a situação do equipamento durante seu processamento.
Critério de aceitação: O equipamento deve possuir uma situação: recebido, em avaliação, em manutenção, recondicionado, disponível, vendido, doado ou destinado à reciclagem. Ao registrar uma doação, devem ser informadas a ONG beneficiada e a data da doação. Equipamentos sem condições de reuso devem ser destinados à reciclagem.
Regra de negócio: RN12: Cada equipamento deve possuir uma única situação atual. Um equipamento marcado como doado deve estar vinculado a uma ONG beneficiada e à data da doação. Equipamentos destinados à reciclagem não podem ser disponibilizados para venda ou doação.
História de usuário: Como Administrador ou Funcionário, quero atualizar a situação do equipamento durante seu processamento, para acompanhar sua etapa até a venda, doação ou reciclagem.

### Regras de outros requisitos que afetam este módulo
- RN13 (RF13, trecho): Somente equipamentos ativos, disponíveis e aptos ao reuso podem ser incluídos em nova venda.
- RN14 (RF14): Após a confirmação da venda, o equipamento deve ser considerado vendido e indisponível para novas vendas.
- RN21 (RF21, trecho): O registro da solicitação não disponibiliza automaticamente os equipamentos no catálogo. A avaliação e a definição da destinação são realizadas pelo Administrador ou Funcionário. A impossibilidade de reuso determina o encaminhamento à reciclagem, não a recusa. O registro não inclui coleta ou transporte.
- RN01: O acesso deve limitar-se às operações autorizadas para o perfil do usuário.
- RN03 (trecho): O Funcionário pode executar as operações internas definidas para seu perfil.

## Requisitos não funcionais relacionados
- **RNF04 – Validação de dados.** Campos obrigatórios e formatos inválidos devem ser apontados com mensagens claras.
- **RNF05 – Controle de acesso.** Apenas usuários autenticados e autorizados conforme o perfil.
- **RNF01, RNF06:** legibilidade (16 px) e acessibilidade nas telas.

## Modelo de dados (seção 6 do documento)
- 6.2 EQUIPAMENTO registra cada item físico, com identificação única, modelo, categoria, origem, condição, situação, data de recebimento e valor, quando aplicável. Um equipamento pode vir de um item de solicitação.
- 6.2 CATEGORIA organiza os equipamentos; cada equipamento deve estar associado a uma categoria ativa.
- 6.2 DOAÇÃO registra equipamento destinado a uma ONG e a data correspondente.

## Acréscimos da versão M3 (texto já aplicado no documento)
- **RN07:** O nome da categoria é único, sem diferenciar maiúsculas de minúsculas. Categorias não são excluídas: apenas desativadas.
- **RF08 critério:** As seis categorias iniciais são criadas pelo sistema, não podem ser desativadas nem renomeadas, e permanecem sempre disponíveis.
- **RF11 critério:** A identificação é informada pelo usuário e deve ser única, sem diferenciar maiúsculas de minúsculas. A condição avaliada é uma entre: A avaliar, Bom, Regular, Necessita reparo e Sem condições de reuso. A origem é um texto livre. A data de recebimento não pode ser futura. O valor, quando informado, não pode ser negativo e tem no máximo duas casas decimais. Cada equipamento é ativo ou inativo; a desativação preserva o histórico, impede novas vendas e destinações do item e pode ser desfeita.
- **RN11:** Somente a condição Sem condições de reuso impede a disponibilização para venda ou doação.
- **RF12 critério:** A situação vendido não é informada manualmente: resulta da confirmação da venda (RF14). As situações vendido, doado e destinado à reciclagem são finais e não podem ser alteradas depois de registradas. A situação disponível exige condição que permita o reuso, valor informado maior que zero e equipamento ativo. Equipamentos vendidos ou doados não podem mais ser alterados.
- **RN12:** Equipamentos inativos não podem ser disponibilizados para venda nem destinados à doação. A doação exige ONG beneficiária ativa do tipo Cliente ONG e data da doação não futura e não anterior à data de recebimento. A impossibilidade de reuso só permite as situações recebido, em avaliação e destinado à reciclagem.
- **UC05:** passo 6 acrescenta "Essas seis categorias não podem ser desativadas nem renomeadas."; FE3 e FE4 acima.
- **UC07:** passo 3 acrescenta "A origem é informada em texto livre e a condição é escolhida entre as opções previstas."; FA2 passa a "Desativar ou reativar. O ator confirma a desativação ou a reativação. A desativação preserva o histórico e impede novas vendas e destinações do item."; **FE2 Equipamento finalizado** (vendido ou doado não pode ser alterado nem desativado); **FE3 Condição incompatível com a situação** (Sem condições de reuso só para recebidos, em avaliação ou destinados à reciclagem).
- **UC08:** passo 3 acrescenta "A situação vendido não é informada manualmente: é registrada pela confirmação da venda."; passo 4: a ONG deve estar ativa e ser do tipo Cliente ONG e a data não pode ser futura nem anterior ao recebimento; **FE3 Transição não permitida** (situação atual final, ou disponível sem condição apta, sem valor maior que zero ou com equipamento inativo); relacionamentos acrescenta "A situação doado registra a doação (UC11) na mesma operação."
- **6.2 EQUIPAMENTO:** O equipamento é ativo ou inativo; a desativação preserva o histórico.
- **Modelo físico (DP-30 A):** `EQUIPAMENTO.ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1))` já aplicado em `banco/Codigo_Modelo_Fisico.sql`.

## Observações do coordenador (não fazem parte do documento)
- **Lacunas do documento que bloqueiam o contrato** (ver `docs/DECISOES_PENDENTES.md`, DP-30 em diante): (1) `EQUIPAMENTO` não tem coluna de situação "ativo/inativo", mas UC07 FA2 e RN13 falam em "desativar"/"equipamentos ativos"; o modelo não pode ser alterado sem passar pelo documento; (2) valores de `condicao` e `origem` não definidos; (3) transições de situação e uso de "vendido"/"doado"; (4) tratamento das seis categorias iniciais; (5) vínculo com `ITEM_SOLICITACAO`, cujo cadastro é do Módulo 4.
- Do que já foi decidido: o login e a organização inativa não afetam este módulo; ONG beneficiada é organização do tipo Cliente ONG com situação `Ativa` (Módulo 2, `Ativa`/`Inativa`).
- A situação "doado" grava uma linha em `DOACAO`; o Módulo 4 (UC10/UC11) reaproveitará essa lógica.
