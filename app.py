import os
import sys

# Allow importing from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from tree import NaryTree
from fetcher import load_all_data, fetch_laps_for_session

app = Flask(__name__)

# Global tree – built once on startup
tree = NaryTree()
_data_loaded = False


def ensure_data_loaded(force: bool = False):
    """Load API data and build the tree (cached after first call)."""
    global _data_loaded
    if _data_loaded and not force:
        return
    print("Loading F1 data and building tree...")
    meetings, sessions, laps = load_all_data(force=force)
    tree.__init__()  # reset
    tree.build_from_data(meetings, sessions, laps)
    _data_loaded = True
    s = tree.summary()
    print(f"Tree built: {s}")

# HTML Templates (inline for simplicity)
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>F1 N-ary Tree Explorer</title>
  <style>
    body { font-family: monospace; max-width: 900px; margin: 30px auto; padding: 0 20px; background: #f9f9f9; }
    h1 { color: #e10600; }
    h2 { color: #333; }
    a { color: #e10600; }
    nav { margin-bottom: 20px; }
    nav a { margin-right: 15px; text-decoration: none; border-bottom: 1px solid #e10600; }
    table { border-collapse: collapse; width: 100%; margin-top: 10px; }
    th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }
    th { background: #eee; }
    tr:nth-child(even) { background: #f5f5f5; }
    .badge { background: #e10600; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em; }
    .missing { color: #999; font-style: italic; }
    .stats-box { background: #fff; border: 1px solid #ccc; padding: 15px; margin: 10px 0; }
    ul { padding-left: 20px; }
    li { margin: 4px 0; }
    .back { display: inline-block; margin-bottom: 15px; }
    form { display: inline; }
    input[type=text] { padding: 4px; width: 300px; }
    button { padding: 4px 10px; cursor: pointer; }
  </style>
</head>
<body>
  <h1>F1 Race Weekend N-ary Tree Explorer</h1>
  <nav>
    <a href="/">Meetings</a>
    <a href="/stats">Tree Stats</a>
    <a href="/search">Search</a>
  </nav>
  {% block content %}{% endblock %}
</body>
</html>
"""

# Routes def
@app.route("/")
def index():
    ensure_data_loaded()
    meetings = tree.root.children
    content = """
    <h2>All Grand Prix Meetings</h2>
    <p>Showing tree root → meetings ({{ meetings|length }} total). Click a meeting to expand.</p>
    <table>
      <tr><th>Year</th><th>Grand Prix</th><th>Country</th><th>Circuit</th><th>Sessions</th></tr>
      {% for m in meetings %}
      <tr>
        <td>{{ m.data.get('year', '?') }}</td>
        <td><a href="/meeting/{{ m.data['meeting_key'] }}">{{ m.data.get('meeting_name', 'Unknown') }}</a></td>
        <td>{{ m.data.get('country_name', 'Unknown') }}</td>
        <td>{{ m.data.get('circuit_name', 'Unknown') }}</td>
        <td>{{ m.children|length }}</td>
      </tr>
      {% endfor %}
    </table>
    """
    from flask import render_template_string as rts
    body = rts(content, meetings=meetings)
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", body))


@app.route("/meeting/<int:meeting_key>")
def meeting(meeting_key):
    ensure_data_loaded()
    node = tree.find_node(f"meeting_{meeting_key}")
    if node is None:
        return "Meeting not found", 404

    content = """
    <a class="back" href="/">← Back to Meetings</a>
    <h2>{{ node.data.get('meeting_name') }} — {{ node.data.get('year') }}</h2>
    <p>Country: {{ node.data.get('country_name') }} | Circuit: {{ node.data.get('circuit_name') }}</p>
    <h3>Sessions ({{ node.children|length }})</h3>
    <table>
      <tr><th>Session</th><th>Type</th><th>Date</th><th>Drivers</th></tr>
      {% for s in node.children %}
      <tr>
        <td><a href="/session/{{ s.data['session_key'] }}">{{ s.data.get('session_name', 'Unknown') }}</a></td>
        <td><span class="badge">{{ s.data.get('session_type', '?') }}</span></td>
        <td>{{ s.data.get('date_start', '')[:10] if s.data.get('date_start') else '<span class="missing">N/A</span>' }}</td>
        <td>{{ s.children|length }}</td>
      </tr>
      {% endfor %}
    </table>
    """
    body = render_template_string(content, node=node)
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", body))


@app.route("/session/<int:session_key>")
def session(session_key):
    ensure_data_loaded()
    node = tree.find_node(f"session_{session_key}")
    if node is None:
        return "Session not found", 404

    leaderboard = tree.get_session_leaderboard(session_key)
    parent_key = node.data.get("meeting_key")

    content = """
    <a class="back" href="/meeting/{{ parent_key }}">← Back to Meeting</a>
    <h2>{{ node.data.get('session_name') }}
      <span class="badge">{{ node.data.get('session_type', '?') }}</span></h2>
    <p>Session key: {{ node.data.get('session_key') }} |
       Date: {{ node.data.get('date_start', '')[:10] or 'N/A' }}</p>

    <h3>Driver Leaderboard ({{ leaderboard|length }} drivers)</h3>
    <table>
      <tr><th>Pos</th><th>Driver #</th><th>Best Lap</th><th>Avg Lap</th>
          <th>Valid Laps</th><th>Missing</th><th>Detail</th></tr>
      {% for i, d in enumerate(leaderboard) %}
      <tr>
        <td>{{ i+1 }}</td>
        <td>{{ d['driver_number'] }}</td>
        <td>{% if d['best_lap'] %}{{ "%.3f"|format(d['best_lap']) }}s{% else %}<span class="missing">N/A</span>{% endif %}</td>
        <td>{% if d['avg_lap'] %}{{ "%.3f"|format(d['avg_lap']) }}s{% else %}<span class="missing">N/A</span>{% endif %}</td>
        <td>{{ d['valid_laps'] }}</td>
        <td>{% if d['missing_laps'] > 0 %}<span style="color:orange">{{ d['missing_laps'] }}</span>{% else %}0{% endif %}</td>
        <td><a href="/driver/{{ session_key }}/{{ d['driver_number'] }}">Laps</a></td>
      </tr>
      {% endfor %}
    </table>
    """
    body = render_template_string(content, node=node, leaderboard=leaderboard,
                                   parent_key=parent_key, enumerate=enumerate)
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", body))


@app.route("/driver/<int:session_key>/<int:driver_number>")
def driver(session_key, driver_number):
    ensure_data_loaded()
    d_node = tree.find_node(f"driver_{session_key}_{driver_number}")
    if d_node is None:
        return "Driver node not found", 404

    stats = tree.get_driver_stats(session_key, driver_number)
    # list of lap TreeNodes
    laps = d_node.children 

    content = """
    <a class="back" href="/session/{{ session_key }}">← Back to Session</a>
    <h2>Driver #{{ driver_number }} — Session {{ session_key }}</h2>

    <div class="stats-box">
      <strong>Summary:</strong>
      Best: {% if stats.get('best_lap') %}{{ "%.3f"|format(stats['best_lap']) }}s{% else %}N/A{% endif %} |
      Avg: {% if stats.get('avg_lap') %}{{ "%.3f"|format(stats['avg_lap']) }}s{% else %}N/A{% endif %} |
      Total laps: {{ stats.get('lap_count', 0) }} |
      Valid: {{ stats.get('valid_laps', 0) }} |
      <span style="color:orange">Missing duration: {{ stats.get('missing_laps', 0) }}</span>
    </div>

    <h3>Lap-by-Lap Breakdown ({{ laps|length }} laps)</h3>
    <table>
      <tr><th>Lap</th><th>Duration</th><th>S1</th><th>S2</th><th>S3</th>
          <th>I1 Speed</th><th>ST Speed</th><th>Pit Out</th></tr>
      {% for lap in laps %}
      {% set d = lap.data %}
      <tr>
        <td>{{ d.get('lap_number', '?') }}</td>
        <td>{% if d.get('lap_duration') %}{{ "%.3f"|format(d['lap_duration']) }}{% else %}<span class="missing">—</span>{% endif %}</td>
        <td>{% if d.get('duration_sector_1') %}{{ "%.3f"|format(d['duration_sector_1']) }}{% else %}<span class="missing">—</span>{% endif %}</td>
        <td>{% if d.get('duration_sector_2') %}{{ "%.3f"|format(d['duration_sector_2']) }}{% else %}<span class="missing">—</span>{% endif %}</td>
        <td>{% if d.get('duration_sector_3') %}{{ "%.3f"|format(d['duration_sector_3']) }}{% else %}<span class="missing">—</span>{% endif %}</td>
        <td>{% if d.get('i1_speed') %}{{ d['i1_speed']|int }}{% else %}<span class="missing">—</span>{% endif %}</td>
        <td>{% if d.get('st_speed') %}{{ d['st_speed']|int }}{% else %}<span class="missing">—</span>{% endif %}</td>
        <td>{% if d.get('is_pit_out_lap') %}✓{% else %}{% endif %}</td>
      </tr>
      {% endfor %}
    </table>
    """
    body = render_template_string(content, d_node=d_node, laps=laps,
                                   stats=stats, session_key=session_key,
                                   driver_number=driver_number)
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", body))


@app.route("/search")
def search():
    ensure_data_loaded()
    query = request.args.get("q", "").strip().lower()
    results = []

    if query:
        # Search meetings by name
        for _, node in tree.dfs_traversal():
            if node.node_type == "meeting":
                name = node.data.get("meeting_name", "").lower()
                country = node.data.get("country_name", "").lower()
                if query in name or query in country:
                    results.append(("meeting", node))
            elif node.node_type == "session":
                stype = node.data.get("session_type", "").lower()
                sname = node.data.get("session_name", "").lower()
                if query in stype or query in sname:
                    results.append(("session", node))

    content = """
    <h2>Search</h2>
    <form action="/search" method="get">
      <input type="text" name="q" placeholder="e.g. Belgium, Race, Qualifying" value="{{ query }}">
      <button type="submit">Search</button>
    </form>

    {% if query %}
    <p>{{ results|length }} result(s) for "{{ query }}"</p>
    <ul>
      {% for rtype, node in results %}
      <li>
        <span class="badge">{{ rtype }}</span>
        {% if rtype == 'meeting' %}
          <a href="/meeting/{{ node.data['meeting_key'] }}">
            {{ node.data.get('meeting_name') }} ({{ node.data.get('year') }})
          </a>
        {% else %}
          <a href="/session/{{ node.data['session_key'] }}">
            {{ node.data.get('session_name') }} — session {{ node.data['session_key'] }}
          </a>
        {% endif %}
      </li>
      {% endfor %}
      {% if not results %}<li>No results found.</li>{% endif %}
    </ul>
    {% endif %}
    """
    body = render_template_string(content, query=query, results=results)
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", body))


@app.route("/stats")
def stats():
    ensure_data_loaded()
    s = tree.summary()

    content = """
    <h2>Tree Statistics</h2>
    <div class="stats-box">
      <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Total nodes</td><td>{{ s['total_nodes'] }}</td></tr>
        <tr><td>Meetings (Level 1)</td><td>{{ s['meeting'] }}</td></tr>
        <tr><td>Sessions (Level 2)</td><td>{{ s['session'] }}</td></tr>
        <tr><td>Drivers (Level 3)</td><td>{{ s['driver'] }}</td></tr>
        <tr><td>Laps (Level 4 — leaves)</td><td>{{ s['lap'] }}</td></tr>
      </table>
    </div>
    <p><strong>Algorithm:</strong> N-ary Tree with O(1) key lookup via hash index.</p>
    <p><strong>Traversal:</strong> DFS pre-order and BFS both implemented in tree.py.</p>
    <p><strong>Noise handling:</strong> Missing/null fields replaced with defaults;
       invalid numeric strings silently coerced to None.</p>

    <h3>Refresh Data</h3>
    <form action="/api/refresh" method="post">
      <button type="submit">Re-fetch from OpenF1 API (clears cache)</button>
    </form>
    """
    body = render_template_string(content, s=s)
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", body))

# JSON API endpoints
@app.route("/api/tree-summary")
def api_tree_summary():
    ensure_data_loaded()
    return jsonify(tree.summary())


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    global _data_loaded
    _data_loaded = False
    ensure_data_loaded(force=True)
    return redirect(url_for("stats"))

# Entry point
if __name__ == "__main__":
    ensure_data_loaded()
    app.run(debug=True, port=5000)
