# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Diagnóstico exclusivo do administrador da instalação única`
- TO: `### Requirement: Diagnóstico exclusivo do operador autorizado da instalação`

## MODIFIED Requirements

### Requirement: Diagnóstico exclusivo do operador autorizado da instalação

O sistema SHALL fornecer `GET /admin/capacity-observability` somente para sessão administrativa válida com permissão explícita, ativa e revalidada de operação da instalação, independente do vínculo comercial com uma conta de fotógrafo. O diagnóstico SHALL permanecer agregado da instalação e somente leitura mesmo com várias contas. Ser fotógrafo MUST NOT conceder essa permissão. Clientes e fotógrafos comuns SHALL ser recusados antes de iniciar coleta ou entregar cache; a interface SHALL omitir o painel e a ação de cópia para esses usuários. Parâmetros externos de conta SHALL NOT selecionar escopo ou conceder privilégio. Revogação SHALL impedir a próxima consulta e remover dados da interface ao detectar acesso negado. O privilégio de diagnóstico MUST NOT conceder acesso comercial aos acervos de outras contas.

#### Scenario: Administrador autorizado
- **WHEN** o dono com permissão ativa consulta capacidade em instalação com dois fotógrafos
- **THEN** recebe somente o diagnóstico agregado sanitizado da instalação, com os mesmos escopos e limites de evidência

#### Scenario: Cliente ou visitante tenta consultar
- **WHEN** a requisição possui sessão cliente ou sessão administrativa sem permissão explícita de operação
- **THEN** o acesso é negado sem devolver métricas, iniciar coleta ou reutilizar cache, e o painel não aparece para esse usuário

#### Scenario: Contexto revogado ou inválido
- **WHEN** a permissão do operador é revogada após uma coleta anterior
- **THEN** a próxima requisição é recusada mesmo com cache preenchido e o frontend retira o snapshot e a ação de cópia

#### Scenario: Operador tenta acessar acervo alheio
- **WHEN** o operador usa seu privilégio de diagnóstico para solicitar cliente, foto ou pedido de outra conta
- **THEN** a operação exige autorização comercial própria e o privilégio de diagnóstico isoladamente não a concede
