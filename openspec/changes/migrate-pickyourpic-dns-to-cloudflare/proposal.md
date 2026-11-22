# Proposal

## Why

O proprietário escolheu Cloudflare para o DNS de `pickyourpic.com.br`, visando subdomínios dos fotógrafos e automação futura. O domínio permanecerá registrado no Registro.br. `markina.pickyourpic.com.br` atende clientes em produção e deve conservar endereço, destino e operação durante a transição.

## What Changes

- Preparar a migração da zona inteira, com inventário autenticado completo e comparação antes de trocar nameservers.
- Usar plano Free e configuração inicialmente DNS-only, preservando apontamentos, TTLs e serviços atuais. Proxy, WAF, cache e novos destinos ficam em etapa posterior, com validação própria.
- Tratar DNSSEC ativo como pré-condição de corte: DS do provedor anterior não pode acompanhar uma troca incompatível de servidores; reativar assinatura da nova zona após validação.
- Preparar o caminho para curinga futuro sem publicar novos hosts antes de validar proxy/HTTPS e isolamento da aplicação. Cadastro de conta e disponibilidade de hostname não são equivalentes.
- Registrar referência saudável, checks de resolução/HTTPS e procedimento de recuperação. Não reiniciar nem reconfigurar serviços do Oracle por causa da troca de DNS.

## Capabilities

### New Capabilities

- `deployment-operations/cloudflare-dns`: migração preservadora da zona e gates para ativação futura de curinga/proxy.

### Modified Capabilities

Nenhuma alteração no contrato de cadastro, autenticação, WhatsApp ou upload nesta change de infraestrutura.

## Impact

DNS autoritativo e DNSSEC de `pickyourpic.com.br`, Registro.br e conta Cloudflare do proprietário. Preparação local e consultas read-only estão autorizadas; a troca pública exige inventário completo e revisão do plano, conforme as instruções operacionais e a proibição de interromper clientes sem consentimento. Sem migration de banco, deploy, mudança de `.env`, token, chave, servidor, container ou projeto vizinho. Refatoração proporcional: escopo documental/operacional, sem limpeza funcional elegível.
