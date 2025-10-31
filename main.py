import os
import json
import asyncio
import tempfile
from functools import lru_cache
import streamlit as st
import edge_tts

# --- Minimal critical comments only ---
# i18n loader (JSON files under ./languages/)
class I18N:
    def __init__(self, dir_path: str = "languages"):
        self.dir = dir_path
        self._cache = {}

    def load(self, lang: str) -> dict:
        if lang in self._cache:
            return self._cache[lang]
        fp = os.path.join(self.dir, f"{lang}.json")
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._cache[lang] = data
        return data

    def langs(self):
        return [os.path.splitext(f)[0] for f in os.listdir(self.dir) if f.endswith(".json")]

# Edge helpers
def to_edge_percent(v: int) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{int(v)}%"

def to_edge_hz(v: int) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{int(v)}Hz"

def default_docs_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Documents", "pars")

def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

async def synth_stream_with_srt(text: str, voice: str, rate_pct: str, vol_pct: str, pitch_hz: str):
    communicate = edge_tts.Communicate(text, voice, rate=rate_pct, volume=vol_pct, pitch=pitch_hz)
    submaker = edge_tts.SubMaker()
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                tmp.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                try:
                    submaker.feed(chunk)
                except Exception:
                    try:
                        submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
                    except Exception:
                        pass
    with open(tmp_path, "rb") as f:
        mp3 = f.read()
    os.remove(tmp_path)
    srt = ""
    for attr in ("to_srt", "generate_subs"):
        fn = getattr(submaker, attr, None)
        if callable(fn):
            srt = fn()
            break
    return mp3, srt or ""

# voices: fetch once, cache in session
async def fetch_voices():
    # returns list of dicts from edge-tts
    return await edge_tts.list_voices()

def get_voices():
    if "all_voices" not in st.session_state:
        st.session_state.all_voices = run_async(fetch_voices())
    return st.session_state.all_voices

# sort: chosen UI language voices on top
def sort_voices_for_lang(voices: list[dict], ui_lang: str) -> list[str]:
    # map UI lang -> preferred locales
    preferred = {
        "tr": ["tr-TR"],
        "en": ["en-US", "en-GB", "en-AU", "en-CA"],
    }.get(ui_lang, [])
    def key(v):
        loc = v.get("Locale", "")
        name = v.get("ShortName", "")
        rank = 0 if any(loc.startswith(p) for p in preferred) else 1
        return (rank, loc, name)
    sorted_list = sorted(voices, key=key)
    # unique by ShortName
    seen, names = set(), []
    for v in sorted_list:
        n = v.get("ShortName", "")
        if n and n not in seen:
            seen.add(n); names.append(n)
    return names

# UI setup
st.set_page_config(page_title="Edge TTS Studio", page_icon="🎧", layout="wide")
os.makedirs(default_docs_dir(), exist_ok=True)

# i18n
i18n = I18N("languages")
available_langs = i18n.langs() or ["tr", "en"]
ui_lang = st.sidebar.selectbox("Language / Dil", available_langs, index=available_langs.index("tr") if "tr" in available_langs else 0)
T = i18n.load(ui_lang)

st.title(T["title"])
st.caption(T["caption"])

# Text + settings
left, right = st.columns([2, 1], gap="large")
with left:
    text = st.text_area(T["text"], height=260, placeholder=T["placeholder"])

with right:
    st.subheader(T["settings"])

    # voices
    voices = get_voices()
    voice_names_sorted = sort_voices_for_lang(voices, ui_lang)
    # set default voice per lang
    default_voice = T.get("default_voice", voice_names_sorted[0] if voice_names_sorted else "")
    try:
        default_idx = voice_names_sorted.index(default_voice)
    except ValueError:
        default_idx = 0
    voice_name = st.selectbox(T["voice"], voice_names_sorted, index=default_idx)

    rate = st.slider(T["rate"], -100, 100, 0, 1)
    volume = st.slider(T["volume"], -100, 100, 0, 1)
    pitch = st.slider(T["pitch"], -50, 50, 0, 1)
    st.write(T["ratevolpitch"].format(rate=to_edge_percent(rate), vol=to_edge_percent(volume), pitch=to_edge_hz(pitch)))

    st.divider()
    st.subheader(T["save"])
    save_dir = st.text_input(T["folder"], value=default_docs_dir())
    file_stem = st.text_input(T["filename"], value="noname")
    auto_mkdir = st.checkbox(T["mkdir"], value=True)
    if auto_mkdir and save_dir.strip():
        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception as e:
            st.warning(str(e))

st.divider()
btn_col, out_col = st.columns([1, 3], gap="large")
generate = btn_col.button(T["gen"], type="primary", use_container_width=True)

if "mp3_bytes" not in st.session_state:
    st.session_state.mp3_bytes = None
if "srt_text" not in st.session_state:
    st.session_state.srt_text = ""

if generate:
    if not text.strip():
        st.error(T["empty"])
    else:
        with st.spinner(T["synthing"]):
            mp3_bytes, srt_text = run_async(
                synth_stream_with_srt(
                    text=text.strip(),
                    voice=voice_name,
                    rate_pct=to_edge_percent(rate),
                    vol_pct=to_edge_percent(volume),
                    pitch_hz=to_edge_hz(pitch),
                )
            )
            st.session_state.mp3_bytes = mp3_bytes
            st.session_state.srt_text = srt_text
        st.success(T["ready"])

if st.session_state.mp3_bytes:
    with out_col:
        st.audio(st.session_state.mp3_bytes, format="audio/mp3")
        c1, c2, c3 = st.columns([1.2, 1, 1])
        c1.download_button(
            T["mp3dl"],
            data=st.session_state.mp3_bytes,
            file_name=f"{file_stem or 'noname'}.mp3",
            mime="audio/mpeg",
            use_container_width=True,
        )
        c2.download_button(
            T["srtdl"],
            data=st.session_state.srt_text.encode("utf-8"),
            file_name=f"{file_stem or "noname"}.srt",
            mime="text/plain",
            use_container_width=True,
        )
        if save_dir.strip() and c3.button(T["srvsave"], use_container_width=True):
            try:
                mp3_path = os.path.join(save_dir, f"{file_stem or 'noname'}.mp3")
                srt_path = os.path.join(save_dir, f"{file_stem or 'noname'}.srt")
                with open(mp3_path, "wb") as f:
                    f.write(st.session_state.mp3_bytes)
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(st.session_state.srt_text)
                st.success(T["saved"].format(mp3=mp3_path, srt=srt_path))
            except Exception as e:
                st.error(T["nosave"].format(e=e))

    with st.expander(T["subs_preview"]):
        if st.session_state.srt_text.strip():
            st.code(st.session_state.srt_text, language="srt")
        else:
            st.info(T["no_subs"])
