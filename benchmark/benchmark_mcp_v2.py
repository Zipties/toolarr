#!/usr/bin/env python3
"""
Benchmark: Toolarr MCP v2 vs Skills approach

Tests both approaches on identical tasks:
1. Series lookup
2. Movie lookup
3. Queue check
4. Quality profiles
5. Get releases for episode (THE BIG TEST - Skills only had this before)
6. Get releases for movie

Measures:
- Time (wall clock)
- Success rate
- Token estimate
"""

import asyncio
import json
import subprocess
import time
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backends import SonarrClient, RadarrClient

# Configuration
SONARR_URL = os.getenv("SONARR_URL", "http://192.168.45.15:8083")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "7ce61d72c943483ca03864e03f013127")
RADARR_URL = os.getenv("RADARR_URL", "http://192.168.45.15:5051")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "d81da54eab704db0aa2d4e1d66cd697a")


class BenchmarkResult:
    def __init__(self, test_name: str, approach: str, time_ms: float,
                 success: bool, result_summary: str, token_estimate: int,
                 error: str = None):
        self.test_name = test_name
        self.approach = approach
        self.time_ms = time_ms
        self.success = success
        self.result_summary = result_summary
        self.token_estimate = token_estimate
        self.error = error


async def benchmark_mcp(sonarr: SonarrClient, radarr: RadarrClient) -> list:
    """Run benchmarks using MCP backend clients"""
    results = []

    # Test 1: Series lookup
    start = time.perf_counter()
    try:
        data = await sonarr.lookup_series("Severance")
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult(
            "series_lookup", "mcp", elapsed, True,
            f"Found {len(data)} results, first: {data[0]['title'] if data else 'N/A'}",
            token_estimate=300  # tool schema + call
        ))
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult("series_lookup", "mcp", elapsed, False, "", 300, str(e)))

    # Test 2: Movie lookup
    start = time.perf_counter()
    try:
        data = await radarr.lookup_movie("Dune")
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult(
            "movie_lookup", "mcp", elapsed, True,
            f"Found {len(data)} results, first: {data[0]['title'] if data else 'N/A'}",
            token_estimate=300
        ))
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult("movie_lookup", "mcp", elapsed, False, "", 300, str(e)))

    # Test 3: Sonarr queue
    start = time.perf_counter()
    try:
        data = await sonarr.get_queue()
        elapsed = (time.perf_counter() - start) * 1000
        count = len(data.get("records", [])) if isinstance(data, dict) else len(data)
        results.append(BenchmarkResult(
            "sonarr_queue", "mcp", elapsed, True,
            f"{count} items in queue",
            token_estimate=250
        ))
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult("sonarr_queue", "mcp", elapsed, False, "", 250, str(e)))

    # Test 4: Quality profiles
    start = time.perf_counter()
    try:
        data = await sonarr.get_quality_profiles()
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult(
            "quality_profiles", "mcp", elapsed, True,
            f"{len(data)} profiles",
            token_estimate=250
        ))
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult("quality_profiles", "mcp", elapsed, False, "", 250, str(e)))

    # Test 5: Get releases for episode (THE BIG TEST)
    start = time.perf_counter()
    try:
        # First get a series with episodes
        series = await sonarr.list_series()
        if series:
            episodes = await sonarr.get_episodes(series[0]['id'])
            if episodes:
                releases = await sonarr.get_releases(episodes[0]['id'])
                elapsed = (time.perf_counter() - start) * 1000
                results.append(BenchmarkResult(
                    "episode_releases", "mcp", elapsed, True,
                    f"{len(releases)} releases found for episode",
                    token_estimate=750  # 3 calls
                ))
            else:
                elapsed = (time.perf_counter() - start) * 1000
                results.append(BenchmarkResult("episode_releases", "mcp", elapsed, False, "No episodes", 750))
        else:
            elapsed = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult("episode_releases", "mcp", elapsed, False, "No series", 750))
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult("episode_releases", "mcp", elapsed, False, "", 750, str(e)))

    # Test 6: Get releases for movie
    start = time.perf_counter()
    try:
        movies = await radarr.list_movies()
        if movies:
            releases = await radarr.get_releases(movies[0]['id'])
            elapsed = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                "movie_releases", "mcp", elapsed, True,
                f"{len(releases)} releases found for movie",
                token_estimate=500  # 2 calls
            ))
        else:
            elapsed = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult("movie_releases", "mcp", elapsed, False, "No movies", 500))
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult("movie_releases", "mcp", elapsed, False, "", 500, str(e)))

    return results


