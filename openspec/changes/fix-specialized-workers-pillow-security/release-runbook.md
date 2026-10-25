# Publicação pontual Pillow

## Escopo e pré-condições

Autorização de 25/10/2026: corrigir primeiro Pillow nos seis workers especializados; proprietário já aceitou manutenção temporária do Pick-your-Pic. PR258 reutilizado; revisão humana, CI de PR/main e fingerprint exato continuam gates. Não executar este roteiro como consequência automática de monitoramento/Dependabot. Publicação Mercado Pago permanece separada.

Host `clearbudget-vnic`, projeto `markina-gallery`, `/opt/markina-gallery`; domínio `https://markina.pickyourpic.com.br`, única porta do projeto127.0.0.1:8080. Banco0087, sem DDL/Alembic. Trocar somente index/search/maintenance SFace, index Gemma, preview adjustment e RAW. Pausar API/worker geral originais para impedir novos claims; web, nginx, PostgreSQL/Redis e Evolution preservam IDs/imagens/StartedAt. Nenhuma alteração de DNS/firewall/certificados, outros projetos, credenciais, modelos, dados ou cobrança.

Usar os quatro scripts versionados `specialized_pillow_candidate.py`, `specialized_pillow_probe.py`, `specialized_pillow_release.py` e `prepare_emergency_api_image.py` em pasta privada0700 sob `/var/lib/markina-gallery/deploy-state/pillow-prepare-*`. O último fornece apenas a função pura de configuração da barreira; não executar seu release antigo. Recibos0600; sem valores de env/segredos/dados de cliente no Git ou logs públicos.

## Preparação sem substituir serviços

1. Confirmar ausência de outro executor, inventário/saúde dos15 serviços e espaço livre. A preparação não usa filas, mounts de produção ou modelos adicionais.
2. Executar `python3 specialized_pillow_candidate.py --receipt <pasta>/prepared.json` no ARM64. Confere wheel PyPI, checksum, pip check, Python/pacotes completos, camadas/configuração e hashes de fontes/modelos. Ensaia padrões sintéticos offline com limites1CPU/1GiB. As únicas tags criadas são aliases locais por conteúdo, nunca tags ativas.
3. Conferir seis recibos e resultados; qualquer deriva não explicada bloqueia. Comparar a regra oficial do resize13 com oráculos exatos, conforme design. Falha de preparação não toca containers ativos. Nunca usar Dockerfiles normais para esta publicação porque resolvem outras dependências e baixam modelos.

## Revisão e selagem

4. Revisar diff/PR258 e integrar somente após CI verde e revisão humana. Não há automerge. A revisão não autoriza substituir API/web pelo código atual de main.
5. Após CI verde do SHA integrado em main, executar `python3 specialized_pillow_release.py seal --prepared <pasta>/prepared.json --source-sha <SHA_MAIN_REVISADO> --receipt <pasta>/sealed.json`. Verifica main/CI oficiais, runtime dos candidatos e inventário completo; nenhuma substituição. Registrar o fingerprint impresso. Apresentar seis imagens, porta/domínio, manutenção, preservações e recuperação ao proprietário antes da operação.
6. Revalidar se surgiu fila/trabalho elegível. A aplicação recusa diferenças de inventário, schema, arquivos, saúde, restart policy, CI ou pending marker; não contornar por edição de recibos/flags. Se houver deriva legítima, inventariar/selar/revisar novamente.

## Janela aprovada

7. Executar `python3 specialized_pillow_release.py apply --receipt <pasta>/sealed.json --approval <FINGERPRINT_APROVADO>`. Lock exclusivo compartilhado `production-release.lock`; marker durável `pillow-in-flight.json` antes de qualquer mutação. Orçamento300s; não utilizar `docker stop`/timeout com SIGKILL.
8. O executor salva atomicamente a configuração nginx do projeto e admite somente health; demais caminhos respondem503. Eventos Evolution permanecem na retentativa existente ensaiada em container isolado; não reiniciar Evolution, que mantém retries em memória. Esta janela limitada não equivale a inbox durável para todas as integrações externas. Falha/tempo excessivo deve preservar barreira e exigir recuperação, nunca reportar sucesso.
9. SIGTERM na API e worker geral originais, com parada confirmada0;13 filas/outboxes sem queued/pending/processing. Registrar digest financeiro após drenagem. Suspender `unless-stopped` e enviar SIGINT aos seis legados somente com wchan ocioso/identidade conhecida, aguardando130. Confirmar ausência de escritor PostgreSQL ativo e repetir filas. Nenhum SIGKILL nem alteração de registros para forçar fila vazia.
10. Aplicar overlay privado contendo **somente seis IDs de imagem**, com todos os seis arquivos Compose atuais e `--env-file docker/.env.homolog -p markina-gallery --profile '*' up -d --no-deps --no-build --pull never --force-recreate <seis>`. Todos os consumidores anteriores devem estar parados antes de `force-recreate`; a flag nunca deve encerrar processo ativo. Não mudar o checkout de produção nesta correção de biblioteca.
11. Exigir saúde dos seis, preservar digest financeiro/schema, retomar os mesmos IDs API/worker e políticas anteriores, conferir configuração/mounts/env por digest, Python/Pillow/pacotes/fontes/modelos carregados, imagens dos nove preservados e StartedAt dos sete que não foram pausados. Reabrir ingresso somente após provas; HTTPS200 nos três smokes. Guardar `published.json`; manter overlay/candidatos/imagens anteriores e os recibos para releases seguintes. Não limpar/prunar recursos.

## Recuperação

12. Qualquer falha mantém marker e tenta manter503; não iniciar outra publicação. Inspecionar o journal privado e processos sem reenviar mensagens nem editar dados. Executar `python3 specialized_pillow_release.py recover --receipt <mesmo sealed.json> --approval <mesmo fingerprint>`. Recuperação não depende de GitHub/CI acessível e nunca restaura banco nem rebaixa schema.
13. A recuperação reconfirma paradas pendentes, impede sinal tardio após restart, recusa imagens desconhecidas/trabalho ativo e permite consumidor ausente somente após composição parcial registrada. Recria somente os seis com imagens anteriores; confirma runtime/config/saúde/digest, retoma os mesmos escritores e só então abre o ingresso. `recovered.json` declara `security_fixed=false`: rollback não corrige a vulnerabilidade. Falha no próprio recover mantém barreira para intervenção; nunca aumentar permissões ou usar SIGKILL.

## Continuidade Orders

Depois de publicação confirmada, renovar inventário e backup do checkout, considerar o novo overlay persistente e reconciliar explicitamente o pin Pillow13 da fonte. Não reaproveitar cegamente o fingerprint anterior Orders nem liberar clientes/pagamentos reais. Atualizar tarefas/specs com evidências; sincronização/arquivo somente após revisão humana.
