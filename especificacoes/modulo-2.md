# Módulo 2 – Organizações e parceiros (UC01, UC06, UC25)

Fonte: `Projeto_LEAF_TI.docx` (`docs/Projeto_LEAF_TI.docx`)
## Casos de uso

### UC01 Manter cadastro de organizações e clientes
**Identificação**
- Objetivo: Cadastrar e manter as organizações que participam da LEAF TI, identificando se atuam como Cliente Empresa, Cliente ONG ou Empresa Doadora.
- Atores: Administrador
- Pré-condições: Administrador autenticado.
- Pós-condições: Organização cadastrada ou atualizada, com situação definida.
- Relacionamentos: «include» UC25 Validar unicidade do CNPJ.
- Requisitos e regras: RF06, RF09; RN06, RN09

**Fluxo principal**
1. O Administrador abre Organizações e seleciona Novo cadastro.
2. O sistema apresenta os campos de identificação, CNPJ, contato, endereço, tipo de organização e situação.
3. O Administrador informa os dados e classifica a organização como Cliente Empresa, Cliente ONG ou Empresa Doadora.
4. O sistema executa UC25 Validar unicidade do CNPJ e verifica os campos obrigatórios.
5. Com os dados válidos, o sistema salva a organização e confirma o cadastro.

**Fluxos alternativos**
- FA1 Consultar ou alterar. O Administrador seleciona uma organização cadastrada. O sistema apresenta seus dados; após alterações, valida novamente o CNPJ e salva.
- FA2 Desativar. O Administrador confirma a desativação. O sistema preserva registros anteriores e impede novas operações da organização.

**Fluxos de exceção**
- FE1 CNPJ duplicado ou inválido. O sistema informa o problema e retorna ao formulário, sem salvar.
- FE2 Dados obrigatórios ausentes. O sistema aponta os campos pendentes e mantém o formulário para correção.

### UC06 Manter cadastro de parceiros
**Identificação**
- Objetivo: Registrar e manter o vínculo formal de parceria com uma organização cadastrada, identificando a atuação como Empresa Doadora ou Patrocinador em Potencial. Ser Empresa Doadora, por si só, não cria uma parceria.
- Atores: Administrador
- Pré-condições: Administrador autenticado; organização previamente cadastrada.
- Pós-condições: Vínculo de parceiro cadastrado ou atualizado, sem duplicar os dados da organização; registros anteriores preservados.
- Relacionamentos: —
- Requisitos e regras: RF10; RN10

**Fluxo principal**
1. O Administrador abre Parceiros e seleciona Novo parceiro.
2. O sistema apresenta o formulário.
3. O Administrador seleciona uma organização, identifica sua atuação na parceria e informa a situação do vínculo.
4. O sistema valida a organização e os dados da parceria e salva o vínculo.
5. O sistema confirma o cadastro.

**Fluxos alternativos**
- FA1 Consultar ou alterar. O Administrador seleciona um parceiro e consulta ou atualiza os dados.
- FA2 Desativar. O Administrador confirma a desativação. O sistema preserva registros anteriores e impede novas associações do parceiro.

**Fluxos de exceção**
- FE1 Dados inválidos. O sistema identifica os campos que precisam de correção e não salva a alteração.
- FE2 Atuação incompatível com a organização. Se a atuação escolhida for Empresa Doadora e a organização não for do tipo Empresa Doadora, o sistema não salva o vínculo e informa a incompatibilidade.

### UC25 Validar unicidade do CNPJ
**Identificação**
- Objetivo: Verificar se o CNPJ informado está em formato válido e não está associado a outra organização.
- Atores: UC01, processado pelo sistema
- Pré-condições: Cadastro ou alteração de organização iniciado em UC01.
- Pós-condições: CNPJ considerado disponível ou duplicidade informada.
- Relacionamentos: «include» de UC01.
- Requisitos e regras: RF06, RF09; RN06, RN09; RNF04

**Fluxo principal**
1. O sistema recebe o CNPJ informado no cadastro ou alteração.
2. O sistema valida o formato e consulta os registros existentes, excluindo o próprio registro durante uma alteração.
3. Se o CNPJ estiver disponível, o sistema autoriza a continuação do fluxo principal.

**Fluxos alternativos**
Não há fluxo alternativo previsto para esta operação.

**Fluxos de exceção**
- FE1 CNPJ já utilizado ou em formato inválido. O sistema informa o problema e devolve o fluxo a UC01 para correção.

## Requisitos funcionais e regras relacionados

