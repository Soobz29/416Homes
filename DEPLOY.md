# Deployment Guide: White-Label AI Agent

Follow these steps to deploy a new AI real estate agent for a client in under 20 minutes.

## 1. Preparation
- Copy the project folder and rename it to the client's name or brokerage.
- Ensure you have the client's API keys (Telegram, ElevenLabs, Gemini, Resend).

## 2. Interactive Setup
Run the onboarding script:
```bash
python onboard.py
```
This will:
- Ask for branding details (Brokerage, Agent Name, Regions).
- Ask for API credentials.
- Automatically generate `.env` and `agent_config.json`.

## 3. Launch
Start the agent and API:
```bash
python demo_api.py
```

## 4. Final Handover
- Send the client their Telegram bot link.
- Provide the report URL: `http://[your-ip]:8000/report` (replace with production IP/domain).
- **Cost**: ~$20/month base + usage.
- **Retainer**: $3,000 setup + $300/month.
