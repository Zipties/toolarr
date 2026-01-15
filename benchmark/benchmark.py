#!/usr/bin/env python3
"""
Benchmark: Toolarr vs Skills approach for Sonarr/Radarr control

Measures:
- Time (wall clock)
- Accuracy (result correctness)
- Iterations (API calls)
- Token estimate (based on payload/prompt size)
"""

import asyncio
import json
import subprocess
import time
import hashlib
import httpx
from dataclasses import dataclass
from typing import Optional, Any, Dict, List
import os

# Configuration
TOOLARR_URL = "http://localhost:8010"
TOOLARR_API_KEY = "toolarr-benchmark-key-2026"

SONARR_URL = "http://192.168.45.15:8083"
SONARR_API_KEY = "7ce61d72c943483ca03864e03f013127"

RADARR_URL = "http://192.168.45.15:5051"
RADARR_API_KEY = "d81da54eab704db0aa2d4e1d66cd697a"


@dataclass
class BenchmarkResult:
    test_name: str
    approach: str  # "toolarr" or "skills"
    time_ms: float
    iterations: int
    success: bool
    result: Any
    result_hash: str
    error: Optional[str] = None
    token_estimate: int = 0


class ToolarrBenchmark:
    """Benchmark using Toolarr MCP/API approach"""

    def __init__(self):
        self.client = httpx.Client(
            base_url=TOOLARR_URL,
            headers={"Authorization": f"Bearer {TOOLARR_API_KEY}"},
            timeout=30.0
        )

    def series_lookup(self, term: str) -> BenchmarkResult:
        """Lookup a series via Toolarr"""
        start = time.perf_counter()
        iterations = 0

        try:
            iterations += 1
            resp = self.client.get(f"/sonarr/sonarr/lookup", params={"term": term})
            resp.raise_for_status()
            data = resp.json()

            elapsed = (time.perf_counter() - start) * 1000
            result = data[0] if data else None
            # Normalize to same fields as skills approach
            normalized = {"title": result.get("title"), "year": result.get("year"), "tvdbId": result.get("tvdbId")} if result else None

            return BenchmarkResult(
                test_name="series_lookup",
                approach="toolarr",
                time_ms=elapsed,
                iterations=iterations,
                success=bool(result),
                result=normalized,
                result_hash=hashlib.md5(json.dumps(normalized, sort_keys=True).encode()).hexdigest() if normalized else "",
                token_estimate=self._estimate_tokens("lookup", term)
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                test_name="series_lookup",
                approach="toolarr",
                time_ms=elapsed,
                iterations=iterations,
                success=False,
                result=None,
                result_hash="",
                error=str(e)
            )

    def movie_lookup(self, term: str) -> BenchmarkResult:
        """Lookup a movie via Toolarr"""
        start = time.perf_counter()
        iterations = 0

        try:
            iterations += 1
            resp = self.client.get(f"/radarr/radarr/lookup", params={"term": term})
            resp.raise_for_status()
            data = resp.json()

            elapsed = (time.perf_counter() - start) * 1000
            result = data[0] if data else None
            # Normalize to same fields as skills approach
            normalized = {"title": result.get("title"), "year": result.get("year"), "tmdbId": result.get("tmdbId")} if result else None

            return BenchmarkResult(
                test_name="movie_lookup",
                approach="toolarr",
                time_ms=elapsed,
                iterations=iterations,
                success=bool(result),
                result=normalized,
                result_hash=hashlib.md5(json.dumps(normalized, sort_keys=True).encode()).hexdigest() if normalized else "",
                token_estimate=self._estimate_tokens("lookup", term)
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                test_name="movie_lookup",
                approach="toolarr",
                time_ms=elapsed,
                iterations=iterations,
                success=False,
                result=None,
                result_hash="",
                error=str(e)
            )

    def queue_check_sonarr(self) -> BenchmarkResult:
        """Check Sonarr download queue via Toolarr"""
        start = time.perf_counter()
        iterations = 0

        try:
            iterations += 1
            resp = self.client.get(f"/sonarr/sonarr/queue")
            resp.raise_for_status()
            data = resp.json()

            elapsed = (time.perf_counter() - start) * 1000

            # Handle both array format and object with records
            if isinstance(data, list):
                count = len(data)
            else:
                count = len(data.get("records", []))

            return BenchmarkResult(
                test_name="queue_check_sonarr",
                approach="toolarr",
                time_ms=elapsed,
                iterations=iterations,
                success=True,
                result={"count": count},
                result_hash=hashlib.md5(str(count).encode()).hexdigest(),
                token_estimate=self._estimate_tokens("queue", "")
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                test_name="queue_check_sonarr",
                approach="toolarr",
                time_ms=elapsed,
                iterations=iterations,
                success=False,
                result=None,
                result_hash="",
                error=str(e)
            )

    def quality_profiles_sonarr(self) -> BenchmarkResult:
        """Get Sonarr quality profiles via Toolarr"""
        start = time.perf_counter()
        iterations = 0

        try:
            iterations += 1
            resp = self.client.get(f"/sonarr/sonarr/qualityprofiles")
            resp.raise_for_status()
            data = resp.json()

            elapsed = (time.perf_counter() - start) * 1000
            profiles = [{"id": p["id"], "name": p["name"]} for p in data]

            return BenchmarkResult(
                test_name="quality_profiles_sonarr",
                approach="toolarr",
                time_ms=elapsed,
                iterations=iterations,
                success=True,
                result=profiles,
                result_hash=hashlib.md5(json.dumps(profiles, sort_keys=True).encode()).hexdigest(),
                token_estimate=self._estimate_tokens("profiles", "")
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                test_name="quality_profiles_sonarr",
                approach="toolarr",
                time_ms=elapsed,
                iterations=iterations,
                success=False,
                result=None,
                result_hash="",
                error=str(e)
            )

    def _estimate_tokens(self, op: str, term: str) -> int:
        """Rough token estimate for Toolarr approach"""
        # Tool schema is ~200 tokens, request ~50 tokens
        base = 250
        if term:
            base += len(term.split()) * 2
        return base


