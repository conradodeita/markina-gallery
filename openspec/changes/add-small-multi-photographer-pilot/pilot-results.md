# Resultado do piloto sintético local

## Estado e origem

Task 7.3 concluída após prontidão 7.2. Janela de execução: 2026-10-01T18:55:11.471299+00:00 a 2026-10-01T18:55:53.065124+00:00 (UTC, 01/10/2026). Não houve deploy ou piloto remoto.

Branch feature/plan-small-multi-photographer-pilot, candidato local ainda em preparação de commit. Alembic 0069 → 0070 → 0071 em database UUID exclusivo do PostgreSQL 17 sintético da porta 15470. Conta vazia da migration preservada como A, com B explicitamente provisionada; nenhum dado operacional real. API Uvicorn loopback 8000 e frontend Next 16.3.2 compilado loopback 3038, portas livres verificadas, processos próprios encerrados no finally. Database/template UUID descartados; mídia somente em basetemp de teste.

## Jornadas e negativas

- Dois admins autenticados na interface por senha Argon2/TOTP, seis clientes por link/OTP em perfis Edge headless independentes, viewport 390 × 844. Seis jornadas cliente simultâneas medidas por intervalos UTC, uma por cadastro; nenhuma sessão compartilhada. OTP obtido da mensagem do adaptador em memória, sem substituir desafio/sessão nem usar código fixo.
- Mesmo telefone em A0/B0, identidades, nomes, UUIDs, sessões, seleções e históricos independentes. Pasta comum com três fotos para todos; mais três restritas somente ao primeiro cadastro de cada conta. Coleção/preview reais conferidos; sem overflow horizontal.
- Comércio exercitado pelas APIs reais com cookies do navegador: preços próprios de 700/800 centavos, seleção de uma foto por cliente e uma adicional restrita para A0/B0, PIX sintético com recebedores diferentes, seis pedidos/oito itens. Confirmação própria e URLs de entrega sintéticas conferidas em Compras; nenhum pagamento ou fetch de álbum.
- 51 recusas diretas esperadas no roteiro final: edição de cliente/configuração alheios, monitor de B, OTP em outro link, galeria/foto/preview/seleção/carrinho cruzados, pasta restrita para não destinatário, confirmação/entrega pelo admin alheio. Status seguem os contratos (401/403/404/409); nenhuma exposição/efeito cruzado aceito.
- Operator A consulta o monitor; B tem capability falsa, endpoint 403 e painel omitido. Cópia real pela interface/clipboard confrontada com formatCapacityReport do produto, preservando capacity-report/v1 e todos os campos. Windows converte LF em CRLF no clipboard: somente essa conversão é permitida na conferência; arquivos finais preservam bytes UTF-8 copiados, sem segunda tradução de newline.
- Worker local sem atrasos artificiais concluiu 12 jobs e 36 derivados JPEG prontos. Seis OTPs foram aceitos pelo adaptador sintético com idempotência tenant:owner:otp:challenge; zero requisições externas do navegador. SMTP/push/WhatsApp reais e biometria não executados.

## Monitor antes durante e depois

| Etapa | Pedido de leitura UTC | Início da amostra UTC | Fim da amostra UTC | Cache | Pool disponível / em uso | PostgreSQL ativo / idle / idle in transaction |
|---|---|---|---|---|---|---|
| before | 2026-10-01T18:55:21.735339+00:00 | 2026-10-01T18:55:20.759621Z | 2026-10-01T18:55:20.951761Z | False | 3 / 0 | 1 / 2 / 0 |
| during | 2026-10-01T18:55:28.188006+00:00 | 2026-10-01T18:55:20.759621Z | 2026-10-01T18:55:20.951761Z | True | 3 / 0 | 1 / 2 / 0 |
| after | 2026-10-01T18:55:53.044115+00:00 | 2026-10-01T18:55:52.353709Z | 2026-10-01T18:55:52.411035Z | False | 5 / 0 | 1 / 4 / 0 |

As cinco filas mostraram queued=0 e processing=0 nas três leituras. Mídia/busca/index/manutenção tiveram candidatos=0; candidatos de ajuste de prévias permaneceram indisponíveis, conforme contrato. Idades vazias: unavailable/empty_queue. A leitura durante reutilizou a mesma amostra inicial: não mede pico, simultaneidade de queries ou pressão das seis jornadas. A final aguardou TTL real de 30 s e apresentou amostra nova. Os jobs curtos terminaram entre leituras; conclusão comprovada separadamente pelos 12 jobs completed/36 derivados ready, sem inventar espera ou pico.

Pool deste processo de teste: base 5, overflow 10, teto potencial 15, timeout configurado 30 s. Espera e contagem de timeouts não instrumentadas permanecem indisponíveis. PostgreSQL próprio: max_connections=20, reserva de superusuário=3, reserva adicional=0; a conexão ativa do coletor participa da observação. API e worker de teste compartilham processo/pool: isso não representa os processos separados da homologação. Aumento de conexões idle é retenção do pool depois do uso, sem transação idle observada nas amostras.

Orçamento global permaneceu indisponível por process_inventory_missing, external_consumers_unknown e operational_reserve_unapproved. Filas faciais vazias não provam saúde dos workers ou desempenho biométrico. Ensaio não demonstra capacidade máxima, p95, fairness, SLO, orçamento/margem global ou canais reais.

## Evidência reproduzível

Relatório externo C:/codex-data/test-runs/pilot-journeys-verified.xml: **4 passed**, 71,59 s (três casos de preparação e piloto integrado). Artefatos sanitizados em C:/codex-data/test-runs/pilot-local-20261001-verified/: pilot-summary.json, capacity-{before,during,after}.json/.txt e operator-after.png; nenhum deles versionado. Reprodução a partir de backend/:

```text
PHOTOGRAPHER_TEST_DATABASE_URL=<URL do PostgreSQL sintético próprio 127.0.0.1:15470/pyp_photographer_test>
DATABASE_URL=sqlite:///<arquivo descartável externo>
PYP_RUN_LOCAL_PILOT=1
PILOT_EVIDENCE_DIR=C:/codex-data/test-runs/<novo-diretório-exclusivo>
python -m pytest tests/test_tenant_pilot_preparation.py tests/test_tenant_pilot_journeys.py -q --basetemp=<novo-diretório-temporário-exclusivo>
```

Pré-requisitos: build Next cujo rewrite aponta para loopback 8000, portas locais 8000/3038 livres e Edge/Playwright instalado. Não executar com URLs operacionais. Falha de porta/dependência impede o ensaio; não encerrar processo vizinho.

Primeiras tentativas não foram aceitas: rota negativa GET inexistente corrigida para PATCH real; CRLF do clipboard Windows conferido explicitamente; chave externa do adaptador inclui namespace tenant; negativa de carrinho usa 403 vigente. Nenhuma correção de produção foi necessária para essas falhas do executor. Reforço final confere status e URL exata da entrega no histórico e preservação dos bytes copiados.

## Próximo gate

Pacote operacional 8.1 e autorização específica de publicação. Depois: deploy/health/legado, autorização de contas/canais/destinatários e ensaio real 8.3. Evidência local não substitui esses aceites. Sincronização/arquivo desta change somente após revisão humana.
