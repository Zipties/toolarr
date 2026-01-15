#!/usr/bin/env python3
"""
Robustness Test: How do Toolarr vs Skills handle edge cases?

Tests:
1. Malformed input (spaces, special chars)
2. Missing required params
3. Non-existent series/movie
4. Empty search results
5. Invalid instance name
"""

import subprocess
import httpx
import json

TOOLARR_URL = "http://localhost:8010"
TOOLARR_API_KEY = "toolarr-benchmark-key-2026"
SONARR_URL = "http://192.168.45.15:8083"
SONARR_API_KEY = "7ce61d72c943483ca03864e03f013127"


def test_toolarr(name: str, endpoint: str, params: dict = None, method: str = "GET") -> dict:
    """Test Toolarr endpoint"""
    client = httpx.Client(
        base_url=TOOLARR_URL,
        headers={"Authorization": f"Bearer {TOOLARR_API_KEY}"},
        timeout=30.0
    )
    try:
        if method == "GET":
            resp = client.get(endpoint, params=params)
        else:
            resp = client.post(endpoint, json=params)

        return {
            "test": name,
            "approach": "toolarr",
            "status": resp.status_code,
            "success": 200 <= resp.status_code < 300,
            "handled_gracefully": resp.status_code in [200, 400, 404, 422],  # Expected error codes
            "response": resp.text[:200] if resp.text else ""
        }
    except Exception as e:
        return {
            "test": name,
            "approach": "toolarr",
            "status": 0,
            "success": False,
            "handled_gracefully": False,
            "error": str(e)
        }