class SkillsBenchmark:
    """Benchmark using direct curl/jq approach (Skills)"""

    def series_lookup(self, term: str) -> BenchmarkResult:
        """Lookup a series via direct API (Skills approach)"""
        start = time.perf_counter()
        iterations = 0

        try:
            iterations += 1
            # URL encode the term
            encoded_term = term.replace(" ", "%20")
            cmd = f'curl -s "{SONARR_URL}/api/v3/series/lookup?term={encoded_term}&apikey={SONARR_API_KEY}" | jq ".[0] | {{title, year, tvdbId}}"'

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            elapsed = (time.perf_counter() - start) * 1000

            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return BenchmarkResult(
                    test_name="series_lookup",
                    approach="skills",
                    time_ms=elapsed,
                    iterations=iterations,
                    success=True,
                    result=data,
                    result_hash=hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest(),
                    token_estimate=self._estimate_tokens("lookup", term)
                )
            else:
                raise Exception(f"Command failed: {result.stderr}")

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                test_name="series_lookup",
                approach="skills",
                time_ms=elapsed,
                iterations=iterations,
                success=False,
                result=None,
                result_hash="",
                error=str(e)
            )

    def movie_lookup(self, term: str) -> BenchmarkResult:
        """Lookup a movie via direct API (Skills approach)"""
        start = time.perf_counter()
        iterations = 0

        try:
            iterations += 1
            encoded_term = term.replace(" ", "%20")
            cmd = f'curl -s "{RADARR_URL}/api/v3/movie/lookup?term={encoded_term}&apikey={RADARR_API_KEY}" | jq ".[0] | {{title, year, tmdbId}}"'

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            elapsed = (time.perf_counter() - start) * 1000

            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return BenchmarkResult(
                    test_name="movie_lookup",
                    approach="skills",
                    time_ms=elapsed,
                    iterations=iterations,
                    success=True,
                    result=data,
                    result_hash=hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest(),
                    token_estimate=self._estimate_tokens("lookup", term)
                )
            else:
                raise Exception(f"Command failed: {result.stderr}")

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                test_name="movie_lookup",
                approach="skills",
                time_ms=elapsed,
                iterations=iterations,
                success=False,
                result=None,
                result_hash="",
                error=str(e)
            )

    def queue_check_sonarr(self) -> BenchmarkResult:
        """Check Sonarr download queue via direct API"""
        start = time.perf_counter()
        iterations = 0

        try:
            iterations += 1
            cmd = f'curl -s "{SONARR_URL}/api/v3/queue?pageSize=100&apikey={SONARR_API_KEY}" | jq ".records | length"'

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            elapsed = (time.perf_counter() - start) * 1000

            if result.returncode == 0:
                count = int(result.stdout.strip()) if result.stdout.strip() else 0
                return BenchmarkResult(
                    test_name="queue_check_sonarr",
                    approach="skills",
                    time_ms=elapsed,
                    iterations=iterations,
                    success=True,
                    result={"count": count},
                    result_hash=hashlib.md5(str(count).encode()).hexdigest(),
                    token_estimate=self._estimate_tokens("queue", "")
                )
            else:
                raise Exception(f"Command failed: {result.stderr}")

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                test_name="queue_check_sonarr",
                approach="skills",
                time_ms=elapsed,
                iterations=iterations,
                success=False,
                result=None,
                result_hash="",
                error=str(e)
            )

    def quality_profiles_sonarr(self) -> BenchmarkResult:
        """Get Sonarr quality profiles via direct API"""
        start = time.perf_counter()
        iterations = 0

        try:
            iterations += 1
            cmd = f'curl -s "{SONARR_URL}/api/v3/qualityprofile?apikey={SONARR_API_KEY}" | jq "[.[] | {{id, name}}]"'

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            elapsed = (time.perf_counter() - start) * 1000

            if result.returncode == 0 and result.stdout.strip():
                profiles = json.loads(result.stdout)
                return BenchmarkResult(
                    test_name="quality_profiles_sonarr",
                    approach="skills",
                    time_ms=elapsed,
                    iterations=iterations,
                    success=True,
                    result=profiles,
                    result_hash=hashlib.md5(json.dumps(profiles, sort_keys=True).encode()).hexdigest(),
                    token_estimate=self._estimate_tokens("profiles", "")
                )
            else:
                raise Exception(f"Command failed: {result.stderr}")

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                test_name="quality_profiles_sonarr",
                approach="skills",
                time_ms=elapsed,
                iterations=iterations,
                success=False,
                result=None,
                result_hash="",
                error=str(e)
            )

    def _estimate_tokens(self, op: str, term: str) -> int:
        """Rough token estimate for Skills approach"""
        # Skill prompt is larger (~500 tokens), but no tool schema overhead
        # Direct bash command is ~100 tokens
        base = 600 if op == "complex" else 150
        if term:
            base += len(term.split()) * 2
        return base


