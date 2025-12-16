"""
Media Manager Agent - AI-powered media management assistant.

This module provides an intelligent agent that can help manage your Radarr and Sonarr instances
through natural language commands. Uses pre-configured RequestsTools for both services.
"""

import os
from typing import Optional, Literal
from acton_agent import Agent
from acton_agent.client import OpenAIClient, OpenRouterClient
from media_tools import configure_radarr, configure_sonarr, get_all_media_tools
from prompts import build_system_prompt


class MediaAgent:
    """
    AI-powered media management agent supporting Radarr and Sonarr.
    
    This agent can help you:
    - Search for and add movies (Radarr) and TV series (Sonarr)
    - Monitor download queues
    - Check calendars for upcoming releases
    - Manage your media libraries
    - View system status and disk space
    - Browse download history
    """
    
    def __init__(
        self,
        radarr_url: Optional[str] = None,
        radarr_api_key: Optional[str] = None,
        sonarr_url: Optional[str] = None,
        sonarr_api_key: Optional[str] = None,
        llm_provider: Literal["openai", "openrouter"] = "openrouter",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 10
    ):
        """
        Initialize the Media Manager Agent.
        
        Args:
            radarr_url: Radarr instance URL (e.g., 'http://localhost:7878')
            radarr_api_key: Radarr API key
            sonarr_url: Sonarr instance URL (e.g., 'http://localhost:8989')
            sonarr_api_key: Sonarr API key
            llm_provider: LLM provider to use - 'openai' or 'openrouter' (default: openrouter)
            api_key: API key for the LLM provider (defaults to OPENAI_API_KEY or OPENROUTER_API_KEY env var)
            model: Model to use (defaults: gpt-4o-mini for OpenAI, anthropic/claude-3.5-sonnet for OpenRouter)
            max_iterations: Maximum reasoning iterations (default: 10)
        """
        self.radarr_url = radarr_url
        self.radarr_api_key = radarr_api_key
        self.sonarr_url = sonarr_url
        self.sonarr_api_key = sonarr_api_key
        
        # Configure services
        services_configured = []
        if radarr_url and radarr_api_key:
            configure_radarr(radarr_url, radarr_api_key)
            services_configured.append("Radarr")
        
        if sonarr_url and sonarr_api_key:
            configure_sonarr(sonarr_url, sonarr_api_key)
            services_configured.append("Sonarr")
        
        if not services_configured:
            raise ValueError("At least one service (Radarr or Sonarr) must be configured")
        
        # Initialize LLM client based on provider
        if llm_provider == "openai":
            final_api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not final_api_key:
                raise ValueError("OpenAI API key must be provided or set in OPENAI_API_KEY environment variable")
            final_model = model or "gpt-4o-mini"
            self.llm_client = OpenAIClient(api_key=final_api_key, model=final_model)
            print(f"🤖 Using OpenAI with model: {final_model}")
        elif llm_provider == "openrouter":
            final_api_key = api_key or os.getenv("OPENROUTER_API_KEY")
            if not final_api_key:
                raise ValueError("OpenRouter API key must be provided or set in OPENROUTER_API_KEY environment variable")
            final_model = model or "anthropic/claude-3.5-sonnet"
            self.llm_client = OpenRouterClient(api_key=final_api_key, model=final_model)
            print(f"🤖 Using OpenRouter with model: {final_model}")
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}. Choose 'openai' or 'openrouter'")
        
        # Get all media tools
        print(f"🔧 Loading media management tools...")
        tools = get_all_media_tools()
        print(f"✓ Loaded {len(tools)} tools for {', '.join(services_configured)}")
        
        # Build comprehensive system prompt from prompts module
        system_prompt = build_system_prompt(services_configured)
        
        # Initialize the agent with streaming enabled
        self.agent = Agent(
            llm_client=self.llm_client,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
            stream=True  # Enable token-by-token streaming
        )
        
        # Register all tools
        for tool in tools:
            self.agent.register_tool(tool)
    
    def chat(self, message: str) -> str:
        """
        Send a message to the agent and get a response.
        
        Args:
            message: User's message/question
            
        Returns:
            Agent's response as a string
        """
        return self.agent.run(message)


# Convenience function for quick setup
def create_media_agent(
    radarr_url: Optional[str] = None,
    radarr_api_key: Optional[str] = None,
    sonarr_url: Optional[str] = None,
    sonarr_api_key: Optional[str] = None,
    llm_provider: Literal["openai", "openrouter"] = "openrouter",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> MediaAgent:
    """
    Create a media agent with the specified configuration.
    
    Args:
        radarr_url: Radarr instance URL
        radarr_api_key: Radarr API key
        sonarr_url: Sonarr instance URL
        sonarr_api_key: Sonarr API key
        llm_provider: LLM provider - 'openai' or 'openrouter' (default: openrouter)
        api_key: API key for the LLM provider
        model: Model to use (optional, uses provider defaults)
        
    Returns:
        Configured MediaAgent instance
    """
    return MediaAgent(
        radarr_url=radarr_url,
        radarr_api_key=radarr_api_key,
        sonarr_url=sonarr_url,
        sonarr_api_key=sonarr_api_key,
        llm_provider=llm_provider,
        api_key=api_key,
        model=model
    )