### RF06 – Gestão de empresas e ONGs
Descrição: O sistema deve permitir que o Administrador cadastre, consulte, altere e desative empresas e ONGs participantes da LEAF TI.
Critério de aceitação: O cadastro deve armazenar razão social ou nome, CNPJ, endereço, telefone, e-mail, tipo de organização e situação. Uma organização pode ser classificada como Cliente Empresa, Cliente ONG ou Empresa Doadora, conforme sua finalidade no sistema.
Regra de negócio: RN06: O CNPJ deve ser único entre as organizações cadastradas. Uma organização desativada não pode realizar novas operações no sistema.
História de usuário: Como Administrador, quero gerenciar empresas e ONGs participantes da LEAF TI, para manter atualizados os dados das organizações.

### RF09 – Gestão de clientes organizacionais
Descrição: O sistema deve permitir que o Administrador cadastre, consulte, altere e desative clientes organizacionais classificados como Empresa ou ONG. O Funcionário pode consultar e alterar os dados autorizados.
Critério de aceitação: O cadastro deve armazenar razão social ou nome da organização, CNPJ, endereço, telefone, e-mail, tipo de cliente e situação. O sistema deve distinguir Cliente Empresa de Cliente ONG para liberar as operações correspondentes.
Regra de negócio: RN09: O CNPJ deve ser único entre os clientes organizacionais. Um cliente desativado não pode realizar novas compras nem participar de novas operações como cliente. Clientes Empresa e Cliente ONG podem cadastrar usuários vinculados à própria organização conforme RF02.
História de usuário: Como Administrador, quero gerenciar os cadastros de Empresas e ONGs clientes, para manter atualizadas as organizações participantes. Como Funcionário, quero consultar e atualizar os dados autorizados, para executar as operações da LEAF TI.

### RF10 – Gestão de parceiros
Descrição: O sistema deve permitir que o Administrador cadastre, consulte, altere e desative os parceiros da LEAF TI.
Critério de aceitação: O cadastro deve associar o parceiro a uma organização e identificar sua atuação como Empresa Doadora ou Patrocinador em Potencial, além da situação da parceria. Nome ou razão social, CNPJ, contato e endereço são reutilizados do cadastro da organização, sem duplicação. A Empresa Doadora só será considerada parceira quando esse vínculo for registrado explicitamente, e a atuação como Empresa Doadora exige que a organização seja desse tipo.
Regra de negócio: RN10: Somente parceiros cadastrados e ativos podem ser associados às operações que dependam de parceria. A operação que depende de parceria é o registro de solicitação de avaliação de equipamentos (RF21): somente uma Empresa Doadora com vínculo de parceria ativo pode registrá-la. A desativação da parceria preserva as solicitações já registradas e impede novas.
História de usuário: Como Administrador, quero registrar e manter organizações parceiras, identificando se atuam como Empresas Doadoras ou Patrocinadores em Potencial, para manter atualizadas as colaborações da LEAF TI.

### RF03 – Perfil de funcionário (trechos que afetam este módulo)
Critério de aceitação: O Funcionário deve conseguir consultar e alterar dados autorizados de clientes, gerenciar equipamentos, analisar solicitações de equipamentos de Empresas Doadoras, registrar e acompanhar vendas e consultar relatórios. As operações exclusivas do Administrador devem permanecer bloqueadas.
Regra de negócio: RN03: O Funcionário pode executar as operações internas definidas para seu perfil, mas não pode cadastrar usuários, atribuir perfis, gerenciar permissões ou emitir notas fiscais simuladas. O Funcionário e a Empresa Doadora não acessam o cadastro de usuários.

### Regras de perfil
- RN01: O acesso deve limitar-se às operações autorizadas para o perfil do usuário.
- RN04 (trecho): Cliente Empresa pode consultar somente seus pedidos, compras e documentos correspondentes. Cliente ONG pode consultar somente suas doações, solicitações e equipamentos vinculados.

## Requisitos não funcionais relacionados
- **RNF04 – Validação de dados.** O sistema deve validar os campos obrigatórios e apresentar mensagens claras quando os dados informados forem inválidos. Critério: Formulários não devem ser enviados com campos obrigatórios vazios ou formatos inválidos, e cada erro deve indicar o que precisa ser corrigido.
- **RNF05 – Controle de acesso.** As funcionalidades devem ser acessíveis somente a usuários autenticados e autorizados conforme os perfis.
- **RNF01, RNF06:** legibilidade (16 px) e acessibilidade nas telas.

## Modelo de dados (seção 6 do documento)
- 6.2 ORGANIZAÇÃO armazena os dados das empresas e ONGs, como nome ou razão social, CNPJ, contato, endereço e situação, além do tipo de organização no sistema: Cliente Empresa, Cliente ONG ou Empresa Doadora. A atuação como Patrocinador em Potencial não é um tipo de organização; ela é registrada somente no vínculo de parceria.
- 6.2 PARCEIRO registra o vínculo de parceria com uma ORGANIZAÇÃO sem repetir seus dados cadastrais. A parceria pode ser com uma Empresa Doadora ou um Patrocinador em Potencial. Uma doadora só é parceira quando esse vínculo é registrado explicitamente.
- 6.3 O RF10 prevê associar parceiros ativos a operações que dependam de parceria. A operação que depende de parceria é o registro de solicitação de avaliação de equipamentos (UC09): somente a Empresa Doadora com vínculo de parceria ativo pode registrá-la. A atuação como Empresa Doadora na parceria exige que a organização seja do tipo Empresa Doadora. O vínculo é verificado pelo sistema por meio da organização que realiza a solicitação, sem alteração na estrutura das tabelas. O Patrocinador em Potencial é apenas registrado e consultado, sem operações associadas.