def run_benchmark(test_name: str = None) -> List[Dict]:
    """Run benchmarks and return results"""
    toolarr = ToolarrBenchmark()
    skills = SkillsBenchmark()

    tests = [
        ("series_lookup", "breaking bad"),
        ("movie_lookup", "the matrix"),
        ("queue_check_sonarr", None),
        ("quality_profiles_sonarr", None),
    ]

    results = []

    for test, arg in tests:
        if test_name and test != test_name:
            continue

        print(f"\n{'='*60}")
        print(f"Running: {test}")
        print(f"{'='*60}")

        # Run Toolarr version
        if arg:
            toolarr_result = getattr(toolarr, test)(arg)
        else:
            toolarr_result = getattr(toolarr, test)()

        # Run Skills version
        if arg:
            skills_result = getattr(skills, test)(arg)
        else:
            skills_result = getattr(skills, test)()

        # Compare
        match = toolarr_result.result_hash == skills_result.result_hash

        print(f"\n{'Method':<12} {'Time (ms)':<12} {'Iterations':<12} {'Success':<10} {'Tokens':<10}")
        print(f"{'-'*56}")
        print(f"{'Toolarr':<12} {toolarr_result.time_ms:<12.1f} {toolarr_result.iterations:<12} {str(toolarr_result.success):<10} {toolarr_result.token_estimate:<10}")
        print(f"{'Skills':<12} {skills_result.time_ms:<12.1f} {skills_result.iterations:<12} {str(skills_result.success):<10} {skills_result.token_estimate:<10}")
        print(f"\nResults match: {'✅ YES' if match else '❌ NO'}")

        if toolarr_result.error:
            print(f"Toolarr error: {toolarr_result.error}")
        if skills_result.error:
            print(f"Skills error: {skills_result.error}")

        results.append({
            "test": test,
            "toolarr": {
                "time_ms": toolarr_result.time_ms,
                "iterations": toolarr_result.iterations,
                "success": toolarr_result.success,
                "tokens": toolarr_result.token_estimate,
                "error": toolarr_result.error
            },
            "skills": {
                "time_ms": skills_result.time_ms,
                "iterations": skills_result.iterations,
                "success": skills_result.success,
                "tokens": skills_result.token_estimate,
                "error": skills_result.error
            },
            "results_match": match
        })

    return results


