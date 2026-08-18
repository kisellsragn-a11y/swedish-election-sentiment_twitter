import os
from typing import Any, List, Tuple, Optional, Dict

import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
from xtf import Router


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Swedish Election X Monitor 2026",
    page_icon="🇸🇪",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_QUERY = "svensk politik"
MAX_QUERY_LENGTH = 200
TEST_QUERY = "svensk politik"  # used for instance health check

# A curated list of known working Nitter instances (updated frequently)
# Source: https://github.com/zedeus/nitter/wiki/Instances
DEFAULT_NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.lunar.icu",
    "https://nitter.woodland.cafe",
    "https://nitter.ktachibana.party",
    "https://nitter.mint.lgbt",
    "https://nitter.nl",
    "https://nitter.priv.si",
]


def _read_optional_secret(name: str) -> str:
    """Read a secret from Streamlit secrets or environment variable."""
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    except (KeyError, AttributeError):
        pass
    return os.getenv(name, "").strip()


def get_nitter_instances() -> Tuple[List[str], str]:
    """Determine the list of Nitter instances to use (from secrets/env or default)."""
    configured = _read_optional_secret("XTF_NITTER")
    if configured:
        instances = [
            item.strip().rstrip("/")
            for item in configured.split(",")
            if item.strip()
        ]
        if instances:
            return instances, "Streamlit secret / environment"

    return DEFAULT_NITTER_INSTANCES.copy(), "curated public pool (updated)"


# Start with the default list; we'll allow overriding via session state later
BASE_INSTANCES, BASE_SOURCE = get_nitter_instances()
# Initialize session state to hold the active list
if "nitter_instances" not in st.session_state:
    st.session_state.nitter_instances = BASE_INSTANCES.copy()
if "nitter_source" not in st.session_state:
    st.session_state.nitter_source = BASE_SOURCE


# ============================================================
# X ROUTER (CACHED)
# ============================================================

@st.cache_resource(show_spinner=False)
def create_router(instances: tuple[str, ...]) -> Router:
    """Create a cached Router using the given instance list."""
    return Router(
        backend="nitter",
        nitter_instances=list(instances),
    )


def search_x(query_text: str, search_limit: int) -> Tuple[List[Any], str, Optional[str]]:
    """
    Perform a search and return results, backend name, and any error message.
    """
    router = create_router(tuple(st.session_state.nitter_instances))
    try:
        results = router.search(query_text, limit=search_limit)
        last_error = None
    except Exception as e:
        results = []
        last_error = str(e)

    # If the router has a last_error attribute, capture it
    if hasattr(router, "last_error") and router.last_error:
        last_error = router.last_error

    return list(results or []), router.last_backend, last_error


def tweet_to_dict(item: Any) -> dict:
    """Convert a tweet object to a dictionary."""
    if isinstance(item, dict):
        return item.copy()
    if hasattr(item, "to_dict") and callable(item.to_dict):
        try:
            return item.to_dict()
        except Exception:
            pass
    try:
        return vars(item).copy()
    except Exception:
        return {"result": str(item)}


# ============================================================
# INSTANCE TESTER
# ============================================================

def test_nitter_instance(url: str, query: str = TEST_QUERY, timeout: int = 10) -> Tuple[bool, str]:
    """
    Check if a Nitter instance returns any tweets for the given query.

    Returns:
        (success, error_message_or_blank)
    """
    try:
        # We search and look for the word "tweet" or a div with class "tweet"
        resp = requests.get(f"{url}/search?q={query}&f=tweets", timeout=timeout)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        # Simple heuristic: presence of 'tweet-content' or 'tweet-text'
        if "tweet-content" in resp.text or "tweet-text" in resp.text:
            return True, ""
        # Also check for any 'tweet' class
        soup = BeautifulSoup(resp.text, "html.parser")
        if soup.find("div", class_="tweet") or soup.find("div", class_="tweet-content"):
            return True, ""
        return False, "No tweet elements found (might be rate-limited or empty)"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


# ============================================================
# UI HELPERS
# ============================================================

def display_tweet_card(tweet: dict) -> None:
    """Render a single tweet as a styled card."""
    author = tweet.get("author", tweet.get("author_name", "Unknown"))
    text = tweet.get("text", "")
    likes = tweet.get("likes", 0)
    retweets = tweet.get("retweets", 0)
    replies = tweet.get("replies", 0)
    views = tweet.get("views", None)
    time_ago = tweet.get("time_ago", "")
    tweet_id = tweet.get("tweet_id", "")

    with st.container():
        col_left, col_right = st.columns([4, 1])
        with col_left:
            st.markdown(f"**{author}**")
            st.caption(f"{time_ago} · {tweet_id}" if tweet_id else time_ago)
            st.write(text)
        with col_right:
            st.metric("❤️", likes)
            st.metric("🔁", retweets)
            st.metric("💬", replies)
            if views is not None:
                st.metric("👁️", views)
        st.divider()


def validate_query(query: str) -> Optional[str]:
    cleaned = query.strip()
    if not cleaned:
        return "Query cannot be empty."
    if len(cleaned) > MAX_QUERY_LENGTH:
        return f"Query must be at most {MAX_QUERY_LENGTH} characters."
    return None


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Search Settings")

query = st.sidebar.text_input(
    "Search query",
    value=DEFAULT_QUERY,
    placeholder="e.g. svensk politik",
    max_chars=MAX_QUERY_LENGTH,
)

