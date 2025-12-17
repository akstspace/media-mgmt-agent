"""
Media Manager UI with Streamlit.

Demo usecase for Acton Agent framework.
Run on local networks , not recommended for production use.
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from functools import lru_cache

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


# Constants
SERVICES = {
    'radarr': {'name': 'Radarr', 'icon': '🎬', 'placeholder': 'http://localhost:7878'},
    'sonarr': {'name': 'Sonarr', 'icon': '📺', 'placeholder': 'http://localhost:8989'}
}

LLM_PROVIDERS = ['openrouter', 'openai']

DEFAULT_PROVIDER = 'openrouter'


@lru_cache(maxsize=1)
def get_custom_css() -> str:
    """Return custom CSS for better styling."""
    return """
    <style>
    .stChatMessage {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1f77b4;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #e0e0e0;
    }
    
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
    
    .info-box {
        background-color: #e7f3ff;
        border-left: 4px solid #2196F3;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.3rem;
    }
    
    .answer-box {
        background-color: #f0f8f0;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        margin-top: 1rem;
        border-radius: 0.3rem;
        font-size: 1.05rem;
    }
    
    @keyframes spin {
        0% { content: '◐'; }
        25% { content: '◓'; }
        50% { content: '◑'; }
        75% { content: '◒'; }
        100% { content: '◐'; }
    }
    .spinner {
        display: inline-block;
        animation: spin 1s linear infinite;
    }
    </style>
    """


def init_page_config():
    """Initialize Streamlit page configuration."""
    st.set_page_config(
        page_title="Media Manager AI Assistant",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(get_custom_css(), unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    defaults = {
        'db': DatabaseManager(data_dir=os.getenv('DATA_DIR', '/data' if os.path.exists('/data') else '.')),
        'user_id': None,
        'username': None,
        'agent': None,
        'messages': [],
        'configured_services': [],
        'page': 'chat',
        'auto_init_attempted': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_data_dir() -> str:
    """Get appropriate data directory."""
    return os.getenv('DATA_DIR', '/data' if os.path.exists('/data') else '.')


def load_credentials() -> Dict[str, Dict[str, str]]:
    """Load all credentials for current user."""
    if not st.session_state.user_id:
        return {}
    return st.session_state.db.get_all_credentials(st.session_state.user_id)


def get_llm_config() -> Dict[str, Optional[str]]:
    """Get LLM provider configuration."""
    provider = st.session_state.db.get_setting(st.session_state.user_id, 'llm_provider') or DEFAULT_PROVIDER
    model = st.session_state.db.get_setting(st.session_state.user_id, 'llm_model') or ''
    return {'provider': provider, 'model': model}


def auto_initialize_agent():
    """Automatically initialize agent if credentials are configured."""
    if st.session_state.auto_init_attempted or st.session_state.agent or not st.session_state.user_id:
        return
    
    st.session_state.auto_init_attempted = True
    
    try:
        all_creds = load_credentials()
        radarr_creds = all_creds.get('radarr', {})
        sonarr_creds = all_creds.get('sonarr', {})
        
        has_radarr = radarr_creds.get('url') and radarr_creds.get('api_key')
        has_sonarr = sonarr_creds.get('url') and sonarr_creds.get('api_key')
        
        if not (has_radarr or has_sonarr):
            return
        
        llm_config = get_llm_config()
        llm_provider = llm_config['provider']
        llm_creds = all_creds.get(llm_provider, {})
        llm_api_key = llm_creds.get('api_key') or os.getenv(f'{llm_provider.upper()}_API_KEY')
        
        if not llm_api_key:
            return
        
        agent = MediaAgent(
            radarr_url=radarr_creds.get('url') if has_radarr else None,
            radarr_api_key=radarr_creds.get('api_key') if has_radarr else None,
            sonarr_url=sonarr_creds.get('url') if has_sonarr else None,
            sonarr_api_key=sonarr_creds.get('api_key') if has_sonarr else None,
            llm_provider=llm_provider,
            api_key=llm_api_key,
            model=llm_config['model'] if llm_config['model'] else None
        )
        st.session_state.agent = agent
        
        services = [SERVICES[s]['name'] for s in ['radarr', 'sonarr'] if (has_radarr if s == 'radarr' else has_sonarr)]
        st.session_state.configured_services = services
        st.toast(f"✅ Auto-initialized with {', '.join(services)}", icon="🤖")
        
    except Exception as e:
        print(f"Auto-initialization skipped: {e}")


def login_page():
    """Display login/signup page."""
    st.title("🎬 Media Manager AI")
    
    has_users = st.session_state.db.has_any_users()
    
    if not has_users:
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
                        user_id = st.session_state.db.verify_user(new_username, new_password)
                        if user_id:
                            st.session_state.user_id = user_id
                            st.session_state.username = new_username
                            auto_initialize_agent()
                        st.rerun()
                    else:
                        st.error("Failed to create account")
    else:
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
                        auto_initialize_agent()
                        st.rerun()
                    else:
                        st.error("Invalid username or password")


def render_service_config(service_key: str, all_creds: Dict):
    """Render configuration form for a service."""
    service = SERVICES[service_key]
    creds = all_creds.get(service_key, {})
    
    st.markdown(f"### {service['name']} Configuration")
    with st.form(f"{service_key}_form"):
        url = st.text_input(
            f"{service['name']} URL",
            value=creds.get('url', ''),
            placeholder=service['placeholder'],
            help=f"Your {service['name']} instance URL"
        )
        api_key = st.text_input(
            f"{service['name']} API Key",
            value=creds.get('api_key', ''),
            type="password",
            help=f"API key from {service['name']} Settings → General"
        )
        col1, col2 = st.columns(2)
        with col1:
            save = st.form_submit_button(f"💾 Save {service['name']}", use_container_width=True)
        with col2:
            delete = st.form_submit_button(f"🗑️ Delete {service['name']}", use_container_width=True)
        
        if save:
            if url and api_key:
                st.session_state.db.save_credentials(
                    st.session_state.user_id, service_key, url=url, api_key=api_key
                )
                st.success(f"✓ {service['name']} credentials saved!")
                st.rerun()
            else:
                st.error("Please enter both URL and API key")
        
        if delete:
            st.session_state.db.delete_credentials(st.session_state.user_id, service_key)
            st.success(f"✓ {service['name']} credentials deleted")
            st.rerun()


def configuration_page():
    """Display configuration page."""
    st.title("⚙️ Configuration")
    st.markdown(f"**User:** {st.session_state.username}")
    
    all_creds = load_credentials()
    llm_config = get_llm_config()
    
    tab1, tab2, tab3 = st.tabs(["🎬 Radarr", "📺 Sonarr", "🤖 AI Settings"])
    
    with tab1:
        render_service_config('radarr', all_creds)
    
    with tab2:
        render_service_config('sonarr', all_creds)
    
    with tab3:
        render_ai_settings(all_creds, llm_config)
    
    st.markdown("---")
    render_agent_initialization(all_creds)


def render_ai_settings(all_creds: Dict, llm_config: Dict):
    """Render AI settings configuration."""
    st.markdown("### AI Provider Configuration")
    
    openrouter_creds = all_creds.get('openrouter', {})
    openai_creds = all_creds.get('openai', {})
    
    with st.form("ai_settings_form"):
        selected_provider = st.selectbox(
            "LLM Provider",
            options=LLM_PROVIDERS,
            index=LLM_PROVIDERS.index(llm_config['provider']),
            help="Choose your AI provider"
        )
        
        st.markdown("---")
        st.markdown("#### OpenRouter Settings")
        openrouter_api_key = st.text_input(
            "OpenRouter API Key",
            value=openrouter_creds.get('api_key', ''),
            type="password",
            help="Get your API key from openrouter.ai"
        )
        
        st.markdown("---")
        st.markdown("#### OpenAI Settings")
        openai_api_key = st.text_input(
            "OpenAI API Key",
            value=openai_creds.get('api_key', ''),
            type="password",
            help="Your OpenAI API key"
        )
        
        st.markdown("---")
        model = st.text_input(
            "Model (optional)",
            value=llm_config['model'],
            placeholder="anthropic/claude-3.5-sonnet (OpenRouter) or gpt-4o-mini (OpenAI)",
            help="Leave empty to use default model"
        )
        
        save_ai = st.form_submit_button("💾 Save AI Settings", use_container_width=True)
        
        if save_ai:
            st.session_state.db.save_setting(st.session_state.user_id, 'llm_provider', selected_provider)
            st.session_state.db.save_setting(st.session_state.user_id, 'llm_model', model)
            
            if openrouter_api_key:
                st.session_state.db.save_credentials(
                    st.session_state.user_id, 'openrouter', api_key=openrouter_api_key
                )
            
            if openai_api_key:
                st.session_state.db.save_credentials(
                    st.session_state.user_id, 'openai', api_key=openai_api_key
                )
            
            st.success("✓ AI settings saved!")
            st.rerun()


def render_agent_initialization(all_creds: Dict):
    """Render agent initialization button and handle initialization."""
    if st.button("🚀 Initialize Agent", use_container_width=True, type="primary"):
        radarr_creds = all_creds.get('radarr', {})
        sonarr_creds = all_creds.get('sonarr', {})
        
        llm_config = get_llm_config()
        llm_provider = llm_config['provider']
        llm_creds = all_creds.get(llm_provider, {})
        llm_api_key = llm_creds.get('api_key')
        
        if not radarr_creds.get('url') and not sonarr_creds.get('url'):
            st.error("❌ Please configure at least one service (Radarr or Sonarr)")
            return
        
        if not llm_api_key:
            st.error(f"❌ Please configure {llm_provider.upper()} API key")
            return
        
        try:
            with st.spinner("🚀 Initializing AI Agent..."):
                agent = MediaAgent(
                    radarr_url=radarr_creds.get('url'),
                    radarr_api_key=radarr_creds.get('api_key'),
                    sonarr_url=sonarr_creds.get('url'),
                    sonarr_api_key=sonarr_creds.get('api_key'),
                    llm_provider=llm_provider,
                    api_key=llm_api_key,
                    model=llm_config['model'] if llm_config['model'] else None
                )
                st.session_state.agent = agent
                
                services = [SERVICES[s]['name'] for s in ['radarr', 'sonarr'] 
                           if all_creds.get(s, {}).get('url')]
                st.session_state.configured_services = services
                
                st.success(f"✅ Agent initialized with {', '.join(services)}")
                st.session_state.page = 'chat'
                st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to initialize agent: {e}")


def build_tool_card_html(tool: Dict, exec_info: Optional[Dict]) -> str:
    """Build HTML for a tool card."""
    params_str = ", ".join([f"{k}={v}" for k, v in tool['params'].items()])
    input_display = f'<strong>{tool["name"]}</strong>({params_str})'
    
    if exec_info:
        status = exec_info['status']
        status_map = {
            'started': ('executing', '⚙️ <em>Executing...</em> <span class="spinner">◐</span>'),
            'completed': ('success', f'✅ <strong>Output:</strong> {exec_info.get("result", "")}'),
            'failed': ('failed', f'❌ <strong>Error:</strong> {exec_info.get("error", "Unknown error")}')
        }
        card_class, output_display = status_map.get(status, ('', '⏳ <em>Waiting...</em>'))
        output_display = f'<div style="margin-top:0.5rem">{output_display}</div>'
    else:
        card_class = ''
        output_display = '<div style="margin-top:0.5rem">⏳ <em>Waiting for execution...</em></div>'
    
    return f'<div class="tool-card {card_class}">{input_display}{output_display}</div>'


def render_step_content(step: Dict) -> str:
    """Build HTML content for a step."""
    html_parts = []
    
    if step.get('plan'):
        html_parts.append(f'<div class="section-header">🗺️ Plan</div><div class="info-box">{step["plan"]}</div>')
    
    if step.get('thought'):
        html_parts.append(f'<div class="section-header">💭 Reasoning</div><div class="info-box">{step["thought"]}</div>')
    
    if step.get('tools'):
        html_parts.append('<div class="section-header">🔧 Tools</div>')
        for tool in step['tools']:
            exec_info = step.get('tool_executions', {}).get(tool.get('id'))
            html_parts.append(build_tool_card_html(tool, exec_info))
    
    return ''.join(html_parts) if html_parts else "🤔 Processing..."


def get_step_title(step: Dict, step_num: int) -> str:
    """Generate title for a step expander."""
    step_type = step.get('type', 'unknown')
    if step_type == 'plan':
        return f"Step {step_num}: 🗺️ Planning"
    elif step_type == 'execution':
        tool_execs = step.get('tool_executions', {})
        completed = sum(1 for t in tool_execs.values() if t['status'] in ['completed', 'failed'])
        return f"Step {step_num}: 🔧 Executing Tools ({completed}/{len(tool_execs)})"
    return f"Step {step_num}"


def render_step_expander(step: Dict, step_num: int, expanded: bool = True):
    """Render a single step in an expander."""
    with st.expander(get_step_title(step, step_num), expanded=expanded):
        content = render_step_content(step)
        if content == "🤔 Processing...":
            st.info(content)
        else:
            st.markdown(content, unsafe_allow_html=True)


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
                if message.get("steps"):
                    intermediate_steps = [s for s in message["steps"] if s.get('type') != 'final']
                    for i, step in enumerate(intermediate_steps, 1):
                        render_step_expander(step, i, expanded=False)
                
                st.markdown(message["content"])
                if message.get("timestamp"):
                    st.caption(f"🕐 {message['timestamp']}")
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about your media..."):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        with st.chat_message("user"):
            st.markdown(prompt)
            st.caption(f"🕐 {timestamp}")
        
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": timestamp
        })
        
        handle_agent_response(prompt, agent)


def handle_agent_response(prompt: str, agent: MediaAgent):
    """Handle streaming response from agent."""
    with st.chat_message("assistant"):
        steps = []
        current_step_id = None
        current_step = None
        main_placeholder = st.empty()
        tool_call_id_map = {}
        
        def render_current_state():
            with main_placeholder.container():
                all_steps = steps + ([current_step] if current_step else [])
                intermediate_steps = [s for s in all_steps if s.get('type') != 'final']
                final_step = next((s for s in all_steps if s.get('type') == 'final'), None)
                
                for i, step in enumerate(intermediate_steps, 1):
                    is_last = (i == len(intermediate_steps) and not final_step)
                    render_step_expander(step, i, expanded=is_last)
                
                if final_step and final_step.get('answer'):
                    st.markdown("**🎯 Final Answer:**")
                    st.markdown(final_step['answer'])
        
        def init_step(step_id):
            nonlocal current_step, current_step_id, steps
            if current_step:
                steps.append(current_step)
            current_step_id = step_id
            current_step = {
                'type': 'unknown',
                'plan': '',
                'thought': '',
                'tools': [],
                'tool_executions': {},
                'answer': ''
            }
        
        try:
            for event in parse_streaming_events(agent.agent.run_stream(prompt)):
                step_id = getattr(event, "step_id", None)
                
                if not current_step or (step_id and step_id != current_step_id):
                    init_step(step_id)
                
                if isinstance(event, AgentPlanEvent):
                    current_step['type'] = 'plan'
                    current_step['plan'] = event.plan.plan
                    render_current_state()
                
                elif isinstance(event, AgentStepEvent):
                    current_step['type'] = 'execution'
                    if event.step.tool_thought:
                        current_step['thought'] = event.step.tool_thought
                    
                    if event.step.tool_calls:
                        current_step['tools'] = []
                        for tc in event.step.tool_calls:
                            tool_info = {'id': tc.id, 'name': tc.tool_name, 'params': tc.parameters}
                            current_step['tools'].append(tool_info)
                            tool_call_id_map[tc.id] = tc.id
                    
                    render_current_state()
                
                elif isinstance(event, AgentToolExecutionEvent):
                    if current_step['type'] != 'execution':
                        current_step['type'] = 'execution'
                    
                    tool_id = tool_call_id_map.get(event.tool_call_id, event.tool_call_id)
                    current_step['tool_executions'][tool_id] = {
                        'name': event.tool_name,
                        'status': event.status
                    }
                    
                    if event.status in ["completed", "failed"] and event.result:
                        key = 'result' if event.result.success else 'error'
                        value = event.result.result if event.result.success else event.result.error
                        current_step['tool_executions'][tool_id][key] = value
                    
                    render_current_state()
                
                elif isinstance(event, AgentToolResultsEvent):
                    if current_step['type'] != 'execution':
                        current_step['type'] = 'execution'
                    
                    for result in event.results:
                        tool_id = result.tool_call_id
                        if tool_id not in current_step['tool_executions']:
                            current_step['tool_executions'][tool_id] = {
                                'name': result.tool_name,
                                'status': 'completed' if result.success else 'failed'
                            }
                        
                        key = 'result' if result.success else 'error'
                        value = result.result if result.success else result.error
                        current_step['tool_executions'][tool_id][key] = value
                        current_step['tool_executions'][tool_id]['status'] = 'completed' if result.success else 'failed'
                    
                    render_current_state()
                
                elif isinstance(event, AgentFinalResponseEvent):
                    current_step['type'] = 'final'
                    current_step['answer'] = event.response.final_answer
                    render_current_state()
            
            if current_step:
                steps.append(current_step)
            
            final_answer = next((s['answer'] for s in steps if s.get('answer')), "⚠️ No final answer provided")
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_answer,
                "timestamp": timestamp,
                "steps": steps
            })
            
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
        
        st.markdown("### 📍 Navigation")
        if st.button("💬 Chat", use_container_width=True, disabled=(st.session_state.page == 'chat')):
            st.session_state.page = 'chat'
            st.rerun()
        
        if st.button("⚙️ Settings", use_container_width=True, disabled=(st.session_state.page == 'settings')):
            st.session_state.page = 'settings'
            st.rerun()
        
        st.markdown("---")
        
        st.markdown("### 📡 Agent Status")
        if st.session_state.agent:
            st.success("🟢 Connected")
            if st.session_state.configured_services:
                st.info(f"**Services:** {', '.join(st.session_state.configured_services)}")
        else:
            st.warning("🟡 Not Initialized")
            st.info("Go to Settings to configure")
        
        if st.session_state.messages and st.session_state.page == 'chat':
            st.markdown("---")
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for key in ['user_id', 'username', 'agent', 'messages', 'configured_services', 'auto_init_attempted']:
                st.session_state[key] = [] if key in ['messages', 'configured_services'] else None
            st.session_state.page = 'chat'
            st.rerun()
        
        st.markdown("---")
        st.markdown("""
        ### ℹ️ About
        **Media Manager AI**
        
        Powered by OpenRouter
        
        **Features:**
        - 🎬 Radarr Integration
        - 📺 Sonarr Integration
        - 🔐 Encrypted Storage
        - 🤖 AI-Powered Chat
        """)


def render_welcome_page():
    """Render welcome page when no agent is configured."""
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
        - 🔍 Search for TV shows
        - ➕ Add series
        - 📅 Episode tracking
        - ⬇️ Season monitoring
        - 📊 Calendar view
        """)
    
    st.markdown("---")
    st.markdown("""
    ### 🚀 Quick Start
    1. Go to **Settings** ⚙️
    2. Configure your Radarr/Sonarr instances
    3. Set up your AI provider (OpenRouter or OpenAI)
    4. Click **Initialize Agent** 🚀
    5. Return to **Chat** 💬 and start asking questions!
    """)


def main():
    """Main application entry point."""
    init_page_config()
    initialize_session_state()
    
    if not st.session_state.user_id:
        login_page()
        return
    
    sidebar()
    auto_initialize_agent()
    
    if st.session_state.page == 'settings':
        configuration_page()
    elif st.session_state.page == 'chat':
        st.title("🎬 Media Manager AI Assistant")
        if st.session_state.agent:
            chat_interface()
        else:
            render_welcome_page()


if __name__ == "__main__":
    main()