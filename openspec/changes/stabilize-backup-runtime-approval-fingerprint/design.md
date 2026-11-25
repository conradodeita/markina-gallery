# Design

## Context

Ver `proposal.md` para a motivação. Hoje o inventário produz uma fingerprint integral que inclui os contadores de uso e espaço disponível; o instalador exige igualdade integral no começo, enquanto `runtime_fingerprint` usada nas leituras seguintes não cobre todas as testemunhas de segurança do inventário. O fluxo protegido também vincula separadamente o SHA/CI, o pacote e a conexão SSH.

## Goals / Non-Goals

**Goals:**

- Definir uma fingerprint de aprovação versionada, estável para oscilações de capacidade e completa para identidade e estado relevantes à instalação.
- Revalidar a capacidade nos filesystems que receberão arquivos antes do staging e antes de trocar o runtime ativo.
- Preservar o contrato atual de CI exata, artefato verificado, lock comum, comandos fixos e aprovação separada do ambiente protegido.

**Non-Goals:**

- Alterar o contrato de fingerprints de outros workflows.
- Instalar o runtime, alterar configurações, vincular Drive, executar backup ou ativar serviço/timer.
- Relaxar identidade, saúde, schema, segurança de arquivos ou precondições de produção.

## Decisions

1. **Introduzir uma versão explícita do contrato de aprovação.** O inventário calcula uma impressão digital de identidade do host/runtime usando serialização canônica e um domínio/version tag. O workflow verifica o vínculo da conexão protegida separadamente entre preflight e operação; o SHA da `main`, CI verde e SHA-256 do pacote também permanecem entradas obrigatórias e comparadas separadamente, apresentadas junto da fingerprint. Isso preserva a arquitetura atual, em que a conexão SSH é verificada por binding do ambiente protegido, sem misturar sua identidade à impressão calculada no host. Inventários e aprovações antigas não são convertidos nem aceitos como versão nova.

2. **Incluir as testemunhas estáveis e omitir apenas contadores voláteis.** A impressão digital abrange host, containers da aplicação, agregado dos containers compartilhados, schema, bindings opacos das configurações protegidas, estado/metadados dos arquivos e diretórios de instalação e estados do serviço/timer. Para `/var/lib`, `/opt/pyp-backup-runtime` e `/etc/systemd/system`, inclui binding opaco da origem/mountpoint e capacidade total. Exclui somente bytes usados, bytes disponíveis e percentual de uso; esses números continuam visíveis no resumo sanitizado e entram nos gates de capacidade atuais. A impressão existente `runtime_fingerprint` não será reutilizada como aprovação, pois não inclui todas essas testemunhas.

3. **Calcular margem por destino a partir do artefato e do estado preservado.** Depois de verificar o hash do pacote, o instalador confere cada entrada dos wheels por leitura/CRC e calcula um bound para arquivos staged, expansão dos wheels, bytecode/metadados, wrappers de entry points, cópias do interpretador, transação e unidades systemd. A expansão descomprimida agregada dos wheels é limitada a 8 GiB para manter o cálculo executável; entradas maiores ou inválidas falham antes de qualquer escrita persistente. Arredonda os dados por bloco do filesystem e agrega destinos que compartilham o mesmo binding. Exige espaço disponível suficiente e uso projetado estritamente abaixo de 75% antes da primeira escrita persistente. Após o staging, mede novamente a margem restante antes da troca; se um limite ou leitura não puder ser comprovado, o fluxo falha fechado. O resumo continua mostrando bytes livres e percentual atuais por destino, sem expor caminhos nem IDs.

4. **Manter a aprovação composta, não derivar segurança da estabilidade.** A igualdade da fingerprint apenas confirma que a identidade aprovada permanece a mesma. Saúde, inércia das unidades, capacidade e demais precondições são verificadas novamente no preflight protegido e pelo instalador sob o lock. Uma precondição que falhe bloqueia a etapa mesmo se a fingerprint corresponder.

5. **Limitar a nova comparação ao `install` inerte do runtime de backup.** Não mudar o tratamento de fingerprints por outros workflows ou operações protegidas. A próxima execução continua exigindo review/merge autorizados, CI verde na `main` do SHA exato, inventário novo, aprovação humana da fingerprint e do pacote, e aprovação separada de `production`.

## Risks / Trade-offs

- [Uma testemunha de segurança ficar fora da normalização] → manter uma lista explícita de campos incluídos, testes de mutação por campo e uma regra de falha fechada para campo ausente, extra ou com tipo inválido.
- [A medição de espaço ficar desatualizada entre verificações] → medir sob o lock antes do staging e imediatamente antes da troca ativa; abortar se qualquer leitura deixar de ser válida ou suficiente.
- [A margem calculada ser menor que a expansão real] → derivar o limite de manifesto validado e tamanhos de arquivos/wheels; recusar instalação se o bound não puder ser comprovado; cobrir pacotes no maior tamanho de teste.
- [A impressão digital nova ser confundida com a antiga] → usar versão e rótulo distintos em workflow, saída e input; rejeitar explicitamente formatos/versões legadas.

## Migration Plan

1. Após revisão humana desta proposta, implementar a normalização e as verificações de capacidade em branch/PR, com testes sintéticos do inventário e do instalador.
2. Revisar a PR, obter autorização de merge e confirmar CI verde da `main` no SHA exato. Aprovações e fingerprints anteriores não são reutilizáveis.
3. Atualizar o forced command no host somente por seu workflow protegido, após nova fingerprint e aprovação próprias; depois, fazer inventário read-only novo que use o contrato v2 e apresentar fingerprint estável, capacidade atual, SHA/CI e pacote para revisão humana.
4. Só após autorização operacional específica e aprovação do ambiente `production`, uma operação `install` inerte poderá ser despachada; qualquer divergência de identidade, capacidade ou precondição aborta antes da troca ativa.

## Open Questions

Nenhuma. O método de cálculo do limite de espaço deve ser verificável a partir do manifesto do pacote e do estado preservado; se a implementação não puder demonstrá-lo, deve permanecer bloqueada e registrar a limitação em `tasks.md`.
