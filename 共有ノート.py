import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta, timezone
import calendar

# =====================================================
# 基本設定
# =====================================================

st.set_page_config(
    page_title="ふたりの共有ノート",
    page_icon="🤝",
    layout="wide"
)

# =====================================================
# セッション状態
# =====================================================

defaults = {
    "font_size": 14,
    "edit_id": None,
    "user_color": "#ff4b6e",
    "input_title": "",
    "input_url": "",
    "input_memo": "",
    "input_time": "12:00",
    "ng_reason": "",
    "clear_wish_inputs": False,
    "clear_ng_inputs": False,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# 入力リセット
# =====================================================

if st.session_state.clear_wish_inputs:
    st.session_state.input_title = ""
    st.session_state.input_url = ""
    st.session_state.input_memo = ""
    st.session_state.input_time = "12:00"
    st.session_state.clear_wish_inputs = False

if st.session_state.clear_ng_inputs:
    st.session_state.ng_reason = ""
    st.session_state.clear_ng_inputs = False

# =====================================================
# 時刻
# =====================================================

def get_jst_now():
    return datetime.now(timezone(timedelta(hours=9)))

# =====================================================
# Firebase
# =====================================================

if not firebase_admin._apps:

    cred_dict = dict(st.secrets["firebase"])

    if "private_key" in cred_dict:
        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")

    cred = credentials.Certificate(cred_dict)

    firebase_admin.initialize_app(cred)

db = firestore.client()

APP_ID = "couple-secure-v2"

def get_events_ref():
    return (
        db.collection("artifacts")
        .document(APP_ID)
        .collection("public")
        .document("data")
        .collection("secure_events")
    )

def get_ng_ref():
    return (
        db.collection("artifacts")
        .document(APP_ID)
        .collection("public")
        .document("data")
        .collection("secure_ng_dates")
    )

def get_rooms_ref():
    return (
        db.collection("artifacts")
        .document(APP_ID)
        .collection("public")
        .document("data")
        .collection("secure_rooms")
    )

# =====================================================
# ログイン保持
# =====================================================

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

# =====================================================
# CSS
# =====================================================

st.markdown(
    f"""
<style>

html, body, [class*="st-"] {{
    font-size:{st.session_state.font_size}px !important;
}}

.calendar-grid {{
    display:grid;
    grid-template-columns:repeat(7, 1fr);
    gap:6px;
}}

.calendar-head {{
    text-align:center;
    font-weight:bold;
    padding:10px;
    background:#202020;
    border-radius:10px;
}}

.calendar-cell {{
    min-height:120px;
    border:1px solid #333;
    border-radius:12px;
    padding:8px;
    background:#111;
}}

.today-cell {{
    border:2px solid #ff4b6e;
    background:#2b1015;
}}

.day-number {{
    font-size:18px;
    font-weight:bold;
    margin-bottom:8px;
}}

.event-dot {{
    font-size:12px;
    background:#222;
    border-radius:8px;
    padding:3px 6px;
    margin-bottom:4px;
    overflow:hidden;
}}

.last-message {{
    background:#1f1f1f;
    border-radius:10px;
    padding:8px;
    margin-top:8px;
}}

.comment-box {{
    padding:8px;
    border-radius:10px;
    margin-bottom:8px;
    background:#1a1a1a;
}}

@media (max-width:768px) {{

    .calendar-cell {{
        min-height:90px;
        padding:4px;
    }}

    .event-dot {{
        font-size:9px;
    }}

    .day-number {{
        font-size:14px;
    }}
}}

</style>
""",
    unsafe_allow_html=True
)

# =====================================================
# サイドバー
# =====================================================

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

# =====================================================
# ログイン画面
# =====================================================

if not st.session_state.get("is_logged"):

    st.title("🤝 Shared Note Sync")

    name_input = st.text_input("表示名")

    col1, col2 = st.columns(2)

    with col1:

        if st.button("新しいノート"):

            if name_input:

                new_key = "-".join([
                    "".join(
                        random.choices(
                            "ABCDEFGHJKLMNPQRSTUVWXYZ23456789",
                            k=4
                        )
                    )
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

# =====================================================
# データ取得
# =====================================================

room_key = st.session_state.room_key
user_name = st.session_state.user_name

events = [
    {"id": d.id, **d.to_dict()}
    for d in get_events_ref()
    .where("roomKey", "==", room_key)
    .stream()
]

ng_dates = [
    {"id": d.id, **d.to_dict()}
    for d in get_ng_ref()
    .where("roomKey", "==", room_key)
    .stream()
]

# =====================================================
# タブ
# =====================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📍 行きたい",
    "📅 予定",
    "🚫 NG日",
    "🗓️ カレンダー"
])

# =====================================================
# 行きたい
# =====================================================

with tab1:

    with st.expander("＋追加"):

        t = st.text_input("場所", key="input_title")

        u = st.text_input("URL", key="input_url")

        tm = st.time_input("時間")

        m = st.text_area("メモ", key="input_memo")

        if st.button("追加", type="primary"):

            if t:

                get_events_ref().add({
                    "roomKey": room_key,
                    "title": t,
                    "url": u,
                    "memo": m,
                    "time": tm.strftime("%H:%M"),
                    "status": "wishlist",
                    "userName": user_name,
                    "createdAt": get_jst_now().isoformat(),
                    "comments": []
                })

                st.session_state.clear_wish_inputs = True

                st.rerun()

    wishlist = [
        e for e in events
        if e.get("status") == "wishlist"
    ]

    wishlist = sorted(
        wishlist,
        key=lambda x: x.get("createdAt", ""),
        reverse=True
    )

    for item in wishlist:

        with st.container(border=True):

            st.markdown(f"## 📍 {item['title']}")

            if item.get("time"):
                st.write(f"🕒 {item['time']}")

            if item.get("url"):
                st.markdown(f"[🔗 リンク]({item['url']})")

            if item.get("memo"):
                st.info(item["memo"])

            comments = item.get("comments", [])

            if comments:

                last_comment = comments[-1]

                color = last_comment.get("color", "#666")

                st.markdown(
                    f"""
<div class='last-message'
style='border-left:5px solid {color};'>
<b>{last_comment['userName']}</b><br>
{last_comment['text']}
</div>
""",
                    unsafe_allow_html=True
                )

            with st.expander("💬 コメント"):

                for c in comments:

                    color = c.get("color", "#666")

                    st.markdown(
                        f"""
<div class='comment-box'
style='border-left:5px solid {color};'>
<b>{c['userName']}</b><br>
{c['text']}
</div>
""",
                        unsafe_allow_html=True
                    )

                with st.form(
                    key=f"comment_form_{item['id']}",
                    clear_on_submit=True
                ):

                    new_comment = st.text_input("コメント")

                    submitted = st.form_submit_button("送信")

                    if submitted and new_comment:

                        get_events_ref().document(item["id"]).update({
                            "comments": firestore.ArrayUnion([
                                {
                                    "userName": user_name,
                                    "text": new_comment,
                                    "createdAt": get_jst_now().isoformat(),
                                    "color": st.session_state.user_color
                                }
                            ])
                        })

                        st.rerun()

            st.divider()

            fix_date = st.date_input(
                "予定日",
                key=f"fix_date_{item['id']}"
            )

            if st.button(
                "📅 予定に追加",
                key=f"fix_btn_{item['id']}"
            ):

                get_events_ref().document(item["id"]).update({
                    "status": "scheduled",
                    "date": str(fix_date)
                })

                st.rerun()

# =====================================================
# 予定
# =====================================================

with tab2:

    scheduled = [
        e for e in events
        if e.get("status") == "scheduled"
    ]

    scheduled = sorted(
        scheduled,
        key=lambda x: x.get("date", "")
    )

    for item in scheduled:

        with st.container(border=True):

            st.markdown(
                f"## 📅 {item.get('date', '')} {item['title']}"
            )

            if item.get("time"):
                st.write(f"🕒 {item['time']}")

            if item.get("memo"):
                st.info(item["memo"])

# =====================================================
# NG日
# =====================================================

with tab3:

    st.subheader("🚫 NG日")

    nd = st.date_input("行けない日")

    nr = st.text_input("理由", key="ng_reason")

    if st.button("NG登録"):

        get_ng_ref().add({
            "roomKey": room_key,
            "userName": user_name,
            "date": str(nd),
            "reason": nr
        })

        st.session_state.clear_ng_inputs = True

        st.rerun()

    st.divider()

    for n in ng_dates:

        with st.container(border=True):

            st.write(
                f"🚫 {n['date']}  {n.get('reason', '')}"
            )

# =====================================================
# カレンダー
# =====================================================

with tab4:

    now = get_jst_now()

    year = now.year
    month = now.month
    today = now.day

    st.subheader(f"🗓️ {year}年 {month}月")

    cal = calendar.monthcalendar(year, month)

    week_names = ["月", "火", "水", "木", "金", "土", "日"]

    st.markdown(
        "<div class='calendar-grid'>",
        unsafe_allow_html=True
    )

    for w in week_names:

        st.markdown(
            f"<div class='calendar-head'>{w}</div>",
            unsafe_allow_html=True
        )

    for week in cal:

        for day in week:

            if day == 0:

                st.markdown(
                    "<div class='calendar-cell'></div>",
                    unsafe_allow_html=True
                )

            else:

                target = f"{year}-{month:02d}-{day:02d}"

                day_events = [
                    e for e in events
                    if e.get("date") == target
                ]

                day_ng = [
                    n for n in ng_dates
                    if n.get("date") == target
                ]

                extra_class = (
                    "today-cell"
                    if day == today
                    else ""
                )

                html = f"""
<div class='calendar-cell {extra_class}'>
<div class='day-number'>{day}</div>
"""

                for e in day_events[:3]:

                    html += f"""
<div class='event-dot'>
📍 {e['title'][:10]}
</div>
"""

                for n in day_ng[:2]:

                    html += f"""
<div class='event-dot'>
🚫 NG
</div>
"""

                html += "</div>"

                st.markdown(
                    html,
                    unsafe_allow_html=True
                )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )
