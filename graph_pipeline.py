
import sqlite3
from typing_extensions import TypedDict
from typing import Tuple

# LangGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph
# Optional: LangChain integration
from langchain_groq import ChatGroq

import os, getpass

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("GROQ_API_KEY")
_set_env("LANGSMITH_API_KEY")

# --- Model Setup ---
model = ChatGroq(
    model = "llama-3.3-70b-versatile", 
    temperature=0
)

# --- Database store and connection with sqlite ---
db_path = "/Users/akshitagrawal/Knowledge-graph-RAG/langgraph_memory.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
memory = SqliteSaver(conn)

# --- State Schemas --
class PublicState(TypedDict, total=False):
    user_message: str
    intent: str
    response: str
    requires_retry: bool

class PrivateState(TypedDict, total=False):
    user_id: str
    credentials: dict
    policy_data: dict

# --- Graph Definition ---
class GraphState(TypedDict, total=False):
    public: PublicState
    private: PrivateState

# --- State Sanitizer for LLMs ---
def sanitize_for_llm(state: GraphState) -> PublicState:
    # Only pass public state to LLMs, never private
    return state['public'].copy()

# --- Intent Classification Node ---
def classify_intent(state: GraphState) -> GraphState:
    print("[classify_intent] Using LLM to classify intent...")
    user_message = sanitize_for_llm(state).get('user_message', '')

    prompt = f"""
    Classify the following user message into one of the categories: explanation, actionable, unknown.
    If actionable, our product only supports ["update_policy", "change_credentials", "file_claim"].
    If not one of these, return "undefined_actionable".

    Message: "{user_message}"

    Output only: explanation, update_policy, change_credentials, file_claim, undefined_actionable, unknown.
    """

    llm_msg = model.invoke(prompt)
    intent = getattr(llm_msg, "content", llm_msg)
    intent = (intent or "").strip().lower()

    allowed = {"explanation","update_policy","change_credentials","file_claim","undefined_actionable","unknown"}
    if intent not in allowed:
        intent = "explanation"

    return {'public': {'intent': intent}}


# --- Unknown Intent Handler ---
def handle_unknown(state: GraphState) -> GraphState:
    print("[handle_unknown] Asking user to clarify intent...")
    prompt = "Sorry, I couldn't understand your request. Please type your question or explain what you want in more detail."
    return {
        'public': {**state['public'], 'response': prompt, 'requires_retry': True},
        'private': state['private']
    }

# --- Explanation Handler (RAG pipeline) ---
def handle_explanation(state: GraphState) -> GraphState:
    print("[handle_explanation] Passing to RAG pipeline (external)")
    explanation = "RAG pipeline would return a detailed explanation here."
    return {
        'public': {**state['public'], 'response': explanation},
        'private': state['private']
    }

# --- Actionable Handlers (API nodes) ---
def handle_update_policy(state: GraphState) -> GraphState:
    print("[handle_update_policy] Updating insurance policy...")
    # Here you would use private['credentials'], private['policy_data'], etc.
    # result = call_insurance_api(private['credentials'], private['policy_data'])
    result = "Your insurance policy has been successfully updated."
    return {
        'public': {**state['public'], 'response': result},
        'private': state['private']
    }

def handle_change_credentials(state: GraphState) -> GraphState:
    print("[handle_change_credentials] Changing credentials...")
    # result = call_change_credentials(private['credentials'])
    result = "Your credentials have been successfully changed."
    return {
        'public': {**state['public'], 'response': result},
        'private': state['private']
    }

def handle_file_claim(state: GraphState) -> GraphState:
    print("[handle_file_claim] Filing a new claim...")
    # result = call_file_claim(private['credentials'], private['policy_data'])
    result = "Your claim has been successfully registered."
    return {
        'public': {**state['public'], 'response': result},
        'private': state['private']
    }

def handle_undefined_actionable(state: GraphState) -> GraphState:
    print("[handle_undefined_actionable] Prompting user to clarify request...")
    message = "Sorry, I don’t have an automated action for that yet. Could you please rephrase your request or explain what you want in more detail?"
    return {
        'public': {**state['public'], 'response': message, 'requires_retry': True},
        'private': state['private']
    }

# --- Conditional Logic Helpers ---
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



if __name__ == "__main__":
    
    config = {"configurable": {"thread_id": "123"}}
    while True:
        user_input = input("Enter your message (or 'quit' to exit): ")
        if user_input.lower() in ["quit", "exit"]:
            break

        initial_state = {
            'public': {'user_message': user_input},
            'private': {'user_id': 'user_123', 'credentials': {}, 'policy_data': {}}
        }

        print("\n[Bot Response]:")
        for state in graph.stream(initial_state, stream_mode="values", config=config):  # stream returns a generator
            response = state['public'].get('response')
            if response:
                print(response)  # you can print partial or final responses
        print("="*50)

