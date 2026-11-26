# Spec Delta

## ADDED Requirements

### Requirement: Provider alternativo preserva o ciclo de arquivo frio

Um provider de armazenamento alternativo SHALL usar o mesmo catálogo, executor, fila, lease, manifesto, API e billing do arquivo frio existente. SHALL preservar isolamento por tenant e a verificação integral antes de promover arquivo ou recuperação. MUST NOT criar autorização, operação, cobrança, prazo ou retenção paralelos.

#### Scenario: Arquivo frio usa provider Rclone aprovado

- **WHEN** o executor recebe explicitamente um provider Rclone durável e autorizado para o tenant
- **THEN** a pasta e seus objetos seguem o ciclo, ownership, namespace e readback já definidos por `add-gallery-media-archive`
- **AND** os prazos, opções de reabertura, reserva/débito/liberação de créditos, isenção do proprietário, reconciliação e ausência de expurgo automático permanecem inalterados
- **AND** as durações selecionáveis de recuperação fria de 7/14/30 dias permanecem distintas da janela normal de reabertura de 30 dias após expiração

#### Scenario: Provider não foi aprovado ou configurado

- **WHEN** não há provider durável explicitamente configurado ou a configuração é inválida/ambígua
- **THEN** o worker não consulta nem reivindica operações e nenhum provider ou storage sintético é selecionado como fallback

### Requirement: Roteamento de objetos preserva a identidade do provider

O fluxo SHALL rotear leitura e exclusão ao provider que possui o objeto. Binding tenant→provider MUST NOT identificar sozinho objetos já catalogados. Antes de coexistência/troca, SHALL haver identidade e mapeamento aprovados para catálogo e manifestos v1, incluindo default legado. Modelo objeto/ciclo e migration/versionamento exigem decisão própria. Até essa decisão, o provider atual permanece inalterado.

#### Scenario: Transição proposta sem identidade compatível

- **WHEN** coexistência ou troca de provider é proposta enquanto catálogo e manifesto v1 identificam somente `remote_id`
- **THEN** a alteração não seleciona provider por suposição de binding tenant→provider nem ativa a transição até que a identidade/roteamento e o comportamento legado sejam aprovados e validados
