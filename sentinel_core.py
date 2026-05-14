import os
import time
from typing import TypedDict
from langgraph.graph import StateGraph, END
from google import genai
from github import Github, Auth

# --- 1. CONFIGURATION ---
REPO_NAME = "Mbongisenithato/Sentinel-A2A-Agent-Plus" 
MODEL_ID = 'gemini-3.1-flash-lite'
GITHUB_TOKEN = "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"

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
auth = Auth.Token(GITHUB_TOKEN)
gh_client = Github(auth=auth)

class AgentState(TypedDict):
    code_snippet: str
    findings: str
    action_required: bool
    issue_url: str

# --- 2. RESILIENT AI CALL ---
def call_gemini(prompt, retries=5):
    for i in range(retries):
        try:
            response = client.models.generate_content(model=MODEL_ID, contents=prompt)
            return response.text
        except Exception as e:
            if "503" in str(e) or "busy" in str(e).lower():
                wait = 2**(i+1)
                print(f"⚠️ Gemini servers busy. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise e
    return "Error: AI unavailable."

# --- 3. AUDIT NODE ---
def security_architect(state: AgentState):
    print(f"🛰️ Sentinel-A2A: Querying {MODEL_ID} for Audit...")
    findings = call_gemini(f"Audit this code for vulnerabilities: {state['code_snippet']}")
    
    # Decision check
    decision = call_gemini(f"Is there a critical leak or vulnerability here? Answer only 'yes' or 'no': {findings}")
    
    return {
        "findings": findings, 
        "action_required": "yes" in decision.lower()
    }

# --- 4. REMEDIATION NODE ---
def github_remediator(state: AgentState):
    if not state["action_required"]:
        # If no leak is found, the agent stops here
        return {"issue_url": "Secure: No action required."}
    
    print(f"🛠️ Sentinel-A2A: Critical vulnerability found. Posting to {REPO_NAME}...")
    try:
        repo = gh_client.get_repo(REPO_NAME)
        issue = repo.create_issue(
            title="🚨 Sentinel-A2A: Automated Security Alert",
            body=f"## AI Security Audit Report\n\n{state['findings']}"
        )
        return {"issue_url": issue.html_url}
    except Exception as e:
        return {"issue_url": f"GitHub Error: {str(e)}"}

# --- 5. WORKFLOW ---
workflow = StateGraph(AgentState)
workflow.add_node("audit", security_architect)
workflow.add_node("remediate", github_remediator)
workflow.set_entry_point("audit")
workflow.add_conditional_edges("audit", lambda x: "remediate" if x["action_required"] else END)
workflow.add_edge("remediate", END)
sentinel_app = workflow.compile()

# --- 6. EXECUTION ---
if __name__ == "__main__":
    # --- TEST PAYLOAD: SAFE CODE ---
    # This code has no secrets. The agent should NOT create an issue.
    test_code = """
def calculate_area(radius):
    \"\"\"Calculates the area of a circle. Safe function.\"\"\"
    import math
    return math.pi * (radius ** 2)
"""
    
    print("--- Sentinel-A2A: Running Safe Code Test ---")
    try:
        result = sentinel_app.invoke({"code_snippet": test_code})
        print(f"\n✅ AUDIT COMPLETE")
        print(f"🔗 Outcome: {result.get('issue_url')}")
    except Exception as e:
        print(f"❌ Error: {e}")