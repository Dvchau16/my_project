import streamlit as st
import requests
import uuid
import os
import json
from datetime import datetime

# Set page config
st.set_page_config(page_title="My AI Chat", layout="wide")

# Ensure chats directory exists
CHATS_DIR = "chats"
os.makedirs(CHATS_DIR, exist_ok=True)

# Load HF_TOKEN from secrets
try:
    hf_token = st.secrets["HF_TOKEN"]
    if not hf_token or hf_token.strip() == "":
        st.error("HF_TOKEN is empty. Please set it in .streamlit/secrets.toml")
        st.stop()
except KeyError:
    st.error("HF_TOKEN not found in secrets. Please set it in .streamlit/secrets.toml")
    st.stop()


def save_chat_to_file(chat):
    """Save a chat to a JSON file"""
    filepath = os.path.join(CHATS_DIR, f"{chat['id']}.json")
    with open(filepath, "w") as f:
        json.dump(chat, f, indent=2)


def load_chats_from_disk():
    """Load all chats from JSON files in the chats directory"""
    chats = {}
    if os.path.exists(CHATS_DIR):
        for filename in os.listdir(CHATS_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(CHATS_DIR, filename)
                try:
                    with open(filepath, "r") as f:
                        chat = json.load(f)
                        chats[chat["id"]] = chat
                except (json.JSONDecodeError, KeyError):
                    pass
    return chats


def delete_chat_file(chat_id):
    """Delete a chat's JSON file"""
    filepath = os.path.join(CHATS_DIR, f"{chat_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)


def send_message(messages):
    """Send messages to the Hugging Face API"""
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "meta-llama/Llama-3.2-1B-Instruct",
        "messages": messages
    }
    
    try:
        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # Handle specific error codes
        if response.status_code == 401:
            st.error("Invalid HF_TOKEN. Please check your token in .streamlit/secrets.toml")
            return None
        elif response.status_code == 429:
            st.error("Rate limit exceeded. Please try again later.")
            return None
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.ConnectionError:
        st.error("Network error: Unable to connect to Hugging Face API")
        return None
    except requests.exceptions.Timeout:
        st.error("Request timeout: Hugging Face API took too long to respond")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with API: {str(e)}")
        return None


# Main app
st.title("My AI Chat")

# Initialize session state with chats loaded from disk
if "chats" not in st.session_state:
    st.session_state.chats = load_chats_from_disk()

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# Sidebar - Chat Management
with st.sidebar:
    st.header("Chats")
    
    # New Chat button
    if st.button("➕ New Chat", use_container_width=True):
        new_chat_id = str(uuid.uuid4())
        new_chat = {
            "id": new_chat_id,
            "title": "New Chat",
            "timestamp": datetime.now().isoformat(),
            "messages": []
        }
        st.session_state.chats[new_chat_id] = new_chat
        save_chat_to_file(new_chat)
        st.session_state.current_chat_id = new_chat_id
        st.rerun()
    
    st.divider()
    
    # Display chat list
    for chat_id, chat in st.session_state.chats.items():
        col1, col2 = st.columns([0.9, 0.1])
        
        # Chat button
        with col1:
            chat_button = st.button(
                f"{chat['title']}\n{chat['timestamp'][:10]}",
                key=f"chat_{chat_id}",
                use_container_width=True
            )
            if chat_button:
                st.session_state.current_chat_id = chat_id
                st.rerun()
        
        # Delete button
        with col2:
            if st.button("✕", key=f"delete_{chat_id}", use_container_width=True):
                delete_chat_file(chat_id)
                del st.session_state.chats[chat_id]
                
                # If deleted chat was active, switch to another
                if st.session_state.current_chat_id == chat_id:
                    if st.session_state.chats:
                        st.session_state.current_chat_id = next(iter(st.session_state.chats))
                    else:
                        st.session_state.current_chat_id = None
                st.rerun()

# Main chat area
if st.session_state.current_chat_id is None:
    st.info("Create a new chat to get started!")
else:
    current_chat = st.session_state.chats[st.session_state.current_chat_id]
    
    # Display chat history
    for message in current_chat["messages"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to current chat
        current_chat["messages"].append({"role": "user", "content": user_input})
        
        # Update chat title to first user message if it's still "New Chat"
        if current_chat["title"] == "New Chat":
            current_chat["title"] = user_input[:50]
        
        # Save chat to file
        save_chat_to_file(current_chat)
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_input)
        
        # Send full message history to API
        response = send_message(current_chat["messages"])
        
        if response:
            # Extract assistant's response
            assistant_message = response["choices"][0]["message"]["content"]
            
            # Add assistant message to current chat
            current_chat["messages"].append({"role": "assistant", "content": assistant_message})
            
            # Save chat to file
            save_chat_to_file(current_chat)
            
            # Display assistant message
            with st.chat_message("assistant"):
                st.write(assistant_message)
