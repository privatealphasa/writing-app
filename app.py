import streamlit as st
import random
import time
import json
from datetime import date, timedelta
import tempfile
import os
import pandas as pd
from openai import OpenAI

# ---------------- CONFIG ----------------
st.set_page_config(page_title="📝 Daily Writing Fun", layout="wide")

DATA_FILE = "progress.json"
WORDS_FILE = "words.json"
DAILY_TIME_LIMIT = 10 * 60  # 10 minutes

# ---------------- OPENAI CLIENT ----------------
# Make sure to set your OPENAI_API_KEY in Streamlit Secrets or environment
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY"))

# ---------------- LOAD WORDS ----------------
def load_words():
    if not os.path.exists(WORDS_FILE):
        st.error("❌ words.json file not found.")
        st.stop()
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        return {int(k): v for k, v in json.load(f).items()}

WORD_LEVELS = load_words()
MAX_LEVEL = max(WORD_LEVELS.keys())

# ---------------- HELPERS ----------------
def speak_openai(text, voice="alloy"):
    """Convert text to speech using OpenAI TTS."""
    if not text:
        return None
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        fp.write(response.audio)
        return fp.name

def today_key():
    return str(date.today())

def load_progress():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_progress(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def calculate_streak(progress):
    streak = 0
    today = date.today()
    for i in range(30):
        if str(today - timedelta(days=i)) in progress:
            streak += 1
        else:
            break
    return streak

def generate_sentence():
    subjects = ["The child", "A boy", "A girl", "The teacher"]
    verbs = ["likes", "sees", "uses", "learns"]

    words = []
    for lvl in range(1, min(5, MAX_LEVEL + 1)):
        words.extend(WORD_LEVELS.get(lvl, []))

    return f"{random.choice(subjects)} {random.choice(verbs)} {random.choice(words)}."

def pick_word():
    level_words = WORD_LEVELS[st.session_state.level]
    remaining = [w for w in level_words if w not in st.session_state.correct_words]
    if not remaining:
        st.session_state.correct_words = []
        remaining = level_words
    return random.choice(remaining)

# ---------------- SESSION STATE ----------------
defaults = {
    "start_time": time.time(),
    "level": 1,
    "correct": 0,
    "wrong": 0,
    "incorrect_attempts": 0,
    "input_id": 0,
    "correct_words": [],
    "mode": "word",
    "word": "",
    "sentence": "",
    "voice": "alloy"
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------- SELECT VOICE ----------------
voice_options = {
    "American": "alloy",
    "British": "aria",
    "South African": "verse"
}
st.sidebar.subheader("🎤 Select Voice/Accent")
selected_voice = st.sidebar.selectbox("Choose a voice:", list(voice_options.keys()))
st.session_state.voice = voice_options[selected_voice]

# ---------------- ENSURE ACTIVE CONTENT ----------------
if st.session_state.mode == "word" and not st.session_state.word:
    st.session_state.word = pick_word()

if st.session_state.mode == "sentence" and not st.session_state.sentence:
    st.session_state.sentence = generate_sentence()

# ---------------- TIMER ----------------
elapsed = int(time.time() - st.session_state.start_time)
remaining = max(0, DAILY_TIME_LIMIT - elapsed)

# ---------------- PLAYFUL HEADER ----------------
st.markdown(
    """
    <div style='text-align:center; background-color:#FFD700; padding:10px; border-radius:15px'>
        <h1 style='color:#FF4500;'>🎉 Daily Writing Fun! 📝</h1>
        <p style='font-size:20px; color:#008080;'>Listen, Type, and Earn Stars!</p>
    </div>
    """, unsafe_allow_html=True
)

st.progress(remaining / DAILY_TIME_LIMIT)
st.markdown(f"<h3 style='color:#4B0082;'>⏱️ Time left: {remaining // 60}:{remaining % 60:02d}</h3>", unsafe_allow_html=True)

# ---------------- STATS ----------------
st.subheader("📊 Your Stats")
cols = st.columns(4)
cols[0].metric("⭐ Correct", st.session_state.correct)
cols[1].metric("❌ Wrong", st.session_state.wrong)
cols[2].metric("🎯 Level", st.session_state.level)
cols[3].metric("📝 Mode", st.session_state.mode.capitalize())

# ---------------- TIME UP ----------------
if remaining == 0:
    progress = load_progress()
    progress[today_key()] = {
        "correct": st.session_state.correct,
        "wrong": st.session_state.wrong,
        "level": st.session_state.level
    }
    save_progress(progress)
    st.success("🎉 Time's up! Great job!")
    st.stop()

# ---------------- TARGET TEXT ----------------
target_text = (
    st.session_state.word
    if st.session_state.mode == "word"
    else st.session_state.sentence
)

# ---------------- AUDIO ----------------
st.subheader("👂 Listen Carefully!")
audio_file = speak_openai(target_text, st.session_state.voice)
if audio_file:
    st.audio(audio_file)

# ---------------- SHOW AFTER 3 FAILS ----------------
if st.session_state.incorrect_attempts >= 3:
    st.markdown(
        f"<div style='text-align:center; background-color:#FFA07A; padding:15px; border-radius:10px;'>"
        f"<h2 style='color:#800080;'>{target_text}</h2></div>", unsafe_allow_html=True
    )

# ---------------- INPUT ----------------
user_input = st.text_input(
    "Type what you hear:",
    key=f"input_{st.session_state.input_id}"
)

# ---------------- SUBMIT ----------------
if st.button("Submit"):
    typed = user_input.lower().strip()
    target = target_text.lower()

    if typed == target:
        st.success("⭐ Correct! 🎉")
        st.session_state.correct += 1
        st.session_state.incorrect_attempts = 0

        if st.session_state.mode == "word":
            st.session_state.correct_words.append(st.session_state.word)
            st.session_state.word = ""

            # Adaptive progression
            if st.session_state.correct % 5 == 0:
                if st.session_state.level < MAX_LEVEL:
                    st.session_state.level += 1
                    st.session_state.correct_words = []
                    st.balloons()
                elif st.session_state.level >= 4:
                    st.session_state.mode = "sentence"
                    st.success("🎊 Sentence Mode Unlocked! Try typing sentences!")

        else:
            st.session_state.sentence = ""

        st.session_state.input_id += 1
        st.rerun()

    else:
        st.session_state.wrong += 1
        st.session_state.incorrect_attempts += 1
        if st.session_state.incorrect_attempts < 3:
            st.error("❌ Try again! Keep going!")
        else:
            st.error(f"✅ Correct answer: {target_text}")
        st.rerun()

# ---------------- REWARDS ----------------
st.divider()
st.subheader("🏆 Achievements")
if st.session_state.correct >= 5:
    st.success("🥉 Bronze Star!")
if st.session_state.correct >= 10:
    st.success("🥈 Silver Star!")
if st.session_state.correct >= 20:
    st.success("🥇 Gold Star!")

# ---------------- PARENT DASHBOARD ----------------
st.divider()
st.subheader("📊 Parent Dashboard")

progress = load_progress()
st.metric("🔥 Streak", f"{calculate_streak(progress)} days")

rows = []
for i in range(7):
    d = str(date.today() - timedelta(days=i))
    if d in progress:
        p = progress[d]
        total = p["correct"] + p["wrong"]
        rows.append({
            "Date": d,
            "Accuracy (%)": int((p["correct"] / total) * 100) if total else 0
        })

if rows:
    df = pd.DataFrame(rows)
    st.line_chart(df.set_index("Date")["Accuracy (%)"])
