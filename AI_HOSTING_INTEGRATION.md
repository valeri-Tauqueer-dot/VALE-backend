# VALE AI Model Hosting integration

The AI Model Hosting dashboard is the second tab inside `/storage/command-center`.
It does not store or execute model weights on Render.

## Configured model identities
- Vision AI: `MdTauqueer/Visionvale`
- Trading AI: `MdTauqueer/vale-trading-model`

## Hosting endpoint contract
Each model is assigned to a saved provider connection. The endpoint must be reachable from the VALE backend over HTTPS.

- `openai`: endpoint base URL must expose `POST /chat/completions`. The request includes the configured Hugging Face repository as `model`.
- `huggingface`: endpoint base URL accepts `POST` with the raw image bytes for Vision or `{"inputs": "...", "options": ...}` for Trading, using a Hugging Face-style inference response.

The endpoint API key is sent as a Bearer token. Provider management tokens and Hugging Face access tokens are encrypted at rest and are never returned by status APIs.

## Runtime lifecycle
Provider consoles remain the operator's control plane. Start/restart the runtime in the provider console when required, then use **Check runtime** in Storage Centre. VALE probes `/health`, `/v1/models`, and the endpoint root. Runtime state is reported from actual HTTP responses; it is not inferred from a saved credential.

## Chat routing
- Text chat uses the assigned external Trading AI when configured.
- Image chat uses the assigned external Vision AI (when `VALE_ENABLE_VISION=true`), then passes its evidence and the user's question to the assigned Trading AI.
- If no Trading AI provider is assigned, existing VALE core chat remains the fallback.
- If a configured hosted inference call fails, VALE returns HTTP 503 instead of silently claiming the hosted model answered.

## Deployment
Deploy the updated backend files together. Keep `SECRET_KEY` stable and at least 32 characters. Do not change the existing `DATABASE_URL` or storage-shelf configuration. The AI hosting registry creates its own three tables in the same primary database.
