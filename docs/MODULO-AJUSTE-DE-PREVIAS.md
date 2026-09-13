# Ajuste opcional de prévias

Change: `add-optional-preview-auto-adjustment`. O módulo começa desligado e a chave fica em Configurações → Ajuste automático das prévias. Ausência do worker não interrompe o fluxo convencional; os ajustes ficam na fila. Falhas usam a prévia convencional.

## Comportamento

O RawTherapee CLI executa um perfil de níveis automáticos, sem nitidez, reconstrução de rostos ou mudança de balanço de branco. A intensidade mistura o resultado com a prévia limpa (50% inicialmente, de 10 a 75%). É um primeiro perfil moderado para avaliação, não equivalência ao Auto do Lightroom nem tratamento final. Nova implementação de `AdjustmentEngine` pode substituir o motor; IA não está integrada nesta versão.

Novas fotos de conteúdo recebem jobs depois das prévias convencionais, independentemente de rosto. Ligar ou mudar intensidade não processa o acervo anterior: selecionar galeria e usar “Processar galeria / tentar falhas”. O navegador agenda páginas de 100 registros; se a página fechar, jobs já persistidos continuam. Repetir o comando retoma sem duplicar trabalho vigente. Progresso distingue fila, processamento, prontas e falhas. Antes/depois usa apenas prévias protegidas autenticadas. Capas e histórico comercial arquivado permanecem convencionais.

Desligar impede novas admissões, cancela filas/reservas e faz próximas requisições usarem o derivado convencional. Fotos já carregadas na memória de um navegador só mudam ao recarregar. Mudança da marca-d'água, fonte ou geração invalida resultados anteriores. O original, `admin_preview`, `client_preview`, miniaturas e embeddings nunca são substituídos pelo ajuste.

## Worker opcional

Após deploy da API/frontend e migration `20260913_0054`, usar o mesmo arquivo de ambiente e opções do projeto existente. Não mudar segredos nem usar exemplos com defaults em servidor real. Inventariar recursos e apresentar o impacto antes de qualquer operação remota.

```powershell
docker compose -p markina-gallery -f docker/docker-compose.yml -f docker/docker-compose.preview-adjustment.yml --profile preview-adjustment up -d --build --no-deps preview-adjustment-worker
```

O override adiciona somente `preview-adjustment-worker`, sem porta publicada, na rede interna existente. Monta apenas o volume de derivados (não originais ou referências faciais). Limites iniciais: 0,5 CPU, 768 MiB, um trabalho, uma thread de OpenMP, subprocesso com timeout de 90 segundos e reserva de 180 segundos. Reservas abandonadas são retomadas até três tentativas; falhas terminais exigem retentativa administrativa. Esses limites não são medição de capacidade ARM.

O serviço tem imagem própria com RawTherapee; não instalar o editor na API. O arquivo `backend/Dockerfile.preview-adjustment` usa Debian Bookworm e o pacote da distribuição. Documentação oficial: https://rawpedia.rawtherapee.com/Command-Line_Options ; código/licença: https://github.com/RawTherapee/RawTherapee . O pacote é GPL-3.0; preservar seus avisos e a documentação de copyright instalada em `/usr/share/doc/rawtherapee/`. Distribuição de binários/imagem deve acompanhar as obrigações de fonte correspondente e licenças do pacote. O motor é invocado como processo externo; não há cópia de seu código para a aplicação.

## Desligamento e higienização

1. Desmarcar “Melhorar prévias automaticamente” e salvar. Confirmar resposta `enabled=false` na API administrativa.
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

## Retirada futura do código

- Remover painel e sua importação em Configurações.
- Retirar o agendamento pós-commit em `media.py`, resolução opcional e registro de rotas em `main.py`, e hooks de limpeza de foto/manifesto em `main.py` e `gallery_lifecycle.py`.
- Remover pacote `app/preview_adjustment`, worker/override Docker e testes exclusivos, depois da limpeza.
- As duas tabelas exclusivas podem permanecer vazias até migration de retirada aprovada; não reverter migrations ou commits de outras funcionalidades.
- Verificar entrega convencional, marca-d'água, exclusão e ausência de jobs. Nenhum rollback de galerias/pedidos/clientes é necessário.

## Validação

Testes locais usam banco/arquivos temporários e motor substituto para testar corridas, falha, retomada e retorno byte a byte. `scripts/preview_adjustment_smoke.py` permite validar o CLI real em contêiner temporário com imagens sintéticas e gravar uma comparação em `/out`. A aceitação estética pelo fotógrafo e a capacidade no host compartilhado precisam de uma amostra real; o benchmark facial não mede esse módulo.

Validação local de 13/09/2026: 67 testes de mídia/módulo aprovados no checkpoint inicial; após os ajustes finais, 17 testes exclusivos do módulo, três regressões de lifecycle e 12 testes da página/painel aprovados. Lint/typecheck e build frontend aprovados (aviso preexistente de imagem no formulário de branding); migration até `20260913_0054` executada em SQLite temporário. Não foi executada a suíte completa.

O painel foi verificado em Chromium, com API simulada, em 390, 768 e 1440 px: nenhum overflow interno/erro JavaScript; comparação vertical no celular e lado a lado no desktop. A comparação visual nessa prova usa amostra sintética, não dados de clientes.

Imagem final `markina-gallery-preview-adjustment:validation` construída e testada sem rede ou volumes de fotos reais, com 0,5 CPU/768 MiB/64 processos. RawTherapee 5.9 processou três sintéticos 640×420 em 1,340 s, 0,913 s e 0,637 s, com entrada intacta. Esses tempos não são benchmark de fotografias reais nem previsão de throughput ARM. A chamada usa `-a` porque a configuração inicial do CLI não inclui PNG nas extensões selecionadas. A avaliação estética do fotógrafo continua pendente; o módulo não foi publicado nem habilitado no servidor.
