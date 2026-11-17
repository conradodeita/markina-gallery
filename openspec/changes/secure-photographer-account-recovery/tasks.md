# Tasks

Decisão substitutiva aprovada: meios verificados primeiro; sem acesso a eles, o proprietário verifica identidade externamente e autoriza recuperação no console. Não exigir documento/selfie nem fator antigo nessa exceção. Aplicação local autorizada em10/11; checkboxes e validation.md identificam o que foi realmente entregue. Todas as provas serão locais/sintéticas; não autorizam produção ou uso de credenciais reais.

## 1. Contratos e reaproveitamento

- [x] 1.1 Inventariar login, reset, TOTP/recovery, troca de identidade tardia, console e reabertura; entregar matriz de provas e consumidores com evidência de código, identificando mudanças e caminhos preservados. Evidência: inventory.md, leitura de rotas, serviços, campos e constraints, sem dados reais.
- [x] 1.2 Reconciliar deltas ativos de encerramento/onboarding com prova independente e sem autoativação; conferir todos os cenários desta spec e validar OpenSpec estrito antes do código dependente. Evidência: design.md e referência de integração na change de encerramento; sem mudança de runtime nesta etapa.

## 2. Atendimento e prova de titularidade

- [x] 2.1 Implementar atendimento restrito ao fotógrafo SaaS elegível e ao proprietário autorizado, usando desafios e fatores existentes; testar contexto, enumeração, rate limit, expiração, exceção manual sem fatores anteriores e tentativa de autoatendimento do PlatformOwner, registrando o contrato.
- [x] 2.2 Implementar declaração manual do proprietário, motivo e vínculo do atendimento à conta/destinatário; provar recusa sem declaração ou privilégio, consumo único, concorrência e proteção contra replay/troca de alvo em PostgreSQL descartável; preservar recuperação comum por fatores anteriores.

## 3. Troca sensível e integração

- [x] 3.1 Implementar confirmação pelo proprietário reautenticado e novo e-mail verificado, com idempotência, revalidação e auditoria sem dados secretos; provar falhas/rollback, sessão alterada, corrida com outro atendimento e isolamento entre tenants.
- [x] 3.2 Invalidar sessões anteriores e integrar tratamento de credenciais comprometidas com mecanismos existentes; testar preservação de fatores válidos, revogações necessárias e ausência de login/reabertura automática, documentando os efeitos exatos.
- [x] 3.3 Integrar o gate de comprovação independente ao fluxo tardio de conta encerrada e ao console; testar que CPF mais e-mail novo não bastam, suspensão não é retirada e exclusão definitiva de mídia não é revertida.

## 4. Interface e documentação de uso

- [x] 4.1 Implementar as interfaces de atendimento e comprovação com linguagem operacional; validar erros, carregamento, acessibilidade, 390/768/1440 px e temas com contas sintéticas, sem exibir segredos ou detalhar infraestrutura.
- [x] 4.2 Atualizar mapa central e instruções por papel com o fluxo efetivamente entregue, decisão externa do proprietário e meios anteriores prioritários e separação de encerramento/eliminação; conferir links e consistência com specs e testes.

## 5. Integração local

- [x] 5.1 Executar jornada sintética com e-mail perdido, fator válido, confirmação administrativa e conta encerrada; executar checks focais e de integração proporcionais, revisar diff e registrar resultados, skips e limites sem afirmar publicação.

## Workflow follow-up

- A decisão manual de identidade é do proprietário, fora do sistema; não adicionar coleta de evidências ou verificação automática sem nova decisão.
- Sincronizar specs principais e arquivar somente após a revisão humana aplicável.
- Release, migrations persistentes, mensagens reais e segredos exigem suas autorizações próprias.

## Checkpoint de pausa — 11/11/2026

6/10 tarefas concluídas com as evidências em validation.md. 2.2, 3.3, 4.2 e 5.1 permanecem pendentes de fechamento/regressões; não iniciar outra change por inferência. Pausa solicitada pelo proprietário, sem novo desenvolvimento até retomada.

Retomada em11/11 autorizada:7/10, documentação por papel revisada e links validados. Checkpoint anterior de pausa é histórico.

## Fechamento local — 11/11/2026

10/10 concluídas. Evidências/limites em validation.md, inclusive execução frontend ampla691/692 e repetição isolada21/21. Não houve alteração de produção nem push. Sincronização/arquivo dependem de revisão humana.
