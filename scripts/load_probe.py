"""Mesure de charge préliminaire (hors JMeter), même profil que le plan .jmx.

N utilisateurs virtuels démarrés progressivement sur RAMPUP secondes, chacun
envoie LOOPS requêtes POST /predict à la suite. Sert à valider l'API avant le
tir JMeter officiel ; ne remplace pas le rapport JMeter.

Usage : python scripts/load_probe.py http://localhost:8000 100 500 1000
"""
import asyncio
import json
import random
import statistics
import sys
import time

import httpx

RAMPUP = 10
LOOPS = 10


def payload():
    return {
        "age": random.randint(18, 69), "anciennete": random.randint(1, 119),
        "revenu": 450000, "nb_reclamations": random.randint(0, 6),
        "montant_mensuel": 25000, "retards_paiement": random.randint(0, 4),
    }


async def user(client, delay, latencies, errors):
    await asyncio.sleep(delay)
    for _ in range(LOOPS):
        t0 = time.perf_counter()
        try:
            r = await client.post("/predict", json=payload())
            ok = r.status_code == 200 and "prediction" in r.json()
        except Exception:
            ok = False
        latencies.append((time.perf_counter() - t0) * 1000)
        if not ok:
            errors.append(1)


def pct(values, p):
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round(p / 100 * len(values) + 0.5)) - 1))
    return values[k]


async def run(base_url, users):
    latencies, errors = [], []
    limits = httpx.Limits(max_connections=users, max_keepalive_connections=users)
    async with httpx.AsyncClient(base_url=base_url, timeout=60, limits=limits) as client:
        start = time.perf_counter()
        await asyncio.gather(*[
            user(client, RAMPUP * i / users, latencies, errors) for i in range(users)
        ])
        elapsed = time.perf_counter() - start
    return {
        "users": users, "requests": len(latencies),
        "avg_ms": round(statistics.mean(latencies), 1),
        "median_ms": round(statistics.median(latencies), 1),
        "p90_ms": round(pct(latencies, 90), 1),
        "p95_ms": round(pct(latencies, 95), 1),
        "p99_ms": round(pct(latencies, 99), 1),
        "max_ms": round(max(latencies), 1),
        "throughput_rps": round(len(latencies) / elapsed, 1),
        "error_pct": round(100 * len(errors) / len(latencies), 2),
        "duration_s": round(elapsed, 1),
    }


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    levels = [int(x) for x in sys.argv[2:]] or [100, 500, 1000]
    results = []
    for users in levels:
        res = asyncio.run(run(base_url, users))
        print(json.dumps(res, ensure_ascii=False))
        results.append(res)
        time.sleep(5)
    return results


if __name__ == "__main__":
    main()
