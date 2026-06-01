# Daily Paper Assistant Template

An automated daily literature assistant template for researchers. It watches journal RSS feeds, enriches papers with Crossref, checks legal open-access PDF availability, uses the OpenAI API for bilingual summaries and structured extraction, and writes daily/weekly Markdown reports.

The repository is designed to be forked or used as a GitHub template. You customize the journals, keywords, scoring prompt, and report fields for your own research area.

## Features

- Python 3.13 compatible.
- Journal targets configured in `config/journals.yaml`.
- Research and exclusion keywords configured in `config/keywords.yaml`.
- RSS feed ingestion.
- Crossref metadata enrichment for DOI, abstract, authors, journal, publication date, license, and URL.
- SQLite storage in `data/papers.db`.
- Duplicate avoidance by DOI first and normalized title second.
- Keyword filtering and simple 0-5 relevance scoring.
- Chinese and English OpenAI summaries.
- Conservative open-access PDF discovery with Unpaywall/Crossref.
- PDF text extraction with `pypdf`, then OpenAI-assisted analysis from metadata plus PDF excerpts.
- Optional Obsidian vault export with frontmatter and wikilinks.
- Daily reports in `reports/daily/YYYY-MM-DD.md`.
- Weekly reports in `reports/weekly/YYYY-WW.md`.
- GitHub Actions schedule for daily runs and Monday weekly reports.
- Windows-compatible paths and commands.

## Who Is This For?

Use this template if you want a private or public GitHub repository that automatically:

- Tracks selected journals.
- Finds new papers in the latest active volume/issue.
- Filters papers for your research topic.
- Uses a small, capped number of OpenAI calls to analyze likely relevant papers.
- Produces Markdown reports that can be read in GitHub, Obsidian, or any notes app.

This repository currently includes an example configuration for XOS laboratory production from xylan/hemicellulose. Replace it with your own field-specific configuration before sharing or deploying.

## Use As A Template

1. Click **Use this template** or fork the repository.
2. Keep the repository private if it will contain generated reports or a SQLite database from your own reading workflow.
3. Edit:

```text
config/journals.yaml
config/keywords.yaml
config/settings.yaml
src/analyzers/summarizer.py
```

4. Add GitHub Actions secrets:

```text
OPENAI_API_KEY
CROSSREF_MAILTO
UNPAYWALL_EMAIL
OPENAI_MODEL
```

5. Run the workflow manually once from the **Actions** tab.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```text
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4.1-mini
CROSSREF_MAILTO=your.email@example.com
UNPAYWALL_EMAIL=your.email@example.com
OBSIDIAN_ENABLED=false
OBSIDIAN_VAULT_PATH=C:\Users\you\Documents\ObsidianVault
OBSIDIAN_REPORT_DIR=Literature/Daily Paper Assistant
```

`CROSSREF_MAILTO` and `UNPAYWALL_EMAIL` are optional but recommended for polite API usage. Use a newly rotated OpenAI key if one was ever pasted into chat or logs.

## Usage

Run the daily assistant:

```bash
python -m src.main --mode daily
```

Generate the weekly report:

```bash
python -m src.main --mode weekly
```

Run both:

```bash
python -m src.main --mode all
```

If `OPENAI_API_KEY` is not set, the pipeline still runs and writes placeholder summaries.

## Configuration

Edit `config/journals.yaml` to add or remove journals:

```yaml
journals:
  - name: Bioresource Technology
    publisher: Elsevier
    issn: "0960-8524"
    rss_url: https://rss.sciencedirect.com/publication/science/09608524
```

Edit `config/keywords.yaml` to tune relevance:

- `core_keywords`: terms that define your research target.
- `biomass_keywords` or equivalent domain group: material/source/context terms.
- `method_keywords`: experimental, computational, or analytical methods.
- `exclude_keywords`: terms that should suppress unrelated papers.

Edit `config/settings.yaml` to adjust thresholds and paths.

For low-budget testing, keep these values small:

```yaml
app:
  max_papers_per_run: 25
  max_openai_summaries_per_run: 2
```

`max_openai_summaries_per_run` caps paid OpenAI calls even if many relevant papers are found.

## Stored Fields

The SQLite database stores the core literature record:

```text
title, authors, journal, publication_date, doi, url, abstract, keywords,
matched_keywords, pdf_url, pdf_downloaded, open_access_status, summary_cn,
summary_en, relevance_score, reason_for_relevance, experimental_conditions,
data_worth_extracting, processed_time
```

The included XOS example extracts:

```text
biomass_type, pretreatment_method, acid_enzyme_type, temperature,
reaction_time, solid_liquid_ratio, pH, yield, XOS_DP_distribution,
monosaccharide_composition, HPLC_column, mobile_phase, flow_rate,
detector, separation_method
```

Relevance is scored from 0 to 5:

```text
0: unrelated
1: broadly related, for example biomass valorization
2: method-related, for example pretreatment / hydrolysis
3: directly related to hemicellulose extraction / XOS
4: highly relevant, including experimental conditions, yield, HPLC, or fraction data
5: directly reusable for experimental design or dataset construction
```

## GitHub Actions

Add these repository secrets:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` optional, defaults to `gpt-4.1-mini`
- `CROSSREF_MAILTO` optional but recommended
- `UNPAYWALL_EMAIL` optional but recommended

The workflow runs:

- Daily at 06:00 UTC.
- Weekly every Monday at 06:30 UTC.
- Manually via `workflow_dispatch`.

Reports and the SQLite database are committed back to the repository by the workflow.

Obsidian export is intended for local runs or a self-hosted runner, because GitHub-hosted runners cannot access your local Obsidian vault.

## Legal PDF Handling

The downloader uses open metadata only. It checks Unpaywall first, then Crossref PDF links. It downloads a PDF only when metadata indicates open access or an open license. It does not scrape publisher websites, bypass paywalls, or use institutional access.

## Example Configurations

The folder below contains a field-specific example:

```text
config/examples/xos-production/
```

To reuse it, copy its files into `config/`:

```bash
cp config/examples/xos-production/journals.yaml config/journals.yaml
cp config/examples/xos-production/keywords.yaml config/keywords.yaml
```

On Windows:

```cmd
copy config\examples\xos-production\journals.yaml config\journals.yaml
copy config\examples\xos-production\keywords.yaml config\keywords.yaml
```

## Publish Checklist

Before making a public repository or template:

- Rotate any API key that was ever pasted into chat, screenshots, or commits.
- Confirm `.env` is not tracked by Git.
- Confirm `.env.example` contains placeholders only.
- Decide whether to commit `data/papers.db` and generated reports. For a clean template, remove generated data first.
- Keep journal RSS URLs and keywords generic or clearly mark them as examples.

## Clean Template Reset

For a clean public template, remove generated runtime artifacts:

```bash
rm -f data/papers.db
rm -f reports/daily/*.md reports/weekly/*.md
rm -f logs/*.log
```

On Windows PowerShell:

```powershell
Remove-Item data\papers.db -ErrorAction SilentlyContinue
Remove-Item reports\daily\*.md,reports\weekly\*.md,logs\*.log -ErrorAction SilentlyContinue
```

## Obsidian

Set:

```text
OBSIDIAN_ENABLED=true
OBSIDIAN_VAULT_PATH=C:\Users\you\Documents\ObsidianVault
OBSIDIAN_REPORT_DIR=Literature/Daily Paper Assistant
```

Daily and weekly reports are copied into the vault with YAML frontmatter and a `[[Daily Paper Assistant]]` wikilink.

## Suggested Next Improvements

- Better PDF parsing: add GROBID table/section parsing and targeted extraction from Methods and Results.
- Email delivery: send daily/weekly Markdown reports through SMTP, SendGrid, or GitHub Actions email integrations.
- Notion export: sync report sections and paper records to a Notion database with DOI, score, tags, summaries, and experimental fields.
