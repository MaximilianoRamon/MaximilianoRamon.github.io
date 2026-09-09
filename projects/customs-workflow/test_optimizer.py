"""Hand-calculated checks and accounting checks for the simulation."""

import tempfile
import unittest
from pathlib import Path
from statistics import mean

from customs_optimizer import Shipment, STAGES, analyze, load_shipments, simulate


class WorkflowTests(unittest.TestCase):
    def test_one_file_does_not_wait_or_start_before_arrival(self):
        report = simulate([Shipment("A", 100, 120, 10, 5, 1)], (1, 1, 1), "fifo")
        self.assertEqual(report["avg_turnaround_min"], 16)
        self.assertEqual(sum(report["avg_wait_min_by_stage"].values()), 0)
        self.assertEqual(report["on_time_pct"], 100)

    def test_known_two_file_schedule_and_stage_waits(self):
        # Review completes at 1 and 2; entry at 6 and 11; handoff at 7 and 12.
        files = [Shipment("A", 0, 10, 1, 5, 1), Shipment("B", 0, 10, 1, 5, 1)]
        report = simulate(files, (1, 1, 1), "fifo")
        self.assertEqual(report["avg_turnaround_min"], 9.5)
        self.assertEqual(report["avg_wait_min_by_stage"][STAGES[0]], .5)
        self.assertEqual(report["avg_wait_min_by_stage"][STAGES[1]], 2)
        self.assertEqual(report["late_files"], 1)

    def test_shortest_rule_uses_only_available_files(self):
        # A arrives first and must start even though B is shorter and due sooner.
        files = [Shipment("A", 0, 50, 10, 1, 1), Shipment("B", 2, 20, 1, 1, 1)]
        for rule in ("fifo", "shortest", "due_date"):
            report = simulate(files, (1, 1, 1), rule)
            self.assertEqual(report["avg_turnaround_min"], 11.5)

    def test_shortest_rule_known_improvement(self):
        files = [Shipment("A", 0, 30, 9, 1, 1),
                 Shipment("B", 0, 30, 1, 1, 1), Shipment("C", 0, 30, 1, 1, 1)]
        self.assertEqual(simulate(files, (1, 1, 1), "fifo")["avg_turnaround_min"], 12)
        self.assertAlmostEqual(simulate(files, (1, 1, 1), "shortest")["avg_turnaround_min"], 20 / 3)

    def test_all_sample_plans_account_for_every_minute(self):
        files = load_shipments(Path(__file__).with_name("sample_shipments.csv"))
        result = analyze(files)
        service = mean(sum(s.durations) for s in files)
        self.assertEqual(result["scenario_count"], 9)
        for plan in result["scenarios"]:
            self.assertEqual(sum(plan["staffing"]), 4)
            self.assertAlmostEqual(plan["avg_turnaround_min"],
                                   service + sum(plan["avg_wait_min_by_stage"].values()))

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("shipment_id,arrival_min,deadline_min,review_min,entry_min,handoff_min\n"
                            "A,0,30,1,2,3\nA,2,40,2,3,4\n")
            with self.assertRaisesRegex(ValueError, "unique"):
                load_shipments(path)


if __name__ == "__main__":
    unittest.main()
