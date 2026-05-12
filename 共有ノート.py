import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta, timezone
import calendar

# ==========================================
# 基本設定
# ==========================================

st.set_page_config(
    page_title="ふたりの共有ノート",
    page_icon="🤝",
    layout="wide"
)

# ==========================================
# セッション状態
# ==========================================

if "font_size" not in st.session_state:
    st.session_state.font_size = 14

if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

if "user_color" not in st.session_state:
    st.session_state.user_color = "#ff4b6e"

if "input_title" not in st.session_state:
    st.session_state.input_title = ""

if "input_url" not in st.session_state:
    st.session_state.input_url = ""

if "input_memo" not in st.session_state:
    st.session_state.input_memo = ""

if "ng_reason" not in st.session_state:
    st.session_state.ng_reason = ""

if "clear_wish_inputs" not in st.session_state:
    st.session_state.clear_wish_inputs = False

if "clear_ng_inputs" not in st.session_state:
    st.session_state.clear_ng_inputs = False

# 入力リセット

if st.session_state.clear_wish_inputs:
    st.session_state.input_title = ""
    st.session_state.input_url = ""
    st.session_state.input_memo = ""
    st.session_state.clear_wish_inputs = False

if st.session_state.clear_ng_inputs:
    st.session_state.ng_reason = ""
    st.session_state.clear_ng_inputs = False

# ==========================================
# 時刻関連
# ==========================================

def get_jst_now():
    return datetime.now(timezone(timedelta(hours=9)))

def get_weekday_jp(dt):
    w = ['月', '火', '水', '木', '金', '土', '日']
    return w[dt.weekday()]

# ==========================================
# Firebase
# ==========================================

if not firebase_admin._apps:
    cred_dict = dict(st.secrets["firebase"])

    if "private_key" in cred_dict:
        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")

    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()
APP_ID = "couple-secure-v2"

def get_events_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_events')

def get_ng_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_ng_dates')

def get_rooms_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_rooms')

# ==========================================
# ログイン保持
# ==========================================

if "is_logged" not in st.session_state:
    q_room = st.query_params.get("room")
    q_user = st.query_params.get("user")

    if q_room and q_user:
        st.session_state.room_key = q_room
        st.session_state.user_name = q_user
        st.session_state.is_logged = True
    else:
        st.session_state.is_logged = False

def login_action(room, user):
    st.session_state.room_key = room
    st.session_state.user_name = user
    st.session_state.is_logged = True

    st.query_params["room"] = room
    st.query_params["user"] = user

def logout():
    st.session_state.is_logged = False
    st.query_params.clear()
    st.rerun()

# ==========================================
# CSS
# ==========================================

st.markdown(f"""
<style>
html, body, [class*="st-"] {{
    font-size: {st.session_state.font_size}px !important;
}}

.calendar-grid {{
    display:grid;
    grid-template-columns:repeat(7,1fr);
    gap:4px;
}}

.calendar-cell {{
    min-height:90px;
    border:1px solid #333;
    border-radius:10px;
    padding:6px;
    background:#111;
    overflow:hidden;
}}

.calendar-head {{
    text-align:center;
    font-weight:bold;
    padding:6px;
}}

.today-cell {{
    background:#3b0d17;
    border:2px solid #ff4b6e;
}}

.day-number {{
    font-weight:bold;
    margin-bottom:4px;
}}

.event-dot {{
    font-size:11px;
    background:#222;
    border-radius:6px;
    padding:2px 4px;
    margin-bottom:3px;
}}

.last-message {{
    background:#1f1f1f;
    border-radius:8px;
    padding:6px;
    margin-top:6px;
}}

@media (max-width: 768px) {{
    .calendar-cell {{
        min-height:65px;
        padding:3px;
        font-size:10px;
    }}

    .event-dot {{
        font-size:9px;
        padding:1px 2px;
    }}
}}
</style>
""", unsafe_allow_html=True)

# ==========================================
# サイドバー
# ==========================================

if st.session_state.get("is_logged"):
    st.sidebar.title("⚙️ 設定")

    new_size = st.sidebar.slider(
        "文字サイズ",
        10,
        30,
        st.session_state.font_size
    )

    new_color = st.sidebar.color_picker(
        "自分の色",
        st.session_state.user_color
    )

    if new_size != st.session_state.font_size:
        st.session_state.font_size = new_size
        st.rerun()

    if new_color != st.session_state.user_color:
        st.session_state.user_color = new_color
        st.rerun()

    st.sidebar.divider()

    st.sidebar.write(f"👤 {st.session_state.user_name}")
    st.sidebar.write(f"🔑 {st.session_state.room_key}")

    if st.sidebar.button("ログアウト"):
        logout()

# ==========================================
# ログイン画面
# ==========================================

if not st.session_state.get("is_logged"):

    st.title("🤝 Shared Note Sync")

    name_input = st.text_input("表示名")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("新しいノート"):
            if name_input:
                new_key = '-'.join([
                    ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4))
                    for _ in range(7)
                ])

                get_rooms_ref().document(new_key).set({
                    "createdAt": get_jst_now().isoformat()
                })

                login_action(new_key, name_input)
                st.rerun()

    with col2:
        room_key_input = st.text_input("秘密鍵")

        if st.button("参加"):
            if room_key_input and name_input:
                login_action(room_key_input, name_input)
                st.rerun()

    st.stop()
