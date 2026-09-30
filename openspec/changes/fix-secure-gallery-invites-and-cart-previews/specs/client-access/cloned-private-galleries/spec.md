# Spec Delta

## ADDED Requirements

### Requirement: Origem segura dos links de capacidade da galeria

O sistema SHALL compor todo link de capacidade entregue ao fotógrafo, geral ou individual, usando a origem pública confiável configurada para o ambiente, independentemente do esquema e do host presentes na requisição administrativa. Em homologação e produção, essa origem SHALL usar HTTPS e SHALL ser válida antes de o sistema devolver um link com token. O sistema SHALL recusar origem ausente ou insegura nesses ambientes, sem substituir por HTTP ou por cabeçalhos encaminhados. Em desenvolvimento/teste local, HTTP para uma origem local SHALL continuar permitido.

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
