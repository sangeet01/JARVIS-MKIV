#!/usr/bin/env python3
"""
JARVIS-MKIII — Personality Test Suite
Tests that JARVIS correctly identifies as built by Khalid, not Tony Stark.
"""

import httpx
import sys
import time

BASE_URL = "http://localhost:8000"
SESSION_ID = f"personality-test-{int(time.time())}"

PROMPTS = [
    "Who made you?",
    "Who are you?",
    "What is your purpose?",
    "Who is Khalid?",
    "What are you running on?",
    "Give me a system status.",
]

PASS_REQUIRES  = ["Khalid", "sir"]
FAIL_TRIGGERS  = ["Tony Stark", "Iron Man"]


def check_health() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def send_prompt(prompt: str) -> str:
    r = httpx.post(
        f"{BASE_URL}/chat",
        json={"prompt": prompt, "session_id": SESSION_ID},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["response"]


def grade(response: str) -> bool:
    has_pass  = any(p in response for p in PASS_REQUIRES)
    has_fail  = any(f in response for f in FAIL_TRIGGERS)
    return has_pass and not has_fail


def main():
    print("=" * 60)
    print("  JARVIS-MKIII — Personality Test Suite")
    print("=" * 60)

    # ── Health check ──────────────────────────────────────────────
    print("\nChecking backend at http://localhost:8000/health ...")
    retries = 0
    while not check_health():
        retries += 1
        if retries > 6:
            print("  FATAL: Backend not reachable after 30s. Start it with:")
            print("    systemctl --user start jarvis-backend")
            sys.exit(1)
        print(f"  Not ready, retrying in 5s... ({retries}/6)")
        time.sleep(5)
    print("  Backend is up.\n")

    # ── Run prompts ───────────────────────────────────────────────
    results = []
    for i, prompt in enumerate(PROMPTS, 1):
        print(f"[{i}/6] PROMPT: {prompt}")
        try:
            response = send_prompt(prompt)
        except Exception as e:
            response = f"[ERROR: {e}]"
        print(f"       RESPONSE: {response}")
        passed = grade(response)
        label = "PASS" if passed else "FAIL"
        print(f"       GRADE: {label}")
        if not passed:
            has_fail = [f for f in FAIL_TRIGGERS if f in response]
            has_pass = [p for p in PASS_REQUIRES if p in response]
            if has_fail:
                print(f"         -> FAIL: contains forbidden phrase(s): {has_fail}")
            if not has_pass:
                print(f"         -> FAIL: missing required phrase(s): {PASS_REQUIRES}")
        print()
        results.append(passed)

    # ── Score ─────────────────────────────────────────────────────
    score = sum(results)
    print("=" * 60)
    print(f"  FINAL SCORE: {score}/6")
    if score == 6:
        print("  All tests passed. Identity anchor is holding.")
    elif score >= 4:
        print("  Mostly passing. Check failed prompts above.")
    else:
        print("  Multiple failures. Personality injection needs review.")
    print("=" * 60)

    sys.exit(0 if score == 6 else 1)


if __name__ == "__main__":
    main()
