import os
from typing import Any

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
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_QUERY = "svensk politik"

# Read Nitter configuration from Streamlit Secrets first,
# then environment variables.
XTF_NITTER = st.secrets.get(
    "XTF_NITTER",
    os.getenv("XTF_NITTER", ""),
).strip()

# Keep backend explicit. Search is handled through Nitter.
BACKEND = "nitter"


# ============================================================
# HEADER
# ============================================================

st.title("🇸🇪 Swedish Election X Monitor 2026")

st.caption(
    "Free X-data prototype using x-tweet-fetcher 3.1.0 + Nitter"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ X Search")

    query = st.text_input(
        "Search query",
        value=DEFAULT_QUERY,
        placeholder="e.g. svensk politik",
    )

    limit = st.slider(
        "Number of posts",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
    )

    st.divider()

    st.subheader("Backend")

    st.write("Nitter")

    if XTF_NITTER:
        st.success("Nitter endpoint configured")
    else:
        st.error("Nitter endpoint missing")

    st.divider()

    st.subheader("🇸🇪 Example searches")

    examples = [
        "svensk politik",
        "riksdagsval 2026",
        "valet 2026",
        "Socialdemokraterna",
        "Moderaterna",
        "Sverigedemokraterna",
        "Magdalena Andersson",
        "Ulf Kristersson",
    ]

    for example in examples:
        st.code(example)


# ============================================================
# NITTER CONFIGURATION CHECK
# ============================================================

if not XTF_NITTER:

    st.warning(
        """
        ### Nitter is not configured

        `x-tweet-fetcher` defaults to:

        `http://127.0.0.1:8788`

        That address is inside the Streamlit container and does not
        provide a Nitter server.

        Add a reachable Nitter server to Streamlit Secrets:

        `XTF_NITTER = "https://your-nitter-server"`

        Multiple servers can be supplied as comma-separated URLs.
        """
    )

    st.stop()


# ============================================================
# SHOW CONFIGURATION WITHOUT EXPOSING SECRETS
# ============================================================

def clean_nitter_display(value: str) -> str:
    """Display configured Nitter hosts without exposing anything sensitive."""
    hosts = []

    for item in value.split(","):
        item = item.strip()

        if not item:
            continue

        # Remove protocol for cleaner display.
        display = (
            item.replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
        )

        hosts.append(display)

    return ", ".join(hosts)


with st.expander("🔌 Connection configuration"):
    st.write("Backend:", BACKEND)
    st.write("Nitter:", clean_nitter_display(XTF_NITTER))


# ============================================================
# SEARCH FUNCTION
# ============================================================

@st.cache_resource
def create_router() -> Router:
    """
    Create the x-tweet-fetcher router.

    XTF_NITTER is read by x-tweet-fetcher from the environment.
    """
    os.environ["XTF_NITTER"] = XTF_NITTER

    return Router(
        backend=BACKEND,
    )


def search_x(query_text: str, search_limit: int) -> list[Any]:

    router = create_router()

    results = router.search(
        query_text,
        limit=search_limit,
    )

    # Convert the returned object into a normal list.
    if results is None:
        return []

    return list(results)


# ============================================================
# SEARCH BUTTON
# ============================================================

search_clicked = st.button(
    "🔎 Search X",
    type="primary",
    use_container_width=True,
)


# ============================================================
# SEARCH
# ============================================================

if search_clicked:

    if not query.strip():
        st.error("Enter a search query.")
        st.stop()

    with st.spinner(
        f'Searching X for "{query.strip()}"...'
    ):

        try:

            results = search_x(
                query.strip(),
                limit,
            )

        except Exception as exc:

            st.error("X search failed.")

            st.code(
                str(exc),
                language="text",
            )

            st.warning(
                """
                The application is installed correctly, but the
                configured Nitter server could not complete the search.

                Check that:

                1. XTF_NITTER is a real reachable Nitter server.
                2. The Nitter server is online.
                3. The URL does not point to 127.0.0.1.
                4. The server supports `/search`.
                """
            )

            st.stop()

    # ========================================================
    # RESULTS
    # ========================================================

    if not results:

        st.info(
            "No X posts were returned for this search."
        )

        st.stop()

    st.success(
        f"Retrieved {len(results)} results."
    )

    # ========================================================
    # NORMALIZE RESULTS
    # ========================================================

    rows = []

    for item in results:

        if isinstance(item, dict):

            row = item.copy()

        else:

            # Try to convert model/object results into a dictionary.
            try:
                row = vars(item)
            except TypeError:
                row = {
                    "result": str(item)
                }

        rows.append(row)

    df = pd.DataFrame(rows)

    # ========================================================
    # RESULTS TABLE
    # ========================================================

    st.subheader("📊 X Search Results")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # RAW RESULTS
    # ========================================================

    with st.expander("🔍 Raw results"):

        for index, result in enumerate(results, start=1):

            st.markdown(f"### Result {index}")

            st.write(result)
