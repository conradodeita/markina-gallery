# Proposal

## Why

O inventário protegido do runtime de backup encerra corretamente com `api_container_record_ambiguous`, sem fingerprint ou precondições aprovadas. O código não revela se a ambiguidade decorre de quantidade de registros ou de seus estados, e os dados brutos do Docker não podem ser expostos. Um diagnóstico agregado e restrito pode orientar a reconciliação sem enfraquecer a guarda que impede instalação, vínculo ou ensaio com identidade incerta.

## What Changes

- Adicionar um diagnóstico operacional somente de leitura para os papéis fixos `api`, `web` e `db`, informando contagens agregadas de registros e categorias de estado `running`, `stopped` e `unknown`.
- Manter o inventário normal estrito: cada serviço continua exigindo exatamente um container identificado pelos labels Compose fixos e validados novamente.
- Ajustar a verificação pós-instalação do forced command protegido para validar a resposta agregada read-only, sem exigir fingerprint do inventário normal ambíguo.
- Vincular o destino de escrita do workflow de instalação ao `connection_binding` produzido pelo preflight atual, sem depender de variáveis `PRODUCTION_PREFLIGHT_*` indisponíveis no ambiente `production`.
- Manter falha fechada: diagnóstico não seleciona containers, não produz fingerprint nem precondições aprovadas, não torna um inventário ambíguo bem-sucedido e não permite `operate`.
- Restringir a execução ao canal protegido e a códigos de erro estáticos; omitir IDs, nomes, valores de labels, saída Docker, caminhos, exceções, configuração e segredos.

## Capabilities

### New Capabilities
- `deployment-operations/backup-runtime-inventory-diagnostics`: diagnóstico agregado e seguro da ambiguidade no inventário de containers do runtime de backup.

### Modified Capabilities
- Nenhuma.

## Impact

Afeta somente o wrapper operacional protegido, a verificação pós-instalação desse wrapper, o módulo read-only do inventário, o binding do workflow de instalação, os testes e as guardas de CI/OpenSpec correspondentes. Não altera API/web da aplicação, Compose, banco, Drive, configuração do destino, serviço ou timer. Instalação da nova referência e execução no host dependem da CI do SHA exato, do preflight protegido e dos gates operacionais aplicáveis.
