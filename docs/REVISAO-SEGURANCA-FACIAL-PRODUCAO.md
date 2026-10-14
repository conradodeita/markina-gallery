# Revisão de segurança do runtime facial

Data da revisão: 2026-09-08. Escopo: código local da change `productionize-facial-search`; nenhuma operação em homologação ou produção foi executada.

## Resultado

Não restou achado crítico ou alto conhecido após a correção do rate limiting de admissão. A revisão não substitui o teste de carga ARM, a validação autenticada nem a aprovação humana dos gates de produção.

| Controle | Evidência verificável | Resultado |
| --- | --- | --- |
| Autorização | sessão de cliente, vínculo ativo, Galeria pública ativa, rollout, política, versões e escopo são repetidos na admissão, execução, leitura, rejeição, cancelamento e seleção | aprovado nos testes de busca, worker, rollout e purge |
| AEAD e AAD | AES-GCM com nonce aleatório e AAD incluindo ambiente, galeria, objeto, finalidade, modelo e versão de dados | transplante de ambiente, galeria, objeto e versão é recusado |
| Rotação de chaves | envelope antigo só é decifrado enquanto a chave antiga autorizada permanece no chaveiro e pode ser recifrado pela chave ativa | rotação e remoção da chave antiga aprovadas |
| Armazenamento temporário | JPEG limitado por bytes/pixels, diretório dedicado, arquivo cifrado com permissão restrita, nome derivado de UUID e defesa contra symlink/travessia | validações e exclusão idempotente aprovadas |
| Retenção | referência terminal ou vencida é removida em até 900 s; candidatas vencem em até 86.400 s; manutenção possui worker reservado | testes de terminal, cleanup, purge e direitos aprovados |
| Logs, métricas e erros | erros persistidos são categorias sanitizadas; logs de indexação usam somente o tipo da exceção; métricas aceitam apenas dimensões e valores agregados em allowlist | validador recusa imagem, foto, embedding, vetor, score, landmarks, caixa facial, nome, telefone e IDs de negócio |
| Rate limiting e abuso | admissão usa limite persistido por fingerprint do vínculo cliente/galeria e fingerprint de rede antes de ler/armazenar o corpo | excesso retorna 429; UUIDs e IP nunca entram em claro no evento de limite |
| Backpressure | profundidade e idade são verificadas antes de armazenar a referência | recusa retentável deixa zero request/job/arquivo novo |

## Achado corrigido

`SEC-FACIAL-001` — severidade alta antes da correção: a rota de criação de consulta possuía backpressure global, mas não limitava repetição abusiva por vínculo e origem de rede. A admissão agora chama `enforce_facial_search_rate_limit` depois da autorização e do tipo de mídia, porém antes da leitura do corpo. O escopo auditado contém dois HMACs com segredo do servidor e nenhuma identidade ou rede em claro. Escopos cliente/galeria distintos não consomem o limite uns dos outros.

## Evidência de execução

- Ruff direcionado: aprovado.
- Suíte consolidada no runtime facial Python 3.13 com NumPy/OpenCV: `51 passed` em 105,31 s.
- O mesmo conjunto na imagem API sem NumPy confirmou corretamente que o caminho vetorial falha fechado; a validação definitiva foi repetida na imagem `Dockerfile.face`, que é o runtime do worker.

## Condições ainda externas

- O teste de carga e recursos no ARM pertence à task 6.4 e exige inventário e autorização imediatamente anteriores.
- A inspeção visual autenticada pertence à task 4.5 e exige login/OTP humano.
- Calibração/equidade e aprovação humana continuam gates independentes; esta revisão não os autoriza.
