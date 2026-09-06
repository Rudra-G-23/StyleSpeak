"""Voice + text shopping assistant page.

Microphone and text box feed the *same* function
(:func:`src.assistant.handler.handle_user_message`). Voice only adds a local
speech-to-text step in front. Text stays as the fallback / debugging input.
"""

from __future__ import annotations

import streamlit as st

from src.assistant.handler import AssistantState, handle_user_message
from src.assistant.ollama_client import health
from src.assistant.voice import TranscriptionError, transcribe
from src.cart import add_to_cart
from src.config import OLLAMA_MODEL, WHISPER_MODEL
from src.ui import cart_count, ensure_session_state, euro, image_src

ensure_session_state()


def ensure_assistant_state() -> None:
    st.session_state.setdefault("assistant_msgs", [])  # [{role, content, kind, results}]
    st.session_state.setdefault("assistant_last_results", [])  # ordered result dicts
    st.session_state.setdefault("assistant_last_filters", None)
    # Bumped after every recording so st.audio_input is rebuilt empty and is
    # immediately ready for the next utterance (never re-processes the old one).
    st.session_state.setdefault("assistant_audio_key", 0)
    st.session_state.setdefault("assistant_warmed", False)


ensure_assistant_state()

RESULT_COLUMNS = 3
_COLOR_DOT = {
    "black": "#222222",
    "white": "#f4f4f4",
    "grey": "#9aa0a6",
    "blue": "#2b6cff",
    "navy": "#1b2a55",
    "red": "#e0393e",
    "green": "#2f9e44",
    "yellow": "#f5c518",
    "orange": "#f08c00",
    "pink": "#e64980",
    "purple": "#8a3ffc",
    "brown": "#8a5a2b",
    "beige": "#d9c9a3",
    "burgundy": "#7d2231",
    "teal": "#0c8599",
    "gold": "#c9a227",
}


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def _add_from_card(sku: str, name: str) -> None:
    add_to_cart(st.session_state.cart, sku, 1)
    st.toast(f"Added to cart: {name}")


def render_results(results: list[dict], *, key_prefix: str, interactive: bool) -> None:
    for row_start in range(0, len(results), RESULT_COLUMNS):
        cols = st.columns(RESULT_COLUMNS)
        for col, product in zip(
            cols, results[row_start : row_start + RESULT_COLUMNS], strict=False
        ):
            with col, st.container(border=True):
                st.image(image_src(product.get("image_path")), use_container_width=True)
                dot = _COLOR_DOT.get(product.get("color", ""), "#cccccc")
                st.markdown(
                    f"<span style='display:inline-block;width:10px;height:10px;border-radius:50%;"
                    f"background:{dot};border:1px solid #0002;margin-right:6px'></span>"
                    f"**{product['position']}. {product.get('name', 'Unnamed')}**",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"{product.get('brand', '')} - {product.get('color', '')} - "
                    f"{product.get('gender', '')}"
                )
                st.markdown(f"**{euro(product.get('promotional_price'))}**")
                sku = product["sku"]
                st.button(
                    "Add to cart",
                    key=f"{key_prefix}_add_{sku}",
                    use_container_width=True,
                    disabled=not interactive,
                    on_click=_add_from_card,
                    args=(sku, product.get("name", sku)),
                )


def render_history() -> None:
    msgs = st.session_state.assistant_msgs
    if not msgs:
        st.info("Your conversation will appear here. Try the examples above.")
        return
    for index, msg in enumerate(msgs):
        avatar = "🧑" if msg["role"] == "user" else "🛍️"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg.get("kind") == "error":
                st.warning(msg["content"])
            else:
                st.markdown(msg["content"])
            if msg.get("results"):
                render_results(
                    msg["results"],
                    key_prefix=f"msg{index}",
                    interactive=(index == len(msgs) - 1),
                )


# --------------------------------------------------------------------------- #
# Sidebar - cart pointer + local-model status
# --------------------------------------------------------------------------- #
cart = st.session_state.cart
with st.sidebar:
    with st.container(border=True):
        st.markdown("#### Cart")
        st.caption(f"{cart_count(cart)} item(s)")
        st.page_link("views/cart.py", label="Open cart", icon=":material/shopping_cart:")
        st.page_link("views/catalog.py", label="Browse full catalog", icon=":material/storefront:")
    st.divider()
    st.caption("Runs fully local")
    st.caption(f"LLM: `{OLLAMA_MODEL}`")
    st.caption(f"Speech: `faster-whisper {WHISPER_MODEL}`")


# --------------------------------------------------------------------------- #
# Header + model health
# --------------------------------------------------------------------------- #
st.title("Shopping Assistant")
st.caption(
    'Say or type things like *"show me black jackets under 100"*, '
    '*"something casual for a birthday dinner"*, or *"add the second one"*.'
)

ok, message = health()
if not ok:
    st.error(message)

# Keep the voice bar parked just above the docked chat input from the first
# load: the conversation area reserves the vertical space so the inputs do not
# drift up the page when the history is short.
st.markdown(
    """
    <style>
    .st-key-assistant_convo { min-height: 56vh; }
    .st-key-assistant_voice [data-testid="stAudioInput"] { margin-top: .25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Conversation renders into this slot; the voice + text inputs sit just below it,
# right above Streamlit's docked chat bar.
conversation = st.container(key="assistant_convo")

# --------------------------------------------------------------------------- #
# Inputs - microphone (voice) and chat box (text). Both call the same handler.
# --------------------------------------------------------------------------- #
with st.container(key="assistant_voice"):
    audio = st.audio_input(
        "Speak your request",
        key=f"voice_{st.session_state.assistant_audio_key}",
        label_visibility="collapsed",
    )

typed = st.chat_input("Type a request, or 'add the second one'")

pending_text: str | None = None

if audio is not None:
    try:
        with st.spinner("Transcribing your voice locally..."):
            pending_text = transcribe(audio.getvalue())
    except TranscriptionError as exc:
        st.session_state.assistant_msgs.append(
            {"role": "assistant", "kind": "error", "content": str(exc)}
        )
    # Consume this recording: next run rebuilds st.audio_input empty.
    st.session_state.assistant_audio_key += 1
    if not pending_text:
        st.rerun()

if typed:
    pending_text = typed.strip()

if pending_text:
    st.session_state.assistant_msgs.append({"role": "user", "content": pending_text})

    state = AssistantState(
        cart=st.session_state.cart,
        last_results=st.session_state.assistant_last_results,
        last_filters=st.session_state.assistant_last_filters,
    )
    first_call = not st.session_state.assistant_warmed
    spinner_text = (
        "Waking up the local model (the first request is slower)..."
        if first_call
        else "Understanding your request..."
    )
    with st.spinner(spinner_text):
        reply = handle_user_message(pending_text, state)
    st.session_state.assistant_warmed = True
    st.session_state.assistant_last_results = state.last_results
    st.session_state.assistant_last_filters = state.last_filters

    st.session_state.assistant_msgs.append(
        {
            "role": "assistant",
            "kind": reply.kind,
            "content": reply.text,
            "results": reply.results,
        }
    )
    st.rerun()


# --------------------------------------------------------------------------- #
# Conversation (filled last so the newest turn is included, shown above inputs)
# --------------------------------------------------------------------------- #
with conversation:
    render_history()
