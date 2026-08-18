#!/usr/bin/env python3
"""
Backend test suite for SOA conversational assistant endpoints.
Tests POST /api/conversation/start, /turn, GET /api/conversation/{id}
with focus on SOA-ID gating, anonymous mode, and audit integrity.
"""
import os
import sys
import time
import requests
from pathlib import Path

# Read backend URL from frontend/.env
env_path = Path(__file__).parent / "frontend" / ".env"
BACKEND_URL = None
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BACKEND_URL = line.split("=", 1)[1].strip()
                break

if not BACKEND_URL:
    print("❌ REACT_APP_BACKEND_URL not found in frontend/.env")
    sys.exit(1)

API_BASE = f"{BACKEND_URL}/api"
print(f"🔗 Testing against: {API_BASE}\n")

# Test counters
passed = 0
failed = 0
test_results = []


def test(name: str, fn):
    """Run a test and track results."""
    global passed, failed
    try:
        print(f"▶ {name}")
        fn()
        passed += 1
        test_results.append(f"✅ {name}")
        print(f"  ✅ PASSED\n")
    except AssertionError as e:
        failed += 1
        test_results.append(f"❌ {name}: {e}")
        print(f"  ❌ FAILED: {e}\n")
    except Exception as e:
        failed += 1
        test_results.append(f"❌ {name}: {type(e).__name__}: {e}")
        print(f"  ❌ ERROR: {type(e).__name__}: {e}\n")


def assert_eq(actual, expected, msg=""):
    """Assert equality with helpful message."""
    if actual != expected:
        raise AssertionError(f"{msg}: expected {expected!r}, got {actual!r}")


def assert_in(needle, haystack, msg=""):
    """Assert substring presence."""
    if needle not in haystack:
        raise AssertionError(f"{msg}: {needle!r} not in {haystack!r}")


def assert_true(condition, msg=""):
    """Assert condition is true."""
    if not condition:
        raise AssertionError(msg or "Condition was false")


def assert_false(condition, msg=""):
    """Assert condition is false."""
    if condition:
        raise AssertionError(msg or "Condition was true")


