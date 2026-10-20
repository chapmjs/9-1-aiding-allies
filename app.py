"""
Case 9-1 "Aiding Allies" - Fastest-route (shortest path) explorer.

Run locally:   streamlit run app.py
Deploy:        push app.py + requirements.txt to GitHub, then connect the repo
               at share.streamlit.io.

IMPORTANT: The air-leg distances and the Globemaster speed come from the case
table. The SEA and TRUCK rows (ship / truck speeds and their distances) were NOT
in the data provided, so they are PLACEHOLDERS. Replace them with the numbers
from your vehicle table / map using the editable table in the app.
"""

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Aiding Allies - Fastest Route", layout="wide")

ORIGINS = ["Boston", "Jacksonville"]
PORTS = ["Napoli", "Hamburg", "Rotterdam"]
AIRFIELDS = ["London", "Berlin", "Istanbul"]
DESTS = ["St. Petersburg", "Moscow", "Rostov"]
ALL_NODES = ORIGINS + PORTS + AIRFIELDS + DESTS

# ---------------------------------------------------------------- default data
# (from, to, mode, distance_km)
DEFAULT_EDGES = [
    # Air: origin -> airfield (from case table)
    ("Boston", "London", "Air", 6200),
    ("Boston", "Berlin", "Air", 7250),
    ("Boston", "Istanbul", "Air", 8300),
    ("Jacksonville", "London", "Air", 7900),
    ("Jacksonville", "Berlin", "Air", 9200),
    ("Jacksonville", "Istanbul", "Air", 10100),
    # Air: airfield -> Russian city (from case table)
    ("London", "St. Petersburg", "Air", 1980),
    ("London", "Moscow", "Air", 2300),
    ("London", "Rostov", "Air", 2860),
    ("Berlin", "St. Petersburg", "Air", 1280),
    ("Berlin", "Moscow", "Air", 1600),
    ("Berlin", "Rostov", "Air", 1730),
    ("Istanbul", "St. Petersburg", "Air", 2040),
    ("Istanbul", "Moscow", "Air", 1700),
    ("Istanbul", "Rostov", "Air", 990),
    # Sea: origin -> port  (PLACEHOLDER distances - replace with case data)
    ("Boston", "Napoli", "Sea", 7300),
    ("Boston", "Hamburg", "Sea", 6200),
    ("Boston", "Rotterdam", "Sea", 5900),
    ("Jacksonville", "Napoli", "Sea", 8200),
    ("Jacksonville", "Hamburg", "Sea", 7600),
    ("Jacksonville", "Rotterdam", "Sea", 7300),
    # Truck: port -> Russian city (PLACEHOLDER distances - replace with case data)
    ("Napoli", "St. Petersburg", "Truck", 3200),
    ("Napoli", "Moscow", "Truck", 3300),
    ("Napoli", "Rostov", "Truck", 3100),
    ("Hamburg", "St. Petersburg", "Truck", 1900),
    ("Hamburg", "Moscow", "Truck", 2500),
    ("Hamburg", "Rostov", "Truck", 2900),
    ("Rotterdam", "St. Petersburg", "Truck", 2300),
    ("Rotterdam", "Moscow", "Truck", 2900),
    ("Rotterdam", "Rostov", "Truck", 3300),
]

SCENARIOS = {
    "Base case": [],
    "Berlin airfield lost": ["Berlin"],
    "London airfield lost": ["London"],
    "Istanbul airfield lost": ["Istanbul"],
    "Boston lost (all from Jacksonville)": ["Boston"],
    "Custom": None,
}

# ---------------------------------------------------------------- sidebar
st.sidebar.header("Inputs")

