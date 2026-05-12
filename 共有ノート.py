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
    "is_logged": False,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# 時刻
# =====================================================

def get_jst_now():
    return datetime.now(
        timezone(timedelta(hours=9))
    )

# =====================================================
# Firebase
# =====================================================

if not firebase_admin._apps:

    cred_dict = dict(st.secrets["firebase"])

    if "private_key" in cred_dict:
        cred_dict["private_key"] = (
            cred_dict["private_key"]
            .replace("\\n", "\n")
        )

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
# ログイン
# =====================================================

q_room = st.query_params.get("room")
q_user = st.query_params.get("user")

if q_room and q_user:
    st.session_state.room_key = q_room
    st.session_state.user_name = q_user
    st.session_state.is_logged = True

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

.last-message {{
    background:#1a1a1a;
    border-radius:10px;
    padding:10px;
    margin-top:10px;
}}

.comment-box {{
    background:#141414;
    border-radius:10px;
    padding:10px;
    margin-bottom:8px;
}}

.google-calendar {{
    display:grid;
    grid-template-columns:repeat(7,1fr);
    width:100%;
    border:1px solid #222;
    background:#111;
}}

.google-head {{
    background:#111;
    color:#999;
    text-align:center;
    padding:12px 0;
    font-weight:bold;
    border-bottom:1px solid #222;
}}

.google-cell {{
    min-height:140px;
    border-right:1px solid #222;
    border-bottom:1px solid #222;
    padding:6px;
    background:#000;
    overflow:hidden;
}}

.google-date {{
    font-size:18px;
    margin-bottom:6px;
}}

.today {{
    background:#151515;
    border:2px solid #ff4b6e;
}}

.sat {{
    color:#4d8dff;
}}

.sun {{
    color:#ff5b5b;
}}

.other {{
    opacity:0.3;
}}

.event {{
    background:#1f8f5f;
    color:white;
    border-radius:6px;
    padding:2px 6px;
    margin-bottom:4px;
    font-size:11px;
    overflow:hidden;
    white-space:nowrap;
    text-overflow:ellipsis;
}}

.ng {{
    background:#b03b3b;
}}

@media (max-width:768px) {{

    .google-cell {{
        min-height:85px;
        padding:4px;
    }}

    .google-date {{
        font-size:12px;
    }}

    .event {{
        font-size:8px;
        padding:1px 4px;
    }}
}}

</style>
""",
    unsafe_allow_html=True
)

# =====================================================
# ログイン画面
# =====================================================

if not st.session_state.is_logged:

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

                login_action(
                    new_key,
                    name_input
                )

    with col2:

        room_key_input = st.text_input("秘密鍵")

        if st.button("参加"):

            if room_key_input and name_input:

                login_action(
                    room_key_input,
                    name_input
                )

    st.stop()

# =====================================================
# サイドバー
# =====================================================

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

st.sidebar.write(
    f"👤 {st.session_state.user_name}"
)

st.sidebar.write(
    f"🔑 {st.session_state.room_key}"
)

if st.sidebar.button("ログアウト"):
    logout()

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

        t = st.text_input("場所")

        u = st.text_input("URL")

        time_mode = st.selectbox(
            "時間設定",
            [
                "終日",
                "午前",
                "午後",
                "カスタム"
            ]
        )

        if time_mode == "カスタム":

            c1, c2 = st.columns(2)

            with c1:
                start_time = st.time_input("開始")

            with c2:
                end_time = st.time_input("終了")

            time_text = (
                f"{start_time.strftime('%H:%M')}〜"
                f"{end_time.strftime('%H:%M')}"
            )

        else:

            time_text = time_mode

        memo = st.text_area("メモ")

        if st.button("追加"):

            if t:

                get_events_ref().add({
                    "roomKey": room_key,
                    "title": t,
                    "url": u,
                    "memo": memo,
                    "time": time_text,
                    "status": "wishlist",
                    "userName": user_name,
                    "createdAt": get_jst_now().isoformat(),
                    "comments": []
                })

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

            top1, top2 = st.columns([8,1])

            with top1:
                st.markdown(
                    f"## 📍 {item['title']}"
                )

            with top2:

                if st.button(
                    "✏️",
                    key=f"edit_{item['id']}"
                ):
                    st.session_state.edit_id = item["id"]
                    st.rerun()

            if st.session_state.edit_id == item["id"]:

                et = st.text_input(
                    "場所",
                    value=item.get("title",""),
                    key=f"et_{item['id']}"
                )

                eu = st.text_input(
                    "URL",
                    value=item.get("url",""),
                    key=f"eu_{item['id']}"
                )

                em = st.text_area(
                    "メモ",
                    value=item.get("memo",""),
                    key=f"em_{item['id']}"
                )

                save1, save2, save3 = st.columns(3)

                if save1.button(
                    "保存",
                    key=f"save_{item['id']}"
                ):

                    get_events_ref().document(
                        item["id"]
                    ).update({
                        "title": et,
                        "url": eu,
                        "memo": em
                    })

                    st.session_state.edit_id = None

                    st.rerun()

                if save2.button(
                    "キャンセル",
                    key=f"cancel_{item['id']}"
                ):

                    st.session_state.edit_id = None
                    st.rerun()

                if save3.button(
                    "削除",
                    key=f"delete_{item['id']}"
                ):

                    get_events_ref().document(
                        item["id"]
                    ).delete()

                    st.session_state.edit_id = None

                    st.rerun()

            else:

                st.write(
                    f"🕒 {item.get('time','')}"
                )

                if item.get("url"):
                    st.markdown(
                        f"[🔗 リンク]({item['url']})"
                    )

                if item.get("memo"):
                    st.info(item["memo"])

                comments = item.get(
                    "comments",
                    []
                )

                if comments:

                    last_comment = comments[-1]

                    color = last_comment.get(
                        "color",
                        "#666"
                    )

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

                        color = c.get(
                            "color",
                            "#666"
                        )

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
                        key=f"form_{item['id']}",
                        clear_on_submit=True
                    ):

                        new_comment = st.text_input(
                            "コメント"
                        )

                        submitted = (
                            st.form_submit_button("送信")
                        )

                        if submitted and new_comment:

                            get_events_ref().document(
                                item["id"]
                            ).update({
                                "comments":
                                firestore.ArrayUnion([
                                    {
                                        "userName":
                                        user_name,

                                        "text":
                                        new_comment,

                                        "createdAt":
                                        get_jst_now()
                                        .isoformat(),

                                        "color":
                                        st.session_state.user_color
                                    }
                                ])
                            })

                            st.rerun()

                fix_date = st.date_input(
                    "予定日",
                    key=f"fix_{item['id']}"
                )

                if st.button(
                    "📅 予定に追加",
                    key=f"fixbtn_{item['id']}"
                ):

                    get_events_ref().document(
                        item["id"]
                    ).update({
                        "status":"scheduled",
                        "date":str(fix_date)
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
        key=lambda x:x.get("date","")
    )

    for item in scheduled:

        with st.container(border=True):

            st.markdown(
                f"## 📅 {item.get('date','')} "
                f"{item['title']}"
            )

            st.write(
                f"🕒 {item.get('time','')}"
            )

# =====================================================
# NG日
# =====================================================

with tab3:

    st.subheader("🚫 NG日")

    nd = st.date_input("日付")

    nt_mode = st.selectbox(
        "時間",
        [
            "終日",
            "午前",
            "午後",
            "カスタム"
        ],
        key="ngmode"
    )

    if nt_mode == "カスタム":

        c1, c2 = st.columns(2)

        with c1:
            ns = st.time_input(
                "開始",
                key="ngstart"
            )

        with c2:
            ne = st.time_input(
                "終了",
                key="ngend"
            )

        ng_time = (
            f"{ns.strftime('%H:%M')}〜"
            f"{ne.strftime('%H:%M')}"
        )

    else:

        ng_time = nt_mode

    nr = st.text_input("理由")

    if st.button("NG登録"):

        get_ng_ref().add({
            "roomKey": room_key,
            "userName": user_name,
            "date": str(nd),
            "time": ng_time,
            "reason": nr
        })

        st.rerun()

    st.divider()

    for n in ng_dates:

        with st.container(border=True):

            st.write(
                f"🚫 {n['date']} "
                f"{n.get('time','')} "
                f"{n.get('reason','')}"
            )

# =====================================================
# カレンダー
# =====================================================

with tab4:

    now = get_jst_now()

    year = now.year
    month = now.month
    today = now.day

    st.subheader(
        f"🗓️ {year}年 {month}月"
    )

    cal = calendar.Calendar(
        firstweekday=0
    )

    month_days = cal.monthdatescalendar(
        year,
        month
    )

    week_names = [
        "月",
        "火",
        "水",
        "木",
        "金",
        "土",
        "日"
    ]

    calendar_html = """
<div class="google-calendar">
"""

    for w in week_names:

        calendar_html += f"""
<div class="google-head">
{w}
</div>
"""

    for week in month_days:

        for day in week:

            target = day.strftime("%Y-%m-%d")

            day_events = [
                e for e in events
                if e.get("date") == target
            ]

            day_ng = [
                n for n in ng_dates
                if n.get("date") == target
            ]

            classes = "google-cell"

            if day.month != month:
                classes += " other"

            if (
                day.day == today and
                day.month == month
            ):
                classes += " today"

            weekday = day.weekday()

            date_class = "google-date"

            if weekday == 5:
                date_class += " sat"

            elif weekday == 6:
                date_class += " sun"

            calendar_html += f"""
<div class="{classes}">
<div class="{date_class}">
{day.day}
</div>
"""

            for e in day_events[:3]:

                calendar_html += f"""
<div class="event">
{e.get("time","")}
{e.get("title","")}
</div>
"""

            for n in day_ng[:2]:

                calendar_html += f"""
<div class="event ng">
🚫 {n.get("time","")}
</div>
"""

            calendar_html += "</div>"

    calendar_html += "</div>"

    st.markdown(
        calendar_html,
        unsafe_allow_html=True
    )
