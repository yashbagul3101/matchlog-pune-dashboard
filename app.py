"""
MatchLog — Container Street-Turn / Triangulation Dashboard
Team: Prarabdha, Pranshu & Pranit (Lead)
Run: streamlit run app.py
"""

import datetime
import uuid

import folium
import pandas as pd
import streamlit as st
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MatchLog – Container Tracker",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shipping-line colour palette ──────────────────────────────────────────────
LINE_COLOURS = {
    "Maersk":      "#00A0E1",   # light blue
    "Hapag-Lloyd": "#F47920",   # orange
    "MSC":         "#FFD700",   # yellow
    "ONE":         "#E91E8C",   # magenta / pink
    "CMA CGM":     "#003087",   # dark blue
    "HMM":         "#E8001C",   # red
}
LINE_OPTIONS   = list(LINE_COLOURS.keys())
SIZE_OPTIONS   = ["20 ft", "20 ft HC", "40 ft", "40 ft HC"]
PUNE_CENTRE    = [18.65, 73.85]   # map default

# ── Dummy seed data ───────────────────────────────────────────────────────────
SEED_ORDERS = [
    {
        "id":           str(uuid.uuid4()),
        "type":         "Import",
        "line":         "Maersk",
        "size":         "40 ft",
        "action_date":  datetime.date.today() + datetime.timedelta(days=2),
        "origin_name":  "Nhava Sheva Port",
        "origin_lat":   18.9500,
        "origin_lon":   72.9500,
        "dest_name":    "Chakan MIDC",
        "dest_lat":     18.7588,
        "dest_lon":     73.8610,
        "notes":        "Destuff → drop empty at Chakan",
    },
    {
        "id":           str(uuid.uuid4()),
        "type":         "Export",
        "line":         "Hapag-Lloyd",
        "size":         "20 ft",
        "action_date":  datetime.date.today() + datetime.timedelta(days=1),
        "origin_name":  "Talegaon Dabhade",
        "origin_lat":   18.7270,
        "origin_lon":   73.6690,
        "dest_name":    "Nhava Sheva Port",
        "dest_lat":     18.9500,
        "dest_lon":     72.9500,
        "notes":        "Empty pick-up at Talegaon → stuff → export",
    },
    {
        "id":           str(uuid.uuid4()),
        "type":         "Import",
        "line":         "MSC",
        "size":         "40 ft HC",
        "action_date":  datetime.date.today() + datetime.timedelta(days=4),
        "origin_name":  "Nhava Sheva Port",
        "origin_lat":   18.9500,
        "origin_lon":   72.9500,
        "dest_name":    "Ranjangaon MIDC",
        "dest_lat":     18.7300,
        "dest_lon":     74.1200,
        "notes":        "Destuff at Ranjangaon",
    },
    {
        "id":           str(uuid.uuid4()),
        "type":         "Export",
        "line":         "ONE",
        "size":         "40 ft",
        "action_date":  datetime.date.today() + datetime.timedelta(days=3),
        "origin_name":  "Chakan MIDC",
        "origin_lat":   18.7588,
        "origin_lon":   73.8610,
        "dest_name":    "Nhava Sheva Port",
        "dest_lat":     18.9500,
        "dest_lon":     72.9500,
        "notes":        "Pick empty at Chakan for export",
    },
    {
        "id":           str(uuid.uuid4()),
        "type":         "Import",
        "line":         "CMA CGM",
        "size":         "20 ft HC",
        "action_date":  datetime.date.today() + datetime.timedelta(days=5),
        "origin_name":  "Nhava Sheva Port",
        "origin_lat":   18.9500,
        "origin_lon":   72.9500,
        "dest_name":    "Talegaon Dabhade",
        "dest_lat":     18.7270,
        "dest_lon":     73.6690,
        "notes":        "Destuff → empty Talegaon",
    },
]

# ── Session-state bootstrap ───────────────────────────────────────────────────
if "orders" not in st.session_state:
    st.session_state.orders = SEED_ORDERS.copy()
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None


# ── Helpers ───────────────────────────────────────────────────────────────────
def active_orders():
    """Return only orders whose action_date is >= today."""
    today = datetime.date.today()
    return [o for o in st.session_state.orders if o["action_date"] >= today]


