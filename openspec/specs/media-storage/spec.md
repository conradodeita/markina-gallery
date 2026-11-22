# media-storage Specification

## Purpose

Receber, armazenar e disponibilizar mídias da plataforma com autorização e isolamento por tenant e controles operacionais apropriados.

## Requirements

### Requirement: Gate operacional comum para uploads SaaS

Toda rota de novo upload de JPEG e cada caminho que aceite fonte de mídia de fotógrafo SaaS SHALL consultar o mesmo gate autoritativo de onboarding, créditos, PIX e WhatsApp por tenant. A interface MUST NOT ser a única barreira; ações de navegação e leitura autorizadas permanecem disponíveis.

#### Scenario: Chamada direta sem configuração

- **WHEN** cliente chama uma rota de upload diretamente sem algum requisito
- **THEN** o backend recusa antes de criar fonte, reserva, job ou foto e retorna somente pendências do próprio tenant
