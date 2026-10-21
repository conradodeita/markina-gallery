# Revisão técnica direcionada — PRs #260 e #262

## Escopo e resultado

Revisão local em 21/10/2026 do contrato herdado de #260 (`0959c64`) e do delta #262, incluindo correções de catálogo/reset e CI nativo. Sem auditoria geral, alteração do PR pai ou do #261, consulta operacional Oracle, segredo real ou chamada financeira externa. Não foi identificado relaxamento de autorização, fallback entre contas ou reemissão automática na área revisada. Aprovação do candidato continua condicionada ao CI integral e à revisão humana.

| Fronteira | Evidência de código e validação pertinente |
|---|---|
| Gestão autenticada | Rotas InfinitePay revalidam sessão ADMIN, vínculo ativo, same-origin, senha e desafio OTP ligado a tenant/sessão/admin/finalidade; proposta versionada sob lock. HTTP/ASGI com dois tenants verifica recusa de cliente, ausência de sessão, origem externa, parâmetro tenant e desafio estrangeiro sem mock de autorização. |
| Cofre e mestre | AES-256-GCM, nonce aleatório e AAD por ambiente/tenant/UUID/finalidade/versão/key-id. Configuração mestre externa e exclusiva da API, sem default; testes de adulteração/transplante, material errado, ausência e restore. Não há endpoint que retorna plaintext ou capacidade de leitura genérica para operador global. |
| Saída e navegador | Resposta do desafio usa allowlist; configuração expõe somente status, erros de validação omitem body/input; chave usa SecretStr no backend e entrada transitória na UI, sem storage ou telemetria adicionada. Respostas no-store; UI exige capacidade explícita do cofre e apaga campo após envio. Testes cobrem erros/logs/auditoria/respostas e entrada não repopulada. |
| Emissão e conta | Checkout usa tenant do cliente persistido e lock da conta; congela handle/version/credential-id. FK composta na configuração e compra impede referência estrangeira. Testes PostgreSQL de concorrência comprovam snapshot antigo ou novo íntegro; ausência de mestre bloqueia antes da reserva. |
| Verificação financeira | Retorno browser é candidato; consulta server-to-server usa credencial do snapshot, handle/order_nsu/transaction_nsu/slug. Aplicação repete tenant/pedido/valor/método, unicidade e deduplicação. HTTP A/B não confirma pedido estrangeiro e replay não duplica aplicação. Webhook sem assinatura documentada não é prova financeira. |
| Troca e histórico | Substituição cria versão e conserva a antiga. Compra legada nula usa somente binding original por tenant, nunca chave gerida atual. Desconexão sob lock recusa qualquer estado não terminal, apaga envelopes somente quando permitida e impede fallback. |
| PIX e incerteza | PIX manual conserva seu contrato; cartão não é obrigatório para disponibilizá-lo. Tentativa financeira unknown é persistida antes do efeito externo e não é emitida novamente automaticamente. Resposta não paga não é prova de ausência de link; recuperação continua conservadora. |
| Rotação | Utilitário dry-run/apply por tenant, confirmação explícita e commit atômico, sem segredo em argumentos/relatório. Testes comprovam A não recifra B e adulteração impede commit integral. Não retirar chave necessária a pendência, OTP aberto ou backup. |
| Cleanup/reset | Cofre é configuração R/K em metadata/FKs e nos dois consumidores de limpeza. Reset proprietário mantém versões/ciphertext/nonce/ponteiro próprios, remove apenas contas elegíveis à política existente e valida referências antes de mutação. Testes sintéticos em PostgreSQL; nenhum reset operacional executado. |
| Gates de imagens | Mesmos builds e conferência do lockfile em AMD64/ARM64 nativos; matriz verifica uname, fail-fast=false e resultado agregado permanece obrigatório. Falha/cancelamento não vale como aprovação. Sem runner pago, alteração de dependências ou workflow de publicação. |

## Limites persistentes

- Testes sintéticos não comprovam aceitação da chave, recebedor, liquidação ou recuperação no provedor real. Cadastro informa validação remota indisponível, sem endpoint fictício ou cobrança automática.
- Não há assinatura de webhook/consulta de recuperação suficiente documentada para resolver automaticamente criação ambígua sem identificadores. Compra `e2194ce5` permanece fora de qualquer mutação; decisão do titular/provedor e autorização própria são necessárias.
- Gerador estático antigo continua limitado por `RawDevelopmentSettings` preexistente; não é evidência verde. Contratos da nova tabela são comprovados separadamente por catálogo/FKs/HTTP/testes de preservação.
- Homologação publicada, inventário de imagens Oracle, backup operacional/restore, provisão mestre e migration/publicação exigem operações e autorizações separadas. Plano em `release-plan.md` não é execução.
- Retorno ao binário #260 isolado após adoção gerida não constitui rollback seguro. Manter imagem compatível identificada por digest e barreira para novas operações, sem apagar snapshots ou escolher outra chave para a compra.

## Refatoração proporcional

Nenhuma oportunidade adicional de remoção ou reorganização foi necessária para corrigir o delta. Reutilizados identidade, desafios, locks, adaptador e políticas existentes. Não alterar gerador RAW, manutenção Python, contratos históricos de migration ou outros cards para obter aprovação aparente.