# ============================================================================
# SCENARIO A: NON-ANONYMOUS certificate + SOA-ID gating
# ============================================================================
def test_scenario_a_non_anonymous_certificate_soa_gating():
    """Non-anonymous certificate request must collect SOA ID before finalizing."""
    print("  📋 Starting non-anonymous conversation...")
    
    # Start conversation
    resp = requests.post(f"{API_BASE}/conversation/start", json={
        "anonymous": False,
        "requester": "Test Student"
    }, timeout=30)
    assert_eq(resp.status_code, 200, "start status")
    data = resp.json()
    
    session_id = data.get("id")
    assert_true(session_id, "session_id must be present")
    assert_true(session_id.startswith("CONV-"), f"session_id format: {session_id}")
    
    # Check greeting message
    messages = data.get("messages", [])
    assert_eq(len(messages), 1, "initial messages count")
    assert_eq(messages[0].get("role"), "agent", "first message role")
    
    # Check audioBase64 is present and non-empty (Deepgram TTS)
    audio_b64 = data.get("audioBase64")
    assert_true(audio_b64, "audioBase64 must be present")
    assert_true(len(audio_b64) > 100, f"audioBase64 should be substantial, got {len(audio_b64)} chars")
    print(f"  ✓ Session {session_id} started with greeting audio ({len(audio_b64)} chars)")
    
    # Turn 1: Request certificate without SOA ID
    print("  📋 Turn 1: Request certificate without SOA ID...")
    time.sleep(1)  # Brief pause between turns
    
    form_data = {
        "sessionId": session_id,
        "text": "I need a bonafide certificate for my bank loan",
        "speak": "false"  # Skip TTS to speed up testing
    }
    resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
    assert_eq(resp.status_code, 200, "turn 1 status")
    turn1 = resp.json()
    
    # Assistant must NOT finalize yet and must ask for SOA ID
    assert_false(turn1.get("done"), "done should be false (no SOA ID yet)")
    assert_eq(turn1.get("requestId"), None, "requestId should be null (not finalized)")
    
    reply1 = turn1.get("reply", "").lower()
    assert_true("soa" in reply1 or "id" in reply1, f"Reply should ask for SOA ID, got: {turn1.get('reply')}")
    print(f"  ✓ Turn 1: done=false, requestId=null, reply asks for SOA ID")
    
    # Turn 2: Provide complete information (SOA ID, deadline, format)
    print("  📋 Turn 2: Provide complete information...")
    time.sleep(2)  # LLM call takes time
    
    form_data = {
        "sessionId": session_id,
        "text": "My SOA ID is 2214-CSE-031 and I need it by Friday in digital format",
        "speak": "false"
    }
    resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
    assert_eq(resp.status_code, 200, "turn 2 status")
    turn2 = resp.json()
    
    # Should finalize now with complete info, or need at most one confirmation
    max_turns = 4  # Allow up to turn 4
    current_turn = 2
    done = turn2.get("done")
    request_id = turn2.get("requestId")
    soa_id = turn2.get("soaId")
    
    while not done and current_turn < max_turns:
        current_turn += 1
        print(f"  📋 Turn {current_turn}: Confirm...")
        time.sleep(2)
        
        form_data = {
            "sessionId": session_id,
            "text": "yes please proceed and file it",
            "speak": "false"
        }
        resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
        assert_eq(resp.status_code, 200, f"turn {current_turn} status")
        turn_data = resp.json()
        
        done = turn_data.get("done")
        request_id = turn_data.get("requestId")
        soa_id = turn_data.get("soaId")
        
        if done:
            print(f"  ✓ Turn {current_turn}: Conversation finalized")
            break
    
    assert_true(done, f"Conversation should finalize within {max_turns} turns with complete info")
    assert_true(request_id, "requestId must be set when done")
    assert_eq(soa_id, "2214-CSE-031", "soaId should be captured")
    
    assert_true(request_id, "requestId must be set when done")
    assert_true(request_id.startswith("REQ-"), f"requestId format: {request_id}")
    assert_eq(soa_id, "2214-CSE-031", "soaId should be captured")
    print(f"  ✓ Conversation finalized: requestId={request_id}, soaId={soa_id}")
    
    # Verify the created request
    print(f"  📋 Verifying request {request_id}...")
    resp = requests.get(f"{API_BASE}/requests/{request_id}", timeout=30)
    assert_eq(resp.status_code, 200, "get request status")
    req = resp.json()
    
    assert_eq(req.get("type"), "certificate", "request type")
    assert_eq(req.get("status"), "awaiting_approval", "request status")
    assert_eq(req.get("soaId"), "2214-CSE-031", "request soaId field")
    print(f"  ✓ Request verified: type=certificate, status=awaiting_approval, soaId=2214-CSE-031")


