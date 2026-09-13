## Why

A Visão geral administrativa não informa quanto espaço as fotos realmente ocupam no servidor, impedindo o fotógrafo de acompanhar a capacidade antes de novos uploads. Além disso, os dados atuais de homologação são descartáveis e precisam ser removidos de forma controlada, preservando somente o acesso administrativo e as preferências globais.

## What Changes

- Adicionar à Visão geral um indicador administrativo com o total físico ocupado pelos arquivos fotográficos, formatado em MB ou GB, e a quantidade total de fotos registradas.
- Medir somente as raízes de mídia da Markina Gallery — originais/JPEGs recebidos, derivados e histórico de mídia — sem incluir banco, modelos faciais, logs ou arquivos de outros projetos.
- Manter a resposta agregada e autenticada, sem revelar caminhos, nomes de arquivos ou dados de clientes, e evitar que a medição bloqueie desnecessariamente o restante do painel.
- Executar em homologação uma higienização explícita de galerias, pastas, clientes, fotos e dependências operacionais, incluindo arquivos de mídia e estado de fila, preservando conta/sessões administrativas e preferências globais.
- Registrar que os dados removidos são de teste, que o proprietário dispensou recuperação por backup para esta execução e que não haverá restauração ou backfill.

## Capabilities

### New Capabilities

- `media-storage/admin-storage-overview`: medição administrativa segura do espaço físico usado pelas fotos e da quantidade total de fotos, apresentada na Visão geral.

### Modified Capabilities

- `deployment-operations`: acrescentar a higienização destrutiva e explicitamente autorizada de dados de teste em homologação, limitada aos recursos da Markina Gallery e preservando identidade administrativa e preferências.

## Impact

- Backend FastAPI: projeção autenticada da Visão geral e utilitário de medição agregada das raízes de mídia.
- Frontend Next.js: card de armazenamento na página `/admin` e estados de carregamento/indisponibilidade compatíveis.
- Testes: autorização administrativa, cálculo de bytes/contagem, formatação MB/GB, ausência de caminhos/PII e preservação de admin/preferências na limpeza.
- Operação: limpeza única do PostgreSQL, Redis e volumes de mídia exclusivos da homologação Markina Gallery; sem migration, alteração de segredo, DNS, certificado, proxy ou recurso de terceiros.
