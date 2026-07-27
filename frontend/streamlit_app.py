import requests
import streamlit as st

BACKEND_URL = "http://backend:8000/chat"
BACKEND_MESSAGES_URL = "http://backend:8000/conversations"
BACKEND_SIDEBAR_URL = "http://backend:8000/conversations/sidebar"
BACKEND_DELETE_URL = "http://backend:8000/conversations/delete"

INTRO_MESSAGE = """
Hello! I'm your consortium banking assistant.

I can help you with:

- Exploring available consortium options for automobiles, motorcycles, real estate, and services.
- Simulating estimated monthly payments based on credit amount, term, and standard plan conditions.
- Comparing consortium options and identifying which plan best fits your needs.
- Evaluating affordability and suitability based on income, budget, risk level, and urgency.
- Explaining consortium rules such as contemplation, bids, late payments, cancellation, FGTS usage, and contract obligations.
- Searching internal consortium documents for policy-based answers.
- Looking up public information when current external data is needed.
"""

st.set_page_config(
    page_title="Banking Agents Chat",
    page_icon="🏦",
)

st.title("Banking Agents Chat")

query_params = st.query_params

def load_conversation_messages(conversation_id: str) -> list[dict]:
    response = requests.get(
        f"http://backend:8000/conversations/{conversation_id}/messages",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["messages"]

def get_conversation_sidebar() -> list[dict]:
    response = requests.get(
        "http://backend:8000/conversations/sidebar",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["conversations"]

def clear_history():
    response = requests.delete(
        "http://backend:8000/conversations/delete",
        timeout = 30,
    )
    response.raise_for_status()

def delete_conversation(conversation_id: str):
    response = requests.delete(
        f"http://backend:8000/conversations/{conversation_id}/exclude",
        timeout = 30,
    )
    response.raise_for_status()

if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = query_params.get("conversation_id")

if 'messages' not in st.session_state:
    if st.session_state.conversation_id:
        try:
            st.session_state.messages = load_conversation_messages(st.session_state.conversation_id)

        except Exception:
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": INTRO_MESSAGE,
                }
            ]
    else:
        st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": INTRO_MESSAGE,
                }
            ]
        
with st.sidebar:
    st.title("Chat History")

    if st.button("New conversation"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": INTRO_MESSAGE,
            }
        ]
        st.session_state.conversation_id = None
        st.query_params.clear()
        st.rerun()

    if st.button("Clear History"):
        clear_history()
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": INTRO_MESSAGE,
            }
        ]
        st.session_state.conversation_id = None
        st.query_params.clear()
        st.rerun()
    
    st.divider()

    try:
        conversations = get_conversation_sidebar()

        if not conversations:
            st.caption("No Previous Conversations")

        for conversation in conversations:
            conversation_id = conversation["conversation_id"]
            title = conversation["title"] or "New Conversation"

            is_current = (conversation_id == st.session_state.conversation_id)

            button_title = title

            if is_current:
                button_title = f"✅ {title}"

            col1, col2 = st.columns([0.85, 0.15])

            with col1:
                if st.button(
                    button_title,
                    key=f"open_{conversation_id}",
                    use_container_width=True,
                ):
                    st.session_state.conversation_id = conversation_id
                    st.query_params["conversation_id"] = conversation_id

                    st.session_state.messages = load_conversation_messages(conversation_id)

                    st.rerun()

            with col2:
                with st.popover(
                    "⋮",
                    help="menu",
                    use_container_width=True
                ):

                    if st.button(
                        "Delete Conversation", 
                        key = f"delete_{conversation_id}",
                        use_container_width=True,
                    ):
                        delete_conversation(conversation_id)
                        if is_current:
                            st.session_state.messages = [
                                {
                                    "role": "assistant",
                                    "content": INTRO_MESSAGE,
                                }
                            ]
                            st.session_state.conversation_id = None
                            st.query_params.clear()
                        st.rerun()

    except Exception as error:
        st.caption("Could not load conversations.")
        st.caption(str(error))

#with st.container(horizontal=True):
    #if st.button("Clear conversation"):
    #    st.session_state.messages = [
    #        {
    #            "role": "assistant",
    #            "content": INTRO_MESSAGE,
    #        }
    #    ]
    #st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"].replace("$", r"\$"))

user_message = st.chat_input("Ask about consortium options...")

if user_message:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    with st.chat_message("user"):
        st.write(user_message)

    payload = {
        "message": user_message,
        "conversation_id": st.session_state.conversation_id
    }

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = requests.post(BACKEND_URL, json=payload, timeout=400)
            response.raise_for_status()
            data = response.json()

        st.session_state.conversation_id = data["conversation_id"]
        st.query_params["conversation_id"] = data["conversation_id"]

        assistant_response = data["response"]
        selected_agent = data["agent"]

        st.caption(f"Agent: {selected_agent}")
        st.markdown(assistant_response.replace("$", r"\$"))

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_response,
        }
    )