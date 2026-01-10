# Git Repository Setup Guide

## Step 1: Initialize Git Repository

```bash
# Navigate to project root
cd /Users/abuaa/Projects/RegimeFlex

# Initialize git repository (if not already initialized)
git init

# Check git status
git status
```

## Step 2: Verify .gitignore

```bash
# Verify .gitignore is in place
cat .gitignore | head -20

# Check what files will be ignored
git status --ignored
```

## Step 3: Add All Files (Respecting .gitignore)

```bash
# Add all files (gitignore will automatically exclude sensitive files)
git add .

# Verify what will be committed
git status
```

## Step 4: Make Initial Commit

```bash
# Create initial commit
git commit -m "feat: initial release of RegimeFlex production core

- Complete systematic trading system for TQQQ/SQQQ
- Regime detection with bull/bear switching
- Institutional-grade execution safeguards
- Real broker integration (Alpaca Markets)
- Comprehensive risk management
- Production-ready with kill switch, run locks, and health monitoring
- Full documentation and audit trail"
```

## Step 5: Create GitHub Repository

1. **Go to GitHub**: https://github.com/new
2. **Repository name**: `regimeflex` (or your preferred name)
3. **Description**: "Automated TQQQ/SQQQ swing trading system with regime detection"
4. **Visibility**: Choose Private (recommended) or Public
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click **"Create repository"**

## Step 6: Link Local Repository to GitHub

```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/regimeflex.git

# Verify remote
git remote -v

# Push to GitHub
git branch -M main  # Rename branch to 'main' if needed
git push -u origin main
```

## Step 7: Verify Upload

1. Visit your GitHub repository: `https://github.com/YOUR_USERNAME/regimeflex`
2. Verify all files are present
3. Check that `.env` and sensitive files are NOT visible (they should be ignored)

## Security Checklist

Before pushing, verify:

- [ ] `.env` file is NOT in repository (check `git status`)
- [ ] `data/state/*.json` files are ignored
- [ ] `logs/` directory is ignored
- [ ] `*.log` files are ignored
- [ ] API keys are NOT in any committed files
- [ ] `.env.example` exists (template only, no real keys)

## Optional: Add GitHub Actions

Create `.github/workflows/ci.yml` for automated testing:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest
```

## Troubleshooting

### If you accidentally committed sensitive files:

```bash
# Remove from git (but keep local file)
git rm --cached .env

# Commit the removal
git commit -m "chore: remove sensitive .env file"

# Push the fix
git push
```

### If .gitignore isn't working:

```bash
# Remove cached files
git rm -r --cached .

# Re-add everything (respecting .gitignore)
git add .

# Commit
git commit -m "chore: update .gitignore"
```

## Next Steps

After initial push:

1. **Set repository description** on GitHub
2. **Add topics/tags**: `trading`, `algorithmic-trading`, `python`, `alpaca`, `systematic-trading`
3. **Enable branch protection** (Settings → Branches → Add rule for `main`)
4. **Set up GitHub Secrets** for CI/CD (if using GitHub Actions)
5. **Create releases** for version tags

## Git Best Practices

```bash
# Create meaningful commit messages
git commit -m "feat: add leverage decay adjustment to position sizing"
git commit -m "fix: prevent look-ahead bias in signal generation"
git commit -m "docs: update README with safety features"

# Use conventional commits format:
# feat: new feature
# fix: bug fix
# docs: documentation changes
# refactor: code refactoring
# test: adding tests
# chore: maintenance tasks
```

