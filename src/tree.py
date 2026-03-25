from collections import deque

class TreeNode:
    # A single node in the N-ary tree=
    def __init__(self, key: str, node_type: str, data: dict = None):
        self.key = key
        self.node_type = node_type
        self.data = data or {}
        self.children: list["TreeNode"] = []

    def add_child(self, child: "TreeNode") -> None:
        self.children.append(child)

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def __repr__(self):
        return f"TreeNode(key={self.key!r}, type={self.node_type!r}, children={len(self.children)})"

class NaryTree:
    def __init__(self):
        self.root = TreeNode(key="ROOT", node_type="root", data={})
        # Fast lookup table: key -> TreeNode (Alliows O(1) access)
        self._index: dict[str, TreeNode] = {"ROOT": self.root}
        self.total_nodes = 1

    @staticmethod
    def _safe_get(d: dict, key: str, default=None):
        # Safely get a value from a dict
        # Returns `default` if the key is absent or stored value == None.
        val = d.get(key, default)
        return default if val is None else val

    @staticmethod
    def _safe_float(value, default=None):
        # Convert value to float, suppressing errors from noisy data
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _register(self, node: TreeNode) -> None:
        # Add node to the lookup index and increment counter
        self._index[node.key] = node
        self.total_nodes += 1

    def build_from_data(self, meetings: list, sessions: list, laps: list) -> None:
        # Populate the tree from raw API data lists.

        # Meetings:
        meeting_nodes: dict[int, TreeNode] = {}
        for m in meetings:
            mk = self._safe_get(m, "meeting_key")
            if mk is None:
                # Noise: no primary key -> skip
                continue
            node_key = f"meeting_{mk}"
            if node_key in self._index:
                continue  # Duplicate
            node = TreeNode(
                key=node_key,
                node_type="meeting",
                data={
                    "meeting_key":    mk,
                    "meeting_name":   self._safe_get(m, "meeting_name", "Unknown GP"),
                    "country_name":   self._safe_get(m, "country_name", "Unknown"),
                    "circuit_name":   self._safe_get(m, "circuit_short_name", "Unknown"),
                    "year":           self._safe_get(m, "year"),
                    "date_start":     self._safe_get(m, "date_start"),
                },
            )
            self.root.add_child(node)
            self._register(node)
            meeting_nodes[mk] = node

        # Sessions :
        session_nodes: dict[int, TreeNode] = {}
        for s in sessions:
            sk = self._safe_get(s, "session_key")
            mk = self._safe_get(s, "meeting_key")
            if sk is None or mk is None:
                continue
            node_key = f"session_{sk}"
            if node_key in self._index:
                continue
            parent = meeting_nodes.get(mk)
            if parent is None:
                # Session references an unknown meeting -> attach to root as orphan
                parent = self.root
            node = TreeNode(
                key=node_key,
                node_type="session",
                data={
                    "session_key":    sk,
                    "meeting_key":    mk,
                    "session_name":   self._safe_get(s, "session_name", "Unknown Session"),
                    "session_type":   self._safe_get(s, "session_type", "Unknown"),
                    "date_start":     self._safe_get(s, "date_start"),
                    "date_end":       self._safe_get(s, "date_end"),
                    "circuit_key":    self._safe_get(s, "circuit_key"),
                },
            )
            parent.add_child(node)
            self._register(node)
            session_nodes[sk] = node

        # Drivers + Laps:
        # Group laps by (session_key, driver_number) to build driver sub-nodes
        driver_nodes: dict[tuple, TreeNode] = {}

        for lap in laps:
            sk = self._safe_get(lap, "session_key")
            dn = self._safe_get(lap, "driver_number")
            lap_num = self._safe_get(lap, "lap_number")

            if sk is None or dn is None:
                continue

            d_key_tuple = (sk, dn)
            if d_key_tuple not in driver_nodes:
                session_parent = session_nodes.get(sk)
                if session_parent is None:
                    continue
                d_node_key = f"driver_{sk}_{dn}"
                if d_node_key not in self._index:
                    d_node = TreeNode(
                        key=d_node_key,
                        node_type="driver",
                        data={
                            "driver_number":     dn,
                            "session_key":       sk,
                            "name_acronym":      self._safe_get(lap, "driver_number"),  # filled later if available
                        },
                    )
                    session_parent.add_child(d_node)
                    self._register(d_node)
                    driver_nodes[d_key_tuple] = d_node

            driver_node = driver_nodes[d_key_tuple]

            if lap_num is None:
                lap_num = "?"
            lap_node_key = f"lap_{sk}_{dn}_{lap_num}"
            if lap_node_key in self._index:
                continue 

            lap_node = TreeNode(
                key=lap_node_key,
                node_type="lap",
                data={
                    "lap_number":           lap_num,
                    "lap_duration":         self._safe_float(self._safe_get(lap, "lap_duration")),
                    "duration_sector_1":    self._safe_float(self._safe_get(lap, "duration_sector_1")),
                    "duration_sector_2":    self._safe_float(self._safe_get(lap, "duration_sector_2")),
                    "duration_sector_3":    self._safe_float(self._safe_get(lap, "duration_sector_3")),
                    "i1_speed":             self._safe_float(self._safe_get(lap, "i1_speed")),
                    "i2_speed":             self._safe_float(self._safe_get(lap, "i2_speed")),
                    "st_speed":             self._safe_float(self._safe_get(lap, "st_speed")),
                    "is_pit_out_lap":       self._safe_get(lap, "is_pit_out_lap", False),
                    "date_start":           self._safe_get(lap, "date_start"),
                },
            )
            driver_node.add_child(lap_node)
            self._register(lap_node)

    def dfs_traversal(self, node: TreeNode = None, depth: int = 0):
        # Depth-first pre-order traversal
        if node is None:
            node = self.root
        yield depth, node
        for child in node.children:
            yield from self.dfs_traversal(child, depth + 1)

    def bfs_traversal(self):
        # Breadth-first traversal starting from root
        queue = deque([(self.root, 0)])
        while queue:
            node, depth = queue.popleft()
            yield depth, node
            for child in node.children:
                queue.append((child, depth + 1))

    def find_node(self, key: str) -> TreeNode | None:
        # O(1) lookup by node key
        return self._index.get(key)

    def search_by_field(self, node_type: str, field: str, value) -> list[TreeNode]:
        # Linear scan returning all nodes of `node_type` where data[field] == value.
        results = []
        for _, node in self.dfs_traversal():
            if node.node_type == node_type:
                if node.data.get(field) == value:
                    results.append(node)
        return results

    def get_driver_stats(self, session_key: int, driver_number: int) -> dict:
        # Aggregate lap statistics for a specific driver in a session; Returns dict
        d_node_key = f"driver_{session_key}_{driver_number}"
        d_node = self._index.get(d_node_key)
        if d_node is None:
            return {}

        durations = []
        missing = 0
        for lap_node in d_node.children:
            dur = lap_node.data.get("lap_duration")
            if dur is not None:
                durations.append(dur)
            else:
                missing += 1

        if not durations:
            return {
                "driver_number": driver_number,
                "session_key":   session_key,
                "lap_count":     len(d_node.children),
                "valid_laps":    0,
                "missing_laps":  missing,
                "best_lap":      None,
                "avg_lap":       None,
            }

        return {
            "driver_number": driver_number,
            "session_key":   session_key,
            "lap_count":     len(d_node.children),
            "valid_laps":    len(durations),
            "missing_laps":  missing,
            "best_lap":      round(min(durations), 3),
            "avg_lap":       round(sum(durations) / len(durations), 3),
        }

    def get_session_leaderboard(self, session_key: int) -> list[dict]:
        # Returns a list of driver stats for all drivers in a session
        s_node = self._index.get(f"session_{session_key}")
        if s_node is None:
            return []

        leaderboard = []
        for driver_node in s_node.children:
            dn = driver_node.data.get("driver_number")
            stats = self.get_driver_stats(session_key, dn)
            if stats:
                leaderboard.append(stats)

        # Sort: valid best laps first (ascending), None times last
        leaderboard.sort(key=lambda x: (x["best_lap"] is None, x["best_lap"] or float("inf")))
        return leaderboard

    def summary(self) -> dict:
        # Returns high-level stats about the tree
        counts = {"meeting": 0, "session": 0, "driver": 0, "lap": 0}
        for _, node in self.dfs_traversal():
            if node.node_type in counts:
                counts[node.node_type] += 1
        return {
            "total_nodes": self.total_nodes,
            **counts,
        }

    def print_tree(self, node: TreeNode = None, depth: int = 0, max_depth: int = 3) -> None:
        # Print the tree up to `max_depth` levels
        if node is None:
            node = self.root
        indent = "  " * depth
        label = node.data.get("meeting_name") or node.data.get("session_name") or \
                node.data.get("driver_number") or node.data.get("lap_number") or node.key
        print(f"{indent}[{node.node_type.upper()}] {label}")
        if depth < max_depth:
            for child in node.children:
                self.print_tree(child, depth + 1, max_depth)
