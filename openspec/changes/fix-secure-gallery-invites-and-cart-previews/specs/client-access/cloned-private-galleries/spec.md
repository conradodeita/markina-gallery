# Spec Delta

## ADDED Requirements

### Requirement: Origem segura dos links de capacidade da galeria

Links de capacidade SHALL usar a origem pública confiável configurada, nunca host ou esquema da requisição. Em homologação e produção, somente uma origem HTTPS válida pode gerar token; origem ausente ou insegura SHALL ser recusada sem fallback. Desenvolvimento/teste local MAY usar HTTP para origem local válida.

#### Scenario: Convite servido atrás de proxy TLS

- **WHEN** o fotógrafo consulta ou emite um link de galeria ou convite individual por uma conexão interna HTTP atrás da entrada pública HTTPS
- **THEN** o endereço devolvido começa na origem HTTPS configurada e contém somente o token correspondente à capacidade emitida

#### Scenario: Cabeçalhos de requisição conflitantes

- **WHEN** uma requisição administrativa traz `Host` ou cabeçalhos de encaminhamento divergentes da origem pública configurada
- **THEN** o endereço com capacidade continua na origem pública configurada, sem aceitar o host ou o esquema informados pela requisição

#### Scenario: Origem insegura em ambiente implantado

- **WHEN** a origem pública está ausente, malformada ou usa HTTP em homologação ou produção
- **THEN** a operação não devolve link com token nem cria uma alternativa HTTP

#### Scenario: Desenvolvimento local e mudança de domínio

- **WHEN** o ambiente é local com origem HTTP local válida, ou a origem HTTPS configurada é trocada para um novo domínio público válido
- **THEN** links novos usam a origem correspondente sem alterar o token, o vínculo ou as regras de OTP
