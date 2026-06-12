# Ingestão

## MediaWiki API

O client usa `https://deepwoken.fandom.com/api.php` com `User-Agent` configurável. As operações principais são:

- `list_all_pages`: usa `action=query&list=allpages`.
- `get_page_html`: usa `action=parse&prop=text`.
- `get_page_info`: usa `action=query&prop=info|categories`.
- `list_categories`: usa `action=query&list=allcategories`.
- `list_category_members`: usa `action=query&list=categorymembers`.

## Paginação e rate limit

O client respeita os campos `continue` da API e aplica atraso configurado por `CRAWLER_DELAY_SECONDS`. Requisições têm retry com backoff exponencial e timeout configurável.

## Limpeza

O cleaner remove scripts, estilos, navegação, anúncios, TOC e referências. Tabelas e infoboxes são preservadas como texto porque a wiki de jogo costuma armazenar requisitos e números importantes nesses blocos.

## Chunking

Chunks seguem headings e parágrafos. Cada chunk preserva:

```text
Page: <title>
Section: <heading>

<conteúdo>
```

O alvo é cerca de 700 tokens, limite de 900 tokens e overlap de 100 tokens.

## Reprocessamento

O hash é calculado sobre `clean_text`. Se o hash não mudou, a página não é reprocessada. Se mudou, os chunks antigos são removidos e os novos chunks recebem embeddings antes de serem salvos.
