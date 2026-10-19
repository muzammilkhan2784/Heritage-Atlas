"""Small reproducible local HTTP timing sample; not a production capacity claim."""

import argparse
import concurrent.futures
import json
import statistics
import time
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:5050")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    paths = [
        "/api/sites",
        "/api/sites?q=temple",
        "/api/sites?lat=48.85&lon=2.35&radius=100",
        "/api/sites?language=Japanese",
    ]

    def fetch(i):
        start = time.perf_counter()
        with urllib.request.urlopen(args.base + paths[i % len(paths)], timeout=10) as response:
            result = json.load(response)
            assert isinstance(result["items"], list)
            status = response.status
        return (time.perf_counter() - start) * 1000, status

    for i in range(8):
        fetch(i)
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        samples = list(executor.map(fetch, range(args.requests)))
    elapsed = time.perf_counter() - start
    timings = sorted(ms for ms, _ in samples)
    result = {
        "environment": "Native Windows, Waitress 8 threads, MongoDB 8.0.34; warmed cache",
        "requests": len(samples),
        "concurrency": args.workers,
        "successful_responses": sum(status == 200 for _, status in samples),
        "p50_ms": round(statistics.median(timings), 2),
        "p95_ms": round(timings[max(0, int(len(timings) * 0.95) - 1)], 2),
        "elapsed_seconds": round(elapsed, 2),
        "note": "A small local sample, not an SLA, scalability proof, or production benchmark.",
    }
    output = Path("work/benchmark.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
