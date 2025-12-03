import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from mem0 import Memory
import supabase
from supabase.client import Client, ClientOptions
from pathlib import Path
import uuid
import sys

# --- 1. STREAMLIT PAGE CONFIGURATION (MUST BE FIRST ST COMMAND) ---
st.set_page_config(
    page_title="Mem0 Chat Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)
# -----------------------------------------------------------------

# --- 2. ENVIRONMENT VARIABLE LOADING ---
# Find the project root (S:\Mem0) assuming the script is in S:\Mem0\iterations
project_root = Path(__file__).resolve().parent.parent

# CRITICAL FIX: The previous line 'dotenv_path = "S:\Mem0\iterations\.env"' was incorrect.
# It should either use Path objects or correctly target the root folder (S:\Mem0)
# or the iterations folder, but using a hardcoded string with backslashes is risky.
# Assuming the .env file is now correctly placed at S:\Mem0\.env (in the project root):
dotenv_path = project_root / '.env'
# If the .env file is still in a subfolder, e.g., S:\Mem0\studio-integration-version\.env, use this instead:
# dotenv_path = project_root / 'studio-integration-version' / '.env'

load_dotenv(dotenv_path, override=True)
load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL", "")
supabase_key = os.environ.get("SUPABASE_KEY", "")
supabase_client = supabase.create_client(supabase_url, supabase_key)

model = os.getenv('MODEL_CHOICE', 'gpt-4o-mini')
# -----------------------------------------------------------------

# --- 3. CACHED RESOURCES (OpenAI Client and Mem0) ---
@st.cache_resource
def get_openai_client():
    return OpenAI()

@st.cache_resource
def get_memory():
    # CRITICAL: This line will raise a KeyError if DATABASE_URL is missing or empty!
    # Ensure DATABASE_URL is correctly set in your .env file.
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        st.error("DATABASE_URL is missing in the environment. Cannot initialize Mem0.")
        # Raise an exception to stop execution gracefully if resources aren't available
        raise ValueError("DATABASE_URL must be set in your .env file.")

    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": model
            }
        },
        "vector_store": {
            "provider": "supabase",
            "config": {
                "connection_string": database_url,
                "collection_name": "memories"
            }
        }
    }
    return Memory.from_config(config)

# Get cached resources
try:
    openai_client = get_openai_client()
    memory = get_memory()
except ValueError:
    # If get_memory failed (due to missing DATABASE_URL), stop here
    st.stop()
# -----------------------------------------------------------------


# --- 4. AUTHENTICATION FUNCTIONS ---
def sign_up(email, password, full_name):
    try:
        response = supabase_client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name
                }
            }
        })
        if response and response.user:
            st.session_state.authenticated = True
            st.session_state.user = response.user
            st.rerun()
        return response
    except Exception as e:
        # Check if the error is due to an existing user
        st.error(f"Error signing up: {str(e)}")
        return None

def sign_in(email, password):
    try:
        response = supabase_client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if response and response.user:
            st.session_state.authenticated = True
            st.session_state.user = response.user
            st.rerun()
        return response
    except Exception as e:
        st.error(f"Error signing in: {str(e)}")
        return None

def sign_out():
    try:
        supabase_client.auth.sign_out()
        st.session_state.authenticated = False
        st.session_state.user = None
        # Set a flag to trigger rerun on next render
        st.session_state.logout_requested = True
    except Exception as e:
        st.error(f"Error signing out: {str(e)}")
# -----------------------------------------------------------------


# --- 5. CHAT LOGIC ---
def chat_with_memories(message, user_id):
    # Retrieve relevant memories
    relevant_memories = memory.search(query=message, user_id=user_id, limit=3)
    memories_str = "\n".join(f"- {entry['memory']}" for entry in relevant_memories["results"])

    # Generate Assistant response
    system_prompt = f"You are a helpful AI assistant with memory. Answer the question based on the query and user's memories.\nUser Memories:\n{memories_str}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": message}]

    with st.spinner("Thinking..."):
        response = openai_client.chat.completions.create(model=model, messages=messages)
        assistant_response = response.choices[0].message.content

    # Create new memories from the conversation
    messages.append({"role": "assistant", "content": assistant_response})
    memory.add(messages, user_id=user_id)

    return assistant_response
# -----------------------------------------------------------------


# --- 6. INITIALIZE SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user" not in st.session_state:
    st.session_state.user = None

# Check for logout flag and clear it after processing
if st.session_state.get("logout_requested", False):
    st.session_state.logout_requested = False
    st.rerun()
# -----------------------------------------------------------------


# --- 7. SIDEBAR AND MAIN APPLICATION LAYOUT ---

# Sidebar for authentication
with st.sidebar:
    st.title("🧠 Mem0 Chat")

    if not st.session_state.authenticated:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])

        with tab1:
            st.subheader("Login")
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            login_button = st.button("Login")

            if login_button:
                if login_email and login_password:
                    sign_in(login_email, login_password)
                else:
                    st.warning("Please enter both email and password.")

        with tab2:
            st.subheader("Sign Up")
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input("Password", type="password", key="signup_password")
            signup_name = st.text_input("Full Name", key="signup_name")
            signup_button = st.button("Sign Up")

            if signup_button:
                if signup_email and signup_password and signup_name:
                    response = sign_up(signup_email, signup_password, signup_name)
                    if response and response.user:
                        st.success("Sign up successful! Please check your email to confirm your account.")
                    # Error handled by sign_up function

                else:
                    st.warning("Please fill in all fields.")
    else:
        user = st.session_state.user
        if user:
            st.success(f"Logged in as: {user.email}")
            st.button("Logout", on_click=sign_out)

            # Display user information
            st.subheader("Your Profile")
            st.write(f"User ID: {user.id}")

            # Memory management options
            st.subheader("Memory Management")
            if st.button("Clear All Memories"):
                memory.clear(user_id=user.id)
                st.session_state.messages = []
                st.success("All memories cleared!")
                st.rerun()

# Main chat interface
if st.session_state.authenticated and st.session_state.user:
    user_id = st.session_state.user.id

    st.title("Chat with Memory-Powered AI")
    st.write("Your conversation history and preferences are remembered across sessions.")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    user_input = st.chat_input("Type your message here...")

    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Display user message
        with st.chat_message("user"):
            st.write(user_input)

        # Get AI response
        ai_response = chat_with_memories(user_input, user_id)

        # Add AI response to chat history
        st.session_state.messages.append({"role": "assistant", "content": ai_response})

        # Display AI response
        with st.chat_message("assistant"):
            st.write(ai_response)
else:
    st.title("Welcome to Mem0 Chat Assistant")
    st.write("Please login or sign up to start chatting with the memory-powered AI assistant.")
    st.write("This application demonstrates how AI can remember your conversations and preferences over time.")

    # Feature highlights
    st.subheader("Features")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🧠 Long-term Memory")
        st.write("The AI remembers your past conversations and preferences.")

    with col2:
        st.markdown("### 🔒 Secure Authentication")
        st.write("Your data is protected with Supabase authentication.")

    with col3:
        st.markdown("### 💬 Personalized Responses")
        st.write("Get responses tailored to your history and context.")

if __name__ == "__main__":
    pass