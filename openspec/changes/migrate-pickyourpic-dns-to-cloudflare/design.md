# Design

## Context

O proprietário escolheu migrar a zona inteira para Cloudflare Free em 05/11/2026 e manter o registro no Registro.br. Markina atende clientes; nenhuma interrupção está autorizada. O inventário autenticado identificou apenas dois registros A. DNSSEC está ativo no provedor anterior. Evidências e roteiro constam em `migration-plan.md`.

## Goals / Non-Goals

- Preservar endereços e disponibilidade sem tocar nos containers, configuração do Oracle ou dados.
- Preparar zona pendente com os dois A, TTL 3600 e DNS-only; comparar antes do corte.
- Tratar DNSSEC como dependência do corte, não ignorar o DS existente.
- Não ativar proxy, WAF, cache, curinga, cliente OAuth, SMTP ou automação SaaS nesta mudança.
- Não criar credenciais ou alterar `.env`. Mudança documental/operacional: não há código elegível para refatoração.

## Decisions

1. **Separar autoridade de tráfego:** usar Cloudflare somente como DNS inicialmente. O IP, TLS e a rota atual de markina permanecem iguais; ativar proxy no mesmo corte ampliaria o risco de uploads, sessões e webhooks.
2. **Espelhamento completo:** tabela autenticada do Registro.br é a referência, corroborada por consultas públicas. Não criar registros MX/TXT/AAAA inexistentes nem importar NS/SOA/DNSKEY antigos. Revisar o resultado da varredura automática.
3. **Zona pendente antes da produção:** criar e validar a zona não altera a delegação no Registro.br. Registrar nameservers atribuídos antes de solicitar o corte concreto.
4. **DNSSEC por procedimento confirmado:** a FAQ do Registro.br confirma que não permite desativar DNSSEC separadamente no seu DNS. Sua documentação técnica descreve a saída integrada: informar pelo menos dois servidores autoritativos e aguardar pelo menos duas horas para retirada da chave antes da publicação dos NS novos; transição descrita de até três horas. Usar esse fluxo gerenciado, com confirmação específica para a redução temporária de proteção, sem inventar botão de desativação ou inserir o DS antigo na nova zona. Revalidar DNSSEC Cloudflare depois que autoridade/caches estiverem coerentes.
5. **Revisão humana final:** o proprietário aprovou a direção da migração, mas o corte público depende da apresentação deste inventário e da confirmação da sequência exata. Não pedir credenciais pelo chat.
6. **Recuperação com estado:** conservar inventário e referência saudável, verificar se o provedor antigo conserva a zona/chaves durante a transição e planejar recuperação com DS/NS compatíveis; não prometer reversão imediata.

## Risks / Trade-offs

- DS incompatível causa SERVFAIL mesmo com registros A corretos. O procedimento oficial integrado foi confirmado; monitorar DS/NS e a transição real depois da autorização, sem antecipar delegação por outro mecanismo.
- Caches podem usar a autoridade anterior por horas; manter respostas equivalentes e não prometer prazo exato nem indisponibilidade zero garantida. O retorno ao DNS Registro.br só é disponibilizado quatro horas após a saída segundo sua documentação, portanto não existe rollback imediato garantido.
- A raiz responde 404 antes da migração; mudar DNS não publica o website. Markina responde 200 e é a referência de serviço.
- DNS-only não adiciona proteção HTTP por WAF/DDoS proxy; é escolha temporária de preservação, não ativação de toda a segurança Cloudflare.
- Usar DNS público não demonstra todos os fluxos autenticados. Smoke não financeiro com sessão autorizada é uma verificação separada; não simular compra real.

## Limites operacionais

- A documentação descreve a transição preservando funcionamento, mas não garante por quanto tempo conservará a zona/chaves antigas depois dela. Não tratar o DNS antigo como backup permanente; o inventário permite reconstrução, sujeita à espera de quatro horas e aos caches. Nenhuma delegação será salva antes da revisão operacional explícita.
