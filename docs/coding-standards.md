# Padrões de Código

## Estrutura

Use módulos por domínio:

- `router.py` para HTTP.
- `schemas.py` para entrada e saída.
- `service.py` para casos de uso.
- `repository.py` para banco.
- clients externos em classes próprias.

## Regras

- Nenhuma regra de negócio em router.
- Nenhum acesso direto ao banco fora de repository.
- Nenhuma chamada externa fora de client.
- Configuração apenas via `Settings`.
- Não hardcodar secrets.
- Logs sem dados sensíveis.
- Funções pequenas e nomes explícitos.

## Testes

Adicione testes para comportamento novo ou correção de bug. Prefira testar comportamento público de funções, services ou endpoints. Use mocks apenas quando chamadas externas ou banco real forem o custo dominante.

## Qualidade

Antes de concluir mudanças:

```bash
python -m pytest -q
python -m ruff check .
python -m mypy app
```
