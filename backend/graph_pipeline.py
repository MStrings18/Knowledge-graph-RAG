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

# Set API keys
def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("GROQ_API_KEY")
_set_env("LANGSMITH_API_KEY")

model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
db_path = "/Users/akshitagrawal/Knowledge-graph-RAG/langgraph_memory.db"
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

class GraphState(TypedDict, total=False):
    public: PublicState
    private: PrivateState

def sanitize_for_llm(state: GraphState) -> PublicState:
    return state['public'].copy()

def classify_intent(state: GraphState) -> GraphState:
    print("[classify_intent] Using LLM to classify intent...")
    user_message = sanitize_for_llm(state).get('user_message', '')

    prompt = f"""
    Classify the following user message into one of the categories: explanation, actionable, unknown.
    If actionable, supports ["update_policy", "change_credentials", "file_claim"].
    user message : {user_message}
    Output only: explanation, update_policy, change_credentials, file_claim, undefined_actionable, unknown.
    """

    llm_msg = model.invoke(prompt)
    intent = getattr(llm_msg, "content", llm_msg).strip().lower()
    print(intent)
    allowed = {"explanation","update_policy","change_credentials","file_claim","undefined_actionable","unknown"}
    if intent not in allowed:
        intent = "explanation"
    return {'public': {'intent': intent}}

def handle_unknown(state: GraphState) -> GraphState:
    return {'public': {'response': "Could not understand your request. Please explain more."}, 'private': state['private']}

def handle_explanation(state: GraphState) -> GraphState:
    explanation = "Mock explanation from RAG."
    return {'public': {'response': explanation}, 'private': state['private']}

MOCK_API_BASE_URL = "http://localhost:5000"

def handle_update_policy(state: GraphState) -> GraphState:
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
        to_email="",
        subject="Policy Updated Confirmation",
        body=f"Your policy {policy_number} was updated. Ref ID: {reference_id}",
        attachment_path=pdf_url
    )


    return {
        'public': {**state['public'], 'response': f"Policy updated successfully. Ref ID: {reference_id}"},
        'private': state['private']
    }


def handle_change_credentials(state: GraphState) -> GraphState:
    print("[handle_change_credentials] Please provide username, old password, new password.")

    username = input("Enter username: ")
    old_password = input("Enter old password: ")
    new_password = input("Enter new password: ")

    try:
        response = requests.post(f"{MOCK_API_BASE_URL}/change_credentials", json={
            "user_id": state['private']['insurance_user_id'],
            "username": username,
            "old_password": old_password,
            "new_password": new_password
        })
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
        to_email="",
        subject="Credentials Updated Confirmation",
        body=f"your password was updated",
        attachment_path=pdf_url
    )


    return {
        'public': {**state['public'], 'response': f"Credentials changed successfully. Ref ID: {reference_id}"},
        'private': state['private']
    }


def handle_file_claim(state: GraphState) -> GraphState:
    creds = state['private'].get('credentials')
    if not creds.get('user_id'):
        return {'public': {'response': "Please log in first.", 'requires_retry': True}, 'private': state['private']}

    try:
        response = requests.post(f"{MOCK_API_BASE_URL}/file_claim", json={"credentials": creds, "user_id": state['private']['insurance_user_id']})
        response.raise_for_status()
        reference_id = response.json()['reference_id']
    except Exception as e:
        print("[ERROR] Failed to call mock API or parse response:", e)
        return {'public': {'response': "Internal error occurred."}, 'private': state['private']}

    pdf_url = generate_pdf({"ref_id": reference_id})

    send_email(
        to_email="user@example.com",
        subject="claim filed",
        body=f"claim filed",
        attachment_path=pdf_url
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


def login_user() -> tuple[str, dict]:
    username = input("Enter username: ")
    password = input("Enter password: ")
    resp = requests.post(f"{MOCK_API_BASE_URL}/login", json={"username": username, "password": password}).json()
    if resp.get("success"):
        print("[Bot]: Login successful.")
        return resp["user_id"], {"user_id": resp["user_id"], "username": username, "token": "mock-token"}
    else:
        print("Login failed. Try again.")
        return login_user()

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "123"}}

    session_user_id = str(uuid4())
    thread_id = str(uuid4())
    db_session.add_user(session_user_id, name="Anonymous", email=f"{session_user_id}@example.com")
    document_path = "/path/to/document.pdf"
    db_session.add_thread(thread_id, session_user_id, document_path, "started")

    # Keep track of insurance login for this session
    insurance_user_id = None
    credentials = {}

    while True:
        user_input = input("Enter your message (or 'quit'): ")
        if user_input.lower() in ["quit", "exit"]:
            db_session.update_status(thread_id, "completed")
            break

        db_session.add_message(thread_id, "user", user_input)

        # Detect if actionable intent
        actionable_intent_detected = any(kw in user_input.lower() for kw in ["update", "change", "claim"])

        # Prompt for login only if we don’t already have insurance credentials
        if actionable_intent_detected and not insurance_user_id:
            print("[Bot]: Please login to your insurance account first.")
            insurance_user_id, credentials = login_user()

        private_state = {
            'session_user_id': session_user_id,
            'insurance_user_id': insurance_user_id,
            'credentials': credentials,
            'policy_graph': {"entities": [{"type": "Policy", "attributes": {"policy_number": "MOCK_POLICY_001"}}], "relations": []}
        }

        initial_state = {'public': {'user_message': user_input}, 'private': private_state}

        print("\n[Bot Response]:")
        for state in graph.stream(initial_state, stream_mode="values", config=config):
            response = state['public'].get('response')
            if response:
                print(response)
                db_session.add_message(thread_id, "bot", response)

        print("="*50)
