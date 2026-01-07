import streamlit as st
import random
import time
import json
from datetime import date, timedelta
import tempfile
import os
import pandas as pd
from openai import OpenAI
from gtts import gTTS


# ---------------- CONFIG ----------------
st.set_page_config(page_title="📝 Daily Writing Fun", layout="wide")

DATA_FILE = "progress.json"
WORDS_FILE = "words.json"
SENTENCES_FILE = "sentence_templates_full.json"
DAILY_TIME_LIMIT = 10 * 60  # 10 minutes

# ---------------- OPENAI CLIENT ----------------
api_key = None
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("❌ OPENAI_API_KEY not set")
    st.stop()

client = OpenAI(api_key=api_key)

# ---------------- LOAD WORDS & SENTENCES ----------------
def load_json(file):
    if not os.path.exists(file):
        st.error(f"❌ {file} not found.")
        st.stop()
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

WORD_SKILLS = load_json(WORDS_FILE)
SENTENCE_TEMPLATES = load_json(SENTENCES_FILE)
SKILLS = list(WORD_SKILLS.keys())
MAX_SKILL = max(int(s) for s in SKILLS)

# ---------------- HELPERS ----------------
def speak_openai(text, voice="alloy"):
    if not text:
        return None
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        fp.write(response.read())
        return fp.name

def speak_gtts(text, lang="en"):
    if not text:
        return None

    tts = gTTS(text=text, lang=lang)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
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

def calculate_streak(progress, skill=None):
    streak = 0
    today = date.today()
    for i in range(30):
        d = str(today - timedelta(days=i))
        if d in progress:
            if skill:
                if skill in progress[d] and progress[d][skill]["correct"] > 0:
                    streak += 1
                else:
                    break
            else:
                streak += 1
        else:
            break
    return streak

def pick_word(skill):
    level_words = WORD_SKILLS[skill]["words"]
    remaining = [w for w in st.session_state.correct_words if w not in st.session_state.correct_words]
    if not remaining:
        st.session_state.correct_words = []
        remaining = level_words
    return random.choice(level_words)

def pick_sentence(skill):
    templates = SENTENCE_TEMPLATES[skill]["templates"]
    return random.choice(templates)

# ---------------- SESSION STATE ----------------
defaults = {
    "start_time": time.time(),
    "skill": "1",
    "correct": 0,
    "wrong": 0,
    "incorrect_attempts": 0,
    "input_id": 0,
    "correct_words": [],
    "mode": "word",
    "word": "",
    "sentence": "",
    "voice": "alloy",

    # 🔊 TTS defaults
    "tts_engine": "OpenAI",
    "gtts_lang": "en"
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------- SELECT VOICE ----------------
voice_options = {
    "American": "alloy",
    "British": "nova",
    "South African": "verse"
}
gtts_lang = st.sidebar.selectbox(
    "gTTS Language",
    ["en", "en-uk", "en-us", "af"],
    disabled=(tts_engine != "gTTS")
)

# ---------------- SELECT TTS ENGINE ----------------
# ---------------- SELECT TTS ENGINE ----------------
st.sidebar.subheader("🔊 Text-to-Speech Engine")

# ensure defaults exist
if "tts_engine" not in st.session_state:
    st.session_state.tts_engine = "OpenAI"
if "gtts_lang" not in st.session_state:
    st.session_state.gtts_lang = "en"

st.sidebar.radio(
    "Choose TTS:",
    ["OpenAI", "gTTS"],
    key="tts_engine"
)

st.sidebar.selectbox(
    "gTTS Language",
    ["en", "af"],
    key="gtts_lang",
    disabled=(st.session_state.tts_engine != "gTTS")
)

# ---------------- ENSURE ACTIVE CONTENT ----------------
if st.session_state.mode == "word" and not st.session_state.word:
    st.session_state.word = pick_word(st.session_state.skill)
if st.session_state.mode == "sentence" and not st.session_state.sentence:
    st.session_state.sentence = pick_sentence(st.session_state.skill)

# ---------------- TIMER ----------------
elapsed = int(time.time() - st.session_state.start_time)
remaining = max(0, DAILY_TIME_LIMIT - elapsed)

# ---------------- HEADER ----------------
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
cols[2].metric("🎯 Skill", WORD_SKILLS[st.session_state.skill]["label"])
cols[3].metric("📝 Mode", st.session_state.mode.capitalize())

# ---------------- TIME UP ----------------
if remaining == 0:
    progress = load_progress()
    if today_key() not in progress:
        progress[today_key()] = {}
    progress[today_key()][st.session_state.skill] = {
        "correct": st.session_state.correct,
        "wrong": st.session_state.wrong,
        "mode": st.session_state.mode
    }
    save_progress(progress)
    st.success("🎉 Time's up! Great job!")
    st.stop()

# ---------------- TARGET TEXT ----------------
target_text = st.session_state.word if st.session_state.mode == "word" else st.session_state.sentence

# ---------------- AUDIO ----------------
st.subheader("👂 Listen Carefully!")

audio_file = None

if tts_engine == "OpenAI":
    audio_file = speak_openai(target_text, st.session_state.voice)

elif tts_engine == "gTTS":
    audio_file = speak_gtts(target_text, lang=gtts_lang)

if audio_file:
    st.audio(audio_file)

# ---------------- SHOW AFTER 3 FAILS ----------------
if st.session_state.incorrect_attempts >= 3:
    st.markdown(
        f"<div style='text-align:center; background-color:#FFA07A; padding:15px; border-radius:10px;'>"
        f"<h2 style='color:#800080;'>{target_text}</h2></div>", unsafe_allow_html=True
    )

# ---------------- INPUT ----------------
user_input = st.text_input("Type what you hear:", key=f"input_{st.session_state.input_id}")

# ---------------- SUBMIT ----------------
if st.button("Submit"):
    typed = user_input.upper().strip()  # CAPS aligned
    target = target_text.upper()

    if typed == target:
        st.success("⭐ Correct! 🎉")
        st.session_state.correct += 1
        st.session_state.incorrect_attempts = 0

        if st.session_state.mode == "word":
            st.session_state.correct_words.append(st.session_state.word)
            st.session_state.word = ""

            # Adaptive progression
            if st.session_state.correct % 5 == 0:
                next_skill = str(int(st.session_state.skill) + 1)
                if next_skill in WORD_SKILLS:
                    st.session_state.skill = next_skill
                    st.session_state.correct_words = []
                    st.balloons()
                elif int(st.session_state.skill) >= 4:
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
st.subheader("📊 Parent/Teacher Dashboard")

progress = load_progress()
st.metric("🔥 Streak", f"{calculate_streak(progress, st.session_state.skill)} days")

rows = []
for i in range(7):
    d = str(date.today() - timedelta(days=i))
    if d in progress and st.session_state.skill in progress[d]:
        p = progress[d][st.session_state.skill]
        total = p["correct"] + p["wrong"]
        rows.append({
            "Date": d,
            "Accuracy (%)": int((p["correct"] / total) * 100) if total else 0
        })

if rows:
    df = pd.DataFrame(rows)
    st.line_chart(df.set_index("Date")["Accuracy (%)"])


