import os
import requests

def test_agent_analysis():
    print("Executing Sprint 11 FVT: LangGraph Agent Analysis")
    
    # Send the latest voice note JSON through the agent
    target_json = "03_voice/voice_747701903_1772144416.json"
    
    payload = {
        "filepath": target_json
    }
    
    print(f"\nSubmitting request to http://localhost:8000/v1/agent/analyze for {target_json}")
    
    try:
        response = requests.post("http://localhost:8000/v1/agent/analyze", json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS: Agent Critique Received")
            print("=" * 50)
            print(data.get("heptatomo_critique"))
            print("=" * 50)
            return True
        else:
            print(f"\n❌ FAILED. Status Code: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API at http://localhost:8000")
        print("Please ensure the backend-engine container is running.")
        return False

if __name__ == "__main__":
    test_agent_analysis()
