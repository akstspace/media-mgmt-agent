"""
Media Manager - Streamlit UI with Authentication

A modern, secure web interface for managing your Radarr and Sonarr instances with AI.
Features login system and encrypted credential storage.
"""

import os
import sys
from typing import Optional
from datetime import datetime

import streamlit as st

from media_agent import MediaAgent
from db_manager import DatabaseManager
from acton_agent.agent import parse_streaming_events
from acton_agent.agent.models import (
    AgentPlanEvent,
    AgentStepEvent,
    AgentToolExecutionEvent,
    AgentToolResultsEvent,
    AgentFinalResponseEvent,
)


# Page configuration
st.set_page_config(
    page_title="Media Manager AI Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    /* Better chat message styling */
    .stChatMessage {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1f77b4;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #e0e0e0;
    }
    
    /* Tool execution cards */
    .tool-card {
        background-color: #f8f9fa;
        border-left: 4px solid #6c757d;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-radius: 0.3rem;
    }
    
    .tool-card.executing {
        border-left-color: #0d6efd;
        background-color: #e7f1ff;
    }
    
    .tool-card.success {
        border-left-color: #28a745;
        background-color: #d4edda;
    }
    
    .tool-card.failed {
        border-left-color: #dc3545;
        background-color: #f8d7da;
    }
    
    /* Plan and thought boxes */
    .info-box {
        background-color: #e7f3ff;
        border-left: 4px solid #2196F3;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.3rem;
    }
    
    /* Answer box */
    .answer-box {
        background-color: #f0f8f0;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        margin-top: 1rem;
        border-radius: 0.3rem;
        font-size: 1.05rem;
    }
    </style>
""", unsafe_allow_html=True)


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


def render_step_expander_static(step, step_num, expanded=False):
    """Render a single step in an expander for chat history."""
    # Determine step title
    step_type = step.get('type', 'unknown')
    if step_type == 'plan':
        title = f"Step {step_num}: 🗺️ Planning"
    elif step_type == 'execution':
        tool_count = len(step.get('tool_executions', {}))
        title = f"Step {step_num}: 🔧 Executed {tool_count} tool(s)"
    else:
        title = f"Step {step_num}"
    
    with st.expander(title, expanded=expanded):
        html_parts = []
        
        # Plan
        if step.get('plan'):
            html_parts.append(f"""
            <div class="section-header">🗺️ Plan</div>
            <div class="info-box">{step['plan']}</div>
            """)
        
        # Reasoning
        if step.get('thought'):
            html_parts.append(f"""
            <div class="section-header">💭 Reasoning</div>
            <div class="info-box">{step['thought']}</div>
            """)
        
        # Tools to execute
        if step.get('tools'):
            html_parts.append('<div class="section-header">🔧 Tools to Execute</div>')
            for tool in step['tools']:
                params_str = ", ".join([f"{k}={v}" for k, v in tool['params'].items()])
                html_parts.append(f'<div class="tool-card"><strong>{tool["name"]}</strong>({params_str})</div>')
        
        # Tool executions
        if step.get('tool_executions'):
            html_parts.append('<div class="section-header">⚙️ Execution Results</div>')
            for tool_id, exec_info in step['tool_executions'].items():
                status = exec_info['status']
                name = exec_info['name']
                
                if status == 'completed':
                    card_class = 'success'
                    icon = '✅'
                    result = exec_info.get('result', '')
                    content = f'{icon} <strong>{name}</strong>: {result}'
                elif status == 'failed':
                    card_class = 'failed'
                    icon = '❌'
                    error = exec_info.get('error', 'Unknown error')
                    content = f'{icon} <strong>{name}</strong>: {error}'
                else:
                    card_class = ''
                    icon = '⚙️'
                    content = f'{icon} <strong>{name}</strong>'
                
                html_parts.append(f'<div class="tool-card {card_class}">{content}</div>')
        
        if html_parts:
            st.markdown(''.join(html_parts), unsafe_allow_html=True)


def chat_interface():
    """Display the chat interface."""
    agent = st.session_state.agent
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
                if message.get("timestamp"):
                    st.caption(f"🕐 {message['timestamp']}")
            else:
                # Render assistant message with steps in expanders
                if message.get("steps"):
                    # Separate intermediate steps from final step
                    intermediate_steps = [s for s in message["steps"] if s.get('type') != 'final']
                    
                    # Render intermediate steps in expanders
                    for i, step in enumerate(intermediate_steps, 1):
                        render_step_expander_static(step, i, expanded=False)
                
                # Show final answer in chat message container
                st.markdown(message["content"])
                
                if message.get("timestamp"):
                    st.caption(f"🕐 {message['timestamp']}")
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about your media..."):
        # Add user message to history
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
            st.caption(f"🕐 {timestamp}")
        
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": timestamp
        })
        
        # Get assistant response with streaming
        with st.chat_message("assistant"):
            # Track current state - organized by steps
            steps = []  # List of step dictionaries
            current_step_id = None
            current_step = None
            
            # Main placeholder for updating content
            main_placeholder = st.empty()
            
            def render_current_state():
                """Render the current state of the agent's response with step expanders."""
                with main_placeholder.container():
                    # Build list of all steps including current
                    all_steps = steps + ([current_step] if current_step else [])
                    
                    # Separate final answer from intermediate steps
                    intermediate_steps = []
                    final_step = None
                    
                    for step in all_steps:
                        if step.get('type') == 'final':
                            final_step = step
                        else:
                            intermediate_steps.append(step)
                    
                    # Render intermediate steps in collapsed expanders
                    for i, step in enumerate(intermediate_steps, 1):
                        is_last_intermediate = (i == len(intermediate_steps) and not final_step)
                        render_step_expander(step, i, expanded=is_last_intermediate)
                    
                    # Render final answer outside expanders
                    if final_step and final_step.get('answer'):
                        st.markdown(final_step['answer'])
            
            def render_step_expander(step, step_num, expanded=True):
                """Render a single step in an expander."""
                # Determine step title
                step_type = step.get('type', 'unknown')
                if step_type == 'plan':
                    title = f"Step {step_num}: 🗺️ Planning"
                elif step_type == 'execution':
                    tool_count = len(step.get('tool_executions', {}))
                    completed = sum(1 for t in step.get('tool_executions', {}).values() if t['status'] in ['completed', 'failed'])
                    title = f"Step {step_num}: 🔧 Executing Tools ({completed}/{tool_count})"
                else:
                    title = f"Step {step_num}"
                
                with st.expander(title, expanded=expanded):
                    html_parts = []
                    
                    # Plan
                    if step.get('plan'):
                        html_parts.append(f"""
                        <div class="section-header">🗺️ Plan</div>
                        <div class="info-box">{step['plan']}</div>
                        """)
                    
                    # Reasoning
                    if step.get('thought'):
                        html_parts.append(f"""
                        <div class="section-header">💭 Reasoning</div>
                        <div class="info-box">{step['thought']}</div>
                        """)
                    
                    # Tools to execute
                    if step.get('tools'):
                        html_parts.append('<div class="section-header">🔧 Tools to Execute</div>')
                        for tool in step['tools']:
                            params_str = ", ".join([f"{k}={v}" for k, v in tool['params'].items()])
                            html_parts.append(f'<div class="tool-card"><strong>{tool["name"]}</strong>({params_str})</div>')
                    
                    # Tool executions
                    if step.get('tool_executions'):
                        html_parts.append('<div class="section-header">⚙️ Execution</div>')
                        for tool_id, exec_info in step['tool_executions'].items():
                            status = exec_info['status']
                            name = exec_info['name']
                            
                            if status == 'started':
                                card_class = 'executing'
                                icon = '⚙️'
                                content = f'{icon} Executing <strong>{name}</strong>...'
                            elif status == 'completed':
                                card_class = 'success'
                                icon = '✅'
                                result = exec_info.get('result', '')
                                content = f'{icon} <strong>{name}</strong>: {result}'
                            elif status == 'failed':
                                card_class = 'failed'
                                icon = '❌'
                                error = exec_info.get('error', 'Unknown error')
                                content = f'{icon} <strong>{name}</strong>: {error}'
                            else:
                                card_class = ''
                                content = f'{name}'
                            
                            html_parts.append(f'<div class="tool-card {card_class}">{content}</div>')
                    
                    if html_parts:
                        st.markdown(''.join(html_parts), unsafe_allow_html=True)
                    else:
                        st.info("🤔 Processing...")
            
            try:
                # Stream events from agent using new parse_streaming_events API
                for event in parse_streaming_events(agent.agent.run_stream(prompt)):
                    step_id = getattr(event, "step_id", None)
                    
                    # Initialize step if needed (for first event or new step)
                    if not current_step or (step_id and step_id != current_step_id):
                        # Save previous step if it exists
                        if current_step:
                            steps.append(current_step)
                        
                        # Start new step
                        current_step_id = step_id
                        current_step = {
                            'type': 'unknown',
                            'plan': '',
                            'thought': '',
                            'tools': [],
                            'tool_executions': {},
                            'answer': ''
                        }
                    
                    # Handle plan events
                    if isinstance(event, AgentPlanEvent):
                        current_step['type'] = 'plan'
                        current_step['plan'] = event.plan.plan
                        render_current_state()
                    
                    # Handle step events (tool thought)
                    elif isinstance(event, AgentStepEvent):
                        current_step['type'] = 'execution'
                        if event.step.tool_thought:
                            current_step['thought'] = event.step.tool_thought
                        
                        if event.step.tool_calls:
                            current_step['tools'] = []
                            for tc in event.step.tool_calls:
                                current_step['tools'].append({
                                    'name': tc.tool_name,
                                    'params': tc.parameters
                                })
                        
                        render_current_state()
                    
                    # Handle tool execution events
                    elif isinstance(event, AgentToolExecutionEvent):
                        if current_step['type'] != 'execution':
                            current_step['type'] = 'execution'
                        
                        # Track tool execution by tool_call_id
                        current_step['tool_executions'][event.tool_call_id] = {
                            'name': event.tool_name,
                            'status': event.status
                        }
                        
                        if event.status in ["completed", "failed"]:
                            if event.result:
                                if event.result.success:
                                    current_step['tool_executions'][event.tool_call_id]['result'] = event.result.result
                                else:
                                    current_step['tool_executions'][event.tool_call_id]['error'] = event.result.error
                        
                        render_current_state()
                    
                    # Handle final response events
                    elif isinstance(event, AgentFinalResponseEvent):
                        current_step['type'] = 'final'
                        current_step['answer'] = event.response.final_answer
                        render_current_state()
                
                # Save final response to history
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Add final step if exists
                if current_step:
                    steps.append(current_step)
                
                # Build final content for history
                final_answer = ""
                for step in steps:
                    if step.get('answer'):
                        final_answer = step['answer']
                        break
                
                if not final_answer:
                    final_answer = "⚠️ No final answer provided"
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_answer,
                    "timestamp": timestamp,
                    "steps": steps
                })
                
                # Show timestamp
                st.caption(f"🕐 {timestamp}")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                with st.expander("🔍 Error Details", expanded=True):
                    st.code(traceback.format_exc())


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
