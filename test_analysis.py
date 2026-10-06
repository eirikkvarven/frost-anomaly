"""Tests for analysis.py using made-up readings. Run with: python -m unittest"""

import unittest
from datetime import datetime, timedelta

from analysis import find_gaps, find_jumps, find_mean_deviations
from frost import Reading

START = datetime(2026, 1, 1)


def readings_at(minutes_and_temperatures):
    """Build readings from (minutes after START, temperature) pairs."""
    return [Reading(START + timedelta(minutes=m), t) for m, t in minutes_and_temperatures]


def steady(count, temperature=10.0):
    """count readings 10 minutes apart, all with the same temperature."""
    return readings_at([(i * 10, temperature) for i in range(count)])


class FindGapsTest(unittest.TestCase):
    def test_no_gaps_in_regular_data(self):
        self.assertEqual(find_gaps(steady(10)), [])

    def test_one_missing_reading_is_a_gap(self):
        readings = readings_at([(0, 10), (10, 10), (30, 10)])
        self.assertEqual(find_gaps(readings), [(readings[1].time, readings[2].time)])

    def test_finds_several_gaps(self):
        readings = readings_at([(0, 10), (60, 10), (70, 10), (200, 10)])
        gaps = find_gaps(readings)
        self.assertEqual(gaps, [(readings[0].time, readings[1].time),
                                (readings[2].time, readings[3].time)])

    def test_custom_interval(self):
        readings = readings_at([(0, 10), (30, 10), (60, 10)])
        self.assertEqual(find_gaps(readings, expected_interval=timedelta(minutes=30)), [])

    def test_empty_and_single_reading(self):
        self.assertEqual(find_gaps([]), [])
        self.assertEqual(find_gaps(steady(1)), [])


class FindJumpsTest(unittest.TestCase):
    def test_small_changes_are_not_jumps(self):
        readings = readings_at([(0, 10.0), (10, 11.0), (20, 10.0)])
        self.assertEqual(find_jumps(readings), [])

    def test_finds_jumps_up_and_down(self):
        readings = readings_at([(0, 10.0), (10, 12.0), (20, 12.0), (30, 9.0)])
        self.assertEqual(find_jumps(readings), [(readings[0], readings[1]),
                                                (readings[2], readings[3])])

    def test_change_equal_to_threshold_is_not_a_jump(self):
        readings = readings_at([(0, 10.0), (10, 11.5)])
        self.assertEqual(find_jumps(readings), [])

    def test_does_not_compare_across_a_gap(self):
        readings = readings_at([(0, 10.0), (120, 20.0)])
        self.assertEqual(find_jumps(readings), [])

    def test_empty(self):
        self.assertEqual(find_jumps([]), [])


class FindMeanDeviationsTest(unittest.TestCase):
    def test_steady_data_has_no_deviations(self):
        self.assertEqual(find_mean_deviations(steady(30)), [])

    def test_finds_spike_after_steady_period(self):
        readings = steady(18) + readings_at([(180, 15.0)])
        self.assertEqual(find_mean_deviations(readings), [(readings[-1], 10.0)])

    def test_finds_drop_below_mean(self):
        readings = steady(18) + readings_at([(180, 5.0)])
        self.assertEqual(find_mean_deviations(readings), [(readings[-1], 10.0)])

    def test_gradual_warming_is_not_a_deviation(self):
        readings = readings_at([(i * 10, 10 + i * 0.1) for i in range(40)])
        self.assertEqual(find_mean_deviations(readings), [])

    def test_readings_older_than_window_are_ignored(self):
        # 0 °C for 3 hours, then 10 °C. Right after the change the cold
        # readings are in the window, but 3 hours later they must not count.
        readings = readings_at([(i * 10, 0.0 if i < 18 else 10.0) for i in range(48)])
        flagged_times = [reading.time for reading, _ in find_mean_deviations(readings)]
        self.assertIn(START + timedelta(minutes=180), flagged_times)
        self.assertTrue(all(t < START + timedelta(minutes=360) for t in flagged_times))

    def test_first_reading_is_skipped(self):
        self.assertEqual(find_mean_deviations(readings_at([(0, 50.0)])), [])

    def test_empty(self):
        self.assertEqual(find_mean_deviations([]), [])


if __name__ == "__main__":
    unittest.main()