def benchmark_skills() -> list:
    """Run benchmarks using Skills/curl approach"""
    results = []

    def run_curl(cmd: str) -> tuple:
        start = time.perf_counter()
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed, result.returncode == 0, result.stdout.strip(), result.stderr
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed, False, "", str(e)

    # Test 1: Series lookup
    cmd = f'curl -s "{SONARR_URL}/api/v3/series/lookup?term=Severance&apikey={SONARR_API_KEY}" | jq "length, .[0].title"'
    elapsed, success, output, err = run_curl(cmd)
    results.append(BenchmarkResult(
        "series_lookup", "skills", elapsed, success,
        output.replace("\n", ", ") if success else err,
        token_estimate=150  # skill prompt snippet
    ))

    # Test 2: Movie lookup
    cmd = f'curl -s "{RADARR_URL}/api/v3/movie/lookup?term=Dune&apikey={RADARR_API_KEY}" | jq "length, .[0].title"'
    elapsed, success, output, err = run_curl(cmd)
    results.append(BenchmarkResult(
        "movie_lookup", "skills", elapsed, success,
        output.replace("\n", ", ") if success else err,
        token_estimate=150
    ))

    # Test 3: Sonarr queue
    cmd = f'curl -s "{SONARR_URL}/api/v3/queue?pageSize=100&apikey={SONARR_API_KEY}" | jq ".records | length"'
    elapsed, success, output, err = run_curl(cmd)
    results.append(BenchmarkResult(
        "sonarr_queue", "skills", elapsed, success,
        f"{output} items" if success else err,
        token_estimate=150
    ))

    # Test 4: Quality profiles
    cmd = f'curl -s "{SONARR_URL}/api/v3/qualityprofile?apikey={SONARR_API_KEY}" | jq "length"'
    elapsed, success, output, err = run_curl(cmd)
    results.append(BenchmarkResult(
        "quality_profiles", "skills", elapsed, success,
        f"{output} profiles" if success else err,
        token_estimate=150
    ))

    # Test 5: Get releases for episode (multi-step)
    start = time.perf_counter()
    try:
        # Step 1: Get first series ID
        cmd1 = f'curl -s "{SONARR_URL}/api/v3/series?apikey={SONARR_API_KEY}" | jq ".[0].id"'
        r1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True, timeout=10)
        series_id = r1.stdout.strip()

        # Step 2: Get first episode ID
        cmd2 = f'curl -s "{SONARR_URL}/api/v3/episode?seriesId={series_id}&apikey={SONARR_API_KEY}" | jq ".[0].id"'
        r2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True, timeout=10)
        episode_id = r2.stdout.strip()

        # Step 3: Get releases
        cmd3 = f'curl -s "{SONARR_URL}/api/v3/release?episodeId={episode_id}&apikey={SONARR_API_KEY}" | jq "length"'
        r3 = subprocess.run(cmd3, shell=True, capture_output=True, text=True, timeout=30)

        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult(
            "episode_releases", "skills", elapsed, r3.returncode == 0,
            f"{r3.stdout.strip()} releases" if r3.returncode == 0 else r3.stderr,
            token_estimate=450  # 3 skill invocations
        ))
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult("episode_releases", "skills", elapsed, False, "", 450, str(e)))

    # Test 6: Get releases for movie (multi-step)
    start = time.perf_counter()
    try:
        # Step 1: Get first movie ID
        cmd1 = f'curl -s "{RADARR_URL}/api/v3/movie?apikey={RADARR_API_KEY}" | jq ".[0].id"'
        r1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True, timeout=10)
        movie_id = r1.stdout.strip()

        # Step 2: Get releases
        cmd2 = f'curl -s "{RADARR_URL}/api/v3/release?movieId={movie_id}&apikey={RADARR_API_KEY}" | jq "length"'
        r2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True, timeout=30)

        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult(
            "movie_releases", "skills", elapsed, r2.returncode == 0,
            f"{r2.stdout.strip()} releases" if r2.returncode == 0 else r2.stderr,
            token_estimate=300  # 2 skill invocations
        ))
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        results.append(BenchmarkResult("movie_releases", "skills", elapsed, False, "", 300, str(e)))

    return results


