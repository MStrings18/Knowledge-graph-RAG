import sqlite3
from typing_extensions import TypedDict
from uuid import uuid4
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph
from langchain_groq import ChatGroq
import os, getpass, requests
from mock_pdf_gen import generate_pdf
from mock_email_service import send_email
from database import db_session
from mock_insurance_db import insurance_credentials_db  

from graph_retriever2 import GraphRetriever
from gemini_client import generate_answer   # <-- make sure you have your answer generator here
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE


# Set API keys
def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("GROQ_API_KEY")
_set_env("LANGSMITH_API_KEY")

model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
db_path = r"C:\Users\Manan Verma\Coding\Projects\kg-rag\backend\langgraph_memory.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
memory = SqliteSaver(conn)

# State Schemas
class PublicState(TypedDict, total=False):
    user_message: str
    intent: str
    response: str
    requires_retry: bool

class PrivateState(TypedDict, total=False):
    session_user_id: str
    insurance_user_id : str
    credentials: dict
    policy_graph: dict
    thread_id: str
  

class GraphState(TypedDict, total=False):
    public: PublicState
    private: PrivateState

def sanitize_for_llm(state: GraphState) -> PublicState:
    return state['public'].copy()

def classify_intent(state: GraphState) -> GraphState:
    print("[classify_intent] Using LLM to classify intent...")
    user_message = sanitize_for_llm(state).get('user_message', '')

    prompt = f"""
    Classify the user's intent into exactly one of:
    - explanation: asking for information or non-actionable guidance
    - update_policy: requests to update/modify policy details, coverage, beneficiaries, address, etc.
    - change_credentials: requests specifically about password/credentials (phrases like 'change password', 'reset password', 'update login password').
    - file_claim: requests to file/submit a claim.
    - undefined_actionable: actionable but not in the above list.
    - unknown: cannot determine.

    IMPORTANT: Do NOT map general 'change/update' requests to change_credentials unless the message is clearly about password or login credentials.

    user message: {user_message}
    Output only one of: explanation, update_policy, change_credentials, file_claim, undefined_actionable, unknown.
    """

    llm_msg = model.invoke(prompt)
    intent = getattr(llm_msg, "content", llm_msg).strip().lower()
    print(intent)
    allowed = {"explanation","update_policy","change_credentials","file_claim","undefined_actionable","unknown"}
    if intent not in allowed:
        intent = "explanation"
    return {
        'public': {**state.get('public', {}), 'intent': intent},
        'private': state.get('private', {})
    }

def handle_unknown(state: GraphState) -> GraphState:
    return {'public': {'response': "Could not understand your request. Please explain more."}, 'private': state['private']}


def handle_explanation(state: GraphState) -> GraphState:
    """
    Handles 'explanation' intent:
    1. Retrieves relevant chunks from the Neo4j knowledge graph using thread_id.
    2. Generates a final answer using retrieved chunks (RAG).
    """
    try:
        user_query = sanitize_for_llm(state).get('user_message', '')
        thread_id = state['private'].get('thread_id')

        if not thread_id:
            return {
                'public': {**state['public'], 'response': "⚠ No thread_id found. Cannot perform graph retrieval."},
                'private': state['private']
            }

        print(f"[handle_explanation] Running RAG for thread_id={thread_id} | query='{user_query}'")

        # --- 1️⃣ Retrieve from Neo4j using thread_id ---
        retriever = GraphRetriever(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE, thread_id)
        retrieved_chunks = retriever.retrieve(user_query)
        retriever.close()

        print(f"[handle_explanation] Retrieved {len(retrieved_chunks)} chunks from graph.")

        if not retrieved_chunks:
            explanation = "No relevant information found in the document graph for your query."
        else:
            # --- 2️⃣ Generate Augmented Answer (RAG) ---
            explanation = generate_answer(user_query, retrieved_chunks)

        return {
            'public': {**state['public'], 'response': explanation},
            'private': state['private']
        }

    except Exception as e:
        print(f"[ERROR] handle_explanation failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'public': {**state['public'], 'response': "⚠ An error occurred while retrieving the explanation."},
            'private': state['private']
        }
def get_stored_insurance_credentials(session_user_id: str) -> dict | None:
    """Helper function to get stored insurance credentials for a user"""
    if not session_user_id:
        return None
    return insurance_credentials_db.get_insurance_credentials(session_user_id)

MOCK_API_BASE_URL = "http://localhost:5000"

