import os
from typing import Any, List, Tuple, Optional

import pandas as pd
import streamlit as st
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
DEFAULT_TIMEOUT = 10  # seconds, if the underlying library supports it

# Public instances currently listed as working by the Nitter project.
DEFAULT_NITTER_INSTANCES = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.privacyredirect.com",
    "https://lightbrd.com",
    "https://nitter.space",
    "https://nitter.tiekoetter.com",
    "https://nitter.catsarch.com",
    "https://nitter.kareem.one",
]


def _read_optional_secret(name: str) -> str:
    """
    Safely read a Streamlit secret, falling back to an environment variable.

    Args:
        name: The secret name (e.g., 'XTF_NITTER').

    Returns:
        The value as a stripped string, or an empty string if not set.
    """
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    except (KeyError, AttributeError):
        pass
    return os.getenv(name, "").strip()


def get_nitter_instances() -> Tuple[List[str], str]:
    """
    Determine the list of Nitter instances to use.

    If XTF_NITTER is configured (secret or env), parse its comma‑separated list.
    Otherwise fall back to the default public pool.

    Returns:
        A tuple: (list of instance URLs, source description).
    """
    configured = _read_optional_secret("XTF_NITTER")
    if configured:
        instances = [
            item.strip().rstrip("/")
            for item in configured.split(",")
            if item.strip()
        ]
        if instances:
            return instances, "Streamlit secret / environment"

    return DEFAULT_NITTER_INSTANCES.copy(), "public Nitter failover pool"


NITTER_INSTANCES, NITTER_SOURCE = get_nitter_instances()


# ============================================================
# X ROUTER (CACHED)
# ============================================================

@st.cache_resource(show_spinner=False)
def create_router(instances: tuple[str, ...]) -> Router:
    """
    Create and cache a Nitter‑only Router.

    Args:
        instances: A tuple of Nitter instance URLs.

    Returns:
        An xtf.Router instance.
    """
    return Router(
        backend="nitter",
        nitter_instances=list(instances),
    )


def search_x(query_text: str, search_limit: int) -> Tuple[List[Any], str]:
    """
    Perform a search on X via the cached Router.

    Args:
        query_text: The search query.
        search_limit: Maximum number of posts to return.

    Returns:
        A tuple: (list of tweet objects, backend name used).
    """
    router = create_router(tuple(NITTER_INSTANCES))
    results = router.search(query_text, limit=search_limit)
    return list(results or []), router.last_backend


def tweet_to_dict(item: Any) -> dict[str, Any]:
    """
    Convert a tweet object (dict, custom object, etc.) to a dictionary.

    This function is defensive: it first tries .to_dict(), then vars(), then
    falls back to a simple string representation.

    Args:
        item: A tweet object returned by xtf.

    Returns:
        A dictionary representation of the tweet.
    """
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
# UI HELPERS
# ============================================================

def display_tweet_card(tweet: dict) -> None:
    """
    Render a single tweet as a styled card using Streamlit columns.

    Args:
        tweet: A dictionary containing tweet fields.
    """
    # Extract fields with fallbacks
    author = tweet.get("author", tweet.get("author_name", "Unknown"))
    text = tweet.get("text", "")
    likes = tweet.get("likes", 0)
    retweets = tweet.get("retweets", 0)
    replies = tweet.get("replies", 0)
    views = tweet.get("views", None)
    time_ago = tweet.get("time_ago", "")
    tweet_id = tweet.get("tweet_id", "")

    # Build a simple card using markdown and columns
    with st.container():
        col_left, col_right = st.columns([4, 1])
        with col_left:
            st.markdown(f"**{author}**")
            st.caption(f"{time_ago} · {tweet_id}" if tweet_id else time_ago)
            st.write(text)
        with col_right:
            # Metrics as a vertical stack
            st.metric("❤️", likes)
            st.metric("🔁", retweets)
            st.metric("💬", replies)
            if views is not None:
                st.metric("👁️", views)
        st.divider()


def validate_query(query: str) -> Optional[str]:
    """
    Validate the search query.

    Args:
        query: The raw query string.

    Returns:
        An error message if invalid, otherwise None.
    """
    cleaned = query.strip()
    if not cleaned:
        return "Query cannot be empty."
    if len(cleaned) > MAX_QUERY_LENGTH:
        return f"Query must be at most {MAX_QUERY_LENGTH} characters."
    return None


# ============================================================
# SIDEBAR & MAIN UI
# ============================================================

