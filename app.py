import streamlit as st
import requests
import uuid
import os
import json
import time
from datetime import datetime

# Debug section - Display available secrets
st.write("Debug - Available Secrets:", list(st.secrets.keys()))

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


def load_memory():
    """Load user memory from memory.json"""
    if os.path.exists("memory.json"):
        try:
            with open("memory.json", "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_memory(memory):
    """Save user memory to memory.json"""
    with open("memory.json", "w") as f:
        json.dump(memory, f, indent=2)


def extract_traits(user_message, assistant_response):
    """Extract personal facts/preferences from user message and save to memory"""
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    
    extraction_prompt = f"""Extract any personal facts, preferences, or traits about the user from this conversation.
User said: "{user_message}"

Return ONLY a valid JSON object (no markdown, no extra text) with key-value pairs of traits. 
If no personal info, return empty object {{}}.
Examples of what to extract: name, age, location, job, hobby, preference, likes/dislikes, personality traits, etc.

Example valid outputs:
{{"name": "John", "location": "New York", "likes_coffee": true}}
{{"hobby": "photography", "experience_level": "beginner"}}
{{}}"""
    
    payload = {
        "model": "meta-llama/Llama-3.2-1B-Instruct",
        "messages": [{"role": "user", "content": extraction_prompt}]
    }
    
    try:
        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                response_text = data["choices"][0]["message"]["content"].strip()
                
                # Try to parse the JSON response
                try:
                    traits = json.loads(response_text)
                    if isinstance(traits, dict):
                        return traits
                except json.JSONDecodeError:
                    pass
        return {}
    except:
        return {}


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


def send_message_stream(messages, placeholder, memory=None):
    """Send messages to the Hugging Face API with streaming"""
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    
    # Inject memory into system prompt
    messages_with_memory = messages.copy()
    if memory and any(memory.values()):
        memory_str = ", ".join([f"{k}: {v}" for k, v in memory.items()])
        system_prompt = f"You are a helpful assistant. Remember these facts about the user: {memory_str}"
        messages_with_memory = [{"role": "system", "content": system_prompt}] + messages_with_memory
    
    payload = {
        "model": "meta-llama/Llama-3.2-1B-Instruct",
        "messages": messages_with_memory,
        "stream": True
    }
    
    try:
        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
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
        
        # Stream the response
        full_message = ""
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8") if isinstance(line, bytes) else line
                
                # Parse SSE format
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    
                    # Skip [DONE] message
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data_str)
                        
                        # Extract token from chunk
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            token = delta.get("content", "")
                            
                            if token:
                                full_message += token
                                # Update placeholder with streamed content
                                placeholder.write(full_message)
                                time.sleep(0.02)
                    except json.JSONDecodeError:
                        pass
        
        return full_message if full_message else None
    
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
    
    st.divider()
    
    # User Memory section
    with st.expander("👤 User Memory"):
        memory = load_memory()
        if memory:
            st.json(memory)
        else:
            st.info("No memory stored yet.")
        
        if st.button("🗑️ Clear Memory", use_container_width=True):
            save_memory({})
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
        # Load user memory
        user_memory = load_memory()
        
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
        
        # Display assistant message with streaming
        with st.chat_message("assistant"):
            # Create empty placeholder for streaming
            response_placeholder = st.empty()
            
            # Send full message history to API with streaming, passing memory
            assistant_message = send_message_stream(current_chat["messages"], response_placeholder, user_memory)
            
            if assistant_message:
                # Add assistant message to current chat
                current_chat["messages"].append({"role": "assistant", "content": assistant_message})
                
                # Save chat to file
                save_chat_to_file(current_chat)
                
                # Extract traits from user message and update memory
                extracted_traits = extract_traits(user_input, assistant_message)
                if extracted_traits:
                    user_memory.update(extracted_traits)
                    save_memory(user_memory)
