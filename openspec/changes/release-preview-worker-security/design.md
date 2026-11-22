# Design

## Context
Fonte aprovada dos pins: 74f61300e7a818d1605afda3db1d07574c443110. Evidência e candidato em prepare-coordinated-python-security-release/preview-worker-preparation-20261030.md. O worker legado não registra SIGTERM e a política Python geral recusa publicação; não alterar essa recusa nem usar a operação de migration0090.

## Decisions
- Escopo único: preview-adjustment-worker. Manter API e worker geral como produtores a pausar, e exigir opcionais faciais/RAW/Gemma parados. Qualquer outro produtor ativo bloqueia a operação.
- Preparação local e homologação serão independentes da produção. O código não conterá SSH, build remoto, migration nem limpeza Docker.
- O primeiro bootstrap exige janela de indisponibilidade aprovada, entrada em manutenção e parada graciosa dos produtores; o worker antigo só recebe SIGINT depois de queued/processing zerados. Timeout não escala para SIGKILL.
- Reutilizar o lock production-release.lock e os mecanismos de Compose e manutenção existentes quando seus contratos forem compatíveis; não chamar a migration ou publicar API/web. Divergência de proveniência Compose bloqueia.
- Recibo antes de cada mutação, recuperação inversa, referência anterior preservada por ID e checagens dos serviços fora do escopo. Falha de recuperação mantém a manutenção e o journal; nunca anunciar sucesso.
- O caminho de pagamentos presente no código atual é Mercado Pago Orders. Seu endpoint valida assinatura, grava a notificação em inbox durável antes da resposta e o worker também reconcilia pedidos enviados por polling, sem depender do webhook. A documentação pública de Orders descreve tentativas repetidas quando não recebe confirmação HTTP 200/201. Isso sustenta o mecanismo para notificações Orders, mas não comprova quais URLs/tópicos estão ativos em cada conta de produção. Tópicos opcionais podem ter política diferente; a documentação do Mercado Pago diz que alertas `stop_delivery_op_wh` não seguem a política usual de retry. A configuração efetiva e a aceitação do impacto continuam gates explícitos antes da janela.

## Sequência operacional proposta

1. Antes da janela, disponibilizar a imagem por artefato verificável e confirmar config ID/camadas/pacotes no daemon de destino, sem usar tag como identidade. Confirmar RawTherapee 5.13 e Python 3.13.16. Este estágio não é autorizado na Oracle pela preparação atual.
2. Inventário somente leitura de todos os containers Markina (inclusive históricos), configurações via hashes, imagens, volumes, redes, restart policy, schema, versão/ordem dos manifests e recibos. Fila apenas por contagem agregada. Conferir checkout limpo sem trocar HEAD, capacidade e backup verificável; não criar backup de dados silenciosamente.
3. Conferir CI/revisão do código de suporte, candidato próprio, fingerprint e aceite explícito da janela e dos callbacks. Adquirir production-release.lock, recusar outros journals pendentes e revalidar inventário antes da primeira mutação. Não aceitar fingerprint de fixtures ou o fingerprint antigo desta conversa.
4. Preservar a imagem anterior por ID e tag sem sobrescrever conflitos. Registrar journal privado/fsync antes de cada ação. Salvar configuração original do proxy, validar manutenção com nginx -t e confirmar HTTP503 nas rotas afetadas. Manter rotas de saúde para verificação.
5. Parar API por SIGTERM com timeout limitado, sem SIGKILL. Parar o worker geral pelo handler cooperativo, aguardando saída zero. Desabilitar restart temporariamente somente nesses IDs, com política original registrada antes da ação. Confirmar os mesmos IDs/imagens após cada passo. Não prosseguir enquanto algum produtor permitido continuar ativo; produtores opcionais ativos bloqueiam desde o preflight.
6. Aguardar por até 120 segundos zero queued/processing em preview_adjustment. Falha de consulta equivale a recusa. Confirmar novamente isolamento dos produtores e imagem/ID do worker de prévias, então usar SIGINT somente nesse legado e aceitar apenas exit130. Timeout não autoriza SIGKILL ou recriação forçada.
7. Usar proveniência Compose do próprio worker, e não a lista API/web por suposição. Validar caminhos e ordem, versão do Compose e hash do serviço ativo; conferir config normalizada antes/depois, permitindo somente imagem e metadados de identidade correspondentes. Overlay privado seleciona ID exato, build/pull proibidos e apenas up --no-deps --no-build --pull never preview-adjustment-worker; proibir remoção de órfãos. Se não houver forma verificável de produzir configuração equivalente, abortar antes da manutenção.
8. Aguardar saúde, confirmar config/camadas/pacotes instalados e contratos read-only de startup, schema intacto e snapshots dos serviços preservados. Retomar os mesmos containers API/worker e restaurar restart policy; verificar saúde, HTTPS e rotas protegidas sem OTP real, compra, upload ou dados de cliente. Restaurar o proxy somente depois dos gates. Registrar recibo de sucesso e imagem anterior para rollback; remover apenas o marcador de tentativa concluída.

## Recuperação e limites

- Antes da troca: retomar os mesmos containers já parados, restaurar políticas e configuração de proxy original, comprovar saúde; nenhuma imagem é substituída.
- Depois da troca: manter entrada e produtores isolados; só interromper o candidato após drenar o seu trabalho pelo mesmo contrato. Restaurar ID anterior pelo mesmo Compose validado, confirmar saúde/configuração, então retomar produtores e tráfego. Não parar à força um candidato processando para obter rollback rápido.
- Falha ao restaurar saúde, identidade ou proxy: manter journal/isolamento e exigir recovery explícito retomável por fase, sem liberar tráfego ou apagar evidência. Uma queda do processo coordenador deve deixar instruções e recibos para recuperação pelo lock comum.
- A imagem antiga preserva código que não oferece drain. Não inserir novo handler no candidato como se isso resolvesse retroativamente a primeira parada. Nenhuma alteração de modelo, dado, fila, schema ou imagens fora do worker de prévias faz parte desta change.
- Nginx sofre somente alteração temporária/restaurável para a barreira; API/worker sofrem pausa, sem publicação de imagem. Portanto não prometer ausência de impacto ou zero downtime.

## Validation
Testes de contrato para ordens, falhas em cada fase, tarefa ativa, timeout, imagem divergente, recuperação e preservação. Rehearsal real isolado deve distinguir containers sintéticos de Oracle, sem credenciais/dados reais. Cada evidência só vale para o código e ambiente executados.

## Open Questions
A autorização da janela e a comprovação/aceitação operacional do tratamento dos callbacks dependem de decisão posterior do proprietário. Nenhuma pausa na Oracle está autorizada nesta change.
