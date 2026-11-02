# Módulo 4 – Solicitações e doações (UC09, UC10, UC11, UC19, UC20)

Fonte: `Projeto_LEAF_TI.docx` (`docs/Projeto_LEAF_TI.docx`)

## Casos de uso

UC09 Solicitar avaliação de equipamentos
Identificação
Objetivo: Informar equipamentos que possui para que a LEAF TI avalie suas condições e registre a destinação adequada.
Atores: Empresa Doadora
Pré-condições: Empresa Doadora autenticada e ativa, com vínculo de parceria ativo.
Pós-condições: Solicitação registrada e disponível para análise pela LEAF TI.
Relacionamentos: —
Requisitos e regras: RF05, RF10, RF21; RN05, RN10, RN21
Fluxo principal
1. A Empresa Doadora abre Solicitações de avaliação e seleciona Nova solicitação.
2. O sistema solicita tipo, modelo e quantidade dos equipamentos.
3. A Empresa Doadora informa os dados dos itens e confirma a solicitação.
4. O sistema valida os campos e associa a solicitação à organização autenticada.
5. O sistema registra a solicitação como aguardando avaliação e confirma o envio.
Fluxos alternativos
FA1 Consultar solicitação. A Empresa Doadora seleciona uma solicitação própria e consulta os dados e a situação atual.
Fluxos de exceção
FE1 Dados obrigatórios ausentes ou quantidade inválida. O sistema solicita correção e não registra a solicitação.
FE2 Organização inativa. O sistema impede o envio de novas solicitações.
FE3 Parceria ausente ou desativada. O sistema impede o envio da solicitação e informa que a Empresa Doadora precisa de vínculo de parceria ativo.
UC10 Avaliar e definir destinação dos equipamentos
Identificação
Objetivo: Registrar a condição de cada equipamento informado pela Empresa Doadora e definir seu reaproveitamento ou reciclagem.
Atores: Administrador ou Funcionário
Pré-condições: Solicitação registrada e disponível para análise.
Pós-condições: Avaliação e destinação registradas individualmente para cada equipamento.
Relacionamentos: «include» UC08 Atualizar situação do equipamento. «extend» UC11 Registrar destinação para doação, quando essa destinação for escolhida.
Requisitos e regras: RF03, RF05, RF11, RF12, RF21; RN03, RN05, RN11, RN12, RN21
Fluxo principal
1. O ator abre uma solicitação pendente de avaliação.
2. O sistema apresenta os itens e as quantidades informadas pela Empresa Doadora.
3. O ator examina cada item e registra a condição avaliada.
4. O ator define para cada equipamento uma destinação: venda, doação ou reciclagem.
5. O sistema executa UC08 para registrar a situação correspondente de cada item.
6. Se a destinação for doação, o sistema aciona UC11 sob a condição indicada.
7. O sistema salva a avaliação e atualiza a situação da solicitação e dos equipamentos.
Fluxos alternativos
FA1 Itens com destinos diferentes. O ator atribui destinações distintas a itens de uma mesma solicitação, conforme as condições avaliadas.
FA2 Recondicionamento necessário. O ator registra a situação de manutenção e, após o recondicionamento, atualiza a avaliação e a destinação.
Fluxos de exceção
FE1 Equipamento sem condições de reuso. O ator registra destinação à reciclagem. O sistema impede sua disponibilização para venda ou doação.
FE2 Avaliação incompleta. O sistema não conclui a solicitação enquanto houver equipamento sem condição avaliada ou sem destinação registrada.
UC11 Registrar destinação para doação
Identificação
Objetivo: Registrar a ONG que receberá os equipamentos definidos para doação.
Atores: Administrador ou Funcionário
Pré-condições: Avaliação concluída para equipamento com destinação para doação; ONG beneficiária ativa.
Pós-condições: Doação vinculada ao equipamento e à ONG, com data registrada.
Relacionamentos: «extend» UC10 Avaliar e definir destinação dos equipamentos [quando a destinação escolhida for doação].
Requisitos e regras: RF12, RF21; RN12, RN21
Fluxo principal
1. Durante UC10, o ator seleciona a destinação para doação.
2. O sistema apresenta as ONGs ativas elegíveis.
3. O ator seleciona a ONG beneficiária e informa a data da doação.
4. O sistema valida o vínculo e registra a situação “doado”.
5. O sistema confirma a destinação.
Fluxos alternativos
Não há fluxo alternativo previsto para esta operação.
Fluxos de exceção
FE1 ONG beneficiária ausente ou inativa. O sistema não conclui a destinação e solicita outra ONG.
FE2 Equipamento sem condições de reuso. O sistema não permite a doação e exige a destinação à reciclagem.
UC19 Consultar doações e equipamentos destinados à ONG
Identificação
Objetivo: Acompanhar as doações e os equipamentos destinados à própria ONG.
Atores: Cliente ONG
Pré-condições: Cliente ONG autenticada e ativa.
Pós-condições: Registros de doação próprios apresentados.
Relacionamentos: —
Requisitos e regras: RF04, RF12, RF15; RN04, RN12, RN15; RNF05
Fluxo principal
1. O Cliente ONG abre Doações e equipamentos destinados.
2. O sistema localiza os registros vinculados à ONG autenticada.
3. O sistema apresenta equipamento, situação e data de doação, quando registrada.
4. O Cliente ONG seleciona um registro para consultar seus detalhes.
Fluxos alternativos
FA1 Consultar sem registros. O sistema informa que ainda não há doações ou equipamentos destinados à ONG.
Fluxos de exceção
FE1 Tentativa de consultar registros de outra ONG. O sistema nega o acesso.
UC20 Consultar solicitações e resultados da avaliação
Identificação
Objetivo: Acompanhar as solicitações de equipamentos enviadas e consultar os resultados registrados pela LEAF TI.
Atores: Empresa Doadora
Pré-condições: Empresa Doadora autenticada e ativa.
Pós-condições: Solicitações próprias e respectivas situações apresentadas.
Relacionamentos: —
Requisitos e regras: RF05, RF21; RN05, RN21; RNF05
Fluxo principal
1. A Empresa Doadora abre Minhas solicitações.
2. O sistema localiza somente solicitações vinculadas à organização autenticada.
3. O sistema apresenta os itens informados, a situação da solicitação, as condições avaliadas e a destinação registrada pela LEAF TI.
4. A Empresa Doadora seleciona uma solicitação para consultar seus detalhes.
Fluxos alternativos
FA1 Solicitação ainda não avaliada. O sistema apresenta a situação pendente sem inventar avaliação ou destinação.
Fluxos de exceção
FE1 Tentativa de consultar solicitação de outra empresa. O sistema nega o acesso.

