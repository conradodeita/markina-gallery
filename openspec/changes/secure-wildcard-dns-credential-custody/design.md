# Design

## Context

Ver `proposal.md` e `../enable-tenant-subdomain-ingress/operations-inventory.md`. NPM 2.15.1 escreve a credencial em `certificate.meta` e em arquivo Certbot 0600; a cópia no SQLite 0644 permanece legível no host. Cloudflare DNSSEC e os hosts existentes estão saudáveis. Não há token DNS criado nem certificado wildcard emitido. O cliente DNS Cloudflare ainda não está instalado.

## Goals / Non-Goals

**Goals:** propor emissor ACME separado do NPM, custódia cifrada, entrega restrita do certificado e prova local de renovação/recuperação sem credencial real.

**Non-Goals:** alterar infraestrutura ou segredos atuais; atualizar o NPM compartilhado; escolher um domínio diferente; publicar runtime SaaS; ampliar permissões Cloudflare; autorizar interrupção. Esta proposta não aprova a arquitetura operacional por si só.

## Decisions

Seleção técnica local detalhada em `feasibility.md`: reutilizar `IntegrationCipher.from_explicit_context`, com contexto e chave de laboratório exclusivos, referência UUID e expiração dentro do ciphertext. Materialização e instalação recusam execução fora de POSIX/diretório marcado de laboratório. O instalador só troca um link `current` para releases validados no mesmo destino fixo; callbacks estreitos de teste/reload/probe não recebem comandos ou caminhos externos. Configuração NPM candidata usa `advanced_config` somente no novo host, com caminhos fixos; sem registro LE nativo, sem include global, sem upload de chave. O loader systemd e o executor privilegiado real continuam fora desta prova e exigem validação operacional própria.

1. **Arquitetura proposta:** emissor dedicado obtém o token por referência a store cifrado do servidor; NPM não conhece o token. Avaliar um cliente ACME de origem oficial e versão fixa em laboratório isolado, registrando licença, dependências e compatibilidade. Não instalar automaticamente o plugin no NPM atual. O inventário comprova o problema atual, não a viabilidade da alternativa.
2. **Custódia:** preferir loader cifrado do servidor com materialização efêmera e permissões exclusivas do emissor. O padrão existente de credenciais do servidor é referência de projeto, não prova de que a materialização funcionará. Provar suporte, recuperação e separação de identidades com valores sintéticos; falha bloqueia a adoção sem fallback para arquivo ou banco em claro. Nenhuma chave/token real será solicitado nesta fase.
3. **Instalação:** interface estreita entre emissor e instalador, recebendo somente bundle validado em staging e referência fixa do destino. O instalador não recebe o token, não aceita caminhos/comandos livres e não concede socket/grupo Docker ao emissor. A integração exata com o NPM precisa ser provada na mesma versão/digest do inventário, sem gravar chave/token em tabelas comuns. Se o caminho suportado exigir isso ou intervenção ampla, rejeitar a implementação candidata e registrar a incompatibilidade.
4. **Renovação:** um único responsável pela renovação; impedir disputa entre renovador nativo NPM e emissor dedicado. Validar bundle antes da troca e manter referência saudável anterior. Testes cobrem repetição, expiração, falha de DNS/CA, falha do instalador e recuperação; não criar timer real nesta fase.
5. **Compatibilidade:** preservar certificados/rotas exatos de raiz e markina, além de projetos vizinhos. Certificado candidato cobre apenas `*.pickyourpic.com.br`. Nenhuma remoção de código do NPM ou refatoração geral está prevista. Reusar padrões existentes somente após comprovar consumidores e fronteiras de privilégio.

## Risks / Trade-offs

- [Emissor separado acrescenta operação] → exigir documentação, observabilidade sanitizada, dono da renovação e restauração ensaiada.
- [Integração NPM pode não satisfazer o contrato] → prova local obrigatória antes de selecionar comandos, caminhos e privilégios operacionais; rejeitar candidato incompatível, sem instalação manual improvisada.
- [Instalador privilegiado pode ampliar acesso] → destino/operação fixos, validação de entrada e nenhuma execução arbitrária ou credencial Docker exposta ao emissor.
- [Store/recuperação ainda não comprovados] → material sintético e gates verificáveis; não tratar criptografia nominal ou permissão isolada como prova de custódia.

## Migration Plan

Primeiro produzir matriz de viabilidade com documentação primária, depois protótipo local isolado e evidência de segurança/renovação/retorno. Submeter o mecanismo concreto e seu inventário à revisão humana. Só então elaborar a aplicação externa, com autorização específica, sem substituir a aprovação de release do SaaS. Esta change não habilita automaticamente tasks 3.3/3.4 do ingresso.
