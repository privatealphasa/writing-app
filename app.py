import streamlit as st
import random, time, json, os, tempfile
from datetime import date, timedelta
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
input { font-size: 26px !important; text-align:center; }

.pixel {
    background:#5DBB63;
    border:4px solid #2E7D32;
    padding:16px;
    border-radius:12px;
    margin-bottom:12px;
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

ITEMS = ["🧱", "🪵", "🪨", "💎"]
AVATARS = ["🧱 Builder", "🧙 Wizard", "🐉 Dragon Trainer"]

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

def load_progress():
    return json.load(open(DATA_FILE)) if os.path.exists(DATA_FILE) else {}

def save_progress(p):
    json.dump(p, open(DATA_FILE, "w"), indent=2)

# ================= SESSION STATE =================
defaults = {
    "screen": "play",
    "skill": "1",
    "mode": "word",
    "word": "",
    "sentence": "",
    "xp": 0,
    "hearts": 3,
    "streak": 0,
    "inventory": [],
    "house": [],
    "badges": [],
    "avatar": AVATARS[0],
    "incorrect_attempts": 0,
    "show_answer": False,
    "reduced_xp": False,
    "input_id": 0,
    "start_time": time.time(),
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ================= SIDEBAR =================
st.sidebar.subheader("🧍 Avatar")
st.session_state.avatar = st.sidebar.selectbox("Choose", AVATARS)

if st.sidebar.button("🗺️ Map"):
    st.session_state.screen = "map"
if st.sidebar.button("🎯 Play"):
    st.session_state.screen = "play"

# ================= MAP =================
if st.session_state.screen == "map":
    st.header("🗺️ World Map")
    for k, v in WORLDS.items():
        unlocked = st.session_state.skill >= k if k.isdigit() else st.session_state.mode == "sentence"
        st.write(("🟢" if unlocked else "🔒") + " " + v)
    st.stop()

# ================= TIMER =================
remaining = max(0, DAILY_TIME_LIMIT - int(time.time() - st.session_state.start_time))
st.progress(remaining / DAILY_TIME_LIMIT)

# ================= HEADER =================
st.markdown(f"""
<div class="pixel" style="text-align:center">
<h1>🎮 Daily Writing Quest</h1>
<h3>{WORLDS.get(st.session_state.skill)}</h3>
</div>
""", unsafe_allow_html=True)

# ================= STATS =================
cols = st.columns(5)
cols[0].metric("⚡ XP", st.session_state.xp)
cols[1].metric("❤️ Hearts", st.session_state.hearts)
cols[2].metric("🌍 World", st.session_state.skill)
cols[3].metric("🧍 Avatar", st.session_state.avatar)
cols[4].metric("🔥 Streak", st.session_state.streak)

# ================= CONTENT =================
if st.session_state.mode == "word" and not st.session_state.word:
    st.session_state.word = pick_word(
        st.session_state.skill,
        easier=st.session_state.incorrect_attempts >= 2
    )
if st.session_state.mode == "sentence" and not st.session_state.sentence:
    st.session_state.sentence = pick_sentence(st.session_state.skill)

target = st.session_state.word if st.session_state.mode == "word" else st.session_state.sentence

# ================= AUDIO =================
st.audio(speak(target))

# ================= SHOW ANSWER (FIXED) =================
if st.session_state.show_answer:
    st.markdown(
        f"<div class='pixel'><h2>✅ Correct spelling:</h2><h1>{target}</h1></div>",
        unsafe_allow_html=True
    )

# ================= INPUT =================
typed = st.text_input("⌨️ Type what you hear", key=f"in_{st.session_state.input_id}")

# ================= SUBMIT =================
if st.button("🚀 Submit"):
    if typed.upper().strip() == target.upper():
        xp_gain = 5 if st.session_state.reduced_xp else 10
        st.session_state.xp += xp_gain
        st.session_state.inventory.append(random.choice(ITEMS))
        st.session_state.streak += 1

        st.session_state.show_answer = False
        st.session_state.reduced_xp = False
        st.session_state.incorrect_attempts = 0
        st.session_state.word = ""
        st.session_state.sentence = ""

        if st.session_state.xp % 50 == 0:
            st.session_state.house.append("🏠")
        if st.session_state.xp % 100 == 0:
            st.session_state.badges.append("💎 Diamond Speller")

        st.balloons()
        st.session_state.input_id += 1
        st.rerun()

    else:
        st.session_state.incorrect_attempts += 1
        st.session_state.streak = 0
        st.error("❌ Try again!")

        if st.session_state.incorrect_attempts >= 3:
            st.session_state.show_answer = True
            st.session_state.reduced_xp = True
            st.session_state.incorrect_attempts = 0
            st.session_state.hearts -= 1

        st.session_state.input_id += 1
        st.rerun()

# ================= INVENTORY =================
st.divider()
st.subheader("🎒 Inventory")
st.write(" ".join(st.session_state.inventory[-20:]))

st.subheader("🏠 House")
st.write(" ".join(st.session_state.house) if st.session_state.house else "Empty plot")

st.subheader("🏆 Badges")
st.write(" ".join(set(st.session_state.badges)) if st.session_state.badges else "None yet")

# ================= PARENT DASHBOARD =================
st.divider()
st.subheader("📊 Parent Dashboard")

progress = load_progress()
today = str(date.today())
progress.setdefault(today, {})
progress[today].setdefault(st.session_state.skill, {"correct": 0, "wrong": 0})

accuracy = 0
total = progress[today][st.session_state.skill]["correct"] + progress[today][st.session_state.skill]["wrong"]
if total:
    accuracy = int(progress[today][st.session_state.skill]["correct"] / total * 100)

st.metric("✏️ Accuracy", f"{accuracy}%")