@st.cache_data(ttl=600, show_spinner=False)
def geocode(place: str):
    """Return (lat, lon) for a place string, or None on failure."""
    try:
        geolocator = Nominatim(user_agent="matchlog_dashboard")
        loc = geolocator.geocode(place + ", Maharashtra, India", timeout=5)
        if loc:
            return loc.latitude, loc.longitude
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass
    return None, None


def build_map(orders, selected_id=None):
    """Build and return a folium.Map with all active markers + optional route."""
    m = folium.Map(
        location=PUNE_CENTRE,
        zoom_start=9,
        tiles="CartoDB dark_matter",
    )

    for o in orders:
        colour = LINE_COLOURS.get(o["line"], "#FFFFFF")
        tooltip_html = (
            f"<b>{o['type']} — {o['line']}</b><br>"
            f"Size: {o['size']}<br>"
            f"Date: {o['action_date']}<br>"
            f"From: {o['origin_name']}<br>"
            f"To:   {o['dest_name']}"
        )
        # Origin marker
        folium.CircleMarker(
            location=[o["origin_lat"], o["origin_lon"]],
            radius=9,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.85,
            tooltip=folium.Tooltip(tooltip_html),
        ).add_to(m)
        # Destination marker (slightly smaller)
        folium.CircleMarker(
            location=[o["dest_lat"], o["dest_lon"]],
            radius=6,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.55,
            tooltip=folium.Tooltip(f"Destination: {o['dest_name']}"),
        ).add_to(m)

        # Draw route ONLY for the selected order
        if selected_id and o["id"] == selected_id:
            folium.PolyLine(
                locations=[
                    [o["origin_lat"], o["origin_lon"]],
                    [o["dest_lat"],   o["dest_lon"]],
                ],
                color=colour,
                weight=4,
                opacity=0.9,
                dash_array="8 4",
                tooltip=f"{o['line']} | {o['size']}",
            ).add_to(m)
            # Pulse rings on selected endpoints
            for lat, lon in [(o["origin_lat"], o["origin_lon"]),
                              (o["dest_lat"],   o["dest_lon"])]:
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=16,
                    color=colour,
                    fill=False,
                    weight=2,
                    opacity=0.45,
                ).add_to(m)

    return m


# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}
h1, h2, h3, .stMarkdown h1 {
    font-family: 'Space Mono', monospace !important;
    letter-spacing: -0.03em;
}
.block-container { padding-top: 1.4rem; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #21262d;
}
section[data-testid="stSidebar"] * {
    color: #c9d1d9 !important;
}

