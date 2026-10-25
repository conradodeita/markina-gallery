# Tasks

## 1. Contrato e inventário
- [x] 1.1 Reconciliar PR258/main, inventariar consumidores/IDs/pacotes e avaliar fontes oficiais/licença/rupturas, preservando o trabalho Orders.
- [x] 1.2 Validar proposta/design/delta e registrar escopo da correção autorizada e plano de impacto.

## 2. Fonte e preparação
- [x] 2.1 Fixar Pillow13 nos manifests e inventário; testar que os seis consumidores usam a versão corrigida sem trocar outras dependências/modelos.
- [x] 2.2 Implementar/testar preparação isolada por imagem anterior com wheel oficial, checksum, comparação completa de distribuições/fontes e recusa de deriva.

## 3. Compatibilidade e recuperação
- [x] 3.1 Construir/validar seis candidatos ARM64 com pip check, imports e matriz sintética de formatos/pixels/EXIF/proteção; registrar qualidade/recursos/limites.
- [x] 3.2 Implementar/ensaiar procedimento pontual sem migration, parada/restart policy, recuperação e negativos de inventário/concorrência/filas; preservar serviços vizinhos e histórico.

## 4. Integração e publicação
- [x] 4.1 Revisar diff, atualizar PR258, passar testes/CI e confirmar autorização/inventário concretos antes da operação.
- [x] 4.2 Publicar a correção autorizada dos seis serviços, verificar Pillow13 efetivo/saúde/preservação e fechamento de alertas quando disponível; não declarar ausência global de vulnerabilidades.
- [x] 4.3 Registrar relatório/continuidade e retomar preparação/publicação Orders com inventário renovado; sincronizar/arquivar somente após revisão humana.
