"""Find gaps and anomalies in a list of readings sorted by time."""

from datetime import timedelta


def find_gaps(readings, expected_interval=timedelta(minutes=10)):
    """Return (last_before, first_after) for every gap in the data.

    A gap is two consecutive readings further apart than expected_interval,
    meaning at least one reading is missing between them.
    """
    gaps = []
    for previous, current in zip(readings, readings[1:]):
        if current.time - previous.time > expected_interval:
            gaps.append((previous.time, current.time))
    return gaps


def find_jumps(readings, threshold=1.5, expected_interval=timedelta(minutes=10)):
    """Return (previous, current) for every sudden jump between two readings.

    A jump is a change of more than threshold degrees between consecutive
    readings. Readings on each side of a gap are not compared, since the
    temperature can change a lot while the station is silent.
    """
    jumps = []
    for previous, current in zip(readings, readings[1:]):
        if current.time - previous.time > expected_interval:
            continue
        if abs(current.temperature - previous.temperature) > threshold:
            jumps.append((previous, current))
    return jumps


def find_mean_deviations(readings, threshold=4.0, window=timedelta(hours=3)):
    """Return (reading, mean) for every reading far from the recent mean.

    The mean is taken over the readings in the window before each reading,
    not including the reading itself. Readings with nothing before them in
    the window are skipped.
    """
    deviations = []
    window_start = 0
    for i, reading in enumerate(readings):
        while readings[window_start].time < reading.time - window:
            window_start += 1
        recent = readings[window_start:i]
        if not recent:
            continue
        mean = sum(r.temperature for r in recent) / len(recent)
        if abs(reading.temperature - mean) > threshold:
            deviations.append((reading, mean))
    return deviations