/* Order cards */
.order-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-left: 4px solid var(--lc);
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: background 0.15s;
}
.order-card:hover { background: #1f2937; }
.order-card.selected { background: #1a2535; border-left-width: 6px; }
.order-card .badge {
    display: inline-block;
    font-size: 11px;
    font-family: 'Space Mono', monospace;
    padding: 2px 8px;
    border-radius: 20px;
    color: #000;
    background: var(--lc);
    font-weight: 700;
    margin-right: 6px;
}
.order-card h4 { margin: 4px 0 2px; font-size: 14px; color: #e6edf3; }
.order-card p  { margin: 0; font-size: 12px; color: #8b949e; }

/* Metric boxes */
.metric-row { display:flex; gap:12px; margin-bottom:16px; }
.metric-box {
    flex:1; background:#161b22; border:1px solid #21262d;
    border-radius:8px; padding:12px 16px; text-align:center;
}
.metric-box .val { font-size:28px; font-family:'Space Mono',monospace; color:#58a6ff; }
.metric-box .lbl { font-size:11px; color:#8b949e; text-transform:uppercase; letter-spacing:.06em; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 9])
with col_logo:
    st.markdown("## 🚢")
with col_title:
    st.markdown("# MatchLog &nbsp;·&nbsp; Container Street-Turn Tracker")
    st.caption("Pune Region · Real-time import/export matching dashboard")

st.divider()

# ── Sidebar: Add Order ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ➕ Log New Order")
    with st.form("add_order", clear_on_submit=True):
        order_type  = st.selectbox("Order Type",        ["Import", "Export"])
        line        = st.selectbox("Shipping Line",     LINE_OPTIONS)
        size        = st.selectbox("Container Size",    SIZE_OPTIONS)
        action_date = st.date_input(
            "Action Date",
            value=datetime.date.today() + datetime.timedelta(days=1),
            min_value=datetime.date.today(),
        )

        st.markdown("---")
        if order_type == "Import":
            origin_label = "Destuffing Location"
            dest_label   = "Empty Drop Location"
        else:
            origin_label = "Current Empty Location"
            dest_label   = "Stuffing Location"

        origin_name = st.text_input(origin_label, placeholder="e.g. Nhava Sheva Port")
        dest_name   = st.text_input(dest_label,   placeholder="e.g. Chakan MIDC")

        st.markdown("**Coordinate Override** *(leave blank to auto-geocode)*")
        c1, c2 = st.columns(2)
        with c1:
            man_olat = st.text_input("Origin Lat",  key="olat")
            man_dlat = st.text_input("Dest Lat",    key="dlat")
        with c2:
            man_olon = st.text_input("Origin Lon",  key="olon")
            man_dlon = st.text_input("Dest Lon",    key="dlon")

        notes   = st.text_area("Notes", height=68)
        submit  = st.form_submit_button("Add Order", use_container_width=True)

    if submit:
        if not origin_name or not dest_name:
            st.error("Both location fields are required.")
        else:
            # Resolve coordinates
            with st.spinner("Geocoding locations…"):
                if man_olat and man_olon:
                    olat, olon = float(man_olat), float(man_olon)
                else:
                    olat, olon = geocode(origin_name)

                if man_dlat and man_dlon:
                    dlat, dlon = float(man_dlat), float(man_dlon)
                else:
                    dlat, dlon = geocode(dest_name)

            if olat is None or dlat is None:
                st.error(
                    "Geocoding failed for one or more locations. "
                    "Please fill in the coordinate override fields."
                )
            else:
                new_order = {
                    "id":          str(uuid.uuid4()),
                    "type":        order_type,
                    "line":        line,
                    "size":        size,
                    "action_date": action_date,
                    "origin_name": origin_name,
                    "origin_lat":  olat,
                    "origin_lon":  olon,
                    "dest_name":   dest_name,
                    "dest_lat":    dlat,
                    "dest_lon":    dlon,
                    "notes":       notes,
                }
                st.session_state.orders.append(new_order)
                st.success(f"✅ Order added: {order_type} · {line} · {size}")

    st.divider()
    st.markdown("### 🗑️ Clear Expired")
    if st.button("Remove Expired Orders", use_container_width=True):
        before = len(st.session_state.orders)
        st.session_state.orders = [
            o for o in st.session_state.orders
            if o["action_date"] >= datetime.date.today()
        ]
        removed = before - len(st.session_state.orders)
        st.info(f"Removed {removed} expired order(s).")


# ── Main area ─────────────────────────────────────────────────────────────────
orders = active_orders()
imports = [o for o in orders if o["type"] == "Import"]
exports = [o for o in orders if o["type"] == "Export"]

# Metric strip
st.markdown(
    f"""
<div class="metric-row">
  <div class="metric-box"><div class="val">{len(orders)}</div><div class="lbl">Active Orders</div></div>
  <div class="metric-box"><div class="val">{len(imports)}</div><div class="lbl">Imports</div></div>
  <div class="metric-box"><div class="val">{len(exports)}</div><div class="lbl">Exports</div></div>
  <div class="metric-box"><div class="val">{len(set(o['line'] for o in orders))}</div><div class="lbl">Shipping Lines</div></div>
</div>
""",
    unsafe_allow_html=True,
)

# ── Map ───────────────────────────────────────────────────────────────────────
st.markdown("### 🗺️ Live Container Map")
st.caption(
    "Markers = active container endpoints. "
    "Select an order below to draw its route on the map."
)

folium_map = build_map(orders, st.session_state.selected_id)
map_data   = st_folium(folium_map, width="100%", height=520, returned_objects=[])

st.divider()

# ── Search & Recall ───────────────────────────────────────────────────────────
st.markdown("### 🔍 Search & Recall")
search_query = st.text_input(
    label="Search orders",
    placeholder='e.g.  "import chakan"  or  "40ft Hapag"  or  "Maersk"',
    label_visibility="collapsed",
)

def order_matches(o, q: str) -> bool:
    q = q.lower()
    haystack = (
        f"{o['type']} {o['line']} {o['size']} "
        f"{o['origin_name']} {o['dest_name']} {o.get('notes','')}"
    ).lower()
    return all(word in haystack for word in q.split())

filtered = [o for o in orders if order_matches(o, search_query)] if search_query else orders

if not filtered:
    st.info("No active orders match your search.")
else:
    st.caption(f"Showing **{len(filtered)}** order(s). Click **Select** to highlight on map.")

    # Table header
    hdr = st.columns([1, 1.4, 1.2, 1, 1.6, 1.6, 1.3, 0.9])
    for col, lbl in zip(
        hdr,
        ["Type", "Line", "Size", "Date", "From", "To", "Notes", ""],
    ):
        col.markdown(f"**{lbl}**")

    st.markdown("<hr style='margin:4px 0 10px'>", unsafe_allow_html=True)

    for o in filtered:
        colour = LINE_COLOURS.get(o["line"], "#FFFFFF")
        is_sel = st.session_state.selected_id == o["id"]
        row    = st.columns([1, 1.4, 1.2, 1, 1.6, 1.6, 1.3, 0.9])

        badge_html = (
            f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
            f'background:{colour};color:#000;font-size:11px;font-weight:700;'
            f'font-family:monospace">{o["type"]}</span>'
        )
        row[0].markdown(badge_html, unsafe_allow_html=True)
        row[1].markdown(
            f'<span style="color:{colour};font-weight:600">{o["line"]}</span>',
            unsafe_allow_html=True,
        )
        row[2].write(o["size"])
        row[3].write(str(o["action_date"]))
        row[4].write(o["origin_name"])
        row[5].write(o["dest_name"])
        row[6].write(o.get("notes", "—") or "—")

        btn_label = "✦ Active" if is_sel else "Select"
        if row[7].button(btn_label, key=f"sel_{o['id']}", use_container_width=True):
            if is_sel:
                st.session_state.selected_id = None
            else:
                st.session_state.selected_id = o["id"]
            st.rerun()

        st.markdown("<hr style='margin:4px 0 8px;opacity:.25'>", unsafe_allow_html=True)

# ── Selected order detail card ────────────────────────────────────────────────
if st.session_state.selected_id:
    sel = next(
        (o for o in orders if o["id"] == st.session_state.selected_id), None
    )
    if sel:
        colour = LINE_COLOURS.get(sel["line"], "#FFFFFF")
        st.divider()
        st.markdown("### 📦 Selected Order Details")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Type",          sel["type"])
        c2.metric("Shipping Line", sel["line"])
        c3.metric("Container",     sel["size"])
        c4.metric("Action Date",   str(sel["action_date"]))

        d1, d2 = st.columns(2)
        d1.info(f"**Origin:** {sel['origin_name']}\n\n`{sel['origin_lat']:.4f}, {sel['origin_lon']:.4f}`")
        d2.info(f"**Destination:** {sel['dest_name']}\n\n`{sel['dest_lat']:.4f}, {sel['dest_lon']:.4f}`")

        if sel.get("notes"):
            st.markdown(f"> 📝 {sel['notes']}")

        days_left = (sel["action_date"] - datetime.date.today()).days
        if days_left == 0:
            st.warning("⚠️ Action date is **today** — coordinate immediately!")
        elif days_left <= 2:
            st.warning(f"⏳ {days_left} day(s) remaining until action date.")
        else:
            st.success(f"✅ {days_left} day(s) until action date.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "MatchLog · Pune Container Optimisation · "
    "Team: Prarabdha, Pranshu & Pranit (Lead) · "
    f"Data refreshed: {datetime.datetime.now().strftime('%d %b %Y %H:%M')}"
)
