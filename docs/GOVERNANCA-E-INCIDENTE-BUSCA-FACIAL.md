# Governança, RIPD e incidente da busca facial

Este documento é o registro operacional mínimo do tratamento biométrico da Markina Gallery. Ele não substitui parecer jurídico. Produção MUST permanecer bloqueada enquanto as aprovações humanas e jurídicas aplicáveis, a calibração representativa e o teste de capacidade ARM estiverem pendentes.

## RIPD — registro e aprovação

O controlador SHALL manter um RIPD versionado e aprovado antes do primeiro canary real. O registro SHALL identificar sem PII nos artefatos técnicos:

- finalidade específica: reordenar, para uma cliente autenticada, fotos de uma Galeria pública à qual ela já possui acesso;
- necessidade e proporcionalidade, incluindo a alternativa sempre disponível de navegação e seleção manual;
- categorias tratadas: referência temporária enviada pela cliente e embeddings cifrados do acervo autorizado;
- origem: upload administrativo do acervo e referência fornecida voluntariamente pela cliente autenticada;
- fluxo e destinatários, incluindo qualquer operador/suboperador efetivamente contratado;
- base legal documentada, aviso e consentimento versionados e procedimento de revogação;
- tratamento infantil separado na fronteira de admissão, com representação legal comprovada e aprovação jurídica/humana;
- retenção: referência terminal ou até 15 minutos, candidatas até 24 horas e purge dos índices no fim do escopo/finalidade;
- controles: AEAD/AAD, chaves separadas por ambiente, autorização repetida, rate limiting, backpressure, auditoria minimizada e isolamento de rede;
- riscos, medidas, risco residual, responsável pela aceitação e data de revisão.

O RIPD SHALL ser revisto quando mudar modelo, limiar, finalidade, categoria de titular, operador, armazenamento, retenção, base legal ou arquitetura de acesso. Referências a evidências devem ser opacas; imagens, vetores, scores, nomes, telefones e documentos não entram no Git, em métricas ou em tickets comuns.

## Matriz controlador/operador

Os nomes jurídicos e contatos reais SHALL existir somente no registro restrito aprovado. A matriz abaixo define responsabilidades; ela não presume que um terceiro específico já foi contratado.

| Atividade | Controlador | Operador técnico autorizado |
| --- | --- | --- |
| Definir finalidade, base legal, galerias e prazo | decide, documenta e aprova | executa somente instruções documentadas |
| Upload e publicação do acervo | garante legitimidade da origem e do compartilhamento | mantém pipeline, isolamento e disponibilidade |
| Representação e consentimento infantil | verifica, registra, revoga e aprova juridicamente | aplica o gate sem inferir idade |
| Chaves, ambientes e acesso privilegiado | aprova política e responsáveis | protege, rotaciona e registra somente metadados mínimos |
| Retenção, purge e direitos | decide escopo legítimo e responde ao titular | inventaria e elimina derivados do escopo autorizado |
| Rollout e suspensão | aprova gates, allowlist e promoção | executa operação protegida e apresenta evidência agregada |
| Incidente e comunicação | classifica impacto e decide notificações legais/titulares | contém, preserva evidência mínima e reporta fatos técnicos |
| Suboperadores | aprova contrato, finalidade e transferência | não adiciona nem amplia acesso sem instrução registrada |

Toda divergência de papel, finalidade ou instrução SHALL falhar fechada. O administrador/fotógrafo pode operar a interface administrativa, mas isso não transforma o kill switch em base legal nem dispensa os gates do escopo cliente.

## Direitos e revogação

Uma solicitação válida SHALL ser vinculada ao cliente, Galeria pública e prova de representação quando aplicável. O inventário deve retornar apenas contagens agregadas. A execução revoga a prova, cancela consultas/jobs/notificações, elimina referência e candidatas e agenda purge dos derivados aplicáveis de forma idempotente. Fotos, seleções, pedidos, pagamentos e mídia histórica com justificativa independente permanecem fora desse purge.

## Resposta a incidente

Trate como crítico qualquer suspeita de acesso indevido, chave comprometida, cruzamento de galeria/cliente, retenção excedida ou biometria/PII em log. Latência, fila, CPU, memória ou falha acima do SLO são incidentes operacionais; tornam-se críticos se houver risco de isolamento, perda de controle ou retenção.

1. Delimite ambiente e escopo sem copiar imagem, referência, embedding, score ou PII para o registro comum.
2. Bloqueie novas admissões: suspenda a allowlist afetada; para risco sistêmico, desligue o kill switch do ambiente pelo processo operacional autorizado.
3. Mantenha o worker `maintenance` quando seguro, cancele requests abertos e execute o purge prioritário do escopo.
4. Isole somente containers, credenciais, chaves e volumes da Markina Gallery afetados. Não altere proxy, firewall, DNS, certificados nem recursos de terceiros sem nova autorização específica.
5. Para chave comprometida, retire o key-id de novas gravações, introduza chave exclusiva do ambiente por canal seguro e planeje purge/reprocessamento; nunca imprima material criptográfico.
6. Preserve SHA, horários UTC, IDs técnicos necessários em repositório restrito, contagens agregadas, decisões e cadeia de aprovação. Não preserve payload biométrico “para investigação” além da retenção autorizada.
7. O controlador avalia obrigações de comunicação, registra decisão e prazo e coordena titulares/autoridades quando aplicável.

## Recuperação e encerramento

O serviço somente MAY voltar ao estágio anterior quando a causa estiver identificada, o escopo contido, referências/candidatas vencidas estiverem em zero, chaves e autorizações forem válidas, migrations/healthchecks estiverem verdes, seleção manual permanecer saudável e a janela de observação não contiver alerta crítico. A promoção exige novo recibo e aprovação humana; um restart ou a simples troca da flag não encerra o incidente.

O registro final contém impacto agregado, linha do tempo UTC, causa, correções, validações, risco residual e aprovador. Mudanças de comportamento descobertas durante o incidente exigem uma change OpenSpec própria ou atualização coerente da change ativa antes do código.
