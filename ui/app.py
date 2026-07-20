"""StyleSwipe's local Streamlit interface."""

from pathlib import Path

import httpx
import streamlit as st

from ui.api_client import (
    NoSeedsError,
    get_api_url,
    get_feed,
    post_embed,
    post_swipe,
)

BACKEND_START_COMMAND = "uv run uvicorn app.main:app --reload"
SEED_INGEST_COMMAND = "uv run python -m app.ingest <folder> --source seed"


def _show_backend_unreachable() -> None:
    st.error("The StyleSwipe backend is not reachable. Start the backend with:")
    st.code(BACKEND_START_COMMAND)


def _show_onboarding() -> None:
    st.info("Add and embed seed wardrobe images before browsing candidates.")
    st.write("First, ingest a folder of seed images:")
    st.code(SEED_INGEST_COMMAND)
    st.write(
        "Then click **Embed pending items** in the sidebar. "
        "That button calls `POST /embed` for you."
    )


def _record_swipe(
    client: httpx.Client,
    item_id: int,
    liked: bool,
) -> None:
    try:
        post_swipe(client, item_id=item_id, liked=liked)
    except httpx.ConnectError:
        _show_backend_unreachable()
        return
    except httpx.HTTPError as exc:
        st.error(f"The backend could not record that swipe: {exc}")
        return

    st.session_state.queue.pop(0)
    count_key = "likes" if liked else "dislikes"
    st.session_state[count_key] += 1
    st.rerun()


st.set_page_config(page_title="StyleSwipe", page_icon="👕", layout="centered")
st.title("StyleSwipe")

st.session_state.setdefault("queue", [])
st.session_state.setdefault("likes", 0)
st.session_state.setdefault("dislikes", 0)

with httpx.Client(base_url=get_api_url(), timeout=30.0) as api_client:
    with st.sidebar:
        st.header("This session")
        likes_column, dislikes_column = st.columns(2)
        likes_column.metric("Likes", st.session_state.likes)
        dislikes_column.metric("Dislikes", st.session_state.dislikes)

        if st.button("Embed pending items", width="stretch"):
            try:
                embed_result = post_embed(api_client)
            except httpx.ConnectError:
                _show_backend_unreachable()
                st.stop()
            except httpx.HTTPError as exc:
                st.error(f"The backend could not embed pending items: {exc}")
            else:
                failed_count = len(embed_result.get("failed", []))
                st.success(
                    f"Embedded: {embed_result.get('embedded', 0)} · "
                    f"Failed: {failed_count}"
                )

    if not st.session_state.queue:
        try:
            st.session_state.queue = get_feed(api_client, limit=20)
        except NoSeedsError:
            _show_onboarding()
            st.stop()
        except httpx.ConnectError:
            _show_backend_unreachable()
            st.stop()
        except httpx.HTTPError as exc:
            st.error(f"The backend could not load the feed: {exc}")
            st.stop()

    if not st.session_state.queue:
        st.info("No more candidates — ingest more or come back later.")
        st.stop()

    item = st.session_state.queue[0]
    image_path = Path(str(item["image_path"]))
    if image_path.is_file():
        st.image(str(image_path), width="stretch")
    else:
        st.caption(f"Missing image: {image_path}")

    title = item.get("title") or image_path.name
    brand = item.get("brand")
    st.subheader(f"{brand} — {title}" if brand else title)
    st.caption(f"Style match: {float(item['score']):.3f}")

    like_column, dislike_column = st.columns(2)
    with like_column:
        if st.button("👍 Like", type="primary", width="stretch"):
            _record_swipe(api_client, item_id=int(item["id"]), liked=True)
    with dislike_column:
        if st.button("👎 Dislike", width="stretch"):
            _record_swipe(api_client, item_id=int(item["id"]), liked=False)
