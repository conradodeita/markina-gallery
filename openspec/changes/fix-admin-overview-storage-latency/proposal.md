## Why

A Visão Geral publicada levou 16,8s para responder. O perfil READ ONLY identificou 16,5s na medição de armazenamento de 3.522 fotos: 17.599 consultas repetidas de tenant e mais de 100 mil resoluções de caminho. O proprietário solicitou aplicar a correção mantendo o isolamento entre fotógrafos.

## What Changes

- Validar tenant ativo no início e antes de devolver ou memorizar a medição, eliminando consulta SQL por arquivo.
- Memorizar somente medições completas por até 30s, separadas por banco, tenant e raízes, com capacidade limitada e coalescência de chamadas concorrentes da mesma chave.
- Consultar somente colunas necessárias e resolver raízes uma vez por medição, mantendo validação de namespace, confinamento físico, histórico por item e deduplicação.
- Executar contagens e agrupamento de jobs no banco, sem carregar entidades apenas para contar.
- Preservar o JSON, o carregamento de chamada única e os fluxos de negócio existentes.

## Capabilities

### New Capabilities
- `media-storage/owned-storage-summary`: medição agregada própria com frescor limitado e custo SQL constante.

### Modified Capabilities
Nenhuma alteração em pagamentos, acesso ao acervo ou UI.

## Impact

Backend `storage_metrics.py`, endpoint `admin_validation_summary` e testes focados. Sem dependências, schema, mídias, credenciais ou operações financeiras. A publicação requer procedimento e autorização próprios; testes de processo candidato READ ONLY não constituem deploy. Trabalho local de limpeza anterior será preservado e não incluído no commit desta correção.