## Requisitos e regras citados

Regra de negócio: RN04: Cliente Empresa pode consultar somente seus pedidos, compras e documentos correspondentes. Cliente ONG pode consultar somente suas doações, solicitações e equipamentos vinculados. Cada cliente pode cadastrar usuários somente para sua própria organização, sem conceder permissões administrativas nem acessar dados de terceiros.
RF05 – Perfil de Empresa Doadora
Descrição: O sistema deve permitir que a Empresa Doadora solicite à LEAF TI a avaliação dos equipamentos eletrônicos que possui e deseja disponibilizar para possível venda, doação ou reciclagem.
Critério de aceitação: A Empresa Doadora deve registrar tipo, modelo e quantidade dos equipamentos. A LEAF TI deve avaliar a condição dos itens e registrar a destinação de cada um: disponibilização para venda, encaminhamento para doação ou reciclagem quando não houver condições de reuso. A Empresa Doadora pode consultar somente as próprias solicitações e os resultados correspondentes.
Regra de negócio: RN05: A solicitação deve estar vinculada a uma Empresa Doadora cadastrada e ativa. A Empresa Doadora informa tipo, modelo e quantidade; a avaliação da condição e a definição da destinação são responsabilidades da LEAF TI. Equipamentos sem condições de reuso devem ser encaminhados à reciclagem, não recusados por esse motivo.
RF10 – Gestão de parceiros
Descrição: O sistema deve permitir que o Administrador cadastre, consulte, altere e desative os parceiros da LEAF TI.
Critério de aceitação: O cadastro deve associar o parceiro a uma organização e identificar sua atuação como Empresa Doadora ou Patrocinador em Potencial, além da situação da parceria. Nome ou razão social, CNPJ, contato e endereço são reutilizados do cadastro da organização, sem duplicação. A Empresa Doadora só será considerada parceira quando esse vínculo for registrado explicitamente, e a atuação como Empresa Doadora exige que a organização seja desse tipo. A situação da parceria é Ativa ou Inativa. Cada organização possui no máximo um vínculo de parceria, que só pode ser registrado ou reativado para organização ativa. A organização de um vínculo não pode ser trocada depois de registrada. A atuação como Patrocinador em Potencial é permitida para qualquer tipo de organização.
Regra de negócio: RN10: Somente parceiros cadastrados e ativos podem ser associados às operações que dependam de parceria. A operação que depende de parceria é o registro de solicitação de avaliação de equipamentos (RF21): somente uma Empresa Doadora com vínculo de parceria ativo pode registrá-la. A desativação da parceria preserva as solicitações já registradas e impede novas.
Regra de negócio: RN11: Todo equipamento deve estar associado a uma categoria ativa. O tipo, modelo e quantidade informados pela Empresa Doadora devem ficar registrados na solicitação correspondente. A avaliação da condição e a destinação são responsabilidades do Administrador ou Funcionário. Equipamentos aptos ao reuso podem ser disponibilizados para venda ou destinados à doação. Equipamentos sem condições de reuso devem ser registrados como destinados à reciclagem. O registro não inclui coleta ou transporte. Somente a condição Sem condições de reuso impede a disponibilização para venda ou doação.
RF15 – Histórico de vendas
Descrição: O sistema deve permitir que o Administrador ou Funcionário consulte o histórico geral de vendas.
Critério de aceitação: A consulta deve permitir filtrar as vendas por período, Cliente Empresa e situação. O Cliente Empresa pode consultar somente as próprias compras.
Regra de negócio: RN15: Somente Administrador e Funcionário podem consultar o histórico geral. O Cliente Empresa pode consultar apenas suas próprias compras. Cliente ONG consulta seus próprios registros de doação, não o histórico geral de vendas.
RF21 – Solicitação, avaliação e destinação de equipamentos
Descrição: O sistema deve permitir o registro de solicitações de Empresas Doadoras e o registro, pela LEAF TI, da avaliação e da destinação dos equipamentos para venda, doação ou reciclagem.
Critério de aceitação: A solicitação só pode ser registrada por Empresa Doadora com vínculo de parceria ativo (RN10) e deve registrar a Empresa Doadora e os tipos, modelos e quantidades informados. O Administrador ou Funcionário deve registrar a condição avaliada de cada equipamento, atualizar sua situação durante eventual recondicionamento e definir sua destinação. Equipamentos aptos ao reuso podem ser disponibilizados para venda ou destinados à doação. Aqueles sem condições de reuso devem ser registrados como destinados à reciclagem, sem disponibilização para compra ou doação.
Regra de negócio: RN21: O registro da solicitação não disponibiliza automaticamente os equipamentos no catálogo. A avaliação e a definição da destinação são realizadas pelo Administrador ou Funcionário. Equipamentos de uma mesma solicitação podem receber destinações diferentes conforme suas condições. A impossibilidade de reuso determina o encaminhamento à reciclagem, não a recusa. O registro não inclui coleta ou transporte.

Critério de aceitação: O equipamento deve possuir uma situação: recebido, em avaliação, em manutenção, recondicionado, disponível, vendido, doado ou destinado à reciclagem. Ao registrar uma doação, devem ser informadas a ONG beneficiada e a data da doação. Equipamentos sem condições de reuso devem ser destinados à reciclagem. A situação vendido não é informada manualmente: resulta da confirmação da venda (RF14). As situações vendido, doado e destinado à reciclagem são finais e não podem ser alteradas depois de registradas. A situação disponível exige condição que permita o reuso, valor informado maior que zero e equipamento ativo. Equipamentos vendidos ou doados não podem mais ser alterados.
Regra de negócio: RN12: Cada equipamento deve possuir uma única situação atual. Um equipamento marcado como doado deve estar vinculado a uma ONG beneficiada e à data da doação. Equipamentos destinados à reciclagem não podem ser disponibilizados para venda ou doação. Equipamentos inativos não podem ser disponibilizados para venda nem destinados à doação. A doação exige ONG beneficiária ativa do tipo Cliente ONG e data da doação não futura e não anterior à data de recebimento. A impossibilidade de reuso só permite as situações recebido, em avaliação e destinado à reciclagem.
