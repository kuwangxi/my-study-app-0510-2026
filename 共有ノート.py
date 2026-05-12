import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta, timezone
import calendar

# ==========================================
# 初期設定
# ==========================================

st.set_page_config(
    page_title="ふたりの共有ノート",
    page_icon="🤝",
    layout="wide"
)

# ==========================================
# セッション初期化
# ==========================================

defaults = {
    "font_size": 14,
    "edit_id": None,
    "input_title": "",
    "input_url": "",
    "input_memo": "",
    "ng_reason": "",
    "clear_wish_inputs": False,
    "clear_ng_inputs": False,
    "user_color": "#ff4b6e"
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================================
# 入力リセット
# ==========================================

if st.session_state.clear_wish_inputs:
    st.session_state.input_title = ""
    st.session_state.input_url = ""
    st.session_state.input_memo = ""
    st.session_state.clear_wish_inputs = False

if st.session_state.clear_ng_inputs:
    st.session_state.ng_reason = ""
    st.session_state.clear_ng_inputs = False

# ==========================================
# 日時
# ==========================================

def get_jst_now():
    return datetime.now(timezone(timedelta(hours=9)))

def get_weekday_jp(dt):
    arr = ["月","火","水","木","金","土","日"]
    return arr[dt.weekday()]

today = get_jst_now().date()
today_str = str(today)

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
    return db.collection("artifacts").document(APP_ID)\
        .collection("public").document("data")\
        .collection("secure_events")

def get_ng_ref():
    return db.collection("artifacts").document(APP_ID)\
        .collection("public").document("data")\
        .collection("secure_ng_dates")

def get_rooms_ref():
    return db.collection("artifacts").document(APP_ID)\
        .collection("public").document("data")\
        .collection("secure_rooms")

# ==========================================
# CSS
# ==========================================

st.markdown(f"""
<style>

html, body, [class*="st-"] {{
    font-size:{st.session_state.font_size}px !important;
}}

.block-container {{
    padding-top: 1rem;
}}

.calendar-grid {{
    display:grid;
    grid-template-columns:repeat(7,1fr);
    gap:4px;
}}

.calendar-cell {{
    border:1px solid #444;
    border-radius:10px;
    min-height:95px;
    padding:5px;
    background:#111;
}}

.calendar-header {{
    text-align:center;
    font-weight:bold;
    background:#222;
    border-radius:8px;
    padding:5px;
}}

.today-cell {{
    border:2px solid #ff4b6e;
    background:#2b1720;
}}

.day-number {{
    font-weight:bold;
    margin-bottom:4px;
}}

.event-chip {{
    background:#1f2937;
    border-radius:6px;
    padding:2px 5px;
    margin-top:3px;
    font-size:11px;
}}

.ng-chip {{
    background:#4b1d1d;
    border-radius:6px;
    padding:2px 5px;
    margin-top:3px;
    font-size:11px;
}}

.comment-preview {{
    background:#161616;
    border-radius:8px;
    padding:8px;
    margin-top:8px;
}}

.user-badge {{
    padding:2px 8px;
    border-radius:999px;
    color:white;
    font-size:12px;
    font-weight:bold;
}}

@media (max-width: 768px) {{

    .calendar-grid {{
        grid-template-columns:repeat(7,minmax(40px,1fr));
        overflow-x:auto;
    }}

    .calendar-cell {{
        min-height:70px;
        font-size:10px;
        padding:2px;
    }}

}}

</style>
""", unsafe_allow_html=True)

# ==========================================
# 時間UI
# ==========================================

def time_selector_ui(key_prefix):

    t_type = st.selectbox(
        "時間指定",
        ["指定なし", "午前中", "午後", "終日", "カスタム"],
        key=f"type_{key_prefix}"
    )

    if t_type == "カスタム":

        c1, c2 = st.columns(2)

        start = c1.time_input(
            "開始",
            key=f"start_{key_prefix}"
        )

        end = c2.time_input(
            "終了",
            key=f"end_{key_prefix}"
        )

        return f"{start.strftime('%H:%M')}〜{end.strftime('%H:%M')}"

    return None if t_type == "指定なし" else t_type

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
# ログイン画面
# ==========================================

if not st.session_state.get("is_logged"):

    st.title("🤝 Shared Note Sync")

    name = st.text_input("表示名")

    c1, c2 = st.columns(2)

    with c1:

        if st.button("新しいノートを作る", use_container_width=True):

            if name:

                key = '-'.join([
                    ''.join(random.choices(
                        'ABCDEFGHJKLMNPQRSTUVWXYZ23456789',
                        k=4
                    ))
                    for _ in range(7)
                ])

                get_rooms_ref().document(key).set({
                    "createdAt": get_jst_now().isoformat()
                })

                login_action(key, name)
                st.rerun()

    with c2:

        join_key = st.text_input("秘密鍵")

        if st.button("参加する", use_container_width=True):

            if join_key and name:

                login_action(join_key, name)
                st.rerun()

    st.stop()

# ==========================================
# サイドバー
# ==========================================

st.sidebar.title("⚙️ 設定")

new_size = st.sidebar.slider(
    "文字サイズ",
    10,
    30,
    st.session_state.font_size
)

if new_size != st.session_state.font_size:
    st.session_state.font_size = new_size
    st.rerun()

new_color = st.sidebar.color_picker(
    "自分の色",
    value=st.session_state.user_color
)

st.session_state.user_color = new_color

st.sidebar.divider()

st.sidebar.write(f"👤 {st.session_state.user_name}")
st.sidebar.write(f"🔑 {st.session_state.room_key}")

if st.sidebar.button("ログアウト"):
    logout()

# ==========================================
# データ取得
# ==========================================

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

# ==========================================
# ソート
# ==========================================

def get_last_comment_time(item):

    comments = item.get("comments", [])

    if comments:
        return comments[-1].get("createdAt", "")

    return item.get("createdAt", "")

wishlist_items = sorted(
    [e for e in events if e.get("status") == "wishlist"],
    key=lambda x: get_last_comment_time(x),
    reverse=True
)

# ==========================================
# タブ
# ==========================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📍 行きたい",
    "📅 予定",
    "🚫 NG日",
    "🗓️ カレンダー"
])

