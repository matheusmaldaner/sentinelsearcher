You can install this package with `uv add sentinelsearcher`

Copy `.env-example` and rename it to `.env` and fill in your API key.

Populate the `sentinel.config.yaml` with the path to the file you want updated as well as the specific schema you want the LLM to follow.

For the GitHub automatic pushes, you can set up your secrets either by navigating to "GitHub Actions -> Secrets" or programatically by executing:

```bash
gh secret set OPENAI_API_KEY --body "$(grep OPENAI_API_KEY .env | cut -d '=' -f2-)"
gh secret set ANTHROPIC_API_KEY --body "$(grep ANTHROPIC_API_KEY .env | cut -d '=' -f2-)"
```

Ensure you have the variables above defined in your `.env` file

If you do not have `gh` installed, you can get it with:

```bash
sudo apt  install gh  # version 2.45.0-1ubuntu0.3
```

You must then authenticate yourself by either:
1. gh auth login
2. setting `GH_TOKEN="yourtoken"` in `.env` which can be done here https://github.com/settings/tokens