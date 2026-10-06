"""Plot temperature readings with gaps and anomalies marked."""

import matplotlib

matplotlib.use("Agg")  # draw to a file, no window needed
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

LINE_COLOR = "#2a78d6"
JUMP_COLOR = "#eb6834"
DEVIATION_COLOR = "#1baf7a"
GAP_COLOR = "#d6d5d0"
TEXT_COLOR = "#52514e"
GRID_COLOR = "#e4e3df"


def plot_readings(readings, gaps, jumps, deviations, title, filename):
    """Save a line chart of the readings with gaps shaded and anomalies marked."""
    fig, ax = plt.subplots(figsize=(14, 5), dpi=150)

    # Insert an empty point after each gap start, so the line breaks there
    # instead of drawing a straight line across missing data.
    gap_starts = {gap_start for gap_start, _ in gaps}
    times, temperatures = [], []
    for reading in readings:
        times.append(reading.time)
        temperatures.append(reading.temperature)
        if reading.time in gap_starts:
            times.append(reading.time)
            temperatures.append(float("nan"))
    ax.plot(times, temperatures, color=LINE_COLOR, linewidth=1.2, label="Air temperature")

    for i, (gap_start, gap_end) in enumerate(gaps):
        ax.axvspan(gap_start, gap_end, color=GAP_COLOR, alpha=0.6,
                   label="Gap in data" if i == 0 else None)

    ax.scatter([current.time for _, current in jumps],
               [current.temperature for _, current in jumps],
               marker="^", s=70, color=JUMP_COLOR, edgecolors="white", linewidths=1.5,
               zorder=3, label="Sudden jump (> 1.5 °C in 10 min)")
    ax.scatter([reading.time for reading, _ in deviations],
               [reading.temperature for reading, _ in deviations],
               marker="o", s=50, color=DEVIATION_COLOR, edgecolors="white", linewidths=1.5,
               zorder=3, label="Far from 3-hour mean (> 4 °C)")

    ax.set_title(title, loc="left", fontsize=13, color="#0b0b0b")
    ax.set_ylabel("°C", color=TEXT_COLOR, rotation=0, labelpad=12)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.tick_params(colors=TEXT_COLOR, length=0)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.08), ncol=4,
              frameon=False, labelcolor=TEXT_COLOR)

    fig.tight_layout()
    fig.savefig(filename)
    plt.close(fig)
