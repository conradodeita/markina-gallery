## Context

Ver proposal.md. `branding_root()` aceita `BRANDING_ASSETS_ROOT`, mas o Compose da API não define essa variável nem monta o diretório padrão `/app/media/branding`. O upload guarda bytes nesse diretório e chaves estáveis no banco. O deploy recria a API; backup lógico cobre apenas as chaves. Diagnóstico e versão publicada estão em `../rebrand-pick-your-pic/deployment-result.md`.

## Goals / Non-Goals

**Goals:** durabilidade explícita, transferência conservadora de arquivos recuperáveis e verificação focada do ciclo de recriação.

**Non-Goals:** refazer rebrand/UI, editar arte, recuperar bytes inexistentes a partir do SQL, alterar tabelas, implementar backup geral de mídia ou interferir em processamento de fotos.

## Decisions

1. Adicionar volume nomeado `branding-assets` ao projeto Compose e montá-lo somente na API em `/var/lib/markina/branding`; definir `BRANDING_ASSETS_ROOT` para esse caminho no Compose. Manter o fallback local atual fora de Docker e configuração explícita usada em testes. Volume próprio evita misturar ativos com rotinas de exclusão de fotos. Não criar URL estática no proxy: as rotas de branding continuam responsáveis pela entrega.
2. Antes da primeira recriação, executar preservação controlada dos ativos referenciados no banco e ainda presentes no container antigo. Usar container identificado por labels do projeto/serviço, caminhos resolvidos com validação, arquivos regulares de branding e staging restrito em `/var/lib/markina-gallery/backups`. Não copiar diretórios arbitrários, symlinks, segredos ou logs; não apagar fontes. Transferir ao novo volume e comparar hashes. Conflitos ou falha de preservação abortam a publicação antes de destruir a única cópia. Ausência já constatada é pendência explícita, não erro fatal de todo o deploy.
3. Integrar o procedimento ao deploy versionado e aos testes do script. Deploys subsequentes usam o volume e incluem seus arquivos no backup restrito pré-publicação, sem renomear chaves ou reprocessar imagens. Usar escrita temporária/atômica e checagem de destino para evitar sobrescrita durante retomada. O período de transferência deve impedir uploads concorrentes apenas na API do projeto, depois de identificado o alvo e preparado o destino; nenhuma pausa ou alteração de terceiros. Registrar o impacto breve no inventário operacional.
4. Preservar contratos existentes do frontend e PWA, incluindo fallback quando não há arquivo. Não preencher automaticamente imagens faltantes com prancha de referência ou arte sintética. Confirmar primeiro a persistência; só depois orientar upload dos três arquivos individuais pelo painel.
5. Regressão de container em fixture isolada com ativos sintéticos, mesma imagem/volume entre duas instâncias e hashes iguais após recriação. Não usar banco real em pytest, nem instalar arte sintética sobre a configuração de homologação. Testes focados de API e contrato Compose complementam o teste real de persistência; se Docker local não estiver disponível, registrar esse teste como pendente e executá-lo em ambiente isolado aprovado.

## Risks / Trade-offs

- Arquivos antigos ausentes → reenvio necessário; não se sabe qual deploy os perdeu. Diagnóstico anterior não deve ser repetido como varredura irrestrita.
- Volume montado vazio oculta arquivo antigo → copiar/verificar antes de substituir o container, não depois.
- Upload concorrente durante cópia → janela curta sem escrita na API durante a transferência; volume persistente elimina necessidade dessa transferência em próximas publicações.
- Permissões ou disco impedem gravação → preflight e falha antes da recriação; logs sanitizados e cópia preservada.
- Rollback para Compose antigo perde visibilidade do novo volume → preservar mount/variável no rollback operacional; não apagar volume nem copiar dados para camada efêmera. Se isso exigir revisão de código/configuração, pausar para aprovação.

## Migration Plan

Sem migration SQL. Após implementar e validar, apresentar inventário atualizado e plano que inclui exclusivamente o novo volume do projeto, backup e breve pausa da API, mantendo domínio e portas. Aguardar aprovação operacional. Preservar legados recuperáveis, publicar, verificar mount e endpoints e comparar recursos de terceiros. No caso atual, pedir reenvio apenas após confirmar a correção; testar leitura da arte real depois do upload sem disparar OTP, mensagens ou alteração de fotografias. Revisão humana precede sync/archive.
