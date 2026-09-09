# Customs Workflow Optimizer

A personal Python portfolio prototype inspired by Maximiliano Ramon's exposure to cross-border operations at Agencia Aduanal in Acuña, Mexico.

**All 120 shipment records are synthetic. The results describe this simulation, not measured improvements at Agencia Aduanal.** This model covers internal file handling; it does not model government clearance decisions, border queues, or transportation.

## The question

Where do shipment files spend the most time waiting, and can the same four people process them more efficiently?

Each file passes through document review, entry preparation, and client handoff. The baseline assigns one person to review, two to preparation, and one to handoff, with files served first in, first out.

## What the program does

1. Loads arrival times, internal deadlines, and processing times from a CSV.
2. Simulates arrivals and task completions using a priority queue. A file waits until a worker is free and completes all three stages in order.
3. Records waiting time by stage and total time from arrival to final handoff.
4. Tests all three positive staffing splits of four people across three stages, each with three queue rules: first in, first out; shortest available task; and earliest internal deadline.
5. Selects the lowest average file turnaround among those nine plans.

This is a discrete-event simulation and a small exhaustive scenario comparison. It is not machine learning, and it does not establish a universally optimal staffing policy.

## Reproduced results

| Metric | Baseline | Selected plan |
|---|---:|---:|
| Synthetic files | 120 | 120 |
| Total staff | 4 | 4 |
| Staff: review / preparation / handoff | 1 / 2 / 1 | 2 / 1 / 1 |
| Queue rule | First in, first out | Shortest available task |
| Mean file turnaround | 56.0 min | 33.6 min |
| 90th percentile turnaround | 88 min | 43 min |
| Mean wait for document review | 27.48 min | 1.65 min |
| Mean wait for entry preparation | 0.00 min | 3.43 min |
| Files within synthetic internal deadlines | 66.7% | 97.5% |
| Files past those deadlines | 40 | 3 |

The simulated mean turnaround reduction is **40.0%**, calculated using the unrounded means:

```text
100 × (55.9916666667 − 33.5833333333) / 55.9916666667
= 40.020836434% → 40.0%
```

Document review is the baseline bottleneck because its queue has the highest mean wait. The selected plan moves one person from entry preparation to review. Preparation then has a small queue, but the reduction in review waiting is much larger. The team still has four people.

## Run it

Use Python 3.8 or later. No additional packages are needed.

Download `customs_optimizer.py` and `sample_shipments.csv` into the same folder, then run:

```bash
python customs_optimizer.py
```

In Spyder, open and run `customs_optimizer.py` with the sample CSV beside it. The program prints the main findings and writes `results.json` in that folder.

To regenerate the included sample and rerun the analysis:

```bash
python customs_optimizer.py --generate-sample
```

To use a CSV with the same column structure:

```bash
python customs_optimizer.py --data your_sample.csv --output your_results.json
```

The published percentage applies only to the included synthetic dataset. A different dataset can produce a different result. Update provenance labels before using independently sourced input.

## Data and assumptions

`generate_sample()` uses the fixed random seed `2026`. It creates five batches of 24 files, with arrivals spread across 360 minutes per batch and a 480-minute offset between batches. Time is measured in minutes on a continuous model clock; shift closures are not enforced.

| CSV column | Meaning |
|---|---|
| `shipment_id` | Invented file identifier, from DEMO-001 to DEMO-120 |
| `arrival_min` | When the file becomes available to the internal workflow |
| `deadline_min` | Invented internal completion target, 40–80 minutes after arrival |
| `review_min` | Invented document review duration, 8–24 minutes |
| `entry_min` | Invented entry preparation duration, 6–12 minutes |
| `handoff_min` | Invented client handoff duration, 2–6 minutes |

- All four people are assumed to be fully cross-trained, with no reassignment cost.
- Each person handles one file at a time. Work already started is not interrupted.
- Every file visits all three steps exactly once. There are no missing documents, rework loops, breaks, or government inspections in the model.
- Processing times are assumed to be known exactly. An operational tool would need estimates and would need to measure their accuracy.
- Queue rules select only among files already available at the relevant step.
- The objective is average turnaround. Shortest-task scheduling can make longer files wait; a real application would need safeguards for age and deadlines.
- The result comes from one fixed sample. Real records, demand patterns, staffing constraints, and additional samples would need evaluation before any operational recommendation.

## Explain it in an interview

“My customs brokerage experience made me interested in how paperwork affects the supply chain. For a separate personal project, I modeled 120 synthetic shipment files in Python. I measured waiting at three steps and found that document review was the bottleneck. Then I compared nine plans using the same four staff. Moving one person to review and handling shorter available tasks first reduced average turnaround from about 56 to 34 minutes in the model, roughly 40%. The next step would be to test anonymized real records and practical staffing constraints.”

If someone asks what the code actually does: it keeps a list of future arrivals and completions, jumps to the next event, and assigns available workers to waiting files. It repeats that process for each plan, then compares the results.

## Verification

Run the checks from the repository root:

```bash
python -m unittest discover -s projects/customs-workflow -p 'test_*.py' -v
```

The six checks cover hand-calculated completion times, waiting by stage, late-file counts, scheduling only available work, a known shortest-task example, invalid duplicate identifiers, and conservation of service plus waiting time across all nine scenarios.
