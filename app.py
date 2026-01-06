import streamlit as st
import random
import time
import json
import os
import tempfile
from datetime import date, timedelta
from openai import OpenAI
import pandas as pd

# ================= CONFIG =================
st.set_page_config(page_title="🎮 Daily Writing Quest", layout="wide")

DATA_FILE = "progress.json"
WORDS_FILE = "words.json"
SENTENCES_FILE = "sentence_templates_full.json"
DAILY_TIME_LIMIT = 10 * 60

# ================= OPENAI =================
api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OPENAI_API_KEY missing")
    st.stop()

client = OpenAI(api_key=api_key)

# ================= LOAD DATA =================
def load_json(file):
    if not os.path.exists(file):
        st.error(f"{file} not found")
        st.stop()
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

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

ITEMS = ["🧱", "🪵", "🪨", "💎"]
SUCCESS_LINES = ["💎 Epic!", "⚔️ Critical Hit!", "🧠 Brain Level Up!"]
FAIL_LINES = ["😅 Almost!", "🪵 Oof! Try again!", "🙈 Tricky one!"]

AVATARS = ["🧙 Wizard", "🧑‍🚀 Astronaut", "🧱 Builder", "🐉 Dragon Trainer"]

# ================= HELPERS =================
def speak(text, voice):
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        f.write(response.read())
        return f.name

def today_key():
    return str(date.today())

def load_progress():
    return json.load(open(DATA_FILE)) if os.path.exists(DATA_FILE) else {}

def save_progress(p):
    json.dump(p, open(DATA_FILE, "w"), indent=2)

def pick_word(skill):
    return random.choice(WORD_SKILLS[skill]["words"])

def pick_sentence(skill):
    return random.choice(SENTENCE_TEMPLATES[skill]["templates"])

# ================= SESSION STATE =================
defaults = {
    "start_time": time.time(),
    "skill": "1",
    "mode": "word",
    "word": "",
    "sentence": "",
    "xp": 0,
    "hearts": 3,
    "inventory": [],
    "house": [],
    "badges": [],
    "streak": 0,
    "input_id": 0,
    "avatar": AVATARS[0],
    "voice": "alloy"
}

for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ================= SIDEBAR =================
st.sidebar.subheader("🧑 Character")
st.session_state.avatar = st.sidebar.selectbox("Choose Avatar", AVATARS)

st.sidebar.subheader("🎤 Voice")
voices = {"American": "alloy", "British": "nova", "South African": "verse"}
st.session_state.voice = voices[
    st.sidebar.selectbox("Accent", list(voices.keys()))
]

# ================= TIMER =================
elapsed = int(time.time() - st.session_state.start_time)
remaining = max(0, DAILY_TIME_LIMIT - elapsed)

# ================= HEADER =================
st.markdown("""
<div style='text-align:center; background:#6BCF63; padding:20px; border-radius:20px'>
<h1>🎮 Daily Writing Quest</h1>
<h3>Spell Words • Earn XP • Build Your World</h3>
</div>
""", unsafe_allow_html=True)

st.progress(remaining / DAILY_TIME_LIMIT)

# ================= GAME STATS =================
cols = st.columns(4)
cols[0].metric("⚡ XP", st.session_state.xp)
cols[1].metric("❤️ Hearts", st.session_state.hearts)
cols[2].metric("🌍 World", WORLDS.get(st.session_state.skill))
cols[3].metric("🧍 Avatar", st.session_state.avatar)

# ================= TIME UP =================
if remaining == 0 or st.session_state.hearts == 0:
    progress = load_progress()
    progress.setdefault(today_key(), {})
    progress[today_key()][st.session_state.skill] = {
        "xp": st.session_state.xp
    }
    save_progress(progress)
    st.success("🎉 Quest Complete!")
    st.stop()

# ================= CONTENT =================
if st.session_state.mode == "word" and not st.session_state.word:
    st.session_state.word = pick_word(st.session_state.skill)

if st.session_state.mode == "sentence" and not st.session_state.sentence:
    st.session_state.sentence = pick_sentence(st.session_state.skill)

target = st.session_state.word if st.session_state.mode == "word" else st.session_state.sentence

# ================= AUDIO =================
st.subheader("👂 Listen")
audio = speak(target, st.session_state.voice)
st.audio(audio)

# ================= INPUT =================
user_input = st.text_input(
    "⌨️ Type what you hear:",
    key=f"input_{st.session_state.input_id}"
)

# ================= SUBMIT =================
if st.button("🚀 Submit"):
    typed = user_input.upper().strip()
    correct = target.upper()

    if typed == correct:
        st.success(random.choice(SUCCESS_LINES))
        st.session_state.xp += 10
        st.session_state.streak += 1
        st.session_state.inventory.append(random.choice(ITEMS))

        if st.session_state.streak % 5 == 0:
            st.session_state.hearts = min(3, st.session_state.hearts + 1)

        if st.session_state.xp % 50 == 0:
            st.session_state.house.append("🏠")

        if st.session_state.xp % 100 == 0:
            st.session_state.badges.append("💎 Diamond Speller")

        if st.session_state.xp % 50 == 0:
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
        st.error(random.choice(FAIL_LINES))
        st.session_state.hearts -= 1
        st.session_state.streak = 0
        st.session_state.input_id += 1
        st.rerun()

# ================= INVENTORY =================
st.divider()
st.subheader("🎒 Inventory")
st.write(" ".join(st.session_state.inventory[-20:]))

st.subheader("🏠 Your House")
st.write(" ".join(st.session_state.house) if st.session_state.house else "Empty plot")

st.subheader("🏆 Badges")
st.write(" ".join(set(st.session_state.badges)) if st.session_state.badges else "No badges yet")

# ================= PARENT DASHBOARD =================
st.divider()
st.subheader("📊 Parent Dashboard")

progress = load_progress()
rows = []
for d, v in progress.items():
    if st.session_state.skill in v:
        rows.append({"Date": d, "XP": v[st.session_state.skill]["xp"]})

if rows:
    df = pd.DataFrame(rows)
    st.line_chart(df.set_index("Date"))