## Acréscimos da versão M2 (texto já aplicado no documento)
- **RF06 critério:** O CNPJ deve ter 14 dígitos, informado com ou sem máscara. O telefone deve ter 10 ou 11 dígitos e o e-mail deve ter formato válido. A situação da organização é Ativa ou Inativa. A desativação não exclui dados: o cadastro é preservado e o Administrador pode reativar a organização.
- **RN06:** Uma organização não pode mudar de tipo enquanto tiver usuários vinculados ou vínculo de parceria como Empresa Doadora. A desativação impede o acesso dos usuários da organização sem apagar registros, e a reativação restaura o acesso.
- **RF09 critério:** O Funcionário consulta as organizações e altera somente telefone, e-mail e endereço de Cliente Empresa e Cliente ONG.
- **RN09:** Os dados autorizados ao Funcionário são telefone, e-mail e endereço; CNPJ, nome ou razão social, tipo, situação e parceiros são exclusivos do Administrador.
- **RF10 critério:** A situação da parceria é Ativa ou Inativa. Cada organização possui no máximo um vínculo de parceria, que só pode ser registrado ou reativado para organização ativa. A organização de um vínculo não pode ser trocada depois de registrada. A atuação como Patrocinador em Potencial é permitida para qualquer tipo de organização.
- **RN03:** O Funcionário não acessa o cadastro de parceiros.
- **UC01:** Atores: Administrador; Funcionário (somente no fluxo alternativo FA3). Requisitos e regras: RF03, RF06, RF09; RN03, RN06, RN09. Passo 4: verifica os campos obrigatórios e seus formatos (telefone com 10 ou 11 dígitos e e-mail válido). FA1 acrescenta: a alteração do tipo é bloqueada enquanto a organização tiver usuários vinculados ou vínculo de parceria como Empresa Doadora. FA2 acrescenta: o Administrador pode reativar a organização, o que restaura o acesso dos seus usuários. **FA3 Consultar e atualizar contato.** O Funcionário consulta as organizações e altera somente telefone, e-mail e endereço de Cliente Empresa ou Cliente ONG. O sistema não permite ao Funcionário alterar CNPJ, nome ou razão social, tipo, situação nem organizações do tipo Empresa Doadora. **FE3 Mudança de tipo bloqueada.** A organização possui usuários vinculados ou vínculo de parceria como Empresa Doadora. O sistema informa o motivo e não altera o tipo. **FE4 Alteração não permitida ao Funcionário.** O Funcionário tenta alterar dado fora de telefone, e-mail e endereço, ou alterar uma Empresa Doadora. O sistema nega a operação e mantém o cadastro sem alterações.
- **UC25 passo 2:** valida o formato (14 dígitos, com ou sem máscara). A verificação ocorre dentro do cadastro e da alteração; o sistema não oferece consulta separada de CNPJ.
- **UC06:** Pré-condições: Administrador autenticado; organização previamente cadastrada e ativa. Passo 4: o sistema valida que a organização está ativa e ainda não possui vínculo, valida os dados da parceria e salva o vínculo. FA2 acrescenta: o Administrador pode reativar o vínculo, desde que a organização esteja ativa. **FE3 Organização inativa ou já vinculada.** Se a organização estiver inativa ou já possuir vínculo de parceria, o sistema não salva nem reativa o vínculo e informa o motivo.
- **6.2:** A situação da organização é Ativa ou Inativa. A situação do vínculo é Ativa ou Inativa, e cada organização possui no máximo um vínculo de parceria.
- **Exclusão (DP-25):** o documento permanece como estava: sem exclusão física; desativar preserva o histórico.

## Observações do coordenador (não fazem parte do documento)
- Decidido antes: `ORGANIZACAO.situacao` = `Ativa`/`Inativa` (DP-03); o login nega acesso a usuários de organização inativa (módulo 0); usuários só podem ser vinculados a organização Ativa do tipo igual ao perfil (módulo 1, DP-14); `/usuarios/opcoes-organizacao` (módulo 1) lê organizações ativas.
- O documento não define: valores de `situacao_parceria`, validação do CNPJ além de "formato válido", formatos de telefone/e-mail/endereço, quais dados o Funcionário pode alterar, mudança de tipo com vínculos existentes e exclusão física. Ver `docs/DECISOES_PENDENTES.md` (DP-21 em diante).