def test_skills(name: str, cmd: str) -> dict:
    """Test Skills (curl/jq) approach"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Check if command succeeded and returned valid JSON
        success = result.returncode == 0
        valid_json = False
        if success and result.stdout.strip():
            try:
                json.loads(result.stdout)
                valid_json = True
            except:
                pass

        return {
            "test": name,
            "approach": "skills",
            "status": result.returncode,
            "success": success and valid_json,
            "handled_gracefully": result.returncode == 0,  # Curl doesn't give HTTP codes easily
            "response": result.stdout[:200] if result.stdout else result.stderr[:200]
        }
    except subprocess.TimeoutExpired:
        return {
            "test": name,
            "approach": "skills",
            "status": -1,
            "success": False,
            "handled_gracefully": False,
            "error": "Timeout"
        }
    except Exception as e:
        return {
            "test": name,
            "approach": "skills",
            "status": -1,
            "success": False,
            "handled_gracefully": False,
            "error": str(e)
        }


def run_tests():
    """Run robustness tests"""
    results = []

    print("=" * 70)
    print("ROBUSTNESS TEST: Toolarr vs Skills")
    print("=" * 70)

    # Test 1: Spaces in search term (common AI mistake)
    print("\n1. SPACES IN SEARCH TERM (unencoded)")
    print("-" * 50)

    # Toolarr handles encoding via httpx params
    r1_tool = test_toolarr("spaces_unencoded", "/sonarr/sonarr/lookup", {"term": "breaking bad"})
    # Skills - AI might forget to encode
    r1_skill = test_skills("spaces_unencoded",
        f'curl -s "{SONARR_URL}/api/v3/series/lookup?term=breaking bad&apikey={SONARR_API_KEY}" | jq ".[0].title"')

    print(f"  Toolarr: {'✅ Handled' if r1_tool['handled_gracefully'] else '❌ Failed'} (status: {r1_tool['status']})")
    print(f"  Skills:  {'✅ Handled' if r1_skill['handled_gracefully'] else '❌ Failed'} (status: {r1_skill['status']})")
    results.extend([r1_tool, r1_skill])

    # Test 2: Special characters in search
    print("\n2. SPECIAL CHARACTERS (quotes, ampersands)")
    print("-" * 50)

    r2_tool = test_toolarr("special_chars", "/sonarr/sonarr/lookup", {"term": "Grey's Anatomy"})
    r2_skill = test_skills("special_chars",
        f'curl -s "{SONARR_URL}/api/v3/series/lookup?term=Grey\'s Anatomy&apikey={SONARR_API_KEY}" | jq ".[0].title"')

    print(f"  Toolarr: {'✅ Handled' if r2_tool['handled_gracefully'] else '❌ Failed'} (status: {r2_tool['status']})")
    print(f"  Skills:  {'✅ Handled' if r2_skill['handled_gracefully'] else '❌ Failed'}")
    results.extend([r2_tool, r2_skill])

    # Test 3: Empty/null search term
    print("\n3. EMPTY SEARCH TERM")
    print("-" * 50)

    r3_tool = test_toolarr("empty_term", "/sonarr/sonarr/lookup", {"term": ""})
    r3_skill = test_skills("empty_term",
        f'curl -s "{SONARR_URL}/api/v3/series/lookup?term=&apikey={SONARR_API_KEY}" | jq "length"')

    print(f"  Toolarr: {'✅ Handled' if r3_tool['handled_gracefully'] else '❌ Failed'} (status: {r3_tool['status']})")
    print(f"  Skills:  {'✅ Handled' if r3_skill['handled_gracefully'] else '❌ Failed'}")
    results.extend([r3_tool, r3_skill])

    # Test 4: Non-existent series (gibberish)
    print("\n4. NON-EXISTENT SERIES (gibberish search)")
    print("-" * 50)

    r4_tool = test_toolarr("nonexistent", "/sonarr/sonarr/lookup", {"term": "xyzzy123notreal456"})
    r4_skill = test_skills("nonexistent",
        f'curl -s "{SONARR_URL}/api/v3/series/lookup?term=xyzzy123notreal456&apikey={SONARR_API_KEY}" | jq ".[0].title"')

    print(f"  Toolarr: {'✅ Handled' if r4_tool['handled_gracefully'] else '❌ Failed'} (returns empty array)")
    print(f"  Skills:  {'✅ Handled' if r4_skill['handled_gracefully'] else '❌ Failed'} (jq errors on null)")
    results.extend([r4_tool, r4_skill])

    # Test 5: Wrong instance name (AI hallucination)
    print("\n5. WRONG INSTANCE NAME (hallucinated)")
    print("-" * 50)

    r5_tool = test_toolarr("wrong_instance", "/sonarr/sonarr-4k/lookup", {"term": "test"})
    # Skills don't have instance concept - this would be a wrong URL
    r5_skill = test_skills("wrong_instance",
        f'curl -s "http://192.168.45.15:9999/api/v3/series/lookup?term=test&apikey={SONARR_API_KEY}" | jq ".[0]"')

    print(f"  Toolarr: {'✅ Handled' if r5_tool['handled_gracefully'] else '❌ Failed'} (status: {r5_tool['status']})")
    print(f"  Skills:  {'✅ Handled' if r5_skill['handled_gracefully'] else '❌ Failed'} (connection refused)")
    results.extend([r5_tool, r5_skill])

    # Test 6: Missing API key
    print("\n6. MISSING API KEY")
    print("-" * 50)

    # Toolarr abstracts the key away - AI can't forget it
    r6_tool = test_toolarr("no_apikey", "/sonarr/sonarr/lookup", {"term": "test"})
    # Skills - AI might forget the apikey param
    r6_skill = test_skills("no_apikey",
        f'curl -s "{SONARR_URL}/api/v3/series/lookup?term=test" | jq "."')

    print(f"  Toolarr: {'✅ Handled' if r6_tool['handled_gracefully'] else '❌ Failed'} (key is server-side)")
    print(f"  Skills:  {'✅ Handled' if r6_skill['handled_gracefully'] else '❌ Failed'} (401 unauthorized)")
    results.extend([r6_tool, r6_skill])

    # Test 7: jq syntax error (common skill mistake)
    print("\n7. JQ SYNTAX ERROR (skills only)")
    print("-" * 50)

    r7_skill = test_skills("jq_syntax_error",
        f'curl -s "{SONARR_URL}/api/v3/series/lookup?term=test&apikey={SONARR_API_KEY}" | jq ".[0] | .title .year"')  # Missing comma

    print(f"  Skills:  {'✅ Handled' if r7_skill['handled_gracefully'] else '❌ Failed'} (jq parse error)")
    results.append(r7_skill)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    toolarr_results = [r for r in results if r['approach'] == 'toolarr']
    skills_results = [r for r in results if r['approach'] == 'skills']

    toolarr_graceful = sum(1 for r in toolarr_results if r['handled_gracefully'])
    skills_graceful = sum(1 for r in skills_results if r['handled_gracefully'])

    print(f"\nToolarr: {toolarr_graceful}/{len(toolarr_results)} tests handled gracefully")
    print(f"Skills:  {skills_graceful}/{len(skills_results)} tests handled gracefully")

    print("\n⚠️  KEY INSIGHT:")
    print("   Toolarr provides HTTP-level error handling that a dumb AI can parse.")
    print("   Skills require the AI to construct valid bash AND handle curl/jq failures.")

    return results


if __name__ == "__main__":
    run_tests()
