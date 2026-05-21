# CI Setup Guide

## What needs to be done once before the workflow runs

---

### 1. Add the Google Sheets secret

The workflow writes `gsheet_key.json` from a GitHub secret at runtime.
The credentials file is **never committed to the repo**.

Steps:
1. Open your `config/credentials/gsheet_key.json` locally
2. Copy the entire file contents
3. Go to GitHub repo → **Settings → Secrets and variables → Actions**
4. Click **New repository secret**
5. Name: `GSHEET_KEY_JSON`
6. Value: paste the entire JSON content
7. Save

The workflow step that uses it:
```yaml
- name: Write GSheet credentials
  run: |
    mkdir -p config/credentials
    echo '${{ secrets.GSHEET_KEY_JSON }}' > config/credentials/gsheet_key.json
```

---

### 2. Verify `.gitignore` blocks credentials and data

Make sure these lines exist in `.gitignore`:

```
# Credentials — never commit
config/credentials/
config/.env

# Data — rebuilt from artifacts
data/prod/
data/dev/

# Keep folder structure
!data/prod/.gitkeep
!data/dev/.gitkeep
!data/prod/raw/.gitkeep
!data/dev/raw/.gitkeep
```

Create the `.gitkeep` files so the empty folders are tracked:
```bash
mkdir -p data/prod/raw data/dev/raw
touch data/prod/.gitkeep data/prod/raw/.gitkeep
touch data/dev/.gitkeep data/dev/raw/.gitkeep
git add data/
```

---

### 3. Branch flow for testing CI

```bash
git checkout dev
git checkout -b feature/ci

# add .github/workflows/pipeline.yml
git add .github/workflows/pipeline.yml
git commit -m "ci: add daily pipeline workflow"
git push origin feature/ci

# → go to GitHub Actions tab
# → watch the run triggered by the push
# → iterate until green
# → PR: feature/ci → dev
# → PR: dev → main
```

---

### 4. Verify the run worked

After a successful run check:
- **Actions tab** → scrape artifact appears with JSON files inside
- **Google Sheets** → new row appended for today's date
- **Actions logs** → Step 5 export shows "Successfully appended N rows"

---

### 5. Rebuild full local history from artifacts

If you need to rebuild DuckDB locally from all CI runs:

```bash
# Install GitHub CLI if not already
# https://cli.github.com

# List all scrape artifacts
gh run list --workflow=pipeline.yml

# Download all artifacts into raw folder
gh run download --pattern "scrape-*" -D data/prod/raw/

# Rebuild DuckDB
APP_ENV=prod uv run python src/load_to_db.py --all
cd dbt_project && uv run dbt run --profiles-dir .
```

---

## Environment variables summary

| Variable | Where set | Value |
|----------|-----------|-------|
| `APP_ENV` | workflow `env:` block | `prod` |
| `APP_ENV` | pytest step override | `dev` |
| `GSHEET_KEY_JSON` | GitHub Secrets | full JSON content of `gsheet_key.json` |