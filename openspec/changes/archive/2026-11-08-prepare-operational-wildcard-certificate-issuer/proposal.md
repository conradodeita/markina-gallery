# Proposal

## Why

O DNS wildcard foi publicado com autorização em 08/11/2026, mas o emissor existente é exclusivamente sintético. A leitura atual do Oracle encontrou systemd 249 sem `systemd-creds`; o estudo baseado em documentação 255 não comprova loader cifrado nesse servidor.

## What Changes

- Preparar e provar localmente as ferramentas operacionais que faltam: loader de credencial cifrada, emissor ACME isolado, verificação de cadeia pública e instalador com interface restrita entre identidades distintas.
- Ensaiar compatibilidade com systemd 249 e ARM64, perda/reinício, recuperação, renovação e preservação dos hosts exatos, usando somente segredos/CA/DNS sintéticos nesta etapa.
- Entregar pacote operacional revisável com versões fixas, caminhos, permissões, hashes, custódia e plano de impacto/retorno; nenhuma instalação real será executada por esta change.
- Preservar os scripts de laboratório existentes e reaproveitar componentes somente após comprovar compatibilidade; não transformar o protótipo sintético em executor de produção retirando suas proteções.

## Capabilities

### New Capabilities

Nenhuma. Ferramentas operacionais para contratos já especificados.

### Modified Capabilities

Nenhuma alteração normativa: aplicam-se `deployment-operations` e os deltas aprovados de `enable-tenant-subdomain-ingress` e `secure-wildcard-dns-credential-custody`. `skip_specs: true` evita duplicar os requisitos existentes de custódia, instalação, continuidade e autorização.

## Impact

Somente ferramentas, fixtures e documentação locais futuras, em caminhos próprios; sem alterar app, migrations, frontend, `.env`, NPM, units, certificados ou credenciais existentes. O mecanismo concreto de desbloqueio após reboot será selecionado por evidência e submetido ao proprietário se exigir nova operação manual, serviço externo ou custo. Não atualizar systemd/SO do host como solução implícita. A revisão desta proposta autoriza implementação local, não emissão ACME, token, timer ou aplicação no Oracle.