# ============================================================================
# SCENARIO B: DETERMINISTIC GUARD - non-anonymous must have SOA ID
# ============================================================================
def test_scenario_b_deterministic_guard():
    """Non-anonymous conversation can NEVER reach done=true without SOA ID."""
    print("  📋 Starting non-anonymous conversation without SOA ID...")
    
    # Start conversation
    resp = requests.post(f"{API_BASE}/conversation/start", json={
        "anonymous": False,
        "requester": "Guard Test Student"
    }, timeout=30)
    assert_eq(resp.status_code, 200, "start status")
    session_id = resp.json().get("id")
    
    # Turn 1: Vague request without SOA ID
    print("  📋 Turn 1: Vague maintenance request...")
    time.sleep(1)
    
    form_data = {
        "sessionId": session_id,
        "text": "The AC in my room is not working properly",
        "speak": "false"
    }
    resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
    assert_eq(resp.status_code, 200, "turn 1 status")
    turn1 = resp.json()
    
    assert_false(turn1.get("done"), "done must be false without SOA ID")
    assert_eq(turn1.get("requestId"), None, "requestId must be null")
    print(f"  ✓ Turn 1: done=false, requestId=null")
    
    # Turn 2: More details but still no SOA ID
    print("  📋 Turn 2: Add details but no SOA ID...")
    time.sleep(2)
    
    form_data = {
        "sessionId": session_id,
        "text": "It's in Room 204 and has been broken since yesterday",
        "speak": "false"
    }
    resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
    assert_eq(resp.status_code, 200, "turn 2 status")
    turn2 = resp.json()
    
    # Must still not be done
    assert_false(turn2.get("done"), "done must still be false without SOA ID")
    assert_eq(turn2.get("requestId"), None, "requestId must still be null")
    
    # Reply should ask for SOA ID
    reply2 = turn2.get("reply", "").lower()
    assert_true("soa" in reply2 or "id" in reply2, f"Reply should ask for SOA ID, got: {turn2.get('reply')}")
    print(f"  ✓ Turn 2: done=false, requestId=null, asks for SOA ID")
    print(f"  ✓ GUARD VERIFIED: Non-anonymous conversation cannot finalize without SOA ID")


# ============================================================================
# SCENARIO C: ANONYMOUS grievance - never asks for SOA ID
# ============================================================================
def test_scenario_c_anonymous_grievance():
    """Anonymous grievance must NEVER ask for SOA ID."""
    print("  📋 Starting anonymous conversation...")
    
    # Start conversation
    resp = requests.post(f"{API_BASE}/conversation/start", json={
        "anonymous": True,
        "requester": "Anonymous Student"
    }, timeout=30)
    assert_eq(resp.status_code, 200, "start status")
    data = resp.json()
    
    session_id = data.get("id")
    assert_true(session_id, "session_id must be present")
    
    # Check greeting mentions anonymous mode
    greeting = data.get("messages", [{}])[0].get("content", "")
    assert_in("anonymous", greeting.lower(), "greeting should mention anonymous mode")
    print(f"  ✓ Session {session_id} started in anonymous mode")
    
    # Turn 1: Report grievance
    print("  📋 Turn 1: Report ragging grievance...")
    time.sleep(1)
    
    form_data = {
        "sessionId": session_id,
        "text": "I want to report repeated ragging in Hostel Block D after 10pm, I am scared",
        "speak": "false"
    }
    resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
    assert_eq(resp.status_code, 200, "turn 1 status")
    turn1 = resp.json()
    
    reply1 = turn1.get("reply", "").lower()
    # Must NEVER ask for SOA ID
    assert_false("soa" in reply1 and "id" in reply1, f"Anonymous mode must NOT ask for SOA ID, got: {turn1.get('reply')}")
    print(f"  ✓ Turn 1: Reply does NOT ask for SOA ID (anonymous mode)")
    
    # Continue until done (may need clarifying details)
    max_turns = 5
    current_turn = 1
    done = turn1.get("done")
    request_id = turn1.get("requestId")
    
    while not done and current_turn < max_turns:
        current_turn += 1
        print(f"  📋 Turn {current_turn}: Provide additional details...")
        time.sleep(2)
        
        # Provide clarifying details
        form_data = {
            "sessionId": session_id,
            "text": "It happens every night around 11pm in the common room. Multiple seniors are involved.",
            "speak": "false"
        }
        resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
        assert_eq(resp.status_code, 200, f"turn {current_turn} status")
        turn_data = resp.json()
        
        # Check reply never asks for SOA ID
        reply = turn_data.get("reply", "").lower()
        assert_false("soa" in reply and "id" in reply, f"Turn {current_turn}: Anonymous mode must NOT ask for SOA ID")
        
        done = turn_data.get("done")
        request_id = turn_data.get("requestId")
        
        if done:
            print(f"  ✓ Turn {current_turn}: Conversation finalized")
            break
    
    assert_true(done, f"Conversation should finalize within {max_turns} turns")
    assert_true(request_id, "requestId must be set when done")
    print(f"  ✓ Finalized: requestId={request_id}")
    
    # Verify the created grievance
    print(f"  📋 Verifying grievance {request_id}...")
    resp = requests.get(f"{API_BASE}/requests/{request_id}", timeout=30)
    assert_eq(resp.status_code, 200, "get request status")
    req = resp.json()
    
    assert_eq(req.get("type"), "grievance", "request type")
    assert_eq(req.get("anonymous"), True, "request anonymous flag")
    assert_true(req.get("pseudonym"), "pseudonym must be set")
    assert_eq(req.get("soaId"), None, "soaId must be null for anonymous")
    print(f"  ✓ Grievance verified: anonymous=true, pseudonym={req.get('pseudonym')}, soaId=null")


