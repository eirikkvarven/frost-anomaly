# Walkthrough

This document explains the program file by file, the main choices behind it,
and what could have been done differently. For setup and usage, see
[README.md](README.md).

## Overview

```
main.py ──► frost.py      fetch readings from the Frost API
        ──► analysis.py   find gaps, jumps and deviations
        ──► plot.py       draw temperature.png
```

Data flows in one direction. `frost.py` turns the API response into a sorted
list of `Reading` objects. Everything after that works on this list and knows
nothing about Frost. That split is the most important design choice in the
project: the analysis can be tested with made-up data, and could be pointed at
another data source (for example a real IoT sensor) without changes.

---

## frost.py – fetching data

### `Reading`

```python
@dataclass(frozen=True)
class Reading:
    time: datetime
    temperature: float
```

One measurement. It is a dataclass instead of a tuple so the code can say
`reading.temperature` instead of `reading[1]`. `frozen=True` makes it
read-only, so a reading cannot be changed by accident after it is created.

The time is a real `datetime`, not the text string Frost sends. That makes it
possible to subtract two times and compare the result with a `timedelta`,
which is what gap and window detection need.

### `get_client_id()`

Reads the Frost client ID from the environment variable `FROST_CLIENT_ID`,
or from `client_id.txt`. The file is in `.gitignore`, so the ID never ends up
in the code or on GitHub. If neither exists, the program stops with a message
saying what to do, instead of failing later with an unclear 401 error.

### `fetch_temperatures(station, start, end)`

Calls the Frost observations endpoint and returns the readings sorted by time.

**Choosing the time series.** Without filtering, Frost returned five series for
Blindern at the same time: sensors at 2 m and 10 m above ground, and values
per minute, per 10 minutes and per hour. That gave more than 3000 rows for one
day, with each time appearing several times. The request now asks for
`levels=2` (the standard height for air temperature) and
`timeresolutions=PT10M`. Ten minutes was chosen because:

- 30 days is 4320 readings – enough detail to see sudden jumps, small enough
  to handle in plain Python lists.
- It is close to how often wireless sensors typically report.
- One-minute data (43 200 readings) is noisy; hourly data (720 readings)
  smooths out the short jumps we want to find.

Filtering in the request rather than in Python also means less data over the
network.

**Removing duplicates.** Readings are collected in a dict keyed by time:

```python
by_time.setdefault(time, observation["value"])
```

A dict key can only exist once, so duplicates disappear automatically.
`setdefault` keeps the first value if the same time shows up again. After
filtering, Frost did not actually send any duplicates, but the API does not
promise unique times, so the check is cheap insurance.

Finally the list is sorted by time. All functions in `analysis.py` rely on
that order.

**One request.** 30 days of 10-minute data is far below Frost's limit per
request, so there is no paging.

---

## analysis.py – gaps and anomalies

All three functions take a sorted list of `Reading` and return a list of
findings. They have no side effects and do not print anything, which makes
them easy to test.

### `find_gaps(readings, expected_interval=10 min)`

Walks through the readings in pairs, using `zip(readings, readings[1:])` to
get each reading together with the next one. If two neighbours are more than
`expected_interval` apart, at least one reading is missing, and the pair
`(last_before, first_after)` is recorded as a gap.

Even a single missing reading counts as a gap. For a sensor that is a real
signal; for a noisy station it could be loosened by passing a larger
`expected_interval`.

Blindern had no gaps in the 30 days used here (exactly 30 × 144 = 4320
readings), so this function is mainly shown to work through the tests.

### `find_jumps(readings, threshold=1.5, expected_interval=10 min)`

Same pairwise walk. A jump is a change of more than `threshold` °C between two
neighbours.

Neighbours on each side of a gap are skipped. If the station is silent for two
hours, a large change across that gap is not a "sudden jump" – the
temperature had two hours to change.

### `find_mean_deviations(readings, threshold=4.0, window=3 h)`

For each reading, takes the mean of the readings in the 3 hours *before* it
and flags the reading if it is more than `threshold` °C from that mean.

Details worth knowing:

- **The reading itself is not part of the mean.** Otherwise a large spike would
  pull the mean towards itself and partly hide.
- **The window is measured in time, not in a number of readings.** If data is
  missing, "the last 18 readings" could cover many hours; "the last 3 hours"
  always means the same thing.
- **A sliding start index.** `window_start` only moves forward, so the loop
  never has to search from the beginning. Each reading is added to and removed
  from the window once. The mean itself is still recomputed with `sum()` each
  time, which is fine for 4320 readings.
- Readings with nothing before them in the window (the very first reading, or
  the first after a long gap) are skipped, since there is no mean to compare
  with.

