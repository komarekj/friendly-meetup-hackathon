# 🔌 Choosing your models

The project works with **any provider that offers an OpenAI-compatible API**. Set these in `.env`:

```bash
AGENT_BASE_URL=...   AGENT_API_KEY=...   AGENT_MODEL=...
```

| Provider | Base URL |
|---|---|
| Ollama (local, free) | `http://localhost:11434/v1` |
| OpenAI | `https://api.openai.com/v1` |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| Mistral | `https://api.mistral.ai/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| OpenRouter (many models, one key) | `https://openrouter.ai/api/v1` |

## Tips

- The **agent** model must support **tool calling**.
- **Local and slow?** On a Mac, Docker can't use the GPU. A hosted model, or Ollama's native app, will be much faster.
- **Never commit `.env`.** It's already in `.gitignore`.
