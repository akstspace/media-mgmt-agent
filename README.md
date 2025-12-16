# 🎬 Media Manager AI

> **Demo application showcasing [acton-agent](https://github.com/akstspace/acton-agent)** - A practical example of building AI agents with tool use capabilities.

An AI-powered assistant for managing your Radarr and Sonarr media servers through natural language. Built with [acton-agent](https://github.com/akstspace/acton-agent) and Streamlit.

## Features

- 🤖 **Natural Language Control** - Manage your media libraries through conversational AI
- 🎥 **Radarr Integration** - Search, add, and monitor movies
- 📺 **Sonarr Integration** - Manage TV series and episodes
- 🔐 **Secure Authentication** - Login system with encrypted credential storage
- 🌐 **Web Interface** - Clean, modern Streamlit UI
- 🐳 **Docker Support** - Easy deployment with Docker Compose

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the app:**
   ```bash
   streamlit run media_ui.py
   ```

## Docker Deployment

```bash
docker-compose up -d
```

Access at `http://localhost:8501`

## Usage Examples

- "Add the movie Inception to my library"
- "What movies are downloading right now?"
- "Show me upcoming TV episodes this week"
- "Check my Radarr disk space"

## Built With

- [acton-agent](https://github.com/actonlabs/acton-agent) - AI agent framework
- [Streamlit](https://streamlit.io) - Web interface
- [OpenRouter](https://openrouter.ai) / [OpenAI](https://openai.com) - LLM providers
