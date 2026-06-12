# Production Readiness

Checklist final antes de deploy/prod:

- variáveis de ambiente revisadas;
- rotas `/api/ingestion/*` protegidas por `X-Admin-Api-Key`;
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `EMBEDDING_MODEL` e dimensão do vetor compatíveis;
- migrations testadas;
- banco com pgvector habilitado;
- logs configurados;
- rate limit configurado;
- ingestão testada;
- backup planejado;
- endpoints revisados;
- prompt anti-alucinação validado;
- testes passando;
- pronto para deploy/prod.

A documentação termina aqui.
