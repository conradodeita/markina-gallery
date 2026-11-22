# Ajuste opcional de prévias

Changes: `add-optional-preview-auto-adjustment` (origem), `gallery-preview-exposure-and-installable-ui` (evolução) e `unify-folder-processing-controls` (painel contextual). Na **etapa Imagens**, uma única área mostra reconhecimento facial, intensidade, exposição e progresso da pasta selecionada, pública ou privada. Pastas públicas começam em 50%/0 EV; privadas, em 75%/0 EV. Cada pasta possui configuração própria, sem herança. Falhas de ajuste preservam a prévia convencional. A ingestão RAW/LightCraft foi aposentada em 26/10/2026; o ajuste de prévias permanece limitado aos JPEGs.

## Comportamento

O RawTherapee CLI executa um perfil de níveis automáticos, sem nitidez, reconstrução de rostos ou mudança de balanço de branco. A intensidade mistura o resultado com a prévia limpa (50% inicialmente, de 10 a 100%). Em 100%, a prévia usa integralmente o resultado ajustado. É um primeiro perfil moderado para avaliação, não equivalência ao Auto do Lightroom nem tratamento final. Nova implementação de `AdjustmentEngine` pode substituir o motor; IA não está integrada nesta versão.

Depois do ajuste automático, a exposição (-2 a +2 EV, passos de 0,1) clareia ou escurece somente aquela pasta em luz linear sRGB. Zero não altera os pixels do resultado automático. Valores altos podem recortar altas luzes; não recuperam detalhes ausentes. Cada processamento parte da prévia limpa, nunca do JPEG ajustado anterior, e a marca-d'água é aplicada por último. Não há importação de presets Lightroom.

Novas fotos de conteúdo recebem jobs conforme a configuração própria da pasta. Alterar intensidade/exposição salva automaticamente após um intervalo curto e reenfileira somente fotos elegíveis daquela pasta, invalidando a geração anterior. Pastas privadas preservam a dependência do reconhecimento facial concluído. Não há botões de salvar parâmetros ou processar toda a galeria. A retentativa facial continua limitada à pasta e ao gate global. Antes/depois e ampliação usam prévias protegidas autenticadas. Capas e histórico comercial arquivado permanecem convencionais.

A etapa Imagens inclui pastas públicas e restritas; os cards de clientes levam ao mesmo painel pela identidade da pasta. O contador de upload conserva pasta de destino, arquivo, posição/total e progresso real em bytes durante troca de seleção. Consultas periódicas preservam a grade e os controles; não criam jobs. O Monitor continua mostrando filas e tentativas reais no escopo autorizado da instalação; reprocessamento reutiliza jobs e telemetria existentes, sem contagem por renderização da interface.

O desligamento legado, disponível pelo contrato administrativo de configuração, impede novas admissões, cancela filas/reservas e faz próximas requisições daquela pasta usarem o derivado convencional. Outras pastas e fotógrafos não são afetados. Fotos já carregadas na memória de um navegador só mudam ao recarregar. Mudança da marca-d'água, fonte ou geração invalida resultados anteriores. O original, `admin_preview`, `client_preview`, miniaturas e embeddings nunca são substituídos pelo ajuste.

Pastas restritas do Acervo do Cliente (`audience_scope=selected`) são sempre ajustadas individualmente, sem herdar nem desligar o módulo. O padrão efetivo é 75% e 0,0 EV; personalizações já salvas permanecem próprias da pasta. O job de prévia só entra na fila após o job facial mais recente daquela foto concluir com sucesso e sempre usa a prévia limpa baseada na fonte original. Alterar intensidade/exposição invalida a geração anterior e reenfileira as fotos com reconhecimento facial concluído. O gate facial global continua obrigatório.

## Worker opcional

Após deploy da API/frontend e migration `20260913_0055`, usar o mesmo arquivo de ambiente e opções do projeto existente. A migration copia configurações anteriores para galerias existentes, preservando geração e resultados com exposição zero; não agenda fotos. Novas galerias não herdam ativação global. Não mudar segredos nem usar exemplos com defaults em servidor real. Inventariar recursos e apresentar o impacto antes de qualquer operação remota.

**Publicação da evolução:** parar exclusivamente o worker opcional antigo antes da migration, publicar API/frontend e reconstruir/reiniciar esse worker com o mesmo SHA. O pipeline base não reconstrói o worker opcional. Não deixar o worker antigo executando junto da API nova. Interrupções de jobs são recuperadas pela reserva; nenhuma foto/fila deve ser apagada. Em rollback, manter o worker parado e desabilitar configurações antes de voltar ao código anterior; não executar downgrade destrutivo sem autorização.

```powershell
docker compose -p markina-gallery -f docker/docker-compose.yml -f docker/docker-compose.preview-adjustment.yml --profile preview-adjustment up -d --build --no-deps preview-adjustment-worker
```

O override adiciona somente `preview-adjustment-worker`, sem porta publicada, na rede interna existente. Monta apenas o volume de derivados (não originais ou referências faciais). Limites iniciais: 0,5 CPU, 768 MiB, um trabalho, uma thread de OpenMP, subprocesso com timeout de 90 segundos e reserva de 180 segundos. Reservas abandonadas são retomadas até três tentativas; falhas terminais exigem retentativa administrativa. Esses limites não são medição de capacidade ARM.

