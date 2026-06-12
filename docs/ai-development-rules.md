# Regras para IA desenvolvedora

1. Não alterar arquitetura sem atualizar docs/architecture.md.
2. Não colocar regra de negócio em routers.
3. Não chamar banco diretamente fora de repositories.
4. Não chamar API externa fora de clients.
5. Não criar nova dependência sem justificar no README.
6. Não remover testes existentes.
7. Não criar endpoints sem schemas de entrada/saída.
8. Não responder perguntas sem fontes no RAG.
9. Não gerar embeddings de HTML bruto.
10. Não misturar ingestão com pergunta do usuário.
11. Não hardcodar secrets.
12. Não ignorar migrations.
13. Não fazer scraping agressivo.
14. Não usar conhecimento externo na resposta da IA.
15. Se faltar informação, retornar que não foi encontrado na base.