# ============================================================================
# SCENARIO D: ERROR CASES
# ============================================================================
def test_scenario_d_error_unknown_session():
    """Turn with unknown sessionId should return 404."""
    print("  📋 Testing unknown sessionId...")
    
    form_data = {
        "sessionId": "CONV-UNKNOWN",
        "text": "test message",
        "speak": "false"
    }
    resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=30)
    assert_eq(resp.status_code, 404, "should return 404 for unknown session")
    print(f"  ✓ Unknown sessionId correctly returns 404")


def test_scenario_d_error_no_input():
    """Turn with neither text nor audio should return 400."""
    print("  📋 Testing turn with no input...")
    
    # Start a session first
    resp = requests.post(f"{API_BASE}/conversation/start", json={
        "anonymous": False,
        "requester": "Error Test"
    }, timeout=30)
    session_id = resp.json().get("id")
    
    # Send turn with no text or audio
    form_data = {
        "sessionId": session_id,
        "speak": "false"
    }
    resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=30)
    assert_eq(resp.status_code, 400, "should return 400 for no input")
    print(f"  ✓ No input correctly returns 400")


def test_scenario_d_error_completed_session():
    """Turn on already-completed session should return 409."""
    print("  📋 Testing turn on completed session...")
    
    # Start and complete a quick conversation with complete info
    resp = requests.post(f"{API_BASE}/conversation/start", json={
        "anonymous": True,
        "requester": "Completion Test"
    }, timeout=30)
    session_id = resp.json().get("id")
    
    # Provide complete maintenance info upfront
    time.sleep(1)
    form_data = {
        "sessionId": session_id,
        "text": "The AC is leaking water in Lab 201 in Building A, I noticed it this morning and it needs immediate repair",
        "speak": "false"
    }
    resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
    turn1 = resp.json()
    
    # Continue until done (should be quick with complete info)
    max_turns = 3
    current_turn = 1
    done = turn1.get("done")
    
    while not done and current_turn < max_turns:
        current_turn += 1
        time.sleep(2)
        form_data = {
            "sessionId": session_id,
            "text": "yes please file it now",
            "speak": "false"
        }
        resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
        turn_data = resp.json()
        done = turn_data.get("done")
        
        if done:
            break
    
    assert_true(done, f"conversation should complete within {max_turns} turns with complete info")
    
    # Now try another turn on the completed session
    time.sleep(1)
    form_data = {
        "sessionId": session_id,
        "text": "another message",
        "speak": "false"
    }
    resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=30)
    assert_eq(resp.status_code, 409, "should return 409 for completed session")
    print(f"  ✓ Completed session correctly returns 409")


