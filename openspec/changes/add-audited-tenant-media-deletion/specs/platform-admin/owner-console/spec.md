# Spec Delta

## ADDED Requirements

### Requirement: Console oferece exclusão permanente somente após revisão

O console do `PlatformOwner` SHALL apresentar a exclusão permanente somente para uma conta `closed` cujo marco manual de dez anos venceu. A confirmação SHALL exigir senha, TOTP e frase explícita vinculada à ação; o fotógrafo e operadores sem papel de proprietário MUST NOT iniciar nem consultar essa operação.

#### Scenario: Proprietário solicita exclusão após dez anos
- **WHEN** o proprietário abre o ciclo elegível, confirma a frase exigida e fornece senha e TOTP válidos
- **THEN** o console registra o pedido e exibe o identificador e o estado da exclusão daquele tenant

#### Scenario: Usuário sem privilégio ou conta antes do prazo
- **WHEN** um fotógrafo, operador técnico, proprietário sem reautenticação ou proprietário antes da revisão tenta solicitar a exclusão
- **THEN** a operação é recusada sem alteração de estado ou efeito no storage

### Requirement: Console acompanha o resultado sem expor dados sensíveis

O console SHALL exibir progresso por ciclos e objetos, conclusão ou necessidade de atenção, com erros sanitizados suficientes para diagnóstico. Respostas MUST NOT conter CPF, impressão protegida, conteúdo de mídia, caminhos locais, credenciais ou IDs/URLs remotos.

#### Scenario: Exclusão em andamento ou concluída
- **WHEN** o proprietário consulta a conta com exclusão enfileirada, em andamento ou completa
- **THEN** o console mostra contagens confirmadas e informa se a mídia ainda pode ser recuperada

#### Scenario: Exclusão falha ou exige reconciliação
- **WHEN** algum objeto não tem ausência remota comprovada
- **THEN** o console mantém o estado pendente, mostra categoria e etapa sanitizadas e oferece retry somente após nova reautenticação e confirmação do proprietário

#### Scenario: Repetição concorrente da mesma ação
- **WHEN** o mesmo `request_id` de exclusão ou retry chega enquanto a primeira chamada confirma a ação
- **THEN** o console retorna o resultado confirmado após serializar pelo proprietário, sem repetir a ação nem gravar auditoria duplicada
