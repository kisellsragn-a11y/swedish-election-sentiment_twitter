import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Swedish Election X Monitor 2026",
    page_icon="🇸🇪",
    layout="wide",
)

st.title("🇸🇪 Swedish Election X Monitor 2026")
st.caption("Experimental X/Twitter data collector")

st.sidebar.header("Search")

query = st.sidebar.text_input(
    "Search X",
    value="svensk politik",
)

limit = st.sidebar.slider(
    "Number of posts",
    min_value=5,
    max_value=100,
    value=20,
)

backend = st.sidebar.selectbox(
    "Backend",
    ["auto", "nitter", "browser"],
)

if st.button("🔎 Search X", type="primary"):

    with st.spinner("Searching X..."):

        try:
            from xtf import Router

            router = Router(backend=backend)

            results = router.search(
                query,
                limit=limit,
            )

            if not results:
                st.warning(
                    "No results returned. "
                    "The selected X backend may not be available."
                )
            else:
                rows = []

                for tweet in results:

                    if hasattr(tweet, "to_dict"):
                        data = tweet.to_dict()
                    elif isinstance(tweet, dict):
                        data = tweet
                    else:
                        data = vars(tweet)

                    rows.append(data)

                df = pd.DataFrame(rows)

                st.success(
                    f"Retrieved {len(df)} posts."
                )

                st.subheader("Posts")

                st.dataframe(
                    df,
                    use_container_width=True,
                )

                st.subheader("Raw data")

                st.json(rows)

        except Exception as e:

            st.error("X search failed.")

            st.code(
                str(e),
                language="text",
            )

            st.info(
                """
                This is expected if no working Nitter
                instance or browser backend is available.

                We will use the error to determine the
                correct deployment architecture.
                """
            )


st.divider()

st.subheader("About")

st.write(
    """
This application tests X/Twitter collection using
the open-source x-tweet-fetcher project.

The project supports FxTwitter, Nitter and browser
backends and provides a unified Tweet data structure.
"""
)