st.sidebar.subheader("Speeds")
air_mph = st.sidebar.number_input("Globemaster speed (mph)", 50.0, 2000.0, 400.0, 10.0)
km_per_mile = st.sidebar.number_input("km per mile", 1.0, 2.0, 1.609, 0.001, format="%.3f")
air_kmh = air_mph * km_per_mile
st.sidebar.caption(f"Globemaster = {air_kmh:,.1f} km/hr")
ship_kmh = st.sidebar.number_input(
    "Transport ship speed (km/hr) - PLACEHOLDER", 5.0, 200.0, 35.0, 1.0
)
truck_kmh = st.sidebar.number_input(
    "Palletized truck speed (km/hr) - PLACEHOLDER", 5.0, 200.0, 70.0, 1.0
)
SPEED = {"Air": air_kmh, "Sea": ship_kmh, "Truck": truck_kmh}

st.sidebar.subheader("Delays at NATO stops (hours)")
dwell_air = st.sidebar.number_input("Refuel/resupply at airfield", 0.0, 100.0, 0.0, 0.25)
dwell_port = st.sidebar.number_input("Unload/reload at port", 0.0, 100.0, 0.0, 0.25)

st.sidebar.subheader("Scenario (follow-up questions)")
scenario = st.sidebar.selectbox("Preset", list(SCENARIOS.keys()))
if SCENARIOS[scenario] is None:
    closed = st.sidebar.multiselect("Closed / unavailable nodes", ALL_NODES)
else:
    closed = SCENARIOS[scenario]
    if closed:
        st.sidebar.caption("Closed: " + ", ".join(closed))

include_sea = st.sidebar.checkbox("Include ship + truck network", value=True)

# ---------------------------------------------------------------- edge table
st.title("Case 9-1: Aiding Allies - Fastest Route to Russia")
st.write(
    "Arc length is **travel time** (distance / speed of that vehicle) plus any delay "
    "at the NATO stop. Change speeds, delays, closures, or distances to answer the "
    "follow-up questions."
)
st.warning(
    "Ship speed, truck speed, and all **Sea / Truck** distances are placeholders, "
    "because they were not in the data provided. Edit them below to match the case."
)

with st.expander("Edit distances (km) / arcs", expanded=False):
    base_df = pd.DataFrame(DEFAULT_EDGES, columns=["From", "To", "Mode", "Distance (km)"])
    edges_df = st.data_editor(
        base_df,
        disabled=["From", "To", "Mode"],
        hide_index=True,
        use_container_width=True,
        key="edges",
    )

edges = []
for _, r in edges_df.iterrows():
    mode = r["Mode"]
    if mode in ("Sea", "Truck") and not include_sea:
        continue
    if r["From"] in closed or r["To"] in closed:
        continue
    hours = r["Distance (km)"] / SPEED[mode]
    edges.append((r["From"], r["To"], mode, float(r["Distance (km)"]), hours))


def dwell(node):
    if node in AIRFIELDS:
        return dwell_air
    if node in PORTS:
        return dwell_port
    return 0.0


adj = {}
for f, t, m, d, h in edges:
    adj.setdefault(f, []).append((t, m, d, h))


def all_paths(origin, dest):
    """Enumerate every route (graph is layered, so no cycles)."""
    out = []

    def dfs(node, legs):
        if node == dest:
            out.append(list(legs))
            return
        for t, m, d, h in adj.get(node, []):
            legs.append((node, t, m, d, h))
            dfs(t, legs)
            legs.pop()

    dfs(origin, [])
    return out


def summarize(legs):
    km = sum(l[3] for l in legs)
    hrs = sum(l[4] for l in legs)
    for l in legs[:-1]:  # delay at each intermediate stop
        hrs += dwell(l[1])
    route = " -> ".join([legs[0][0]] + [l[1] for l in legs])
    modes = "/".join(sorted({l[2] for l in legs}, key=["Air", "Sea", "Truck"].index))
    return route, modes, km, hrs


rows = []
for dest in DESTS:
    for origin in ORIGINS:
        if origin in closed:
            continue
        for legs in all_paths(origin, dest):
            route, modes, km, hrs = summarize(legs)
            rows.append(
                {
                    "Destination": dest,
                    "Route": route,
                    "Modes": modes,
                    "Total km": km,
                    "Hours": hrs,
                    "_legs": legs,
                }
            )

