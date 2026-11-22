# Tasks

## 1. Viabilidade e seleção local

- [x] 1.1 Conferir documentação primária dos candidatos ACME, store cifrado e integração NPM; entregar matriz com versões/digests, licença, permissões, renovador responsável e limitações. Verificar especificamente se o caminho de instalação evita token/chave privada em tabelas comuns e comandos privilegiados arbitrários; rejeitar candidato incompatível antes de escrever integração.
- [x] 1.2 Registrar o mecanismo local selecionado a partir da matriz, seus contratos e dependências em `design.md`; comprovar que atende aos deltas e preserva a fronteira do NPM compartilhado. Mudança material de arquitetura ou exceção ao contrato exige revisão humana, não fallback implícito.

## 2. Protótipo isolado e provas de segurança

- [x] 2.1 Implementar adaptador local de referência cifrada/materialização temporária usando apenas segredo sintético e transporte de teste; verificar permissões, ausência em argumentos/DB/logs, expiração e limpeza em sucesso/falha. Não configurar token nem store real.
- [x] 2.2 Implementar e documentar staging/validação do bundle e instalador de operação/destino fixos; testar chave incompatível, nome incorreto, cadeia/validade inválidas, caminho malicioso e recusa de operação fora do wildcard. Nenhum acesso ao socket Docker ou shell arbitrário pelo emissor.
- [x] 2.3 Ensaiar integração em laboratório NPM isolado e compatível com o digest inventariado, após inventariar recursos/portas locais; verificar entrega do certificado sem persistir token/chave em tabelas comuns e sem alcançar serviços preexistentes. Usar somente certificado sintético e dados descartáveis próprios; se inviável, registrar bloqueio sem adaptar produção.

## 3. Renovação, retorno e revisão

- [x] 3.1 Exercitar renovação idempotente, falha de DNS/CA sintética, falha de instalação e retorno ao bundle saudável; entregar relatório sanitizado com evidência de continuidade e nenhuma chamada ACME/DNS real.
- [x] 3.2 Revisar o código diretamente afetado segundo a política de refatoração contínua, executar validações pertinentes e OpenSpec strict; entregar runbook com custódia/recuperação, versões, caminhos/comandos fixos, impacto, limites e autorizações exigidas. Não publicar, criar timer real, emitir certificado ou modificar DNS/NPM/Oracle.

## Workflow follow-up

- Submeter o protótipo e o mecanismo concreto à revisão humana antes de vincular a solução operacional às tasks 3.3/3.4 do ingresso.
- Configuração de credencial real, instalação/renovação externa e qualquer mudança em serviços exigem inventário atual e autorização própria. Nenhuma aprovação desta proposta autoriza indisponibilidade.
- Sincronizar specs e arquivar somente após implementação validada e revisão humana.
