# AI Interaction Log

## Task 1

### Task: Part A – Page Setup & API Connection
**Prompt:** "Build a Streamlit chat app in app.py that uses st.set_page_config with page_title 'My AI Chat' and layout='wide', loads HF_TOKEN from st.secrets and shows an error message if missing or empty, has a function called send_message that posts to the Hugging Face API at https://router.huggingface.co/v1/chat/completions using model meta-llama/Llama-3.2-1B-Instruct, sends a hardcoded 'Hello!' test message and displays the response, and handles API errors gracefully (401 invalid token, 429 rate limit, network errors)."

**AI Suggestion:** Generated app.py with all requested features: page config with wide layout, HF_TOKEN loading from st.secrets with error handling, a send_message function calling the Hugging Face API with the Llama-3.2-1B-Instruct model, a hardcoded "Hello!" test message, and graceful error handling for 401, 429, network errors, timeouts, and other request exceptions.

**My Modifications & Reflections:** The app worked but was displaying the full raw JSON response. Fixed the code to extract only the assistant's reply using `response.json()["choices"][0]["message"]["content"]` so the output is clean and readable.

---

### Task: Part B – Multi-Turn Conversation UI
**Prompt:** "Extend the existing Streamlit chat app in app.py to add a multi-turn conversation UI: remove the hardcoded test message, initialize st.session_state.messages as an empty list if it doesn't exist, display chat history using st.chat_message() for each message in session state, collect user input using st.chat_input() fixed at the bottom, when user submits a message append it to session state as role 'user', send the full message history to the Hugging Face API, append the assistant's response to session state as role 'assistant', and keep all existing API function and error handling from Part A."

**AI Suggestion:** Modified send_message() to accept the full message history instead of a single message, added session state initialization, implemented chat history display with st.chat_message(), added st.chat_input() for user input, and ensured the full conversation context is sent to the API on each request.

**My Modifications & Reflections:** Reviewed the output and used it as-is. The implementation matched all requirements without needing changes.

---

### Task: Part C – Chat Management
**Prompt:** "Extend the existing Streamlit chat app in app.py to add chat management in the sidebar: a 'New Chat' button that creates a fresh empty conversation, unique chat IDs using uuid or timestamp, a title based on the first user message and a timestamp per chat, all chats stored in st.session_state as a dictionary, a sidebar list showing title and timestamp, visual highlighting of the active chat, chat switching without deleting other chats, a delete (✕) button next to each chat, and smart deletion that switches to another chat or shows an empty state. Keep all existing multi-turn conversation and API functionality from Part B."

**AI Suggestion:** Added full chat management using st.session_state.chats as a dictionary and st.session_state.current_chat_id to track the active chat. Each chat stores a UUID, auto-generated title from the first message (truncated to 50 chars), and a timestamp. Sidebar displays all chats with switch and delete buttons, and smart deletion auto-switches to another chat or shows an empty state.

**My Modifications & Reflections:** Reviewed the output and used it as-is. The implementation matched all requirements without needing changes.

---

### Task: Part D – Chat Persistence
**Prompt:** "Extend the existing Streamlit chat app in app.py to add chat persistence: save each chat as a separate JSON file inside a chats/ folder containing chat ID, title, timestamp, and full message history. On app startup automatically load all existing JSON files from chats/ into the sidebar. Save the chat to its JSON file every time a new message is added. When a chat is deleted with the ✕ button also delete its corresponding JSON file using os.remove(). Keep all existing chat management and API functionality from Part C."

**AI Suggestion:** Added os and json imports, auto-created chats/ directory on startup, and three helper functions: save_chat_to_file(), load_chats_from_disk(), and delete_chat_file(). Chats are loaded from disk on startup, saved after every new message, and their JSON files are removed on deletion. Each file stores the chat ID, title, timestamp, and full message history.

**My Modifications & Reflections:** Reviewed the output and used it as-is. The implementation matched all requirements without needing changes.

---

## Task 2

### Task: Token-by-Token Response Streaming
**Prompt:** "Extend the existing Streamlit chat app in app.py to stream responses token by token: add stream=True to the API request payload and requests.post() call, parse the server-sent events (SSE) response line by line, extract and parse JSON from each chunk (lines starting with 'data: '), use st.empty() to update the response as each chunk arrives, add a time.sleep(0.02) delay between chunks so streaming is visible, and once streaming is complete save the full assembled response to chat history and to the chat JSON file. Keep all existing functionality from Parts A, B, C and D."

**AI Suggestion:** Added a new send_message_stream() function that sets stream=True in both the payload and requests.post(), parses SSE line by line, extracts delta content tokens from each chunk, updates an st.empty() placeholder in real-time with a 0.02s delay between tokens, and saves the fully assembled response to chat history and the JSON file once streaming is complete. Imported time for the delay.

**My Modifications & Reflections:** Reviewed the output and used it as-is. The implementation matched all requirements without needing changes.

---

## Task 3

### Task: User Memory
**Prompt:** "Extend the existing Streamlit chat app in app.py to add user memory: after each assistant response make a second API call to extract any personal facts or preferences from the user's message as a JSON object (return {} if none found), load and merge extracted traits into memory.json updating existing keys with new values, display memory in a st.sidebar.expander panel called 'User Memory' showing all stored traits, add a native Streamlit button to clear and reset memory.json back to {}, and inject stored traits into the system prompt at the start of each API call. Keep all existing functionality from Parts A, B, C, D and Task 2."

**AI Suggestion:** Added load_memory(), save_memory(), and extract_traits() functions. The extract_traits() function makes a second API call after each assistant response to extract personal facts as JSON. Memory is injected into the system prompt via send_message_stream(), and a sidebar expander panel displays all stored traits with a clear button that resets memory.json to {}.

**My Modifications & Reflections:** Reviewed the output and used it as-is. The implementation matched all requirements without needing changes.