def handle_update_policy(state: GraphState) -> GraphState:
    # Ensure insurance session (attempt auto-login if creds provided)
    if not state['private'].get('insurance_user_id'):
        # First try stored credentials
        stored_creds = get_stored_insurance_credentials(state['private'].get('session_user_id'))
        if stored_creds:
            try:
                insurance_user_id, base_creds = perform_insurance_login(
                    stored_creds['insurance_username'], 
                    stored_creds['insurance_password']
                )
                # Update the stored credentials with the insurance_user_id
                insurance_credentials_db.update_insurance_user_id(
                    state['private'].get('session_user_id'),
                    stored_creds['insurance_username'],
                    insurance_user_id
                )
                new_private = {**state['private'], 'insurance_user_id': insurance_user_id, 'credentials': {**base_creds}}
                state = {'public': state['public'], 'private': new_private}
            except Exception:
                # Mark stored credentials as invalid and ask user to re-enter
                insurance_credentials_db.invalidate_insurance_credentials(
                    state['private'].get('session_user_id'),
                    stored_creds['insurance_username']
                )
                public = {**state['public'], 'response': "Stored insurance credentials are invalid. Please update your insurance credentials.", 'requires_retry': True}
                return {'public': public, 'private': state['private']}
        else:
            # Fallback to manual credentials if provided
            creds_try = state['private'].get('credentials') or {}
            username_try = creds_try.get('insurance_username') or creds_try.get('username')
            password_try = creds_try.get('old_password') or creds_try.get('new_password')
            if username_try and password_try:
                try:
                    insurance_user_id, base_creds = perform_insurance_login(username_try, password_try)
                    # Store the credentials for future use
                    insurance_credentials_db.store_insurance_credentials(
                        chatbot_user_id=state['private'].get('session_user_id'),
                        insurance_username=username_try,
                        insurance_password=password_try,
                        insurance_user_id=insurance_user_id
                    )
                    new_private = {**state['private'], 'insurance_user_id': insurance_user_id, 'credentials': {**creds_try, **base_creds}}
                    state = {'public': state['public'], 'private': new_private}
                except Exception:
                    public = {**state['public'], 'response': "Insurance login failed. Please check credentials.", 'requires_retry': True}
                    return {'public': public, 'private': state['private']}
            else:
                public = {**state['public'], 'response': "Please log in to your insurance account first", 'requires_retry': True}
                return {'public': public, 'private': state['private']}

    policy_graph = state['private']['policy_graph']
    policy_number = next(
        e['attributes']['policy_number'] for e in policy_graph['entities'] if e['type'] == "Policy"
    )

    try:
        response = requests.post(f"{MOCK_API_BASE_URL}/update_policy", json={
            "credentials": state['private']['credentials'],
            "policy_data": {"policy_number": policy_number},
            "user_id": state['private']['insurance_user_id']  
        })

        response.raise_for_status()  
        data = response.json()
        reference_id = data.get('reference_id')

        if not reference_id:
            raise ValueError(f"Missing reference_id in response: {data}")

    except Exception as e:
        print("[ERROR] Failed to call mock API or parse response:", e)
        return {
            'public': {**state['public'], 'response': "Internal error occurred."},
            'private': state['private']
        }

    policy_doc = requests.get(f"{MOCK_API_BASE_URL}/policy_document/{reference_id}").json()
    pdf_url = generate_pdf(policy_doc)

    send_email(
        to_email=None,
        subject="Policy Updated Confirmation",
        body=f"Your policy {policy_number} was updated. Ref ID: {reference_id}",
        attachment_path=pdf_url,
        insurance_username=(
            state['private'].get('credentials', {}).get('insurance_username')
            or state['private'].get('credentials', {}).get('username')
        ),
        user_id=state['private'].get('session_user_id')
    )
    print(f"[DEBUG] Email params: session_user_id={state['private'].get('session_user_id')}, insurance_username={state['private'].get('credentials', {}).get('insurance_username')}")


    return {
        'public': {**state['public'], 'response': f"Policy updated successfully. Ref ID: {reference_id}"},
        'private': state['private']
    }