limit = st.sidebar.slider(
    "Number of posts",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
)

view_mode = st.sidebar.radio(
    "Display mode",
    options=["Cards", "Table"],
    index=0,
)

show_raw = st.sidebar.checkbox("Show raw data", value=False)

search_clicked = st.sidebar.button(
    "🔎 Search X",
    type="primary",
    use_container_width=True,
)

st.sidebar.divider()

# --- Instance management ---
st.sidebar.subheader("🌐 Nitter Instances")
st.sidebar.caption(f"Active source: {st.session_state.nitter_source}")

# Allow manual override of instance list
custom_instances = st.sidebar.text_area(
    "Override instances (one per line)",
    value="\n".join(st.session_state.nitter_instances),
    help="Enter one Nitter URL per line. Leave empty to use the default pool.",
)

if st.sidebar.button("🔄 Apply custom instances"):
    lines = [line.strip().rstrip("/") for line in custom_instances.splitlines() if line.strip()]
    if lines:
        st.session_state.nitter_instances = lines
        st.session_state.nitter_source = "manual override"
        # Clear the router cache so it picks up new instances
        create_router.clear()
        st.sidebar.success(f"Applied {len(lines)} instances.")
    else:
        # Revert to default
        st.session_state.nitter_instances = BASE_INSTANCES.copy()
        st.session_state.nitter_source = BASE_SOURCE
        create_router.clear()
        st.sidebar.success("Reverted to default pool.")

# --- Instance tester ---
if st.sidebar.button("🔍 Test all instances"):
    with st.spinner("Testing instances..."):
        results = []
        for url in st.session_state.nitter_instances:
            ok, err = test_nitter_instance(url)
            results.append((url, ok, err))
        st.session_state.instance_test_results = results

if "instance_test_results" in st.session_state:
    st.sidebar.subheader("Test results")
    for url, ok, err in st.session_state.instance_test_results:
        if ok:
            st.sidebar.success(f"✅ {url}")
        else:
            st.sidebar.error(f"❌ {url} — {err}")

# Clear cache button
if st.sidebar.button("🔄 Clear router cache"):
    create_router.clear()
    st.sidebar.success("Cache cleared.")

st.sidebar.divider()
st.sidebar.subheader("🇸🇪 Example searches")
st.sidebar.code("riksdagsval 2026")
st.sidebar.code("valet 2026")
st.sidebar.code("Socialdemokraterna")
st.sidebar.code("Moderaterna")
st.sidebar.code("Sverigedemokraterna")
st.sidebar.code("Magdalena Andersson")
st.sidebar.code("Ulf Kristersson")


# ============================================================
# MAIN AREA
# ============================================================

st.title("🇸🇪 Swedish Election X Monitor 2026")
st.caption("Free public X‑data prototype using x‑tweet‑fetcher + Nitter")

with st.expander("🔌 Current Nitter configuration"):
    st.write(f"**Source:** {st.session_state.nitter_source}")
    st.write("**Instances tried in order:**")
    for host in st.session_state.nitter_instances:
        st.code(host)
    st.caption(
        "You can override the instance list in the sidebar. "
        "Set XTF_NITTER in Streamlit Secrets for persistent overrides."
    )

st.info(
    "This MVP uses free public Nitter instances. They can be unreliable. "
    "If you get no results, use the sidebar to test instances and apply a working one."
)


# ============================================================
# SEARCH EXECUTION
# ============================================================

if search_clicked:
    error = validate_query(query)
    if error:
        st.error(error)
        st.stop()

    with st.spinner(f'Searching X for "{query}"...'):
        results, backend_used, last_error = search_x(query, limit)

    # Display any error from the router
    if last_error:
        st.warning(f"Router error: {last_error}")

    if results is None:
        st.error("The router returned None. This is unexpected.")
        st.stop()

    if not results:
        st.warning("The search returned zero posts.")
        st.info(
            "Possible reasons:\n"
            "- All Nitter instances are rate‑limited or blocking cloud IPs.\n"
            "- The query is too specific and returns no results.\n"
            "- The instance list is stale. Use the sidebar to test and apply a working instance."
        )
        # Show the raw response from the last attempt if available
        st.stop()

    # Convert to DataFrame
    rows = [tweet_to_dict(item) for item in results]
    df = pd.DataFrame(rows)

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Posts returned", len(df))
    col2.metric("Backend", backend_used or "nitter")
    col3.metric("Query", query)

    st.subheader("📊 X Search Results")

    if view_mode == "Cards":
        for _, row in df.iterrows():
            display_tweet_card(row.to_dict())
    else:
        preferred_columns = [
            "author_name",
            "author",
            "text",
            "likes",
            "retweets",
            "replies",
            "views",
            "time_ago",
            "tweet_id",
        ]
        visible_columns = [c for c in preferred_columns if c in df.columns]
        column_config = {}
        for col in visible_columns:
            if col in ["likes", "retweets", "replies", "views"]:
                column_config[col] = st.column_config.NumberColumn(format="%d")
            elif col == "text":
                column_config[col] = st.column_config.TextColumn(width="large")
        if visible_columns:
            st.dataframe(
                df[visible_columns],
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
            )
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

    if show_raw:
        with st.expander("🔍 Raw returned fields", expanded=True):
            st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.subheader("What this test proves")
    st.write(
        "Search for a Swedish political term. If results appear, the free "
        "X collection layer is working. If not, use the sidebar to test and "
        "switch Nitter instances."
)
