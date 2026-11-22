# Spec Delta

## Purpose

Migrar a autoridade DNS de Pick-your-Pic preservando o serviço em produção e a validade da resolução durante a transição de DNSSEC.

## ADDED Requirements

### Requirement: Inventário e espelhamento preservador

A migração SHALL conferir a zona completa no provedor atual e espelhar todos os registros de serviço na Cloudflare Free com proxy desativado, sem alterar destinos ou serviços Oracle. A varredura automática SHALL NOT substituir o inventário autenticado. NS, SOA e assinaturas gerenciadas SHALL corresponder ao novo provedor, sem importar chaves do anterior.

#### Scenario: Preparação antes da delegação

- **WHEN** a zona Cloudflare estiver pendente
- **THEN** os registros de serviço SHALL corresponder ao inventário e responder nos novos servidores antes de alterar a delegação pública
- **AND** a preparação SHALL NOT reiniciar containers nem modificar dados, proxy ou certificados

### Requirement: Corte autorizado com DNSSEC compatível

O executor MUST apresentar inventário, hosts/portas e plano de impacto zero para revisão explícita antes do corte público. A transição SHALL impedir delegação para uma zona incompatível com o DS publicado. Qualquer redução temporária de DNSSEC SHALL exigir confirmação específica e verificações de cache; a assinatura nova SHALL ser habilitada e validada após a transição.

#### Scenario: DS anterior ainda publicado ou em cache

- **WHEN** o DS do Registro.br ainda puder exigir a assinatura anterior
- **THEN** o executor SHALL NOT efetuar uma troca incompatível de nameservers
- **AND** SHALL manter a tarefa pendente até existir procedimento confirmado pelo provedor e autorização aplicável

### Requirement: Evidência e recuperação compatíveis

A migração SHALL registrar respostas DNS e HTTPS anteriores e posteriores, propagação, divergências e estado de DNSSEC. A recuperação SHALL considerar simultaneamente nameservers, DS, DNSKEY e caches; trocar apenas nameservers SHALL NOT ser apresentado como recuperação instantânea garantida.

#### Scenario: Divergência durante a transição

- **WHEN** ocorrer SERVFAIL, destino divergente ou falha TLS/HTTP nova em markina
- **THEN** o executor SHALL interromper novas mudanças e diagnosticar a cadeia e os destinos preservando os serviços ativos
- **AND** somente SHALL executar recuperação compatível com o estado observado e a autorização operacional

### Requirement: Separação do provisionamento SaaS

A migração SHALL preservar markina e SHALL NOT publicar curinga, novos destinos ou ativar proxy/cache como efeito colateral. Provisionamento de host por tenant SHALL exigir DNS, TLS, proxy e resolução isolada pela aplicação validados em escopo próprio.

#### Scenario: Zona migrada com sucesso

- **WHEN** a autoridade DNS estiver na Cloudflare
- **THEN** o cadastro e o WhatsApp SHALL manter seus contratos existentes
- **AND** a mudança de provedor SHALL NOT ser apresentada como subdomínio automático já implementado