def test_scenario_d_get_conversation():
    """GET /api/conversation/{id} should return conversation details."""
    print("  📋 Testing GET conversation...")
    
    # Start a session
    resp = requests.post(f"{API_BASE}/conversation/start", json={
        "anonymous": False,
        "requester": "GET Test"
    }, timeout=30)
    session_id = resp.json().get("id")
    
    # GET the conversation
    resp = requests.get(f"{API_BASE}/conversation/{session_id}", timeout=30)
    assert_eq(resp.status_code, 200, "GET conversation status")
    data = resp.json()
    
    assert_eq(data.get("id"), session_id, "conversation id")
    assert_eq(data.get("status"), "active", "conversation status")
    assert_true(len(data.get("messages", [])) >= 1, "messages should be present")
    print(f"  ✓ GET conversation returns correct data")


# ============================================================================
# SCENARIO E: AUDIT INTEGRITY
# ============================================================================
def test_scenario_e_audit_integrity():
    """After conversation finalizes a request, audit chain must verify."""
    print("  📋 Testing audit integrity after conversation...")
    
    # Start and complete a conversation with complete info
    resp = requests.post(f"{API_BASE}/conversation/start", json={
        "anonymous": True,
        "requester": "Audit Test"
    }, timeout=30)
    session_id = resp.json().get("id")
    
    # Provide complete maintenance info
    time.sleep(1)
    form_data = {
        "sessionId": session_id,
        "text": "The projector is not working in Room 305 in the Engineering Block, I noticed it this morning during class",
        "speak": "false"
    }
    resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
    turn1 = resp.json()
    
    # Continue until done
    max_turns = 3
    current_turn = 1
    done = turn1.get("done")
    request_id = turn1.get("requestId")
    
    while not done and current_turn < max_turns:
        current_turn += 1
        time.sleep(2)
        form_data = {
            "sessionId": session_id,
            "text": "yes please file it",
            "speak": "false"
        }
        resp = requests.post(f"{API_BASE}/conversation/turn", data=form_data, timeout=90)
        turn_data = resp.json()
        done = turn_data.get("done")
        request_id = turn_data.get("requestId")
        
        if done:
            break
    
    assert_true(done, f"conversation should complete within {max_turns} turns with complete info")
    assert_true(request_id, "request should be created")
    print(f"  ✓ Request {request_id} created via conversation")
    
    # Verify audit chain
    print("  📋 Verifying audit chain...")
    resp = requests.post(f"{API_BASE}/audit/verify", timeout=30)
    assert_eq(resp.status_code, 200, "audit verify status")
    audit = resp.json()
    
    assert_eq(audit.get("ok"), True, "audit chain should be valid")
    print(f"  ✓ Audit chain verified: ok=true, count={audit.get('count')}")
    
    # Verify request appears in GET /api/requests
    print("  📋 Verifying request in list...")
    resp = requests.get(f"{API_BASE}/requests", timeout=30)
    assert_eq(resp.status_code, 200, "get requests status")
    requests_list = resp.json()
    
    request_ids = [r.get("id") for r in requests_list]
    assert_true(request_id in request_ids, f"request {request_id} should be in list")
    print(f"  ✓ Request {request_id} appears in GET /api/requests")


# ============================================================================
# SCENARIO F: REGRESSION - POST /api/requests still works
# ============================================================================
def test_scenario_f_regression_post_requests():
    """POST /api/requests should still work as before."""
    print("  📋 Testing POST /api/requests (regression)...")
    
    resp = requests.post(f"{API_BASE}/requests", json={
        "text": "AC leaking water in Lab 201",
        "anonymous": False,
        "requester": "Regression Test"
    }, timeout=90)
    assert_eq(resp.status_code, 200, "POST /api/requests status")
    req = resp.json()
    
    assert_true(req.get("id"), "request id should be present")
    assert_true(req.get("id").startswith("REQ-"), "request id format")
    assert_eq(req.get("type"), "maintenance", "request type")
    assert_eq(req.get("status"), "completed", "maintenance should auto-execute")
    assert_true(req.get("recordId"), "recordId should be set")
    assert_true(req.get("recordId").startswith("MT-"), "maintenance ticket format")
    print(f"  ✓ POST /api/requests works: {req.get('id')} -> {req.get('recordId')}")


