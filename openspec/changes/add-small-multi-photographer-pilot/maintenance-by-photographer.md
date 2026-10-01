# Manutenção por fotógrafo

Estatísticas, opções de filtro, listas TXT/CSV/HTML, resumo de arquivos e recibos pertencem à conta revalidada. Filtros de outra conta produzem resultado vazio; recursos por UUID têm resposta equivalente ao inexistente. O resumo de armazenamento soma arquivos associados a registros próprios; arquivos sem atribuição demonstrável permanecem fora dele. A medição física integral é operação da instalação, cuja permissão será validada na task 6.1.

Inventário e exclusão de cliente mantêm histórico comercial protegido. Clientes elegíveis são removidos somente da conta do administrador vinculado, inclusive sessões, OTPs e entregas cliente dessa conta. Mesmo telefone em B e OTPs técnicos administrativos permanecem intactos. Recibo, replay e classificação de falha pós-commit exigem conta; chave idempotente igual em A/B representa duas operações independentes.

Inventário, agendamento, status, retry e cancelamento de exclusão/desvinculação de galeria também exigem owner. Cancelar A não reativa B. A execução assíncrona, arquivos/retenção e biometria continuam na task 5.3; nenhuma autorização de dado biométrico real é inferida dessa implementação.

Cleanup integral de homologação continua offline, exige confirmação e instalação única. Recusa uma instalação com A/B antes de arquivos. Nenhum comando integral de limpeza, banco real, deploy ou ambiente foi executado nesta etapa; os testes usam apenas schemas e arquivos sintéticos descartáveis.

Evidência: `test_tenant_lifecycle.py`, regressões de migration/cleanup e `validation.md`.

## Execução assíncrona e retenção — task 5.3

O worker faz claim apenas de contas ativas e revalida o vínculo inequívoco do ator, origem e lease antes de cada etapa de lifecycle. Suspensão/revogação conserva trabalho próprio sem consumir tentativa nem interromper B. Preflight integral confere manifestos contra recursos da origem e rejeita namespace alheio, symlink que cruza conta ou chave legada que coincide com referência viva de B, antes do primeiro unlink. Exclusões e minimização comercial exigem owner explícito; pedidos protegidos e seus snapshots permanecem. Novos históricos usam namespace por conta/item; referências antigas conservam caminho e checksum.

Jobs e consultas faciais carregam owner e lease tipados, com prova de galeria/foto/cliente/política/rollout e público atual antes de descriptografia/publicação/purge. Representação legal e calibração não ampliam privilégios para outra conta. Envelope AEAD/AAD e arquivos UUID de referências permanecem compatíveis; nenhum motor ou dado biométrico real foi autorizado nesta implementação. Novas fontes temporárias usam staging por conta, revalidado antes da escrita/publicação. Fragmentos globais legados sem origem demonstrável ficam preservados quando houver várias contas, exigindo reconciliação explícita.

A retomada no navegador guarda somente UUID da consulta sob contexto opaco fornecido pelo servidor para conta/cliente/sessão. Não conserva imagens, vetores ou tokens. Chaves antigas ou de outra sessão são descartadas antes da leitura; logout, recusa de acesso e troca detectada no foco invalidam respostas em voo. O contexto de storage não concede acesso, e todos os endpoints continuam autorizando no backend. Gates globais de ativação permanecem até o checkpoint 7.2.
