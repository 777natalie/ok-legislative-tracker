"""Oklahoma Legislative Vote Tracker dashboard.

Run locally:  streamlit run app/dashboard.py
Reads only dbt models (staging, intermediate and marts), never raw or meta, so it runs
as the read-only dashboard_reader role. Connection comes from the standard PG* variables.
"""
import os

import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Oklahoma Legislative Vote Tracker", layout="wide")


@st.cache_data(ttl=3600)
def query(sql, params=None):
    """Run one read-only query and return a DataFrame. Results are cached for an hour."""
    with psycopg.connect(os.getenv("DATABASE_URL", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [c.name for c in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=columns)


# ---------- Header ----------

st.title("Oklahoma Legislative Vote Tracker")
st.caption(
    "How Oklahoma legislators vote when the two parties split. "
    "Data provided by [LegiScan](https://legiscan.com) (CC BY 4.0). "
    "Independent project, not affiliated with LegiScan or the Oklahoma Legislature."
)

sessions = query(
    """
    SELECT DISTINCT b.session_id, b.session_name
    FROM analytics_staging.stg_bills AS b
    JOIN analytics_marts.legislator_party_unity AS u ON u.session_id = b.session_id
    ORDER BY b.session_id DESC
    """
)
if sessions.empty:
    st.warning("No data yet. Run the pipeline first.")
    st.stop()

session_name = st.selectbox("Session", sessions["session_name"])
session_id = int(sessions.loc[sessions["session_name"] == session_name, "session_id"].iloc[0])

# ---------- Session summary ----------

summary = query(
    """
    SELECT COUNT(*) AS final_votes,
           SUM(CASE WHEN is_party_unity_vote THEN 1 ELSE 0 END) AS party_line_votes
    FROM analytics_intermediate.int_party_positions
    WHERE session_id = %s
    """,
    (session_id,),
).iloc[0]
as_of = query("SELECT MAX(loaded_at) AS loaded_at FROM analytics_staging.stg_bills").iloc[0]["loaded_at"]

c1, c2, c3 = st.columns(3)
c1.metric("Final passage votes", f"{int(summary['final_votes']):,}")
c2.metric("Party-line votes", f"{int(summary['party_line_votes']):,}")
c3.metric(
    "Share that split the parties",
    f"{100 * summary['party_line_votes'] / summary['final_votes']:.0f}%",
)
if as_of is not None:
    st.caption(f"Data last updated {as_of:%B %d, %Y}.")

st.info(
    "**Party-line vote:** a final passage vote where most Republicans and most Democrats "
    "voted opposite ways. **Party unity score:** on those votes, the share where a legislator "
    "voted with their own party's majority. A lower score means the legislator voted with the "
    "other party's majority more often; the score does not explain why."
)

# ---------- Legislator table ----------

st.header("Party unity by legislator")

f1, f2, f3 = st.columns(3)
chambers = f1.multiselect("Chamber", ["House", "Senate"], default=["House", "Senate"])
parties = f2.multiselect("Party", ["R", "D"], default=["R", "D"])
min_votes = f3.slider("Minimum party-line votes cast", 0, 300, 50, step=10)

scores = query(
    """
    SELECT people_id, name, party, chamber, district_code, unity_votes_cast, votes_with_party, party_unity_pct
    FROM analytics_marts.legislator_party_unity
    WHERE session_id = %s
    ORDER BY party_unity_pct
    """,
    (session_id,),
)
shown = scores[
    scores["chamber"].isin(chambers)
    & scores["party"].isin(parties)
    & (scores["unity_votes_cast"] >= min_votes)
]

st.dataframe(
    shown.drop(columns="people_id"),
    hide_index=True,
    width="stretch",
    column_config={
        "name": "Legislator",
        "party": "Party",
        "chamber": "Chamber",
        "district_code": "District",
        "unity_votes_cast": "Party-line votes cast",
        "votes_with_party": "Voted with party",
        "party_unity_pct": st.column_config.ProgressColumn(
            "Party unity", format="%.1f%%", min_value=0, max_value=100
        ),
    },
)
st.caption(f"{len(shown)} of {len(scores)} legislators shown.")

# ---------- One legislator ----------

st.header("Look up a legislator")

people = query(
    """
    SELECT d.people_id, d.name, d.party, d.chamber, d.district_code, d.photo_url, d.capitol_phone
    FROM analytics_marts.dim_legislators AS d
    JOIN analytics_marts.legislator_party_unity AS u
      ON u.people_id = d.people_id AND u.session_id = %s
    ORDER BY d.last_name, d.first_name
    """,
    (session_id,),
)
people["label"] = (
    people["name"] + " (" + people["party"] + ", " + people["district_code"].fillna("") + ")"
)
choice = st.selectbox("Legislator (type a name or district, e.g. HD-037)", people["label"])
person = people[people["label"] == choice].iloc[0]
score = scores[scores["people_id"] == person["people_id"]].iloc[0]


left, right = st.columns([1, 3])
with left:
    if person["photo_url"]:
        st.image(person["photo_url"], width=160)
with right:
    st.subheader(person["name"])
    st.write(f"**{person['party']}** · {person['chamber']} · {person['district_code']}")
    if person["capitol_phone"]:
        st.write(f"Capitol office: {person['capitol_phone']}")
    st.metric(
        "Party unity",
        f"{score['party_unity_pct']:.1f}%",
        help=f"Voted with their party on {int(score['votes_with_party'])} "
        f"of {int(score['unity_votes_cast'])} party-line votes.",
    )

breaks = query(
    """
    SELECT vote_date, bill_number, title, state_url, vote_text AS their_vote, party_position
    FROM analytics_marts.fct_unity_votes
    WHERE session_id = %s AND people_id = %s AND NOT voted_with_party
    ORDER BY vote_date DESC
    """,
    (session_id, int(person["people_id"])),
)
st.markdown(f"**Party-line votes where {person['name']} voted against their party's majority ({len(breaks)})**")
st.dataframe(
    breaks,
    hide_index=True,
    width="stretch",
    column_config={
        "vote_date": "Date",
        "bill_number": "Bill",
        "title": "Title",
        "state_url": st.column_config.LinkColumn("Official page", display_text="View bill"),
        "their_vote": "Their vote",
        "party_position": "Party majority",
    },
)