def handle_change_credentials(state: GraphState) -> GraphState:
    creds = state['private'].get('credentials') or {}
    username = creds.get('insurance_username') or creds.get('username')
    old_password = creds.get('old_password')
    new_password = creds.get('new_password')

    # If credentials not provided, try to use stored credentials for username and old_password
    if not username or not old_password:
        stored_creds = get_stored_insurance_credentials(state['private'].get('session_user_id'))
        if stored_creds:
            username = username or stored_creds['insurance_username']
            old_password = old_password or stored_creds['insurance_password']

    if not username or not old_password or not new_password:
        # Ask UI to provide missing credentials
        missing = []
        if not username:
            missing.append("insurance username")
        if not old_password:
            missing.append("old password")
        if not new_password:
            missing.append("new password")
        
        public = {
            **state['public'],
            'response': f"Please provide {', '.join(missing)}. You can store your current credentials using the /insurance-credentials endpoint.",
            'requires_retry': True,
        }
        return {'public': public, 'private': state['private']}

    try:
        response = requests.post(
            f"{MOCK_API_BASE_URL}/change_credentials",
            json={
                "username": username,
                "old_password": old_password,
                "new_password": new_password,
            },
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print("[ERROR] Failed to call mock API:", e)
        return {
            'public': {**state['public'], 'response': "Internal error occurred."},
            'private': state['private']
        }

    reference_id = data['reference_id']
    pdf_url = generate_pdf({"ref_id": reference_id, "content": "Mock content"})

    send_email(
        to_email=None,
        subject="Credentials Updated Confirmation",
        body=f"your password was updated",
        attachment_path=pdf_url,
        insurance_username=username,
        user_id=state['private'].get('session_user_id')
    )

    # Update stored credentials with new password
    if state['private'].get('session_user_id'):
        insurance_credentials_db.store_insurance_credentials(
            chatbot_user_id=state['private'].get('session_user_id'),
            insurance_username=username,
            insurance_password=new_password
        )

    # Update session credentials: new password becomes the current password
    updated_credentials = {
        **state['private']['credentials'],
        'old_password': new_password,  # New password becomes current password
        'new_password': None,          # Clear the new password field
    }
    
    return {
        'public': {**state['public'], 'response': f"Credentials changed successfully. Ref ID: {reference_id}"},
        'private': {**state['private'], 'credentials': updated_credentials}
    }


def handle_file_claim(state: GraphState) -> GraphState:
    if not state['private'].get('insurance_user_id'):
        # First try stored credentials
        stored_creds = get_stored_insurance_credentials(state['private'].get('session_user_id'))
        if stored_creds:
            try:
                insurance_user_id, base_creds = perform_insurance_login(
                    stored_creds['insurance_username'], 
                    stored_creds['insurance_password']
                )
                # Update the stored credentials with the insurance_user_id
                insurance_credentials_db.update_insurance_user_id(
                    state['private'].get('session_user_id'),
                    stored_creds['insurance_username'],
                    insurance_user_id
                )
                new_private = {**state['private'], 'insurance_user_id': insurance_user_id, 'credentials': {**base_creds}}
                state = {'public': state['public'], 'private': new_private}
            except Exception:
                # Mark stored credentials as invalid and ask user to re-enter
                insurance_credentials_db.invalidate_insurance_credentials(
                    state['private'].get('session_user_id'),
                    stored_creds['insurance_username']
                )
                return {'public': {'response': "Stored insurance credentials are invalid. Please update your insurance credentials.", 'requires_retry': True}, 'private': state['private']}
        else:
            # Fallback to manual credentials if provided
            creds_try = state['private'].get('credentials') or {}
            username_try = creds_try.get('insurance_username') or creds_try.get('username')
            password_try = creds_try.get('old_password') or creds_try.get('new_password')
            if username_try and password_try:
                try:
                    insurance_user_id, base_creds = perform_insurance_login(username_try, password_try)
                    # Store the credentials for future use
                    insurance_credentials_db.store_insurance_credentials(
                        chatbot_user_id=state['private'].get('session_user_id'),
                        insurance_username=username_try,
                        insurance_password=password_try,
                        insurance_user_id=insurance_user_id
                    )
                    new_private = {**state['private'], 'insurance_user_id': insurance_user_id, 'credentials': {**creds_try, **base_creds}}
                    state = {'public': state['public'], 'private': new_private}
                except Exception:
                    return {'public': {'response': "Insurance login failed. Please check credentials.", 'requires_retry': True}, 'private': state['private']}
            else:
                return {'public': {'response': "Please log in to your insurance account first", 'requires_retry': True}, 'private': state['private']}

    try:
        response = requests.post(f"{MOCK_API_BASE_URL}/file_claim", json={"credentials": state['private']['credentials'], "user_id": state['private']['insurance_user_id']})
        response.raise_for_status()
        reference_id = response.json()['reference_id']
    except Exception as e:
        print("[ERROR] Failed to call mock API or parse response:", e)
        return {'public': {'response': "Internal error occurred."}, 'private': state['private']}

    pdf_url = generate_pdf({"ref_id": reference_id})

    send_email(
        to_email=None,
        subject="claim filed",
        body=f"claim filed",
        attachment_path=pdf_url,
        insurance_username=(
            state['private'].get('credentials', {}).get('insurance_username')
            or state['private'].get('credentials', {}).get('username')
        ),
        user_id=state['private'].get('session_user_id')
    )


    return {'public': {'response': f"Claim filed. Ref ID: {reference_id}"}, 'private': state['private']}

def handle_undefined_actionable(state: GraphState) -> GraphState:
    return {'public': {'response': "Unsupported action yet."}, 'private': state['private']}

# Conditions
def is_explanation(state: GraphState) -> bool:
    return state['public'].get('intent') == 'explanation'

def is_update_policy(state: GraphState) -> bool:
    return state['public'].get('intent') == 'update_policy'

def is_change_credentials(state: GraphState) -> bool:
    return state['public'].get('intent') == 'change_credentials'

def is_file_claim(state: GraphState) -> bool:
    return state['public'].get('intent') == 'file_claim'

def is_undefined_actionable(state: GraphState) -> bool:
    return state['public'].get('intent') == 'undefined_actionable'

def is_unknown(state: GraphState) -> bool:
    return state['public'].get('intent') == 'unknown'

workflow = StateGraph(GraphState)

workflow.add_node('classify_intent', classify_intent)
workflow.add_node('handle_explanation', handle_explanation)
workflow.add_node('handle_update_policy', handle_update_policy)
workflow.add_node('handle_change_credentials', handle_change_credentials)
workflow.add_node('handle_file_claim', handle_file_claim)
workflow.add_node('handle_undefined_actionable', handle_undefined_actionable)
workflow.add_node('handle_unknown', handle_unknown)

workflow.add_edge('__start__', 'classify_intent')
workflow.add_conditional_edges(
    'classify_intent',
    lambda s: s['public'].get('intent'),
    {
        'explanation': 'handle_explanation',
        'update_policy': 'handle_update_policy',
        'change_credentials': 'handle_change_credentials',
        'file_claim': 'handle_file_claim',
        'undefined_actionable': 'handle_undefined_actionable',
        'unknown': 'handle_unknown',
    }
)

workflow.add_edge('handle_explanation', '__end__')
workflow.add_edge('handle_update_policy', '__end__')
workflow.add_edge('handle_change_credentials', '__end__')
workflow.add_edge('handle_file_claim', '__end__')
workflow.add_edge('handle_undefined_actionable', '__end__')
workflow.add_edge('handle_unknown', '__end__')

graph = workflow.compile(checkpointer=memory)


def perform_insurance_login(username: str, password: str) -> tuple[str, dict]:
    """Log in to the mock insurance API and return (insurance_user_id, credentials_dict)."""
    resp = requests.post(
        f"{MOCK_API_BASE_URL}/login",
        json={"username": username, "password": password},
    )
    resp.raise_for_status()
    data = resp.json()
    user_id = data.get("user_id")
    if not user_id:
        raise ValueError("Login failed: user_id missing in response")
    creds = {
        "user_id": user_id,
        "username": username,
        "insurance_username": username,
        "token": "mock-token",
    }
    return user_id, creds

def run_graph_message(user_message: str, session_user_id: str, thread_id: str, *, insurance_username: str | None = None, insurance_old_password: str | None = None, insurance_new_password: str | None = None, insurance_user_id: str | None = None, credentials: dict | None = None) -> dict:
    """Run a single user message through the graph and return the final response string.

    This is a thin wrapper for API usage. It uses a default mock policy graph and
    empty insurance credentials. If your API authenticates the user with the
    insurance provider, pass those into the graph instead.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    
    # Use provided credentials or create default ones
    if credentials is None:
        credentials = {
            'insurance_username': insurance_username,
            'old_password': insurance_old_password,
            'new_password': insurance_new_password,
        }
    
    private_state = {
        'session_user_id': session_user_id,
        'insurance_user_id': insurance_user_id,
        'credentials': credentials,
        'policy_graph': {
            "entities": [
                {"type": "Policy", "attributes": {"policy_number": "MOCK_POLICY_001"}}
            ],
            "relations": []
        },
        'thread_id':thread_id
    }
    initial_state = {'public': {'user_message': user_message}, 'private': private_state}

    last_response = None
    last_public = None
    for state in graph.stream(initial_state, stream_mode="values", config=config):
        last_public = state.get('public') or last_public
        response = state['public'].get('response')
        if response:
            last_response = response
    requires_retry = False
    if isinstance(last_public, dict):
        requires_retry = bool(last_public.get('requires_retry'))
    return {"response": last_response or "", "requires_retry": requires_retry}

def login_user() -> tuple[str, dict]:
    username = input("Enter username: ")
    password = input("Enter password: ")
    try:
        user_id, creds = perform_insurance_login(username, password)
        print("[Bot]: Login successful.")
        return user_id, creds
    except Exception:
        print("Login failed. Try again.")
        return login_user()