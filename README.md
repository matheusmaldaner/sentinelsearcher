


For the GitHub automatic pushes, you can set up your secrets either by navigating to "GitHub Actions -> Secrets" or programatically by executing:



```bash
gh secret set OPENAI_API_KEY --body "$(grep OPENAI_API_KEY .env | cut -d '=' -f2-)"
gh secret set ANTHROPIC_API_KEY --body "$(grep ANTHROPIC_API_KEY .env | cut -d '=' -f2-)"
```

Ensure you have the variables above defined in your `.env` file