def test_scenario_f_regression_reset_wipes_conversations():
    """POST /api/reset should wipe conversations collection."""
    print("  📋 Testing POST /api/reset wipes conversations...")
    
    # Create a conversation
    resp = requests.post(f"{API_BASE}/conversation/start", json={
        "anonymous": False,
        "requester": "Reset Test"
    }, timeout=30)
    session_id = resp.json().get("id")
    print(f"  ✓ Created conversation {session_id}")
    
    # Reset
    resp = requests.post(f"{API_BASE}/reset", timeout=30)
    assert_eq(resp.status_code, 200, "reset status")
    assert_eq(resp.json().get("ok"), True, "reset ok")
    print(f"  ✓ Reset completed")
    
    # Try to GET the conversation - should be 404
    resp = requests.get(f"{API_BASE}/conversation/{session_id}", timeout=30)
    assert_eq(resp.status_code, 404, "conversation should be deleted after reset")
    print(f"  ✓ Conversation {session_id} deleted after reset")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def main():
    print("=" * 80)
    print("SOA CONVERSATIONAL ASSISTANT BACKEND TEST SUITE")
    print("=" * 80)
    print()
    
    # Reset to clean state
    print("🔄 Resetting to clean state...")
    resp = requests.post(f"{API_BASE}/reset", timeout=30)
    if resp.status_code == 200:
        print("✅ Reset successful\n")
    else:
        print(f"⚠️  Reset returned {resp.status_code}\n")
    
    print("=" * 80)
    print("SCENARIO A: NON-ANONYMOUS CERTIFICATE + SOA-ID GATING")
    print("=" * 80)
    test("A: Non-anonymous certificate with SOA-ID gating", test_scenario_a_non_anonymous_certificate_soa_gating)
    
    print("=" * 80)
    print("SCENARIO B: DETERMINISTIC GUARD")
    print("=" * 80)
    test("B: Non-anonymous cannot finalize without SOA ID", test_scenario_b_deterministic_guard)
    
    print("=" * 80)
    print("SCENARIO C: ANONYMOUS GRIEVANCE")
    print("=" * 80)
    test("C: Anonymous grievance never asks for SOA ID", test_scenario_c_anonymous_grievance)
    
    print("=" * 80)
    print("SCENARIO D: ERROR CASES")
    print("=" * 80)
    test("D1: Unknown sessionId returns 404", test_scenario_d_error_unknown_session)
    test("D2: No input returns 400", test_scenario_d_error_no_input)
    test("D3: Completed session returns 409", test_scenario_d_error_completed_session)
    test("D4: GET conversation works", test_scenario_d_get_conversation)
    
    print("=" * 80)
    print("SCENARIO E: AUDIT INTEGRITY")
    print("=" * 80)
    test("E: Audit integrity after conversation", test_scenario_e_audit_integrity)
    
    print("=" * 80)
    print("SCENARIO F: REGRESSION")
    print("=" * 80)
    test("F1: POST /api/requests still works", test_scenario_f_regression_post_requests)
    test("F2: POST /api/reset wipes conversations", test_scenario_f_regression_reset_wipes_conversations)
    
    # Final reset
    print("=" * 80)
    print("🔄 Final reset to clean state...")
    resp = requests.post(f"{API_BASE}/reset", timeout=30)
    if resp.status_code == 200:
        print("✅ Final reset successful\n")
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    total = passed + failed
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print(f"Pass rate: {passed / total * 100:.1f}%\n")
    
    if failed > 0:
        print("FAILED TESTS:")
        for result in test_results:
            if result.startswith("❌"):
                print(f"  {result}")
        print()
    
    print("DETAILED RESULTS:")
    for result in test_results:
        print(f"  {result}")
    print()
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
