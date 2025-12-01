import streamlit as st
import requests
import uuid
import json
from datetime import timedelta

# --- Configuration ---
# It's recommended to use st.secrets for storing sensitive information like API tokens
API_URL = "https://elastic.snaplogic.com/api/1/rest/slsched/feed/SIE_Health_Dev/SHS_IT_DCE_PM/MCP_POC/SHSAgentDriver_TriggeredTask"
API_TOKEN = "T4eplJ7hZxOcBlopQP1TON1fT959wyqO"  # or st.secrets["API_TOKEN"]

# --- Example Prompts Data Structure ---
EXAMPLE_PROMPTS = {
    "DXCompetitiveInformation": [
        "How does Roche’s portfolio compare to Siemens Healthineers (SHS) in terms of breadth, depth, and innovation?",
        "How do Roche’s analyzers compare to Siemens Healthineers’?"
    ],
    "Brandville": [
        "What is the Siemens logo?",
        "What are the Siemens brand colors and their hex codes?"
    ]
}

# --- Streamlit Page Setup ---
st.set_page_config(
    page_title="Knowledge Assistant with MCP",
    page_icon="🤖",
    layout="wide"
)

# --- Caching the API Call ---
@st.cache_data(ttl=timedelta(minutes=10), show_spinner=False)
def get_assistant_response(session_id, messages_tuple):
    """
    Sends the user's prompt to the backend API and returns the response.
    This function is cached to avoid repeated API calls with the same input.
    """
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    # Convert the tuple back to a list of dictionaries
    messages = [dict(m) for m in messages_tuple]

    payload = [
        {
            "session_id": session_id,
            "messages": messages
        }
    ]

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=180
        )
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return {"error": f"Error communicating with agent: {e}"}


def extract_assistant_reply(data):
    """
    Normalize different possible API response formats to a single string.

    Handles:
    - dict with 'response' / 'answer' / 'message' / 'content' / 'error'
    - list of such dicts
    - fallback to string conversion
    """

    def from_dict(d):
        # Prefer explicit error if present
        if "error" in d and isinstance(d["error"], str):
            return f"⚠️ {d['error']}"
        for key in ("response", "answer", "message", "content"):
            if key in d and isinstance(d[key], str):
                return d[key]
        return None

    if isinstance(data, dict):
        extracted = from_dict(data)
        if extracted is not None:
            return extracted
        return str(data)

    if isinstance(data, list) and len(data) > 0:
        for item in data:
            if isinstance(item, dict):
                extracted = from_dict(item)
                if extracted is not None:
                    return extracted
        return str(data[0])

    return "I received an unexpected response format from the backend."


def initialize_session_state():
    """Initializes all necessary session state variables."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "active_category" not in st.session_state:
        st.session_state.active_category = "Brandville"
    if "last_full_data" not in st.session_state:
        st.session_state.last_full_data = None


def add_message(role, content):
    """
    Adds a message to the session state chat history.
    role: 'USER' or 'ASSISTANT'
    """
    st.session_state.messages.append(
        {"sl_role": role, "content": content}
    )


def display_sidebar():
    """Displays the sidebar with configuration and session info."""
    with st.sidebar:
        st.title("🔧 Configuration")
        st.markdown("Manage session and view the raw API data here.")
        
        st.markdown("**Session ID**")
        st.code(st.session_state.session_id, language="text")
        
        if st.button("♻️ New Session"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.last_full_data = None
            st.experimental_rerun()
        
        st.markdown("---")
        st.markdown("### Raw API Response")
        if st.session_state.last_full_data is not None:
            st.json(st.session_state.last_full_data)
        else:
            st.write("No API response yet. Start by asking a question.")


def set_active_category(category):
    """Sets the active example category."""
    st.session_state.active_category = category


def handle_prompt_submission(prompt_text):
    """
    Handles sending of a prompt (from chat input or example button),
    calling the backend API, and updating the UI.
    """
    if not prompt_text.strip():
        return
    
    # Add user message to the chat history
    add_message("USER", prompt_text)
    
    # Prepare messages for the API call
    messages_tuple = tuple(
        {"sl_role": msg["sl_role"], "content": msg["content"]}
        for msg in st.session_state.messages
    )

    # Local spinner near the chat / button instead of global "Running …"
    with st.spinner("SAM is thinking..."):
        data = get_assistant_response(st.session_state.session_id, messages_tuple)
    
    # Store the full response (for raw view in sidebar)
    st.session_state.last_full_data = data
    
    # Extract a "nice" message to show in the main chat
    assistant_reply = extract_assistant_reply(data)
    
    # Add assistant message to the chat history
    add_message("ASSISTANT", assistant_reply)


def display_main_content():
    """Displays the main layout of the application."""
    st.title("🤖 Knowledge Assistant with MCP")
    st.write("Ask questions and explore example prompts for different use case categories.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Use Case Categories")
        st.write("Select a category to see example prompts:")
        
        with st.container(border=True):
            st.markdown("##### 🚀 Competitive Information for DX Business")
            st.write("Discover opportunities and competitive insights.")
            st.button(
                "Show DX Competitive Examples",
                on_click=set_active_category,
                args=("DXCompetitiveInformation",),
                key="b_leads",
                use_container_width=True
            )
        
        with st.container(border=True):
            st.markdown("##### 🎨 Brand & Communication")
            st.write("Ask about brand guidelines, assets, and visual identity.")
            st.button(
                "Show Brand Examples",
                on_click=set_active_category,
                args=("Brandville",),
                key="b_brand",
                use_container_width=True
            )
    
    with col2:
        st.subheader("About This Assistant")
        st.write(
            """
            This assistant is powered by:
            - **SnapLogic** as the orchestration and MCP backend  
            - A **knowledge graph / RAG backend** for retrieving relevant documents and data  
            - A chat-style interface implemented in **Streamlit**
            """
        )
        
        st.markdown("#### How it works")
        st.markdown(
            """
            1. You select an example or type your own question.  
            2. The app sends your query and conversation history to a SnapLogic task.  
            3. The backend orchestrates retrieval and reasoning across multiple systems.  
            4. You see the response in this chat and can inspect the full JSON in the sidebar.
            """
        )
    
    st.markdown("---")
    st.subheader(f"Example Prompts for: {st.session_state.active_category}")
    prompts_to_show = EXAMPLE_PROMPTS.get(st.session_state.active_category, [])
    for i, prompt in enumerate(prompts_to_show):
        st.button(
            prompt,
            on_click=handle_prompt_submission,
            args=(prompt,),
            use_container_width=True,
            key=f"ex_{st.session_state.active_category}_{i}"
        )

    st.markdown("---")


def display_chat_interface():
    """Manages the chat display and response processing."""
    st.subheader("Chat with SAM")
    
    chat_container = st.container()
    with chat_container:
        # Display existing messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["sl_role"].lower()):
                st.markdown(msg["content"])
    
    # Process new user message
    user_input = st.chat_input("Type your question here...")
    if user_input:
        handle_prompt_submission(user_input)
        st.experimental_rerun()


# --- Main App Execution ---
def main():
    initialize_session_state()
    display_sidebar()
    display_main_content()
    display_chat_interface()  # debug panel removed from main()


if __name__ == "__main__":
    main()
