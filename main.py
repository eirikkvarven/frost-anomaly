"""Fetch 30 days of temperatures from one station and report gaps and anomalies."""

from datetime import date, timedelta

from analysis import find_gaps, find_jumps, find_mean_deviations
from frost import fetch_temperatures
from plot import plot_readings

STATION = "SN18700"  # Oslo-Blindern
DAYS = 30


def main():
    end = date.today()
    start = end - timedelta(days=DAYS)
    readings = fetch_temperatures(STATION, start, end)
    print(f"{len(readings)} readings from {STATION}, "
          f"{readings[0].time:%Y-%m-%d %H:%M} to {readings[-1].time:%Y-%m-%d %H:%M}")

    gaps = find_gaps(readings)
    print(f"\n{len(gaps)} gap(s) in the data")
    for gap_start, gap_end in gaps:
        print(f"  {gap_start:%Y-%m-%d %H:%M} -> {gap_end:%Y-%m-%d %H:%M}  ({gap_end - gap_start})")

    jumps = find_jumps(readings)
    print(f"\n{len(jumps)} sudden jump(s) between readings")
    for previous, current in jumps:
        change = current.temperature - previous.temperature
        print(f"  {current.time:%Y-%m-%d %H:%M}  {previous.temperature:5.1f} -> "
              f"{current.temperature:5.1f} °C  ({change:+.1f})")

    deviations = find_mean_deviations(readings)
    print(f"\n{len(deviations)} reading(s) far from the 3-hour mean")
    for reading, mean in deviations:
        print(f"  {reading.time:%Y-%m-%d %H:%M}  {reading.temperature:5.1f} °C  "
              f"(mean {mean:.1f}, {reading.temperature - mean:+.1f})")

    plot_file = "temperature.png"
    plot_readings(readings, gaps, jumps, deviations,
                  f"Air temperature at {STATION} (Oslo-Blindern), "
                  f"{readings[0].time:%Y-%m-%d} to {readings[-1].time:%Y-%m-%d}", plot_file)
    print(f"\nPlot saved to {plot_file}")


if __name__ == "__main__":
    main()