# ==========================================
# 行きたい
# ==========================================

with tab1:

    with st.expander("＋ 追加する"):

        t = st.text_input("場所/内容", key="input_title")
        u = st.text_input("URL", key="input_url")
        m = st.text_area("メモ", key="input_memo")

        wt = time_selector_ui("wish")

        if st.button("追加", type="primary"):

            if t:

                get_events_ref().add({
                    "roomKey": room_key,
                    "title": t,
                    "url": u,
                    "memo": m,
                    "status": "wishlist",
                    "time": wt,
                    "userName": user_name,
                    "createdAt": get_jst_now().isoformat(),
                    "comments": [],
                    "lastUserColor": st.session_state.user_color
                })

                st.session_state.clear_wish_inputs = True
                st.rerun()

    for item in wishlist_items:

        with st.container(border=True):

            last_color = item.get("lastUserColor", "#666")

            st.markdown(f"""
            <div style="
                width:100%;
                height:6px;
                border-radius:999px;
                background:{last_color};
                margin-bottom:10px;
            "></div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns([6,1])

            with c1:
                st.subheader(item["title"])

            with c2:
                if st.button("📝", key=f"edit_{item['id']}"):
                    st.session_state.edit_id = item["id"]
                    st.rerun()

            if item.get("url"):
                st.markdown(f"[🔗 リンク]({item['url']})")

            if item.get("memo"):
                st.info(item["memo"])

            comments = item.get("comments", [])

            if comments:

                last = comments[-1]

                st.markdown(f"""
                <div class="comment-preview">
                <span class="user-badge"
                style="background:{last.get('color','#666')}">
                {last['userName']}
                </span>
                {last['text']}
                </div>
                """, unsafe_allow_html=True)

            if st.session_state.edit_id == item["id"]:

                et = st.text_input(
                    "タイトル",
                    value=item["title"],
                    key=f"et_{item['id']}"
                )

                em = st.text_area(
                    "メモ",
                    value=item.get("memo",""),
                    key=f"em_{item['id']}"
                )

                c1, c2, c3 = st.columns(3)

                if c1.button("保存", key=f"save_{item['id']}"):

                    get_events_ref().document(item["id"]).update({
                        "title": et,
                        "memo": em
                    })

                    st.session_state.edit_id = None
                    st.rerun()

                if c2.button("キャンセル", key=f"cancel_{item['id']}"):

                    st.session_state.edit_id = None
                    st.rerun()

                if c3.button("削除", key=f"delete_{item['id']}"):

                    get_events_ref().document(item["id"]).delete()
                    st.rerun()

            with st.expander("💬 相談・確定"):

                for c in comments:

                    st.markdown(f"""
                    <div style="
                        border-left:5px solid {c.get('color','#666')};
                        padding-left:10px;
                        margin-bottom:10px;
                    ">
                    <b>{c['userName']}</b><br>
                    {c['text']}
                    </div>
                    """, unsafe_allow_html=True)

                with st.form(f"comment_{item['id']}", clear_on_submit=True):

                    msg = st.text_input("メッセージ")

                    ok = st.form_submit_button("送信")

                    if ok and msg:

                        get_events_ref().document(item["id"]).update({

                            "comments": firestore.ArrayUnion([{
                                "userName": user_name,
                                "text": msg,
                                "createdAt": get_jst_now().isoformat(),
                                "color": st.session_state.user_color
                            }]),

                            "lastUserColor": st.session_state.user_color
                        })

                        st.rerun()

                st.divider()

                fix_date = st.date_input(
                    "確定日",
                    value=today,
                    key=f"fd_{item['id']}"
                )

                fix_time = time_selector_ui(f"fix_{item['id']}")

                if st.button("この日で確定", key=f"fix_{item['id']}"):

                    get_events_ref().document(item["id"]).update({
                        "status": "scheduled",
                        "date": str(fix_date),
                        "time": fix_time
                    })

                    st.rerun()

# ==========================================
# 予定
# ==========================================

with tab2:

    st.header("📅 これからの予定")

    scheduled = sorted(
        [e for e in events if e.get("status") == "scheduled"],
        key=lambda x: x.get("date","")
    )

    if not scheduled:
        st.info("予定はありません")

    for item in scheduled:

        with st.container(border=True):

            st.subheader(item["title"])

            st.write(f"📅 {item.get('date','')}")

            if item.get("time"):
                st.write(f"⏰ {item['time']}")

            if item.get("memo"):
                st.info(item["memo"])

            c1, c2, c3 = st.columns(3)

            if c1.button("📝 編集", key=f"sch_edit_{item['id']}"):
                st.session_state.edit_id = item["id"]

            if c2.button("📍 行きたいに戻す", key=f"back_{item['id']}"):

                get_events_ref().document(item["id"]).update({
                    "status": "wishlist",
                    "date": None
                })

                st.rerun()

            if c3.button("🗑️ 削除", key=f"sch_del_{item['id']}"):

                get_events_ref().document(item["id"]).delete()
                st.rerun()

            if st.session_state.edit_id == item["id"]:

                new_title = st.text_input(
                    "タイトル変更",
                    value=item["title"],
                    key=f"new_title_{item['id']}"
                )

                new_date = st.date_input(
                    "日付変更",
                    value=datetime.strptime(
                        item["date"],
                        "%Y-%m-%d"
                    ).date(),
                    key=f"new_date_{item['id']}"
                )

                new_time = st.text_input(
                    "時間変更",
                    value=item.get("time",""),
                    key=f"new_time_{item['id']}"
                )

                if st.button("保存", key=f"save_schedule_{item['id']}"):

                    get_events_ref().document(item["id"]).update({
                        "title": new_title,
                        "date": str(new_date),
                        "time": new_time
                    })

                    st.session_state.edit_id = None
                    st.rerun()

# ==========================================
# NG日
# ==========================================

with tab3:

    st.header("🚫 NG日")

    nd = st.date_input("行けない日", value=today)

    nt = time_selector_ui("ng")

    reason = st.text_input("理由", key="ng_reason")

    if st.button("NG登録", type="primary"):

        get_ng_ref().add({
            "roomKey": room_key,
            "userName": user_name,
            "date": str(nd),
            "time": nt,
            "reason": reason
        })

        st.session_state.clear_ng_inputs = True
        st.rerun()

    st.divider()

    for n in sorted(ng_dates, key=lambda x: x["date"]):

        with st.container(border=True):

            st.write(f"📅 {n['date']}")

            if n.get("time"):
                st.write(f"⏰ {n['time']}")

            st.write(f"🚫 {n.get('reason','')}")

# ==========================================
# カレンダー
# ==========================================

with tab4:

    st.header("🗓️ カレンダー")

    now = get_jst_now()

    year = now.year
    month = now.month

    st.subheader(f"{year}年 {month}月")

    headers = ["月","火","水","木","金","土","日"]

    st.markdown('<div class="calendar-grid">', unsafe_allow_html=True)

    for h in headers:
        st.markdown(
            f'<div class="calendar-header">{h}</div>',
            unsafe_allow_html=True
        )

    cal = calendar.monthcalendar(year, month)

    for week in cal:

        for day in week:

            if day == 0:

                st.markdown(
                    '<div class="calendar-cell"></div>',
                    unsafe_allow_html=True
                )

            else:

                cell_date = datetime(year, month, day).date()
                cell_str = str(cell_date)

                day_events = [
                    e for e in events
                    if e.get("date") == cell_str
                ]

                day_ng = [
                    n for n in ng_dates
                    if n.get("date") == cell_str
                ]

                today_class = ""

                if cell_date == today:
                    today_class = "today-cell"

                html = f"""
                <div class="calendar-cell {today_class}">
                <div class="day-number">{day}</div>
                """

                for ev in day_events[:2]:
                    html += f"""
                    <div class="event-chip">
                    📍 {ev['title'][:8]}
                    </div>
                    """

                for ng in day_ng[:1]:
                    html += f"""
                    <div class="ng-chip">
                    🚫 NG
                    </div>
                    """

                html += "</div>"

                st.markdown(html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
