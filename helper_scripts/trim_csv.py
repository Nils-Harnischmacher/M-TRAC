import argparse
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def parse_args():
    p = argparse.ArgumentParser(
        description="Interactively trim a CSV by start/end sample index and save the result."
    )
    p.add_argument("csv", help="Path to the input CSV file")
    p.add_argument(
        "--cols",
        nargs=3,
        required=True,
        metavar=("COL1", "COL2", "COL3"),
        help="Exactly three columns to plot",
    )
    p.add_argument(
        "--sample-col",
        default=None,
        help="Column to use as sample number (default: auto-generate)",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Output CSV path (default: <input>_trimmed.csv in same folder)",
    )
    p.add_argument(
        "--delimiter",
        default=None,
        help="CSV delimiter (default: auto-detect by pandas)",
    )
    return p.parse_args()


def plot_view(df, sample_col, cols, title_suffix=""):
    plt.clf()
    plt.title(f"Interactive trim view {title_suffix}")
    plt.xlabel(sample_col)
    plt.grid(True, which="both", linestyle="--", alpha=0.4)

    for c in cols:
        plt.plot(df[sample_col], df[c], label=c, linewidth=1.2)

    plt.legend()
    plt.pause(0.001)  # Keep plot interactive


def ask_sample_point(df, sample_col, cols, mode_label):
    """
    Loop asking the user for a sample index until they confirm.
    Returns the chosen index (integer).
    """
    max_sample = int(df[sample_col].max())
    while True:
        print(
            f"\nEnter {mode_label} sample index (0 to {max_sample}): "
        )
        user_input = input(f"{mode_label} sample index: ").strip()
        if not user_input.isdigit():
            print("Please enter a valid integer.")
            continue

        idx = int(user_input)
        if idx < 0 or idx > max_sample:
            print(f"Index out of bounds (0 to {max_sample}). Try again.")
            continue

        # Show preview with trimming on the chosen side
        if mode_label.lower() == "start":
            preview = df[df[sample_col] >= idx]
            suffix = f"(preview: start @ sample {idx})"
        else:
            preview = df[df[sample_col] <= idx]
            suffix = f"(preview: end @ sample {idx})"

        plot_view(preview, sample_col, cols, title_suffix=suffix)
        print(f"Previewing with {mode_label.lower()} at sample = {idx}")
        ok = input("Happy with this? [y/N]: ").strip().lower()
        if ok == "y":
            return idx
        else:
            print("Okay, let's try a different sample index.")


def main():
    args = parse_args()
    path = Path(args.csv)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    # Load CSV
    try:
        df = pd.read_csv(path, delimiter=args.delimiter)
    except Exception as e:
        print(f"Failed to read CSV: {e}", file=sys.stderr)
        sys.exit(1)

    needed = list(args.cols)
    missing = [c for c in needed if c not in df.columns]
    if missing:
        print(f"CSV is missing required columns: {missing}", file=sys.stderr)
        sys.exit(1)

    # Prepare sample column
    if args.sample_col and args.sample_col in df.columns:
        sample_col = args.sample_col
    else:
        sample_col = "SampleIndex"
        df[sample_col] = range(len(df))  # Create sample index

    # Plot initial data
    plt.ion()
    plot_view(df, sample_col, args.cols, title_suffix="(initial)")

    # Ask for start
    print("\n--- Choose START sample index ---")
    start_idx = ask_sample_point(df, sample_col, args.cols, "Start")

    # Ask for end
    print("\n--- Choose END sample index ---")
    end_idx = ask_sample_point(df, sample_col, args.cols, "End")

    # Ensure proper ordering
    if end_idx <= start_idx:
        print(
            f"End index ({end_idx}) must be greater than start index ({start_idx}). "
            "Swapping them just in case."
        )
        start_idx, end_idx = min(start_idx, end_idx), max(start_idx, end_idx)

    # Final preview of the slice
    final_df = df[(df[sample_col] >= start_idx) & (df[sample_col] <= end_idx)].reset_index(drop=True)
    plot_view(final_df, sample_col, args.cols, title_suffix="(final selection)")
    print(
        f"\nFinal selection:\nStart sample = {start_idx}\n"
        f"End sample   = {end_idx}\n"
        f"Rows kept    = {len(final_df)}"
    )
    ok = input("Save this selection? [y/N]: ").strip().lower()
    if ok != "y":
        print("Aborted without saving.")
        return

    out_path = Path(args.out) if args.out else path.with_name(path.stem + "_trimmed.csv")
    try:
        final_df.to_csv(out_path, index=False)
    except Exception as e:
        print(f"Failed to save CSV: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Saved trimmed CSV to: {out_path.resolve()}")
    print("Done.")
    plt.ioff()
    plt.show()


if __name__ == "__main__":
    main()
