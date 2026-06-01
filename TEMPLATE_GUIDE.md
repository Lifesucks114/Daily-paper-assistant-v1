# Template Guide

Use this repository as a starting point for a field-specific literature assistant.

## 1. Define The Research Scope

Edit `config/keywords.yaml`.

- Keep `core_keywords` narrow.
- Add broader context terms only if they improve recall.
- Add strong `exclude_keywords` for common false positives.

## 2. Choose Journals

Edit `config/journals.yaml`.

Each journal needs:

```yaml
- name: Journal Name
  publisher: Publisher
  issn: "0000-0000"
  rss_url: https://example.com/feed.xml
```

Prefer official journal RSS feeds. Do not scrape paywalled pages.

## 3. Tune Relevance

Edit `config/settings.yaml`.

Important controls:

```yaml
max_openai_summaries_per_run: 2
max_openai_screening_candidates: 3
min_relevance_score: 1.5
min_ai_relevance_score: 3.0
```

Start strict, then loosen only after checking false negatives.

## 4. Customize The OpenAI Prompt

Edit `src/analyzers/summarizer.py`.

Replace the domain-specific prompt with your own:

- What counts as relevant?
- What should score 0-5?
- Which experimental or analytical fields should be extracted?

## 5. Configure Delivery

GitHub Actions always writes reports into `reports/`.

Local runs can also write to Obsidian if `.env` contains:

```text
OBSIDIAN_ENABLED=true
OBSIDIAN_VAULT_PATH=...
```

## 6. Keep Secrets Safe

Never commit `.env`.

Use GitHub repository secrets for:

```text
OPENAI_API_KEY
CROSSREF_MAILTO
UNPAYWALL_EMAIL
OPENAI_MODEL
```
