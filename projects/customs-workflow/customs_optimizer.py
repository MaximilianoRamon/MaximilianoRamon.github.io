"""Compare staffing and queue rules for a simulated customs brokerage workflow.

Personal portfolio prototype inspired by Agencia Aduanal experience in Acuna.
All shipment records are synthetic. Results are model outcomes, not employer
measurements or a prediction of government clearance or border crossing times.
Uses only the Python standard library. Run this file to reproduce results.json.
"""

import argparse
import csv
import heapq
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


STAGES = ("Document review", "Entry preparation", "Client handoff")
RULES = ("fifo", "shortest", "due_date")
BASELINE_STAFF = (1, 2, 1)


@dataclass(frozen=True)
class Shipment:
    shipment_id: str
    arrival_min: int
    deadline_min: int
    review_min: int
    entry_min: int
    handoff_min: int

    @property
    def durations(self):
        return (self.review_min, self.entry_min, self.handoff_min)


def generate_sample(path):
    """Create the same 120 invented files every time; seed = 2026."""
    rng = random.Random(2026)
    rows = []
    for day in range(5):
        arrivals = sorted(rng.sample(range(360), 24))
        for arrival in arrivals:
            arrival += day * 480
            rows.append(Shipment(
                f"DEMO-{len(rows) + 1:03d}", arrival,
                arrival + rng.randint(40, 80),
                round(rng.triangular(8, 24, 14)),
                rng.randint(6, 12), rng.randint(2, 6),
            ))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(Shipment.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(row.__dict__ for row in rows)


def load_shipments(path):
    shipments = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            shipment = Shipment(row["shipment_id"], **{
                key: int(value) for key, value in row.items()
                if key != "shipment_id"
            })
            if (shipment.arrival_min < 0
                    or shipment.deadline_min < shipment.arrival_min
                    or min(shipment.durations) <= 0):
                raise ValueError("Arrival, deadline, or processing time is invalid.")
            shipments.append(shipment)
    if not shipments:
        raise ValueError("The input needs at least one shipment.")
    if len({s.shipment_id for s in shipments}) != len(shipments):
        raise ValueError("Shipment IDs must be unique.")
    return shipments


def allocations(total=4):
    """All staffing splits with at least one person at each of three stages."""
    for review in range(1, total - 1):
        for entry in range(1, total - review):
            yield (review, entry, total - review - entry)


def simulate(shipments, staffing, rule):
    """Advance between arrivals and completions instead of ticking a clock.

    A worker handles one file at a time. Files visit every stage in order.
    Queue rules only select among files that have already reached that stage.
    """
    if not shipments or len(staffing) != 3 or any(n < 1 for n in staffing):
        raise ValueError("Need shipments and at least one worker at each stage.")
    if rule not in RULES:
        raise ValueError("Unknown queue rule.")

    # Event type 0 = completion, 1 = arrival. Tuple ordering resolves ties.
    events = [(s.arrival_min, 1, 0, i) for i, s in enumerate(shipments)]
    heapq.heapify(events)
    idle = list(staffing)
    queues = [[], [], []]
    waits = [[], [], []]
    finished = {}

    while events:
        now = events[0][0]
        # Collect simultaneous events before assigning any idle workers.
        while events and events[0][0] == now:
            _, event_type, stage, index = heapq.heappop(events)
            if event_type == 0:
                idle[stage] += 1
                stage += 1
            if stage == len(STAGES):
                finished[index] = now
            else:
                queues[stage].append((now, index))

        for stage in range(len(STAGES)):
            def priority(item):
                ready, index = item
                shipment = shipments[index]
                if rule == "shortest":
                    return (shipment.durations[stage], ready, index)
                if rule == "due_date":
                    return (shipment.deadline_min, ready, index)
                return (ready, index)

            while idle[stage] and queues[stage]:
                selected = min(queues[stage], key=priority)
                queues[stage].remove(selected)
                ready, index = selected
                waits[stage].append(now - ready)
                idle[stage] -= 1
                end = now + shipments[index].durations[stage]
                heapq.heappush(events, (end, 0, stage, index))

    if len(finished) != len(shipments):
        raise RuntimeError("A shipment did not complete the workflow.")
    turnaround = [finished[i] - s.arrival_min for i, s in enumerate(shipments)]
    late = sum(finished[i] > s.deadline_min for i, s in enumerate(shipments))
    return {
        "staffing": list(staffing),
        "rule": rule,
        "avg_turnaround_min": mean(turnaround),
        "p90_turnaround_min": sorted(turnaround)[math.ceil(.9 * len(turnaround)) - 1],
        "avg_wait_min_by_stage": {name: mean(waits[i]) for i, name in enumerate(STAGES)},
        "late_files": late,
        "on_time_pct": 100 * (len(shipments) - late) / len(shipments),
    }


def analyze(shipments):
    baseline = simulate(shipments, (1, 2, 1), "fifo")
    plans = [
        simulate(shipments, staff, rule)
        for staff in allocations(total=4)
        for rule in ("fifo", "shortest", "due_date")
    ]
    best = min(plans, key=lambda p: p["avg_turnaround_min"])
    reduction = 100 * (1 - best["avg_turnaround_min"] / baseline["avg_turnaround_min"])
    bottleneck = max(baseline["avg_wait_min_by_stage"],
                     key=baseline["avg_wait_min_by_stage"].get)
    return {
        "data_type": "synthetic",
        "seed": 2026,
        "shipment_count": len(shipments),
        "staff_count": sum(BASELINE_STAFF),
        "scenario_count": len(plans),
        "objective": "Lowest mean file turnaround among the nine tested plans",
        "bottleneck": bottleneck,
        "baseline": baseline,
        "best": best,
        "reduction_pct": reduction,
        "scenarios": sorted(plans, key=lambda p: p["avg_turnaround_min"]),
        "assumptions": [
            "All records, durations, and internal deadlines are invented.",
            "Four staff are fully cross-trained and each works on one file at a time.",
            "Each file visits review, entry preparation, and client handoff in order.",
            "Processing times are known exactly; real deployments would need estimates.",
            "No interruptions, rework, breaks, shift closures, or reassignment costs.",
            "No government inspections, border queues, transport times, or clearance decisions.",
            "Best means best of nine tested plans on this one dataset; no global guarantee.",
        ],
    }


def main():
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=folder / "sample_shipments.csv")
    parser.add_argument("--output", type=Path, default=folder / "results.json")
    parser.add_argument("--generate-sample", action="store_true")
    args = parser.parse_args()
    if args.generate_sample:
        generate_sample(args.data)
    report = analyze(load_shipments(args.data))
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    before = report["baseline"]["avg_turnaround_min"]
    after = report["best"]["avg_turnaround_min"]
    print("SYNTHETIC CUSTOMS WORKFLOW SIMULATION")
    print(f"{report['shipment_count']} files | {report['scenario_count']} plans | 4 staff")
    print(f"Bottleneck: {report['bottleneck']}")
    print(f"Mean file turnaround: {before:.1f} -> {after:.1f} min")
    print(f"Simulated reduction: {report['reduction_pct']:.1f}%")
    print(f"Staffing (review / entry / handoff): {report['best']['staffing']}")
    print(f"Queue rule: {report['best']['rule']}")


if __name__ == "__main__":
    main()
