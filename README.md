# F1 Race Weekend N-ary Tree Explorer

## Overview

This project pulls real Formula 1 data from the OpenF1 API and organizes it into an N-ary tree structure.

The idea is pretty simple: a race weekend already has a natural hierarchy, so we mirror that in a tree format.

ROOT

|── Meeting (e.g. Belgian Grand Prix 2023)

|── Session (Practice, Qualifying, Sprint, Race)

|── Driver (by driver number)

└── Lap (lap-by-lap timing data)


On top of that, there’s a small web UI where you can click through the tree (kind of like a file explorer) and check things like lap data and session leaderboards.

---

## Project Structure
f1-tree-explorer/

├── app.py # Flask app (routes + templates)

├── run_tree.py # CLI script to build + explore the tree

├── requirements.txt

├── README.md

├── src/

│ ├── tree.py # N-ary tree implementation

│ └── fetcher.py # API calls + caching logic

└── data/ # Cache folder (auto-created)


---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```
Make sure you're using Python 3.10 or newer.

## 2. Run the CLI demo
```bash
python run_tree.py
```
This is the best way to understand what’s going on.

What it does:

Fetches meetings, sessions, and lap data from 2023–2024
Builds the full tree (~30,000+ laps)
Runs DFS and BFS traversals
Prints sample stats and a leaderboard
Reports any missing/noisy data

First run can take ~5–10 minutes because of API calls. After that, everything is cached so it’s fast.

If you want to ignore cache:
```bash
python run_tree.py --refresh
```

## 3. Run the web app
```bash
python app.py
```

Then open: http://127.0.0.1:5000


Core Idea: N-ary Tree

File: src/tree.py

Each node in the tree represents one level of the race weekend.

Node structure

Each TreeNode contains:

- key → unique identifier (like session_9159)
- node_type → one of root, meeting, session, driver, lap
- data → dictionary with metadata
- children → list of child nodes

There’s also a hash map (dict[str, TreeNode]) to quickly look up nodes in O(1) time.

# Traversals
| Method | What it does |
|--------|-------------|
| `dfs_traversal()` | Depth-first (pre-order), useful for full tree walks |
| `bfs_traversal()` | Level-by-level traversal |
| `find_node(key)` | Direct lookup using hash map |
| `search_by_field()` | Linear scan using DFS |

# Complexity
| Step | Time | Space |
|------|------|-------|
| Meetings | O(M) | O(M) |
| Sessions | O(S) | O(S) |
| Laps | O(L) | O(L) |
| **Total** | O(M + S + L) | O(M + S + L) |


Even with ~30k laps, building the tree takes under a second once data is cached.

# Data Requirements
- Uses 30,000+ lap records
- Each lap includes multiple fields (sector times, speeds, etc.)
- Data is real-world → meaning it’s messy

# Handling messy data-
Since the API isn’t perfect, some cleanup is needed.

Here’s how different cases are handled:
| Issue | What happens |
|-------|-------------|
| Missing meeting/session key | Node is skipped |
| Missing lap duration | Stored as `None`, ignored in stats |
| Invalid numeric values | Safely converted to `None` |
| Duplicate keys | Ignored |
| Session without meeting | Attached to root |
| Empty API response | Returns empty list and continues |

# Data Source
All data comes from:

https://openf1.org

Example endpoint:
https://api.openf1.org/v1/laps?session_key=9159
Responses are cached locally in the data/ folder to avoid repeated API calls.

# Notes
- First run is slow because of API calls — this is expected
- After caching, everything runs much faster
- The project is more about practicing data structures than building a production app

AI Statement- All the work done in this project is my own, AI has only been used in some parts to generate presentation slides structure