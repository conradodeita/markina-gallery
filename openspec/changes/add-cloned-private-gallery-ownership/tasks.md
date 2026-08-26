## 1. Correção da base e migração aditiva

- [x] 1.1 Remover a autorização compartilhada provisória de galerias derivadas e restaurar a propriedade exclusiva por `DerivedGallery.client_id`; verificar tentativa de acesso cruzado com teste FastAPI.
- [x] 1.2 Criar migration aditiva para registro de entrada em acervo-fonte, visualização ampliada, histórico de telefones e snapshots comerciais; verificar upgrade e downgrade em banco SQLite sintético.
- [x] 1.3 Migrar clientes e pedidos existentes sem perda de propriedade ou histórico; verificar com teste de migration que dados originais e snapshots permanecem consultáveis.

## 2. Autorização, clonagem e estados privados

- [x] 2.1 Implementar registro por link não listado após OTP, sem conceder leitura do acervo-fonte; verificar que cliente sem galeria privada recebe apenas estado neutro.
- [x] 2.2 Implementar criação idempotente de galeria privada clonada a partir de acervo-fonte ou galeria derivada, reaproveitando referências de fotos e copiando somente configurações permitidas; verificar isolamento de mãe e pai por testes de API.
- [x] 2.3 Implementar bloqueio, reativação e consulta de uma galeria privada da proprietária, com auditoria; verificar que a ação não afeta outra galeria originada do mesmo acervo.
- [x] 2.4 Registrar abertura ampliada e retornar estados `nova`, `visualizada mas não comprada` e `já comprada`; verificar que miniatura não cria visualização e compra confirmada prevalece.
- [x] 2.5 Implementar troca controlada de telefone com novo OTP, telefone histórico e snapshots de pedido; verificar que novo telefone recupera a mesma biblioteca e telefone antigo não autentica.

## 3. Operação administrativa backend-driven

- [x] 3.1 Implementar contratos administrativos paginados para galerias-fonte, registros de clientes e galerias privadas, com busca por nome/telefone e estados operacionais; verificar autorização e resposta sem dados sensíveis à cliente.
- [x] 3.2 Implementar ficha individual de seleção com resumo comercial, prévias administrativas sem marca d'água, ampliação e agregação de vendas por foto; verificar proteção de rota e teste de contrato.
- [x] 3.3 Implementar exportação auditável TXT e CSV dos identificadores da seleção individual; verificar conteúdo, codificação e ausência de URL de original ou dados de terceiros.

## 4. Interfaces de fotógrafo e cliente

- [x] 4.1 Atualizar lista e ficha administrativa de galerias para distinguir fonte não listada, clientes registradas e galerias privadas clonadas; verificar carregando, vazio, erro, busca e confirmação de ação destrutiva em testes de componente.
- [x] 4.2 Criar ficha administrativa da seleção individual com conferência, ampliação e exportação; verificar renderização a partir das APIs e `npm run lint`.
- [x] 4.3 Atualizar biblioteca, grade e ampliador da cliente para propriedade exclusiva, estados de foto e histórico após expiração; verificar que não há vazamento entre duas sessões de cliente.

## 5. Qualidade e homologação

- [x] 5.1 Executar `pytest backend/tests -q`, `ruff check backend/app backend/tests`, `npm run lint` e `npm run build`; corrigir falhas antes de marcar esta tarefa.
- [x] 5.2 Validar o change com `npx --yes @fission-ai/openspec@latest validate add-cloned-private-gallery-ownership --strict`; registrar qualquer bloqueio restante.
- [ ] 5.3 Preparar validação manual com dados sintéticos e plano de impacto zero para homologação; obter aprovação explícita antes de qualquer deploy e registrar versão, resultado e rollback.