st.title("🇸🇪 Swedish Election X Monitor 2026")
st.caption("Free public X‑data prototype using x‑tweet‑fetcher 3.1.0 + Nitter")

with st.sidebar:
    st.header("⚙️ Search Settings")

    query = st.text_input(
        "Search query",
        value=DEFAULT_QUERY,
        placeholder="e.g. svensk politik",
        max_chars=MAX_QUERY_LENGTH,
    )

    limit = st.slider(
        "Number of posts",
        min_value=5,
        max_value=50,
        value=20,
        step=5,
    )

    view_mode = st.radio(
        "Display mode",
        options=["Cards", "Table"],
        index=0,
        help="Cards show a more social‑media style; Table is compact and sortable.",
    )

    show_raw = st.checkbox("Show raw data", value=False, help="Display all returned fields in an expander.")

    search_clicked = st.button(
        "🔎 Search X",
        type="primary",
        use_container_width=True,
    )

    # Clear cache button (optional)
    if st.button("🔄 Clear router cache", use_container_width=True):
        create_router.clear()
        st.success("Router cache cleared. New instances will be used on next search.")

    st.divider()
    st.subheader("Connection")
    st.success("Free Nitter search enabled")
    st.caption(f"Source: {NITTER_SOURCE}")
    st.caption(f"Failover instances: {len(NITTER_INSTANCES)}")

    st.divider()
    st.subheader("🇸🇪 Example searches")
    st.code("riksdagsval 2026")
    st.code("valet 2026")
    st.code("Socialdemokraterna")
    st.code("Moderaterna")
    st.code("Sverigedemokraterna")
    st.code("Magdalena Andersson")
    st.code("Ulf Kristersson")


with st.expander("🔌 Nitter configuration"):
    st.write(f"**Mode:** Nitter direct HTTP")
    st.write(f"**Configuration source:** {NITTER_SOURCE}")
    st.write("**Instances tried in order:**")
    for host in NITTER_INSTANCES:
        st.code(host)
    st.caption(
        "Optional: set XTF_NITTER in Streamlit Secrets to a comma‑separated "
        "list of preferred Nitter instances. It is no longer required."
    )

st.info(
    "This MVP uses free public Nitter instances rather than the paid X API. "
    "Public instances can rate‑limit, block cloud IPs, or go offline, so the app "
    "tries several in sequence. Keep collection volumes modest."
)


# ============================================================
# SEARCH EXECUTION
# ============================================================

if search_clicked:
    # Validate query
    error = validate_query(query)
    if error:
        st.error(error)
        st.stop()

    with st.spinner(f'Searching X for "{query}"...'):
        try:
            results, backend_used = search_x(query, limit)
        except Exception as exc:
            # Provide a more user‑friendly error
            st.error("X search failed across the configured Nitter instances.")
            st.code(str(exc), language="text")
            st.warning(
                "This usually means the public Nitter pool is rate‑limiting, "
                "blocking cloud IPs, or experiencing an outage. You can override "
                "the pool with XTF_NITTER in Streamlit Secrets without changing App.py."
            )
            st.stop()

    if not results:
        st.warning("The search completed, but returned no posts. Try a different query.")
        st.stop()

    # Convert results to DataFrame
    rows = [tweet_to_dict(item) for item in results]
    df = pd.DataFrame(rows)

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Posts returned", len(df))
    col2.metric("Backend", backend_used or "nitter")
    col3.metric("Query", query)

    # Display based on view mode
    st.subheader("📊 X Search Results")

    if view_mode == "Cards":
        # Show each tweet as a card
        for _, row in df.iterrows():
            display_tweet_card(row.to_dict())
    else:
        # Table view with column configuration
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

        # Configure columns for better display
        column_config = {}
        for col in visible_columns:
            if col in ["likes", "retweets", "replies", "views"]:
                column_config[col] = st.column_config.NumberColumn(format="%d")
            elif col == "text":
                column_config[col] = st.column_config.TextColumn(width="large")
            elif col == "tweet_id":
                # Could add a link to the tweet if needed
                pass

        if visible_columns:
            st.dataframe(
                df[visible_columns],
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
            )
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Raw data expander
    if show_raw:
        with st.expander("🔍 Raw returned fields", expanded=True):
            st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.subheader("What this test proves")
    st.write(
        "Search for a Swedish political term. If results appear, the free "
        "X collection layer is working and the next step is to add SQLite, "
        "party/issue detection, sentiment analysis, and the election dashboard."
    )
