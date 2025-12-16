"""
Media Manager - Streamlit UI with Authentication

A modern, secure web interface for managing your Radarr and Sonarr instances with AI.
Features login system and encrypted credential storage.
"""

import os
import sys
from typing import Optional

import streamlit as st

from media_agent import MediaAgent
from db_manager import DatabaseManager


# Page configuration
st.set_page_config(
    page_title="Media Manager AI Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_session_state():
    """Initialize session state variables."""
    if 'db' not in st.session_state:
        # Use /data directory for Docker, current directory otherwise
        data_dir = os.getenv('DATA_DIR', '/data' if os.path.exists('/data') else '.')
        st.session_state.db = DatabaseManager(data_dir=data_dir)
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'configured_services' not in st.session_state:
        st.session_state.configured_services = []
    if 'page' not in st.session_state:
        st.session_state.page = 'chat'
    if 'auto_init_attempted' not in st.session_state:
        st.session_state.auto_init_attempted = False


def auto_initialize_agent():
    """Automatically initialize agent if credentials are configured and agent is not yet initialized."""
    # Skip if already attempted or agent already exists
    if st.session_state.auto_init_attempted or st.session_state.agent:
        return
    
    # Skip if no user logged in
    if not st.session_state.user_id:
        return
    
    # Mark as attempted to avoid repeated initialization
    st.session_state.auto_init_attempted = True
    
    try:
        # Load credentials
        all_creds = st.session_state.db.get_all_credentials(st.session_state.user_id)
        radarr_creds = all_creds.get('radarr', {})
        sonarr_creds = all_creds.get('sonarr', {})
        openrouter_creds = all_creds.get('openrouter', {})
        openai_creds = all_creds.get('openai', {})
        
        # Check if at least one service is configured
        has_radarr = radarr_creds.get('url') and radarr_creds.get('api_key')
        has_sonarr = sonarr_creds.get('url') and sonarr_creds.get('api_key')
        
        if not (has_radarr or has_sonarr):
            # No services configured - skip auto-initialization
            return
        
        # Get AI provider settings
        llm_provider = st.session_state.db.get_setting(st.session_state.user_id, 'llm_provider') or 'openrouter'
        llm_model = st.session_state.db.get_setting(st.session_state.user_id, 'llm_model') or ''
        
        # Get API key based on provider
        if llm_provider == 'openrouter':
            llm_api_key = openrouter_creds.get('api_key') or os.getenv('OPENROUTER_API_KEY')
        else:
            llm_api_key = openai_creds.get('api_key') or os.getenv('OPENAI_API_KEY')
        
        if not llm_api_key:
            # No AI API key available - skip auto-initialization
            return
        
        # Initialize agent
        agent = MediaAgent(
            radarr_url=radarr_creds.get('url') if has_radarr else None,
            radarr_api_key=radarr_creds.get('api_key') if has_radarr else None,
            sonarr_url=sonarr_creds.get('url') if has_sonarr else None,
            sonarr_api_key=sonarr_creds.get('api_key') if has_sonarr else None,
            llm_provider=llm_provider,
            api_key=llm_api_key,
            model=llm_model if llm_model else None
        )
        st.session_state.agent = agent
        
        # Track configured services
        services = []
        if has_radarr:
            services.append("Radarr")
        if has_sonarr:
            services.append("Sonarr")
        st.session_state.configured_services = services
        
        # Show success message in sidebar (will be visible on next render)
        st.toast(f"✅ Auto-initialized with {', '.join(services)}", icon="🤖")
        
    except Exception as e:
        # Silent fail - user can manually initialize if needed
        print(f"Auto-initialization skipped: {e}")


def login_page():
    """Display login/signup page."""
    st.title("🎬 Media Manager AI")
    
    # Check if any users exist
    has_users = st.session_state.db.has_any_users()
    
    if not has_users:
        # No users exist - show registration page
        st.markdown("### Create your account to get started")
        
        with st.form("signup_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit_signup = st.form_submit_button("Create Account", use_container_width=True)
            
            if submit_signup:
                if not new_username or not new_password:
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    if st.session_state.db.create_user(new_username, new_password):
                        st.success("✓ Account created! Please login.")
                        # Log in the newly created user automatically
                        user_id = st.session_state.db.verify_user(new_username, new_password)
                        if user_id:
                            st.session_state.user_id = user_id
                            st.session_state.username = new_username
                            # Auto-initialize agent if credentials exist
                            auto_initialize_agent()
                        st.rerun()
                    else:
                        st.error("Failed to create account")
    else:
        # User exists - show login page only
        st.markdown("### Welcome! Please login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    user_id = st.session_state.db.verify_user(username, password)
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.success(f"✓ Welcome back, {username}!")
                        # Auto-initialize agent if credentials exist
                        auto_initialize_agent()
                        st.rerun()
                    else:
                        st.error("Invalid username or password")


def configuration_page():
    """Display configuration page for managing credentials."""
    st.title("⚙️ Configuration")
    st.markdown(f"**User:** {st.session_state.username}")
    
    # Load existing credentials
    all_creds = st.session_state.db.get_all_credentials(st.session_state.user_id)
    radarr_creds = all_creds.get('radarr', {})
    sonarr_creds = all_creds.get('sonarr', {})
    openrouter_creds = all_creds.get('openrouter', {})
    openai_creds = all_creds.get('openai', {})
    
    # Get settings
    llm_provider = st.session_state.db.get_setting(st.session_state.user_id, 'llm_provider') or 'openrouter'
    llm_model = st.session_state.db.get_setting(st.session_state.user_id, 'llm_model') or ''
    
    tab1, tab2, tab3 = st.tabs(["🎬 Radarr", "📺 Sonarr", "🤖 AI Settings"])
    
    with tab1:
        st.markdown("### Radarr (Movies) Configuration")
        with st.form("radarr_form"):
            radarr_url = st.text_input(
                "Radarr URL",
                value=radarr_creds.get('url', ''),
                placeholder="http://localhost:7878",
                help="Your Radarr instance URL"
            )
            radarr_api_key = st.text_input(
                "Radarr API Key",
                value=radarr_creds.get('api_key', ''),
                type="password",
                help="API key from Radarr Settings → General"
            )
            col1, col2 = st.columns(2)
            with col1:
                save_radarr = st.form_submit_button("💾 Save Radarr", use_container_width=True)
            with col2:
                delete_radarr = st.form_submit_button("🗑️ Delete Radarr", use_container_width=True)
            
            if save_radarr:
                if radarr_url and radarr_api_key:
                    st.session_state.db.save_credentials(
                        st.session_state.user_id,
                        'radarr',
                        url=radarr_url,
                        api_key=radarr_api_key
                    )
                    st.success("✓ Radarr credentials saved!")
                    st.rerun()
                else:
                    st.error("Please enter both URL and API key")
            
            if delete_radarr:
                st.session_state.db.delete_credentials(st.session_state.user_id, 'radarr')
                st.success("✓ Radarr credentials deleted")
                st.rerun()
    
    with tab2:
        st.markdown("### Sonarr (TV Series) Configuration")
        with st.form("sonarr_form"):
            sonarr_url = st.text_input(
                "Sonarr URL",
                value=sonarr_creds.get('url', ''),
                placeholder="http://localhost:8989",
                help="Your Sonarr instance URL"
            )
            sonarr_api_key = st.text_input(
                "Sonarr API Key",
                value=sonarr_creds.get('api_key', ''),
                type="password",
                help="API key from Sonarr Settings → General"
            )
            col1, col2 = st.columns(2)
            with col1:
                save_sonarr = st.form_submit_button("💾 Save Sonarr", use_container_width=True)
            with col2:
                delete_sonarr = st.form_submit_button("🗑️ Delete Sonarr", use_container_width=True)
            
            if save_sonarr:
                if sonarr_url and sonarr_api_key:
                    st.session_state.db.save_credentials(
                        st.session_state.user_id,
                        'sonarr',
                        url=sonarr_url,
                        api_key=sonarr_api_key
                    )
                    st.success("✓ Sonarr credentials saved!")
                    st.rerun()
                else:
                    st.error("Please enter both URL and API key")
            
            if delete_sonarr:
                st.session_state.db.delete_credentials(st.session_state.user_id, 'sonarr')
                st.success("✓ Sonarr credentials deleted")
                st.rerun()
    
    with tab3:
        st.markdown("### AI Provider Configuration")
        
        with st.form("ai_settings_form"):
            selected_provider = st.selectbox(
                "LLM Provider",
                options=["openrouter", "openai"],
                index=0 if llm_provider == "openrouter" else 1,
                help="Choose your AI provider"
            )
            
            st.markdown("---")
            
            # OpenRouter settings
            st.markdown("#### OpenRouter Settings")
            openrouter_api_key = st.text_input(
                "OpenRouter API Key",
                value=openrouter_creds.get('api_key', ''),
                type="password",
                help="Get your API key from openrouter.ai"
            )
            
            st.markdown("---")
            
            # OpenAI settings
            st.markdown("#### OpenAI Settings")
            openai_api_key = st.text_input(
                "OpenAI API Key",
                value=openai_creds.get('api_key', ''),
                type="password",
                help="Your OpenAI API key"
            )
            
            st.markdown("---")
            
            # Model selection
            model = st.text_input(
                "Model (optional)",
                value=llm_model,
                placeholder="anthropic/claude-3.5-sonnet (OpenRouter) or gpt-4o-mini (OpenAI)",
                help="Leave empty to use default model"
            )
            
            save_ai = st.form_submit_button("💾 Save AI Settings", use_container_width=True)
            
            if save_ai:
                # Save provider and model
                st.session_state.db.save_setting(st.session_state.user_id, 'llm_provider', selected_provider)
                st.session_state.db.save_setting(st.session_state.user_id, 'llm_model', model)
                
                # Save OpenRouter credentials if provided
                if openrouter_api_key:
                    st.session_state.db.save_credentials(
                        st.session_state.user_id,
                        'openrouter',
                        api_key=openrouter_api_key
                    )
                
                # Save OpenAI credentials if provided
                if openai_api_key:
                    st.session_state.db.save_credentials(
                        st.session_state.user_id,
                        'openai',
                        api_key=openai_api_key
                    )
                
                st.success("✓ AI settings saved!")
                st.rerun()
    
    st.markdown("---")
    
    # Initialize Agent button
    if st.button("🚀 Initialize Agent", use_container_width=True, type="primary"):
        # Reload credentials
        all_creds = st.session_state.db.get_all_credentials(st.session_state.user_id)
        radarr_creds = all_creds.get('radarr', {})
        sonarr_creds = all_creds.get('sonarr', {})
        
        # Get LLM provider and credentials
        llm_provider = st.session_state.db.get_setting(st.session_state.user_id, 'llm_provider') or 'openrouter'
        llm_model = st.session_state.db.get_setting(st.session_state.user_id, 'llm_model') or None
        
        llm_creds = all_creds.get(llm_provider, {})
        llm_api_key = llm_creds.get('api_key')
        
        # Validate
        if not radarr_creds.get('url') and not sonarr_creds.get('url'):
            st.error("❌ Please configure at least one service (Radarr or Sonarr)")
            return
        
        if not llm_api_key:
            st.error(f"❌ Please configure {llm_provider.upper()} API key")
            return
        
        # Create agent
        try:
            with st.spinner("🚀 Initializing AI Agent..."):
                agent = MediaAgent(
                    radarr_url=radarr_creds.get('url'),
                    radarr_api_key=radarr_creds.get('api_key'),
                    sonarr_url=sonarr_creds.get('url'),
                    sonarr_api_key=sonarr_creds.get('api_key'),
                    llm_provider=llm_provider,
                    api_key=llm_api_key,
                    model=llm_model if llm_model else None
                )
                st.session_state.agent = agent
                
                # Track configured services
                services = []
                if radarr_creds.get('url'):
                    services.append("Radarr")
                if sonarr_creds.get('url'):
                    services.append("Sonarr")
                st.session_state.configured_services = services
                
                st.success(f"✅ Agent initialized with {', '.join(services)}")
                st.session_state.page = 'chat'
                st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to initialize agent: {e}")


def chat_interface():
    """Display the chat interface."""
    agent = st.session_state.agent
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Show reasoning steps if available
            if message.get("reasoning"):
                reasoning = message["reasoning"]
                with st.expander("🔍 View Agent Reasoning", expanded=False):
                    # Show plan if available
                    if reasoning.get("plan"):
                        st.markdown("### 🧠 Plan")
                        plan_data = reasoning["plan"]
                        if isinstance(plan_data, list):
                            plan_text = "\n".join([f"{i}. {step}" for i, step in enumerate(plan_data, 1)])
                            st.info(plan_text)
                        else:
                            st.info(plan_data)
                        st.markdown("---")
                    
                    # Show each reasoning step
                    for idx, step in enumerate(reasoning.get("steps", []), 1):
                        st.markdown(f"### 🔧 Step {idx}")
                        
                        # Thought
                        st.markdown("**💭 Thought:**")
                        st.write(step["thought"])
                        
                        # Tool calls
                        if step.get("tool_calls"):
                            st.markdown("**🛠️ Tool Calls:**")
                            for tool_call in step["tool_calls"]:
                                with st.container():
                                    col1, col2 = st.columns([1, 3])
                                    with col1:
                                        st.code(tool_call.tool_name, language=None)
                                    with col2:
                                        if tool_call.parameters:
                                            import json
                                            params_str = json.dumps(tool_call.parameters, indent=2)
                                            st.code(params_str, language="json")
                                        else:
                                            st.write("_(no parameters)_")
                        
                        # Tool results
                        if step.get("results"):
                            st.markdown("**📊 Results:**")
                            for result in step["results"]:
                                if result.error:
                                    st.error(f"❌ **{result.tool_name}**: {result.error}")
                                else:
                                    with st.success(f"✅ **{result.tool_name}**"):
                                        if len(result.result) > 500:
                                            st.text(result.result[:500] + "...")
                                            with st.expander("Show full result"):
                                                st.code(result.result, language="json")
                                        else:
                                            st.code(result.result, language="json")
                        
                        if idx < len(reasoning.get("steps", [])):
                            st.markdown("---")
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about your media..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Get assistant response with streaming
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            status_container = st.container()
            
            plan_info = None
            reasoning_steps = []
            final_response = ""
            
            try:
                for event in agent.agent.run_stream(prompt):
                    if event.type == "agent_plan":
                        plan_info = event.plan.plan
                        if isinstance(plan_info, list):
                            plan_display = "\n".join([f"{i}. {step}" for i, step in enumerate(plan_info, 1)])
                        else:
                            plan_display = str(plan_info)
                        with status_container:
                            st.info(f"🧠 **Planning:**\n{plan_display}")
                    
                    elif event.type == "agent_step":
                        step = event.step
                        step_info = {
                            "thought": step.thought,
                            "tool_calls": step.tool_calls,
                        }
                        reasoning_steps.append(step_info)
                        
                        with status_container:
                            st.info(f"🔧 **Step {len(reasoning_steps)}:** {step.thought}")
                            
                            if step.tool_calls:
                                tool_names = ", ".join([tc.tool_name for tc in step.tool_calls])
                                with st.spinner(f"⚙️ Executing: {tool_names}"):
                                    st.write("")
                    
                    elif event.type == "tool_results":
                        if reasoning_steps:
                            reasoning_steps[-1]["results"] = event.results
                        with status_container:
                            st.success("✅ **Tools executed**")
                    
                    elif event.type == "final_response":
                        final_response = event.response.final_answer
                        status_container.empty()
                        response_placeholder.markdown(final_response)
                        break
                
                # Store reasoning data
                reasoning_data = {}
                if plan_info:
                    reasoning_data["plan"] = plan_info
                if reasoning_steps:
                    reasoning_data["steps"] = reasoning_steps
                
                message_data = {"role": "assistant", "content": final_response}
                if reasoning_data:
                    message_data["reasoning"] = reasoning_data
                st.session_state.messages.append(message_data)
                
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                response_placeholder.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        st.rerun()


def sidebar():
    """Display sidebar navigation."""
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        
        st.markdown("---")
        
        # Navigation
        st.markdown("### 📍 Navigation")
        if st.button("💬 Chat", use_container_width=True, disabled=(st.session_state.page == 'chat')):
            st.session_state.page = 'chat'
            st.rerun()
        
        if st.button("⚙️ Settings", use_container_width=True, disabled=(st.session_state.page == 'settings')):
            st.session_state.page = 'settings'
            st.rerun()
        
        st.markdown("---")
        
        # Agent status
        st.markdown("### 📡 Agent Status")
        if st.session_state.agent:
            st.success("🟢 Connected")
            if st.session_state.configured_services:
                st.info(f"**Services:** {', '.join(st.session_state.configured_services)}")
        else:
            st.warning("🟡 Not Initialized")
            st.info("Go to Settings to configure")
        
        # Clear chat
        if st.session_state.messages and st.session_state.page == 'chat':
            st.markdown("---")
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        # Logout
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.agent = None
            st.session_state.messages = []
            st.session_state.configured_services = []
            st.session_state.page = 'chat'
            st.session_state.auto_init_attempted = False  # Reset auto-init flag on logout
            st.rerun()
        
        # Info
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        **Media Manager AI**
        
        Powered by OpenRouter
        
        **Features:**
        - 🎬 Radarr Integration
        - 📺 Sonarr Integration
        - 🔐 Encrypted Storage
        - 🤖 AI-Powered Chat
        """)


def main():
    """Main application."""
    initialize_session_state()
    
    # Check if user is logged in
    if not st.session_state.user_id:
        login_page()
        return
    
    # Auto-initialize agent on page load if not already done
    auto_initialize_agent()
    
    # Show sidebar
    sidebar()
    
    # Show appropriate page
    if st.session_state.page == 'settings':
        configuration_page()
    elif st.session_state.page == 'chat':
        st.title("🎬 Media Manager AI Assistant")
        
        if not st.session_state.agent:
            st.info("👋 Welcome! Go to **Settings** to configure your services and initialize the AI agent.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                ### 🎬 Radarr Features
                - 🔍 Search for movies
                - ➕ Add to library
                - 📅 Check releases
                - ⬇️ Monitor downloads
                - 📊 System stats
                """)
            
            with col2:
                st.markdown("""
                ### 📺 Sonarr Features
                - 🔍 Search TV shows
                - ➕ Add series
                - 📅 Episode air dates
                - ⬇️ Monitor downloads
                - 📊 System stats
                """)
            
            st.markdown("---")
            st.markdown("**Example queries:**")
            st.markdown("- *'Search for The Matrix'*")
            st.markdown("- *'What movies are releasing this week?'*")
            st.markdown("- *'Add Breaking Bad to my library'*")
            st.markdown("- *'Show me my download queue'*")
        else:
            chat_interface()


if __name__ == "__main__":
    main()
