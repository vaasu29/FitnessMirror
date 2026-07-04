"""
dashboard.py
Standalone progress dashboard. Run this any time (no webcam needed) to see
charts of your workout history, saved by main.py into data/workouts.db.

Run:
    python dashboard.py
"""
import matplotlib.pyplot as plt
import storage


def show_dashboard():
    rows = storage.get_history(limit=50)
    if not rows:
        print("No workout history yet. Run main.py first to log a session.")
        return

    rows = list(reversed(rows))  # chronological order
    timestamps, exercises, reps, scores, durations = zip(*rows)

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    fig.suptitle("Fitness Mirror - Progress Dashboard", fontsize=14, fontweight="bold")

    axes[0, 0].plot(range(len(reps)), reps, marker="o", color="tab:blue")
    axes[0, 0].set_title("Reps per Session")
    axes[0, 0].set_xlabel("Session #")
    axes[0, 0].set_ylabel("Reps")

    axes[0, 1].plot(range(len(scores)), scores, marker="o", color="tab:green")
    axes[0, 1].set_title("Average Form Score")
    axes[0, 1].set_xlabel("Session #")
    axes[0, 1].set_ylabel("Form Score (%)")
    axes[0, 1].set_ylim(0, 100)

    axes[1, 0].bar(range(len(durations)), [d / 60 for d in durations], color="tab:orange")
    axes[1, 0].set_title("Session Duration")
    axes[1, 0].set_xlabel("Session #")
    axes[1, 0].set_ylabel("Minutes")

    exercise_counts = {}
    for e in exercises:
        exercise_counts[e] = exercise_counts.get(e, 0) + 1
    axes[1, 1].pie(exercise_counts.values(), labels=exercise_counts.keys(), autopct="%1.0f%%")
    axes[1, 1].set_title("Exercise Distribution")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    show_dashboard()
