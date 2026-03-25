import sys
import os
import argparse
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fetcher import load_all_data
from tree import NaryTree


def fmt_time(seconds: float | None) -> str:
    """Formats lap duration as M:SS.mmm or N/A."""
    if seconds is None:
        return "N/A"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}:{s:06.3f}"


def main():
    parser = argparse.ArgumentParser(description="F1 N-ary Tree CLI demo")
    parser.add_argument("--refresh", action="store_true", help="Force re-fetch data from API")
    args = parser.parse_args()

    # Step 1. Load data and build tree
    print("-" * 15)
    print("Step 1: Loading data from OpenF1 API / cache")
    print("-" * 15)
    t0 = time.time()
    meetings, sessions, laps = load_all_data(force=args.refresh)
    print(f"  Raw records — meetings: {len(meetings)}, sessions: {len(sessions)}, laps: {len(laps)}")

    print("\nBuilding N-ary tree...")
    tree = NaryTree()
    tree.build_from_data(meetings, sessions, laps)
    elapsed = time.time() - t0

    summary = tree.summary()
    print(f"\nTree summary (built in {elapsed:.2f}s):")
    for k, v in summary.items():
        print(f"  {k:20s}: {v:,}")

    if summary["lap"] < 10_000:
        print(f"\n  NOTE: Only {summary['lap']:,} laps loaded. Run with --refresh to fetch full dataset,")
        print("  or ensure data/laps_all.json exists with a full pull.")

    # Step 2. DFS traversal demo
    print("\n" + "-" * 20)
    print("Steps 2: DFS Pre-order Traversal for first 30 nodes")
    print("-" * 20)
    for i, (depth, node) in enumerate(tree.dfs_traversal()):
        if i >= 30:
            print("  ...")
            break
        indent = "  " * depth
        label = (node.data.get("meeting_name")
                 or node.data.get("session_name")
                 or f"Driver #{node.data.get('driver_number')}"
                 or f"Lap {node.data.get('lap_number')}"
                 or node.key)
        print(f"  {indent}[{node.node_type.upper():8s}] {label}")

    # Step 3. BFS traversal demo
    print("\n" + "-" * 15)
    print("Step 3: BFS Traversal (first 30 nodes)")
    print("-" * 15)
    for i, (depth, node) in enumerate(tree.bfs_traversal()):
        if i >= 30:
            print("  ...")
            break
        label = (node.data.get("meeting_name")
                 or node.data.get("session_name")
                 or f"Driver #{node.data.get('driver_number')}"
                 or f"Lap {node.data.get('lap_number')}"
                 or node.key)
        print(f"  depth={depth}  [{node.node_type.upper():8s}] {label}")

    # Step 4. O(1) key lookup
    print("\n" + "-" * 15)
    print("Step 4: O(1) Key Lookup")
    print("-" * 15)
    if tree.root.children:
        first_meeting = tree.root.children[0]
        mk = first_meeting.data["meeting_key"]
        key = f"meeting_{mk}"
        t1 = time.time()
        found = tree.find_node(key)
        t2 = time.time()
        print(f"  find_node('{key}') → {found}")
        print(f"  Lookup time: {(t2-t1)*1e6:.2f} microseconds (O(1) hash table)")

    # Step 5. Field-based search
    # ------------------------------------------------------------------
    print("\n" + "-" * 15)
    print("Step  5: Field-based Search (session_type == 'Race')")
    print("-" * 15)
    race_sessions = tree.search_by_field("session", "session_type", "Race")
    print(f"  Found {len(race_sessions)} Race sessions")
    for s in race_sessions[:5]:
        print(f"    session_key={s.data['session_key']} | {s.data.get('session_name')} "
              f"| drivers={len(s.children)}")
    if len(race_sessions) > 5:
        print(f"    ... and {len(race_sessions)-5} more")

    # Step 6. Driver lap statistics (first race session, first driver)
    print("\n" + "-" * 15)
    print("Step  6: Driver Lap Statistics")
    print("-" * 15)
    if race_sessions:
        s_node = race_sessions[0]
        sk = s_node.data["session_key"]
        print(f"  Session: {s_node.data.get('session_name')} (key={sk})")
        if s_node.children:
            first_driver = s_node.children[0]
            dn = first_driver.data["driver_number"]
            stats = tree.get_driver_stats(sk, dn)
            print(f"  Driver #{dn} stats:")
            print(f"    Lap count  : {stats.get('lap_count')}")
            print(f"    Valid laps : {stats.get('valid_laps')}")
            print(f"    Missing dur: {stats.get('missing_laps')}  ← noisy data")
            print(f"    Best lap   : {fmt_time(stats.get('best_lap'))}")
            print(f"    Avg lap    : {fmt_time(stats.get('avg_lap'))}")

    # Step 7. Session leaderboard
    print("\n" + "-" * 15)
    print("Step  7: Session Leaderboard (top 5 drivers by best lap)")
    print("-" * 15)
    if race_sessions:
        sk = race_sessions[0].data["session_key"]
        board = tree.get_session_leaderboard(sk)
        print(f"  {'Pos':>3}  {'Driver':>7}  {'Best Lap':>10}  {'Avg Lap':>10}  {'Valid':>5}  {'Miss':>4}")
        print("  " + "-" * 50)
        for pos, d in enumerate(board[:10], 1):
            print(f"  {pos:>3}  #{d['driver_number']:>5}  "
                  f"{fmt_time(d['best_lap']):>10}  "
                  f"{fmt_time(d['avg_lap']):>10}  "
                  f"{d['valid_laps']:>5}  "
                  f"{d['missing_laps']:>4}")
    # 8. Noise summary
    print("\n" + "-" * 15)
    print("Step 8: Noise / Missing Data Summary")
    print("-" * 15)
    missing_dur = 0
    total_laps = 0
    for _, node in tree.dfs_traversal():
        if node.node_type == "lap":
            total_laps += 1
            if node.data.get("lap_duration") is None:
                missing_dur += 1

    pct = (missing_dur / total_laps * 100) if total_laps else 0
    print(f"  Total lap nodes   : {total_laps:,}")
    print(f"  Missing lap_dur   : {missing_dur:,}  ({pct:.1f}%) ← pit-out laps, VSC, etc.")
    print(f"  These are stored  : tree keeps the node; stats exclude None values")

    print("\n" + "-" * 60)
    print("Done. Run  python app.py  to launch the web UI.")
    print("-" * 60)


if __name__ == "__main__":
    main()
