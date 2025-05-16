# Monolito PromptOS – Deploy no Railway

## Instruções

1. **Crie um novo projeto no [Railway](https://railway.app)** e importe este repositório.

2. **Configure as variáveis de ambiente** no painel `Variables`:
   - `WEBHOOK_SECRET`: o mesmo token configurado no seu GitHub App
   - `GITHUB_TOKEN`: seu token GitHub para acesso à API do model `copilot-chat`
   - `LLM_TIMEOUT` e `LLM_RETRIES`: opcionais

3. **Configure o Webhook no GitHub App**:
   - URL: `https://<seu-projeto>.up.railway.app/webhook`
   - Secret: mesmo valor de `WEBHOOK_SECRET`
   - Marque os eventos desejados (issues, pull_request, push...)

4. **Deploy**:
   - Railway instalará `Flask`, `requests`, `dotenv` automaticamente
   - O app escutará na porta correta (`PORT`)

5. **Logs**:
   - Toda LogLine gerada será impressa no console do Railway
   - Se o diretório `loglines/` existir localmente, logs também serão salvos em `.json`

Pronto para uso institucional.
