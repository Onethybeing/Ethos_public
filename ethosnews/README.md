# PNC Onboarding Prototype

Converts your natural-language news preferences into a structured **Personal News Constitution** using an LLM.

## Run

```bash
python3 ethosnews/pnc_onboarding/pnc_onboarding.py --groq_api_key YOUR_KEY
```

## What it does

1. Asks you to describe your ideal news diet.
2. Sends it to Groq (Llama 3.3) to extract a structured profile.
3. Validates the output and shows your constitution.
4. Saves to `mock_db_pnc.json` on confirmation.

> Works without an API key too — just omit `--groq_api_key` and it uses a mock fallback.