O serviço tem imagem própria com RawTherapee 5.13 oficial para x86_64 e ARM64; não instalar o editor na API. `backend/Dockerfile.preview-adjustment` valida SHA-256 do AppImage upstream, extrai o runtime para o worker e confere a versão CLI no build. Documentação oficial: https://rawpedia.rawtherapee.com/Command-Line_Options ; release/licença: https://github.com/RawTherapee/RawTherapee/releases/tag/5.13 . RawTherapee é GPL-3.0; preservar avisos e a oferta de fonte correspondente conforme os termos de distribuição do AppImage. O motor é invocado como processo externo; não há cópia de seu código para a aplicação.

O runtime extraído requer `libexpat1` do Debian. A checagem usa `rawtherapee-cli` sem argumentos, exige retorno zero e o banner exato de 5.13; `-v` não é uma opção válida da CLI dessa versão. O smoke sintético também exige retorno zero antes de validar renderização, dimensões e preservação da entrada. Referência do contrato CLI: https://github.com/RawTherapee/RawTherapee/blob/5.13/rtgui/main-cli.cc .

## Desligamento e higienização

1. O painel contextual não oferece desligamento. A higienização exige inventário de configurações da galeria e das pastas e desligamento explícito autorizado pelo contrato administrativo antes da limpeza. Confirmar `enabled=false` em `/admin/preview-adjustment/galleries/{id}/configuration`; para inventário global, consultar `gallery_preview_settings`. A limpeza recusa execução se qualquer galeria continua habilitada ou existe pasta restrita de cliente, pois essas pastas são sempre processadas.
2. Parar exclusivamente o worker:

```powershell
docker compose -p markina-gallery -f docker/docker-compose.yml -f docker/docker-compose.preview-adjustment.yml --profile preview-adjustment stop preview-adjustment-worker
```

3. Inventariar sem apagar, usando a API já atualizada:

```powershell
docker compose -p markina-gallery -f docker/docker-compose.yml exec -T api python -m app.preview_adjustment.cleanup
```

4. Com exclusão autorizada e worker confirmado parado, executar:

```powershell
docker compose -p markina-gallery -f docker/docker-compose.yml exec -T api python -m app.preview_adjustment.cleanup --execute --worker-stopped
```

A ferramenta aceita somente `derivatives/<UUID>/preview-adjustment/<UUID>.jpg`, rejeita links simbólicos e não usa exclusão recursiva. Ela apaga esses arquivos e linhas de `preview_adjustment`, mantendo a configuração desligada. Arquivos desconhecidos não são apagados. A limpeza física desses derivados não possui backup, mas eles são regeneráveis; originais, prévias convencionais e dados comerciais permanecem intactos. Não executar simultaneamente com o worker: `--worker-stopped` é uma declaração operacional explícita, não uma detecção de processos remotos.

## Aposentadoria do pipeline RAW

- A change `retire-lightcraft-and-gemma` removeu o intake RAW, LightCraft, staging, conversor e UI do código executável. A seleção e a API agora aceitam somente JPEG.
- O override RAW, Dockerfile, rotas/worker e testes exclusivos foram removidos. Migrations 0078/0079 e registros existentes permanecem históricos; nenhum RAW, volume ou linha de banco foi apagado.
- A aposentadoria operacional de qualquer serviço/volume legado exige inventário atual e autorização específica; os registros de produção conhecidos são históricos.
- O ajuste de prévias, suas rotas, perfil, jobs e worker continuam ativos para JPEG e não fazem parte desta retirada.

## Validação

Testes locais usam banco/arquivos temporários e motor substituto para testar corridas, falha, retomada e retorno byte a byte. `scripts/preview_adjustment_smoke.py` permite validar o CLI real em contêiner temporário com imagens sintéticas e gravar uma comparação em `/out`. A aceitação estética pelo fotógrafo e a capacidade no host compartilhado precisam de uma amostra real; o benchmark facial não mede esse módulo.

Validação local de 13/09/2026: 67 testes de mídia/módulo aprovados no checkpoint inicial; após os ajustes finais, 17 testes exclusivos do módulo, três regressões de lifecycle e 12 testes da página/painel aprovados. Lint/typecheck e build frontend aprovados (aviso preexistente de imagem no formulário de branding); migration até `20260913_0054` executada em SQLite temporário. Não foi executada a suíte completa.

O painel foi verificado em Chromium, com API simulada, em 390, 768 e 1440 px: nenhum overflow interno/erro JavaScript; comparação vertical no celular e lado a lado no desktop. A comparação visual nessa prova usa amostra sintética, não dados de clientes.

Histórico: a imagem inicial usava RawTherapee 5.9 e processou três sintéticos 640×420 sem alterar entradas; esses tempos não são benchmark de fotografias reais nem previsão de throughput ARM. A imagem atual usa 5.13, SHA por arquitetura e smoke sintético headless no CI. A aprovação estética continua dependendo do fotógrafo e não é demonstrada pelo smoke técnico. Publicação inicial e ativação posterior do worker estão registradas em `openspec/changes/add-optional-preview-auto-adjustment/deployment-result.md`; isso não comprova o runtime remoto atual.
