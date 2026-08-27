import requests
import json

BASE_URL = "http://127.0.0.1:8000"

history_step1 = [
    {"role": "user", "content": "I would like to start the step-by-step guided setup"},
    {"role": "assistant", "content": "Wonderful! I will guide you step-by-step through our simple steps so we can arrange transport and lock in your price. Let's begin with Step 1: May I know the name of your departed loved one?"}
]

history_step2 = [
    {"role": "user", "content": "I would like to start the step-by-step guided setup"},
    {"role": "assistant", "content": "Wonderful! I will guide you step-by-step through our simple steps so we can arrange transport and lock in your price. Let's begin with Step 1: May I know the name of your departed loved one?"},
    {"role": "user", "content": "Tan Ah Kow"},
    {"role": "assistant", "content": "Thank you. May I know your departed loved one's Date of Birth (DOB)?"}
]

test_cases = [
    ("Step 1: Beating around the bush on Name", history_step1, "Why do you need his legal name? Is it compulsory? Can't we just call him John Doe?"),
    ("Step 1: Hesitation / Uncertainty on Name", history_step1, "I'm not sure of his legal spelling on the IC. Can I give a nickname first?"),
    ("Step 2: Missing IC / Beating around the bush on DOB", history_step2, "We dont have his IC card right now so I am not 100% sure of the exact date"),
    ("Step 2: Asking if DOB is compulsory", history_step2, "Is date of birth mandatory just to get a price quote?")
]

for title, hist, msg in test_cases:
    print("=" * 60)
    print(f"CASE: {title}")
    print(f"USER MESSAGE: \"{msg}\"")
    resp = requests.post(f"{BASE_URL}/api/chat", json={"message": msg, "history": hist}, timeout=60)
    data = resp.json()
    print(f"REPLY:\n{data.get('response')}\n")
    print(f"UPDATES COMMITTED: {data.get('updates')}")
