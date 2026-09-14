## Purpose

Definir a identidade Pick-your-Pic em toda apresentação e comunicação do produto, preservando a continuidade de acesso e a identidade visual fornecida pelo proprietário.

## ADDED Requirements

### Requirement: Nome único de produto

As superfícies voltadas ao usuário SHALL identificar o produto como `Pick-your-Pic`, substituindo Markina Gallery e variantes da marca antiga em textos padrão, navegação, entrada, títulos de página, nomes acessíveis, manifesto do aplicativo, estado offline, documentação vigente e nomes amigáveis de exportação. O rebrand SHALL NOT duplicar desnecessariamente o nome ao lado da logotipo que já o contém.

#### Scenario: Admin e cliente
- **WHEN** o usuário acessa entrada, administração, biblioteca, galeria ou aplicativo nos temas claro e escuro
- **THEN** o produto usa o novo nome sem referências padrão à marca antiga, mantendo legibilidade e navegação responsiva

#### Scenario: Instalação
- **WHEN** o navegador consulta o manifesto e instala o aplicativo
- **THEN** o nome e o nome curto identificam Pick-your-Pic e os ícones permanecem os oficiais configurados

### Requirement: Arte oficial preservada

O sistema SHALL usar a logotipo, favicon e ícone enviados em Configurações sem redesenhar, recortar, distorcer ou inverter sua arte e tipografia. A imagem de referência contendo várias aplicações da marca SHALL NOT substituir automaticamente esses arquivos. Sem logo configurado, SHALL apresentar o nome novo como alternativa textual acessível.

#### Scenario: Logo com nome incorporado
- **WHEN** uma logotipo oficial está configurada
- **THEN** a interface a apresenta com proporção preservada e nome acessível Pick-your-Pic, sem transcrever sobre a arte nem inventar a fonte

### Requirement: Comunicações e preferências existentes

Novas mensagens padrão de OTP, recuperação/verificação de e-mail e demais comunicações do produto SHALL usar Pick-your-Pic. Novos defaults de marca-d'água SHALL seguir o novo nome. Textos personalizados, credenciais, nomes de clientes/galerias, mensagens já enviadas, registros de consentimento e fotografias processadas SHALL permanecer intactos; nenhuma substituição ampla em dados persistidos será feita.

#### Scenario: Nova comunicação padrão
- **WHEN** o sistema gera uma nova mensagem padrão de acesso ou recuperação
- **THEN** o texto identifica Pick-your-Pic e mantém o mesmo destino, token, prazo e proteção de segurança

#### Scenario: Preferência do fotógrafo
- **WHEN** existe mensagem ou marca-d'água personalizada salva
- **THEN** o rebrand não a sobrescreve nem dispara reprocessamento ou reenvio

### Requirement: Continuidade técnica e histórica

O rebrand SHALL preservar domínio, links, rotas, sessões, filas, identificadores internos, volumes, containers, repositório e chaves de configuração. A documentação atual SHALL diferenciar nome do produto e identificadores técnicos legados. Histórico de commits, migrations aplicadas, evidências datadas e changes arquivadas SHALL permanecer auditáveis.

#### Scenario: Retomada após atualização
- **WHEN** um usuário retorna por um link ou sessão existente após a publicação
- **THEN** mantém o mesmo acesso autorizado, agora identificado pela nova marca, sem necessidade de migração de conta
