import streamlit as st
import requests
import uuid
import json
from datetime import timedelta

# --- Configuration ---
# It's recommended to use st.secrets for storing sensitive information like API tokens
API_URL = "https://elastic.snaplogic.com/api/1/rest/slsched/feed/SIE_Health_Dev/SHS_IT_DCE_PM/MCP_POC/SHSAgentDriver_TriggeredTask"
API_TOKEN = "T4eplJ7hZxOcBlopQP1TON1fT959wyqO" # Replace with your actual token or use st.secrets

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
@st.cache_data(ttl=timedelta(minutes=10))
def get_assistant_response(session_id, messages_tuple):
    """
    Sends the user's prompt to the backend API and returns the response.
    This function is cached to avoid repeated API calls with the same input.
    """
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    # Convert the tuple of tuples back to a list of dictionaries
    messages = [dict(m) for m in messages_tuple]
    # Construct the payload as expected by the API
    payload = [{"session_id": session_id, "messages": messages, "last_full_data": st.session_state.get('last_full_data', None)}]
    
    try:
        # Make the POST request to the API
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=180)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        # The API can return a single object or a list of objects.
        # We handle this ambiguity in the display_chat_interface function.
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        # Return an error message if the API call fails
        return {"error": f"Error communicating with agent: {e}"}

def initialize_session_state():
    """Initializes all necessary session state variables."""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'active_category' not in st.session_state:
        st.session_state.active_category = "Leads"
    if 'last_full_data' not in st.session_state:
        st.session_state.last_full_data = None
    if 'raw_response_for_debug' not in st.session_state:
        st.session_state.raw_response_for_debug = {}

def set_active_category(category):
    """Callback to set the active example category."""
    st.session_state.active_category = category

def handle_prompt_submission(prompt_text):
    """Callback to add a user message to the chat history."""
    st.session_state.messages.append({"sl_role": "USER", "content": prompt_text})

def display_main_content():
    """Renders the main UI components in the correct order."""
    st.title("🤖 SAM AI Knowledge Assistant")
    st.caption("Your intelligent partner for accessing Siemens Healthineers sales and marketing information.")
    st.markdown("---")
    
    st.subheader("What Can I Do For You?")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("##### 📊 Analyze Sales & Marketing Leads")
            st.write("Query active leads or perform historical analysis on all past leads.")
            st.button("Show Lead Examples", on_click=set_active_category, args=("Leads",), key="b_leads", use_container_width=True)
    with col2:
        with st.container(border=True):
            st.markdown("##### 📈 Explore Customer & Product Data")
            st.write("View installed products, find opportunities, and check quote statuses.")
            st.button("Show Customer Examples", on_click=set_active_category, args=("Customer",), key="b_customer", use_container_width=True)
            
    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown("##### 🛠️ Access Technical & Service Information")
            st.write("Find detailed equipment data like hardware/software versions and service status.")
            st.button("Show Technical Examples", on_click=set_active_category, args=("Technical",), key="b_tech", use_container_width=True)
    with col4:
        with st.container(border=True):
            st.markdown("##### 📚 Find Documents & Product Literature")
            st.write("List all available documents or ask general questions about a product.")
            st.button("Show Document Examples", on_click=set_active_category, args=("Documents",), key="b_docs", use_container_width=True)
    
    st.markdown("---")
    st.subheader(f"Example Prompts for: {st.session_state.active_category}")
    prompts_to_show = EXAMPLE_PROMPTS.get(st.session_state.active_category, [])
    for i, prompt in enumerate(prompts_to_show):
        st.button(prompt, on_click=handle_prompt_submission, args=(prompt,), use_container_width=True, key=f"ex_{st.session_state.active_category}_{i}")

    st.markdown("---")

def display_chat_interface():
    """Manages the chat display and response processing."""
    st.subheader("Chat with SAM")
    
    # Display existing messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["sl_role"].lower()):
            st.markdown(msg["content"])
            
    # Process new user message
    if st.session_state.messages and st.session_state.messages[-1]["sl_role"] == "USER":
        with st.spinner("SAM is thinking..."):
            messages_tuple = tuple(map(lambda m: tuple(sorted(m.items())), st.session_state.messages))
            raw_response_obj = get_assistant_response(st.session_state.session_id, messages_tuple)
            
            st.session_state.raw_response_for_debug = raw_response_obj

            display_text = "An error occurred."
            full_data = None
            
            try:
                # --- THIS IS THE UPDATED LOGIC BLOCK ---
                # It now handles three cases:
                # 1. API returns a list containing an object: [{"response": ...}]
                # 2. API returns a single object: {"response": ...}
                # 3. API returns an error object: {"error": ...}

                response_container = None
                if isinstance(raw_response_obj, list) and raw_response_obj:
                    # Case 1: API returned a list, take the first element.
                    response_container = raw_response_obj[0]
                elif isinstance(raw_response_obj, dict):
                    # Case 2 & 3: API returned a single object.
                    response_container = raw_response_obj

                if response_container and 'response' in response_container:
                    agent_response_content = response_container['response']
                    
                    # Check the TYPE of the agent's actual response
                    if isinstance(agent_response_content, dict):
                        # It's the OLD format (a dictionary with keys)
                        display_text = agent_response_content.get("display_text", "Error: Agent response is missing 'display_text'.")
                        full_data = agent_response_content.get("full_data", None)
                    elif isinstance(agent_response_content, str):
                        # It's the NEW format (a simple text string)
                        display_text = agent_response_content
                        full_data = None
                    else:
                        display_text = f"Error: Received an unexpected response format from the agent: {type(agent_response_content)}"
                
                elif response_container and 'error' in response_container:
                    display_text = response_container['error']
                
                else:
                    display_text = "Error: Unexpected API response structure."
                # --- END OF UPDATED LOGIC BLOCK ---

            except Exception as e:
                display_text = f"An unexpected error occurred while processing the response: {e}"

            st.session_state.last_full_data = full_data
            st.session_state.messages.append({"sl_role": "ASSISTANT", "content": display_text})
            st.rerun()

def display_sidebar():
    """Manages the sidebar content."""
    with st.sidebar:
        st.header("Session Control")
        st.write(f"**Session ID:**")
        st.code(st.session_state.session_id, language=None)
        if st.button("Start New Conversation", use_container_width=True):
            st.cache_data.clear()
            keys_to_clear = list(st.session_state.keys())
            for key in keys_to_clear:
                del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        st.subheader("Raw API Response")
        data_to_display = st.session_state.get('raw_response_for_debug')
        if data_to_display:
            st.json(data_to_display)
        else:
            st.json({"info": "No API call made yet."})

# --- Main App Execution ---
def main():
    """Main function to run the Streamlit app."""
    initialize_session_state()
    display_sidebar()
    display_main_content()
    
    if prompt := st.chat_input("Or ask your own question here..."):
        handle_prompt_submission(prompt)
        st.rerun()

    display_chat_interface()

if __name__ == "__main__":
    main()
