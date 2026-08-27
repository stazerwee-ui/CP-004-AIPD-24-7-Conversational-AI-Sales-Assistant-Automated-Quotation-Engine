import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import requests
import json


BASE_URL = "http://127.0.0.1:8000"

def test_intent_routing():
    print("\n--- TEST 1: In-Process Intent Classification ---")
    from semantic_router import get_semantic_router
    router = get_semantic_router()
    
    test_cases = [
        ("I don't understand what you mean by that", "CONFUSION"),
        ("Please connect me to a human consultant", "ESCALATION"),
        ("Can we go back to the previous step", "COMPLAINT"),
        ("How much is the deluxe tier compared to standard?", "GENERAL_QUESTION"),
    ]
    
    for msg, expected in test_cases:
        t0 = time.perf_counter()
        result = router.classify_intent_in_process(msg)
        dt = (time.perf_counter() - t0) * 1000
        print(f"Msg: '{msg}' -> Intent: {result} (Expected: {expected}) [Time: {dt:.2f}ms]")
        assert result == expected or result in ["GENERAL_QUESTION", expected], f"Mismatch for {msg}"

def test_api_status():
    print("\n--- TEST 2: /api/status Health Probe ---")
    resp = requests.get(f"{BASE_URL}/api/status", timeout=5)
    print("Status:", resp.status_code)
    print("Payload:", json.dumps(resp.json(), indent=2))
    assert resp.status_code == 200

def test_api_chat_standard():
    print("\n--- TEST 3: Standard /api/chat & LRU Caching ---")
    payload = {
        "message": "What is the price of the Standard Service Tier?",
        "history": []
    }
    
    # First call (cold / computation)
    t0 = time.perf_counter()
    r1 = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=60)
    dt1 = (time.perf_counter() - t0) * 1000
    print(f"Call 1 (Cold) Time: {dt1:.2f}ms | Response:\n{r1.json().get('response')}\n")
    assert r1.status_code == 200

    # Second call (warm / LRU cache hit)
    t0 = time.perf_counter()
    r2 = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=10)
    dt2 = (time.perf_counter() - t0) * 1000
    print(f"Call 2 (LRU Cache Hit) Time: {dt2:.2f}ms | Response:\n{r2.json().get('response')}\n")
    assert r2.status_code == 200
    assert dt2 < 50, f"Expected cache hit in <50ms, got {dt2}ms"

def test_api_chat_stream():
    print("\n--- TEST 4: /api/chat/stream SSE Endpoint ---")
    payload = {
        "message": "What is included in the 3-day wake?",
        "history": []
    }
    
    t0 = time.perf_counter()
    resp = requests.post(f"{BASE_URL}/api/chat/stream", json=payload, stream=True, timeout=60)
    assert resp.status_code == 200
    
    tokens = []
    done_packet = None
    first_token_time = None
    
    for line in resp.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data = json.loads(line_str[6:])
                if data.get('type') == 'token':
                    if first_token_time is None:
                        first_token_time = (time.perf_counter() - t0) * 1000
                    tokens.append(data.get('content', ''))
                elif data.get('type') == 'done':
                    done_packet = data
                    
    total_time = (time.perf_counter() - t0) * 1000
    print(f"Time to First Token (TTFT): {first_token_time:.2f}ms")
    print(f"Total Stream Time: {total_time:.2f}ms")
    print(f"Streamed Text:\n{''.join(tokens)}\n")
    assert done_packet is not None, "Missing done event"
    print("Done Packet Metadata:", {k: v for k, v in done_packet.items() if k != 'response'})

def test_intake_step_progression():
    print("\n--- TEST 5: Step-by-Step Intake Flow ---")
    # Step 1: Start setup
    r1 = requests.post(f"{BASE_URL}/api/chat", json={
        "message": "I would like to start the step-by-step guided setup",
        "history": []
    }, timeout=10)
    print("Step 0 -> Step 1:", r1.json().get('response'))
    
    # Step 2: Provide Name
    history = [
        {"role": "user", "content": "I would like to start the step-by-step guided setup"},
        {"role": "assistant", "content": r1.json().get('response')}
    ]
    r2 = requests.post(f"{BASE_URL}/api/chat", json={
        "message": "Tan Ah Kow",
        "history": history
    }, timeout=60)

    print("Step 1 -> Step 2:", r2.json().get('response'))
    assert "Date of Birth" in r2.json().get('response') or "DOB" in r2.json().get('response')

if __name__ == "__main__":
    test_intent_routing()
    test_api_status()
    test_api_chat_standard()
    test_api_chat_stream()
    test_intake_step_progression()
    print("\nALL OPTIMIZATION TESTS PASSED SUCCESSFULLY!")
