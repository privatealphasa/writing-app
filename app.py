import streamlit as st
import random
import time
import json
import os
import tempfile
from datetime import date
from openai import OpenAI
import pandas as pd

# ================= CONFIG =================
st.set_page_config("🎮 Daily Writing Quest", layout="wide")

WORDS_FILE = "words.json"
SENTENCES_FILE = "sentence_templates_full.json"
DATA_FILE = "progress.json"
DAILY_TIME_LIMIT = 10 * 60

# ================= PIXEL UI =================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

html, body, input, button {
    font-family: 'Press Start 2P', cursive !important;
}

input {
    font-size: 24px !important;
    text-align: center;
}

.pixel-box {
    background:#5DBB63;
    padding:20px;
    border-radius:10px;
    border:4px solid #2E7D32;
    margin-bottom:15px;
}

.pixel-btn {
    background:#FFD700;
    border:4px solid #B8860B;
    padding:10px;
}
</style>
""", unsafe_allow_html=True)

# ================= OPENAI =================
api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ================= LOAD DATA =================
def load_json(f):
    with open(f, "r", encoding="utf-8") as file:
        return json.load(file)

WORD_SKILLS = load_json(WORDS_FILE)
SENTENCE_TEMPLATES = load_json(SENTENCES_FILE)

# ================= GAME DATA =================
WORLDS = {
    "1": "🌱 Grass World",
    "2": "🪨 Stone Caves",
    "3": "🌲 Forest Realm",
    "4": "🔥 Nether Zone",
    "sentence": "🏰 Creative World"
}

# ================= SESSION STATE =================
defaults = {
    "screen": "play",   # play | map
    "skill": "1",
    "mode": "word",
    "word": "",
    "sentence": "",
    "xp": 0,
    "hearts": 3,
    "streak": 0,
    "incorrect_attempts": 0,
    "input_id": 0,
    "start_time": time.time(),
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ================= HELPERS =================
def speak(text):
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        f.write(response.read())
        return f.name

def pick_word(skill, easier=False):
    words = WORD_SKILLS[skill]["words"]
    return random.choice(words[:5] if easier else words)

def pick_sentence(skill):
    return random.choice(SENTENCE_TEMPLATES[skill]["templates"])

# ================= SIDEBAR =================
st.sidebar.title("🎮 Menu")
if st.sidebar.button("🎯 Play"):
    st.session_state.screen = "play"
if st.sidebar.button("🗺️ Map"):
    st.session_state.screen = "map"

# ================= MAP SCREEN =================
if st.session_state.screen == "map":
    st.header("🗺️ World Map")
    for k, v in WORLDS.items():
        unlocked = int(st.session_state.skill) >= int(k) if k.isdigit() else st.session_state.mode == "sentence"
        st.markdown(
            f"{'🟢' if unlocked else '🔒'} **{v}**"
        )
    st.stop()

# ================= TIMER =================
remaining = max(0, DAILY_TIME_LIMIT - int(time.time() - st.session_state.start_time))
st.progress(remaining / DAILY_TIME_LIMIT)

# ================= HEADER =================
st.markdown(f"""
<div class='pixel-box' style='text-align:center'>
<h1>🎮 Daily Writing Quest</h1>
<h3>{WORLDS.get(st.session_state.skill)}</h3>
</div>
""", unsafe_allow_html=True)

# ================= PICK CONTENT =================
if st.session_state.mode == "word" and not st.session_state.word:
    st.session_state.word = pick_word(
        st.session_state.skill,
        easier=st.session_state.incorrect_attempts >= 2
    )

if st.session_state.mode == "sentence" and not st.session_state.sentence:
    st.session_state.sentence = pick_sentence(st.session_state.skill)

target = st.session_state.word if st.session_state.mode == "word" else st.session_state.sentence

# ================= AUDIO =================
st.subheader("👂 Listen")
st.audio(speak(target))

# ================= INPUT =================
typed = st.text_input(
    "⌨️ Type what you hear",
    key=f"in_{st.session_state.input_id}"
)

# ================= SUBMIT =================
if st.button("🚀 Submit"):
    if typed.upper().strip() == target.upper():
        st.success("💎 Correct!")
        st.session_state.xp += 10
        st.session_state.streak += 1
        st.session_state.incorrect_attempts = 0

        # Adaptive difficulty
        if st.session_state.streak >= 3:
            next_skill = str(int(st.session_state.skill) + 1)
            if next_skill in WORD_SKILLS:
                st.session_state.skill = next_skill
            else:
                st.session_state.mode = "sentence"

        st.session_state.word = ""
        st.session_state.sentence = ""
        st.session_state.input_id += 1
        st.balloons()
        st.rerun()

    else:
        st.session_state.incorrect_attempts += 1
        st.error("❌ Try again!")

        # ✅ FIX: SHOW ANSWER AFTER 3 FAILS
        if st.session_state.incorrect_attempts >= 3:
            st.warning(f"✅ Correct answer was: **{target}**")
            st.session_state.incorrect_attempts = 0
            st.session_state.streak = 0
            st.session_state.hearts -= 1
            st.session_state.word = ""
            st.session_state.sentence = ""
            time.sleep(2)

        st.session_state.input_id += 1
        st.rerun()

# ================= GAME OVER =================
if st.session_state.hearts <= 0 or remaining == 0:
    st.success("🏁 Quest Complete! Great job today!")
    st.stop()