all_df = pd.DataFrame(rows)

# ---------------------------------------------------------------- results
st.header("Fastest route to each city")

best_edges = set()
if all_df.empty:
    st.error("No routes available with these settings.")
else:
    summary = []
    for dest in DESTS:
        sub = all_df[all_df["Destination"] == dest].sort_values("Hours")
        if sub.empty:
            summary.append({"Destination": dest, "Fastest route": "NO ROUTE"})
            continue
        best = sub.iloc[0]
        for l in best["_legs"]:
            best_edges.add((l[0], l[1]))
        runner = sub.iloc[1] if len(sub) > 1 else None
        summary.append(
            {
                "Destination": dest,
                "Fastest route": best["Route"],
                "Hours": round(best["Hours"], 2),
                "Total km": f"{best['Total km']:,.0f}",
                "Runner-up route": runner["Route"] if runner is not None else "-",
                "Runner-up hours": round(runner["Hours"], 2) if runner is not None else None,
                "Cost of losing best (hrs)": (
                    round(runner["Hours"] - best["Hours"], 2) if runner is not None else None
                ),
            }
        )
    st.dataframe(pd.DataFrame(summary), hide_index=True, use_container_width=True)

    cols = st.columns(3)
    for c, s in zip(cols, summary):
        if "Hours" in s:
            c.metric(s["Destination"], f"{s['Hours']:.2f} hrs")
        else:
            c.metric(s["Destination"], "No route")

    # ------------------------------------------------------------ network
    st.header("Network (fastest paths highlighted in red)")
    dot = ['digraph G { rankdir=LR; node [shape=box, style=filled, fontsize=11];']
    colors = {"Origin": "#cfe2ff", "Port": "#d1e7dd", "Airfield": "#fff3cd", "Dest": "#f8d7da"}
    for n in ALL_NODES:
        grp = (
            "Origin" if n in ORIGINS else "Port" if n in PORTS
            else "Airfield" if n in AIRFIELDS else "Dest"
        )
        fill = "#e0e0e0" if n in closed else colors[grp]
        label = f"{n}\\n(CLOSED)" if n in closed else n
        dot.append(f'"{n}" [label="{label}", fillcolor="{fill}"];')
    edge_style = {"Air": "solid", "Sea": "dashed", "Truck": "dotted"}
    for f, t, m, d, h in edges:
        hot = (f, t) in best_edges
        color = "red" if hot else "gray60"
        width = 3 if hot else 1
        dot.append(
            f'"{f}" -> "{t}" [label="{h:.1f} h", color="{color}", penwidth={width}, '
            f'style={edge_style[m]}, fontsize=9, fontcolor="{color}"];'
        )
    dot.append("}")
    st.graphviz_chart("\n".join(dot), use_container_width=True)
    st.caption("Solid = Globemaster, dashed = ship, dotted = truck. Labels are travel hours.")

    # ------------------------------------------------------------ all routes
    with st.expander("All routes, ranked"):
        show = all_df.drop(columns=["_legs"]).copy()
        best_by = show.groupby("Destination")["Hours"].transform("min")
        show["Hours behind best"] = show["Hours"] - best_by
        show["Hours"] = show["Hours"].round(2)
        show["Hours behind best"] = show["Hours behind best"].round(2)
        show["Total km"] = show["Total km"].map(lambda x: f"{x:,.0f}")
        show = show.sort_values(["Destination", "Hours"])
        st.dataframe(show, hide_index=True, use_container_width=True)

st.divider()
st.subheader("Try these follow-ups")
st.markdown(
    """
- **Berlin lost** -> which city's answer changes, and by how much?
- **London lost** -> how many cities are affected? Which node is critical?
- **Istanbul lost** -> nothing changes? Why is it redundant?
- **Boston lost** -> how much slower is every city?
- **Add a 2-hour refuel delay** at airfields -> does the ranking of Berlin vs. London for Rostov change?
- **Raise the Globemaster speed or shrink a distance** -> how much would it take for Istanbul to win Rostov?
"""
)
