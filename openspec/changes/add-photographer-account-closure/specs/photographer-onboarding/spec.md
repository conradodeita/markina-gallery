# Spec Delta

## ADDED Requirements

### Requirement: Informação clara de encerramento nos Termos

Os Termos SHALL explicar como solicitar encerramento, o fim do acesso do fotógrafo, o que continua disponível nas galerias publicadas, quais pedidos e obrigações adiam a conclusão, o arquivo frio e as categorias de dados preservadas ou apagadas. Créditos não utilizados, por si só, não impedem o encerramento após confirmação consciente. O protocolo SHALL preservar a versão e o texto/hash aceitos.

#### Scenario: Fotógrafo consulta os Termos vigentes
- **WHEN** fotógrafo abre os Termos antes de aceitar
- **THEN** encontra a seção de encerramento junto das demais condições e pode lê-la antes da confirmação

#### Scenario: Fotógrafo aceita a versão atualizada
- **WHEN** fotógrafo aceita uma versão dos Termos com a regra de encerramento
- **THEN** o protocolo imutável identifica a versão e preserva o texto/hash exato aceito

#### Scenario: Regra de encerramento muda
- **WHEN** a regra é alterada em uma nova versão dos Termos
- **THEN** o aceite anterior não é tratado como aceite do texto novo e as operações protegidas seguem o gate da versão vigente

#### Scenario: Encerramento com crédito remanescente
- **WHEN** há saldo de créditos não utilizados antes da confirmação final
- **THEN** o fotógrafo vê o valor registrado e o efeito aprovado do encerramento antes de confirmar

### Requirement: Transparência sobre dados após o encerramento

Termos versionados SHALL conter uma seção própria de Aviso de Privacidade no mesmo texto integral e no mesmo hash/protocolo de aceite; não haverá versão nem aceite paralelo. Ambos SHALL descrever categorias de dados mantidas, finalidades, restrições de acesso e períodos aplicáveis. A comunicação MUST NOT identificar provedor, localização ou mecanismo interno de armazenamento.

#### Scenario: Fotógrafo lê a regra de preservação
- **WHEN** fotógrafo revisa os Termos e o aviso de privacidade
- **THEN** entende que compras e transações seguem políticas próprias; nome/e-mail mínimos permanecem sob acesso restrito para permitir restauração pelo proprietário, com revisão manual aos dez anos e sem exclusão automática; reabertura posterior exige confirmação por CPF, e-mail atual verificado e dados atuais; uma referência protegida e versionada do CPF pode permanecer enquanto houver mídia recuperável e será removida junto com ela; o protocolo de aceite é mantido por dez anos; mídias arquivadas podem permanecer após dez anos, quando passam por revisão manual do proprietário, sem exclusão automática, e podem ser recuperadas enquanto não forem explicitamente removidas; também entende quais dados são reduzidos ou mantidos, sem detalhes internos de armazenamento

#### Scenario: Aviso de Privacidade na versão do aceite
- **WHEN** fotógrafo lê e aceita uma versão publicada dos Termos
- **THEN** o texto, versão e hash imutáveis do protocolo incluem também a seção do Aviso de Privacidade e suas regras de retenção

#### Scenario: Aceite do texto com a regra de retenção
- **WHEN** fotógrafo aceita a versão que descreve o encerramento e a retenção de dados por categoria
- **THEN** o protocolo imutável preserva a versão e o texto/hash exatos dessa regra