def print_summary(results: List[Dict]):
    """Print summary of benchmark results"""
    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}\n")

    toolarr_wins = 0
    skills_wins = 0
    ties = 0

    for r in results:
        if r["toolarr"]["time_ms"] < r["skills"]["time_ms"]:
            toolarr_wins += 1
        elif r["skills"]["time_ms"] < r["toolarr"]["time_ms"]:
            skills_wins += 1
        else:
            ties += 1

    total_toolarr_time = sum(r["toolarr"]["time_ms"] for r in results)
    total_skills_time = sum(r["skills"]["time_ms"] for r in results)
    total_toolarr_tokens = sum(r["toolarr"]["tokens"] for r in results)
    total_skills_tokens = sum(r["skills"]["tokens"] for r in results)

    print(f"Speed comparison:")
    print(f"  Toolarr wins: {toolarr_wins}")
    print(f"  Skills wins:  {skills_wins}")
    print(f"  Ties:         {ties}")
    print()
    print(f"Total time:")
    print(f"  Toolarr: {total_toolarr_time:.1f}ms")
    print(f"  Skills:  {total_skills_time:.1f}ms")
    print()
    print(f"Token estimates:")
    print(f"  Toolarr: {total_toolarr_tokens}")
    print(f"  Skills:  {total_skills_tokens}")
    print()

    all_match = all(r["results_match"] for r in results)
    all_success = all(r["toolarr"]["success"] and r["skills"]["success"] for r in results)

    print(f"Accuracy: {'✅ All tests passed' if all_success else '❌ Some tests failed'}")
    print(f"Consistency: {'✅ All results match' if all_match else '⚠️ Some results differ'}")


if __name__ == "__main__":
    import sys

    test_name = None
    if len(sys.argv) > 2 and sys.argv[1] == "--test":
        test_name = sys.argv[2]

    print("=" * 60)
    print("TOOLARR vs SKILLS BENCHMARK")
    print("=" * 60)
    print(f"Toolarr URL: {TOOLARR_URL}")
    print(f"Sonarr URL:  {SONARR_URL}")
    print(f"Radarr URL:  {RADARR_URL}")

    results = run_benchmark(test_name)
    print_summary(results)

    # Save results
    output_file = "/tmp/benchmark_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")