### How the thresholds were chosen

Before choosing, the 30 days of Blindern data were measured:

| | Typical | 99th percentile | Max |
|---|---|---|---|
| Change between two readings | 0.1 °C | 1.0 °C | 2.4 °C |
| Distance from 3-hour mean | 0.6 °C | 3.5 °C | 4.7 °C |

Thresholds of 1.5 °C (jumps) and 4 °C (mean) give 7 and 18 hits – rare enough
that each one is worth looking at. The alternative for the mean was a
statistical threshold (more than 4 standard deviations from the window). It
adapts to how much the temperature is varying, but is harder to explain and
fires too easily when the temperature has been almost perfectly flat, since the
standard deviation is then close to zero.

### What the results show

On 9 September around midday, both methods fire together: the temperature
rises fast and then drops almost 7 °C in an hour, which looks like a rain
shower. Most other mean deviations are sunny mornings (6, 21 and 29
September), where the temperature rises 4 °C within a few hours. That is
normal weather, not a sensor problem – see "What could have been done
differently" below.

---

## plot.py – the chart

`plot_readings` draws one line chart with matplotlib and saves it to a file.

- `matplotlib.use("Agg")` makes matplotlib draw straight to a file without
  opening a window, so the program also works on a server or in CI.
- **Breaking the line at gaps.** matplotlib connects every point with a
  straight line, which would make a gap look like the station was measuring.
  A `NaN` value is inserted after each gap start; matplotlib does not draw
  through `NaN`, so the line breaks. Gaps are also shaded grey.
- **Jumps and deviations use different shapes** (triangles and circles), not
  only different colours, so they can be told apart by colour-blind readers
  and on black-and-white print.
- The legend sits below the chart so it never covers data, and the date axis
  shows every third day so the labels do not overlap.

---

## main.py – putting it together

Sets the station and number of days, calls the three steps in order, prints
the findings and saves the chart. `STATION` and `DAYS` are constants at the
top, so changing them does not require reading the rest of the code.

The period is the last 30 full days. Frost treats the end of `referencetime`
as exclusive, so with today's date as the end, today's partial data is not
included.

---

## test_analysis.py – tests

Uses `unittest` from the standard library, so no extra package is needed:

```bash
python -m unittest
```

Two helpers build made-up data: `readings_at([(minutes, temperature), ...])`
and `steady(count)` for a flat series. The 17 tests cover:

- **Gaps:** one missing reading, several gaps, a custom interval, empty and
  single-reading lists.
- **Jumps:** jumps up and down, a change exactly at the threshold (not a
  jump), no comparison across a gap, empty list.
- **Mean deviations:** a spike and a drop after a flat period, slow warming
  that should *not* fire, the window forgetting old readings, the first
  reading being skipped, empty list.

The window test was first written so that it passed for the wrong reason (the
window was empty, so nothing was ever compared). It was rewritten, and then
checked by deliberately breaking the window code in `analysis.py` to make sure
the test fails. A test that cannot fail does not prove anything.

---

## What could have been done differently

**Daily cycle.** The biggest weakness is that the mean-deviation check only
looks backwards and does not know that it normally gets warmer at 07:00. Most
of its hits are sunny mornings. Better options:

- Compare each reading with the same time of day over the previous days.
- Remove the daily cycle first, then look for deviations in what is left.
- Use a centred window (before *and* after), if the analysis does not need to
  run in real time.

**Grouping hits into events.** Five readings in a row on the morning of
21 September are reported as five separate deviations. Grouping consecutive
hits into one event with a start and end time would make the output shorter
and closer to how an alert system would work.

**Real-time use.** The program analyses 30 days at once. A sensor system would
process one reading at a time as it arrives. The functions could be rewritten
to keep a small state (last reading, current window) and check each new value
immediately.

**Sensor faults vs. weather.** The program flags *unusual* values but cannot
say whether the cause is the weather or a broken sensor. Comparing with nearby
stations would help: if only one station jumps, the sensor is suspect.

**Frost's own quality flags.** Each observation has a `qualityCode`. It is
ignored here; it could be used to drop readings that MET Norway has already
marked as doubtful.

**pandas.** pandas has built-in time-based rolling windows and would make
`find_mean_deviations` a few lines shorter. Plain Python was chosen to keep
the dependencies small and to make every step of the logic visible.

**Error handling.** If Frost returns no data for the period (for example a
station that was down), `main.py` will fail on `readings[0]`. Network errors
are only reported through `raise_for_status()`. Both would need clearer
handling in a tool used by others.

**Configuration.** Station, period and thresholds are constants in the code.
Command-line arguments (`argparse`) would make it possible to try another
station without editing files.