def print_comparison(mcp_results: list, skills_results: list):
    """Pretty print the comparison"""
    print("\n" + "=" * 80)
    print("  BENCHMARK RESULTS: MCP v2 vs Skills")
    print("=" * 80)

    print(f"\n{'Test':<20} {'Approach':<10} {'Time (ms)':<12} {'Success':<10} {'Tokens':<10} {'Result'}")
    print("-" * 100)

    for mcp, skills in zip(mcp_results, skills_results):
        # MCP row
        status = "PASS" if mcp.success else "FAIL"
        print(f"{mcp.test_name:<20} {'MCP':<10} {mcp.time_ms:<12.1f} {status:<10} {mcp.token_estimate:<10} {mcp.result_summary[:30]}")

        # Skills row
        status = "PASS" if skills.success else "FAIL"
        print(f"{'':<20} {'Skills':<10} {skills.time_ms:<12.1f} {status:<10} {skills.token_estimate:<10} {skills.result_summary[:30]}")

        # Winner
        if mcp.success and skills.success:
            if mcp.time_ms < skills.time_ms:
                winner = f"MCP {((skills.time_ms - mcp.time_ms) / skills.time_ms * 100):.0f}% faster"
            else:
                winner = f"Skills {((mcp.time_ms - skills.time_ms) / mcp.time_ms * 100):.0f}% faster"
        elif mcp.success:
            winner = "MCP (Skills failed)"
        elif skills.success:
            winner = "Skills (MCP failed)"
        else:
            winner = "Both failed"
        print(f"{'':<20} {'Winner:':<10} {winner}")
        print()

    # Summary
    print("=" * 80)
    print("  SUMMARY")
    print("=" * 80)

    mcp_total_time = sum(r.time_ms for r in mcp_results)
    skills_total_time = sum(r.time_ms for r in skills_results)
    mcp_total_tokens = sum(r.token_estimate for r in mcp_results)
    skills_total_tokens = sum(r.token_estimate for r in skills_results)
    mcp_success = sum(1 for r in mcp_results if r.success)
    skills_success = sum(1 for r in skills_results if r.success)

    print(f"\n{'Metric':<25} {'MCP v2':<20} {'Skills':<20} {'Winner'}")
    print("-" * 80)
    print(f"{'Total Time':<25} {mcp_total_time:.1f}ms{'':<12} {skills_total_time:.1f}ms{'':<12} {'MCP' if mcp_total_time < skills_total_time else 'Skills'}")
    print(f"{'Success Rate':<25} {mcp_success}/{len(mcp_results)}{'':<16} {skills_success}/{len(skills_results)}{'':<16} {'Tie' if mcp_success == skills_success else ('MCP' if mcp_success > skills_success else 'Skills')}")
    print(f"{'Est. Tokens (per run)':<25} {mcp_total_tokens}{'':<16} {skills_total_tokens}{'':<16} {'Skills' if skills_total_tokens < mcp_total_tokens else 'MCP'}")

    # Analysis
    print("\n" + "=" * 80)
    print("  ANALYSIS")
    print("=" * 80)

    if mcp_total_time < skills_total_time:
        pct = ((skills_total_time - mcp_total_time) / skills_total_time) * 100
        print(f"\n  Speed: MCP is {pct:.0f}% faster overall")
    else:
        pct = ((mcp_total_time - skills_total_time) / mcp_total_time) * 100
        print(f"\n  Speed: Skills is {pct:.0f}% faster overall")

    if mcp_total_tokens < skills_total_tokens:
        pct = ((skills_total_tokens - mcp_total_tokens) / skills_total_tokens) * 100
        print(f"  Tokens: MCP uses {pct:.0f}% fewer tokens")
    else:
        pct = ((mcp_total_tokens - skills_total_tokens) / mcp_total_tokens) * 100
        print(f"  Tokens: Skills uses {pct:.0f}% fewer tokens")

    print("\n  Note: Token estimates are approximations based on typical tool/skill sizes")


async def main():
    print("=" * 80)
    print("  TOOLARR MCP v2 vs SKILLS BENCHMARK")
    print("=" * 80)
    print(f"\nSonarr: {SONARR_URL}")
    print(f"Radarr: {RADARR_URL}")

    # Run MCP benchmarks
    print("\n[Running MCP benchmarks...]")
    async with SonarrClient(SONARR_URL, SONARR_API_KEY) as sonarr:
        async with RadarrClient(RADARR_URL, RADARR_API_KEY) as radarr:
            mcp_results = await benchmark_mcp(sonarr, radarr)

    # Run Skills benchmarks
    print("[Running Skills benchmarks...]")
    skills_results = benchmark_skills()

    # Compare
    print_comparison(mcp_results, skills_results)


if __name__ == "__main__":
    asyncio.run(main())
