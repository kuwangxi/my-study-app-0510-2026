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
# JST
# ==========================================

JST = timezone(timedelta(hours=9))

def get_jst_now():
    return datetime.now(JST)

def get_weekday_jp(dt):

    w_list = ['月', '火', '水', '木', '金', '土', '日']

    return w_list[dt.weekday()]

# ==========================================
# セッション
# ==========================================

defaults = {
    "font_size": 14,
    "edit_id": None,
    "is_logged": False,
    "input_title": "",
    "input_url": "",
    "input_memo": "",
    "clear_inputs": False,
    "user_color": "#22c55e"
}

for k, v in defaults.items():

    if k not in st.session_state:
        st.session_state[k] = v

# 入力リセット

if st.session_state.clear_inputs:

    st.session_state.input_title = ""
    st.session_state.input_url = ""
    st.session_state.input_memo = ""

    st.session_state.clear_inputs = False

# ==========================================
# Firebase
# ==========================================

if not firebase_admin._apps:

    try:

        cred_dict = dict(st.secrets["firebase"])

        if "private_key" in cred_dict:

            cred_dict["private_key"] = cred_dict[
                "private_key"
            ].replace("\\n", "\n")

        cred = credentials.Certificate(cred_dict)

        firebase_admin.initialize_app(cred)

    except Exception as e:

        st.error(f"Firebase認証エラー : {e}")
        st.stop()

db = firestore.client()

APP_ID = "couple-secure-v2"

def get_events_ref():

    return db.collection("artifacts") \
        .document(APP_ID) \
        .collection("public") \
        .document("data") \
        .collection("secure_events")

def get_ng_ref():

    return db.collection("artifacts") \
        .document(APP_ID) \
        .collection("public") \
        .document("data") \
        .collection("secure_ng_dates")

def get_rooms_ref():

    return db.collection("artifacts") \
        .document(APP_ID) \
        .collection("public") \
        .document("data") \
        .collection("secure_rooms")

# ==========================================
# CSS
# ==========================================

st.markdown(f"""

<style>

html, body, [class*="st-"] {{
    font-size: {st.session_state.font_size}px !important;
}}

.block-container {{
    padding-top: 1rem;
}}

.time-badge {{
    background-color: rgba(128,128,128,0.2);
    padding: 2px 6px;
    border-radius: 999px;
    font-size: 11px;
}}

.last-message-box {{
    background: rgba(255,255,255,0.04);
    padding: 8px;
    border-radius: 10px;
    margin-top: 8px;
}}

.chat-bubble {{
    padding: 10px;
    border-radius: 14px;
    color: white;
    margin-bottom: 8px;
    word-break: break-word;
}}

.calendar-card {{
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 8px;
    min-height: 120px;
    background: rgba(255,255,255,0.02);
}}

.today-circle {{
    background: #ef4444;
    color: white;
    width: 28px;
    height: 28px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
}}

.event-pill {{
    background: #16a34a;
    color: white;
    border-radius: 8px;
    padding: 3px 6px;
    font-size: 11px;
    margin-bottom: 4px;
}}

.ng-pill {{
    background: #dc2626;
    color: white;
    border-radius: 8px;
    padding: 3px 6px;
    font-size: 11px;
    margin-bottom: 4px;
}}

@media (max-width: 768px) {{

    .calendar-mobile-scroll {{
        overflow-x: auto;
        white-space: nowrap;
        padding-bottom: 10px;
    }}

    .calendar-mobile-grid {{
        min-width: 700px;
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
        key=f"time_type_{key_prefix}"
    )

    if t_type == "カスタム":

        col1, col2 = st.columns(2)

        start = col1.time_input(
            "開始",
            value=get_jst_now().time(),
            key=f"start_{key_prefix}"
        )

        end = col2.time_input(
            "終了",
            value=(get_jst_now() + timedelta(hours=2)).time(),
            key=f"end_{key_prefix}"
        )

        return f"{start.strftime('%H:%M')}～{end.strftime('%H:%M')}"

    return None if t_type == "指定なし" else t_type

# ==========================================
# URLログイン保持復元
# ==========================================

if not st.session_state.is_logged:

    q_room = st.query_params.get("room")
    q_user = st.query_params.get("user")
    q_color = st.query_params.get("color")

    if q_room and q_user:

        st.session_state.room_key = q_room
        st.session_state.user_name = q_user
        st.session_state.user_color = q_color or "#22c55e"
        st.session_state.is_logged = True

# ==========================================
# ログイン
# ==========================================

if not st.session_state.is_logged:

    st.title("🤝 Shared Note Sync")

    name = st.text_input("表示名")

    color = st.color_picker(
        "自分の色",
        "#22c55e"
    )

    room_key = st.text_input("ルームキー")

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "新規作成",
            use_container_width=True
        ):

            if name:

                new_key = '-'.join([

                    ''.join(random.choices(
                        'ABCDEFGHJKLMNPQRSTUVWXYZ23456789',
                        k=4
                    ))

                    for _ in range(7)

                ])

                get_rooms_ref().document(new_key).set({
                    "createdAt": get_jst_now().isoformat()
                })

                st.session_state.room_key = new_key
                st.session_state.user_name = name
                st.session_state.user_color = color
                st.session_state.is_logged = True

                st.query_params["room"] = new_key
                st.query_params["user"] = name
                st.query_params["color"] = color

                st.rerun()

    with col2:

        if st.button(
            "参加",
            use_container_width=True
        ):

            if room_key and name:

                st.session_state.room_key = room_key
                st.session_state.user_name = name
                st.session_state.user_color = color
                st.session_state.is_logged = True

                st.query_params["room"] = room_key
                st.query_params["user"] = name
                st.query_params["color"] = color

                st.rerun()

    st.stop()

# ==========================================
# サイドバー
# ==========================================

with st.sidebar:

    st.title("⚙️ 設定")

    size = st.slider(
        "文字サイズ",
        10,
        30,
        st.session_state.font_size
    )

    if size != st.session_state.font_size:

        st.session_state.font_size = size
        st.rerun()

    st.divider()

    st.caption(
        f"ユーザー : {st.session_state.user_name}"
    )

    st.caption(
        f"ルーム : {st.session_state.room_key}"
    )

    st.color_picker(
        "自分の色",
        st.session_state.user_color,
        disabled=True
    )

# ==========================================
# データ取得
# ==========================================

room_key = st.session_state.room_key
user_name = st.session_state.user_name
user_color = st.session_state.user_color

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

today = get_jst_now().date()

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

    with st.expander("＋追加"):

        t = st.text_input(
            "場所/内容",
            key="input_title"
        )

        u = st.text_input(
            "URL",
            key="input_url"
        )

        m = st.text_area(
            "メモ",
            key="input_memo"
        )

        wt = time_selector_ui("wish")

        if st.button(
            "追加",
            type="primary"
        ):

            if t:

                get_events_ref().add({

                    "roomKey": room_key,
                    "title": t,
                    "url": u,
                    "memo": m,
                    "userName": user_name,
                    "status": "wishlist",
                    "comments": [],
                    "time": wt,
                    "createdAt": get_jst_now().isoformat()

                })

                st.session_state.clear_inputs = True

                st.rerun()

    wishlist = [

        e for e in events
        if e.get("status") == "wishlist"

    ]

    # 活発順

    def get_last_activity(item):

        comments = item.get("comments", [])

        if comments:

            return max([
                c.get("createdAt", "")
                for c in comments
            ])

        return item.get("createdAt", "")

    wishlist = sorted(
        wishlist,
        key=lambda x: get_last_activity(x),
        reverse=True
    )

    for item in wishlist:

        comments = item.get("comments", [])

        last_two = comments[-2:]

        latest_color = "#444"

        if comments:

            latest_color = comments[-1].get(
                "color",
                "#444"
            )

        with st.container(border=True):

            c1, c2 = st.columns([8,1])

            time_html = ""

            if item.get("time"):

                time_html = f"""
                <span class='time-badge'>
                ⏰ {item['time']}
                </span>
                """

            c1.markdown(
                f"""
                <div style="
                    border-left: 8px solid {latest_color};
                    padding-left: 10px;
                ">
                    <h3>
                        {time_html}
                        {item['title']}
                    </h3>
                </div>
                """,
                unsafe_allow_html=True
            )

            if item.get("url"):

                st.markdown(
                    f"[🔗 リンク]({item['url']})"
                )

            if item.get("memo"):

                st.info(item["memo"])

            # 最新2件表示

            if last_two:

                st.markdown("##### 最新メッセージ")

                for msg in reversed(last_two):

                    st.markdown(
                        f"""
                        <div class='last-message-box'
                        style='border-left:6px solid {msg.get("color","#444")}'>
                            <b>{msg['userName']}</b><br>
                            {msg['text']}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            with st.expander("💬 相談・確定"):

                for c in comments:

                    align = "flex-start"

                    if c["userName"] == user_name:
                        align = "flex-end"

                    st.markdown(
                        f"""
                        <div style="
                            display:flex;
                            justify-content:{align};
                        ">
                            <div class='chat-bubble'
                            style='background:{c.get("color","#444")};
                            max-width:80%;'>
                                <b>{c['userName']}</b><br>
                                {c['text']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with st.form(
                    key=f"form_{item['id']}",
                    clear_on_submit=True
                ):

                    cc1, cc2 = st.columns([5,1])

                    new_msg = cc1.text_input(
                        "メッセージ"
                    )

                    submit = cc2.form_submit_button(
                        "送信"
                    )

                    if submit and new_msg:

                        get_events_ref().document(
                            item["id"]
                        ).update({

                            "comments":
                            firestore.ArrayUnion([{

                                "userName": user_name,
                                "text": new_msg,
                                "color": user_color,
                                "createdAt":
                                get_jst_now().isoformat()

                            }])

                        })

                        st.rerun()

                st.divider()

                fix_date = st.date_input(
                    "確定日",
                    value=today,
                    key=f"fix_date_{item['id']}"
                )

                fix_time = time_selector_ui(
                    f"fix_{item['id']}"
                )

                if st.button(
                    "この日で確定",
                    key=f"fix_btn_{item['id']}"
                ):

                    get_events_ref().document(
                        item["id"]
                    ).update({

                        "status": "scheduled",
                        "date": str(fix_date),
                        "time": fix_time

                    })

                    st.rerun()

# ==========================================
# 予定
# ==========================================

with tab2:

    st.subheader("📅 予定一覧")

    sched = [

        e for e in events
        if e.get("status") == "scheduled"

    ]

    sched = sorted(
        sched,
        key=lambda x: (
            x.get("date", ""),
            x.get("time") or ""
        )
    )

    if not sched:

        st.write("予定はありません")

    for item in sched:

        with st.container(border=True):

            dt_obj = datetime.strptime(
                item["date"],
                "%Y-%m-%d"
            )

            st.markdown(
                f"""
                ### 📅
                {item['date']}
                ({get_weekday_jp(dt_obj)})
                """
            )

            st.write(
                f"⏰ {item.get('time','時間未定')}"
            )

            st.write(
                f"📍 {item['title']}"
            )

# ==========================================
# NG
# ==========================================

with tab3:

    st.subheader("🚫 NG日登録")

    nd = st.date_input(
        "行けない日",
        value=today
    )

    nt = time_selector_ui("ng")

    nr = st.text_input("理由")

    if st.button(
        "NG登録",
        type="primary"
    ):

        get_ng_ref().add({

            "roomKey": room_key,
            "userName": user_name,
            "date": str(nd),
            "reason": nr,
            "time": nt

        })

        st.rerun()

    st.divider()

    for n in sorted(
        ng_dates,
        key=lambda x: x.get("date","")
    ):

        with st.container(border=True):

            st.write(
                f"📅 {n.get('date','')}"
            )

            st.write(
                f"⏰ {n.get('time','時間未定')}"
            )

            st.write(
                f"🚫 {n.get('reason','')}"
            )

# ==========================================
# カレンダー
# ==========================================

with tab4:

    current = get_jst_now().date()

    selected = st.date_input(
        "表示月",
        value=current,
        key="calendar"
    )

    year = selected.year
    month = selected.month

    st.markdown(
        f"# {year}年 {month}月"
    )

    cal = calendar.monthcalendar(
        year,
        month
    )

    weekdays = [
        "月", "火", "水",
        "木", "金", "土", "日"
    ]

    st.markdown(
        "<div class='calendar-mobile-scroll'>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='calendar-mobile-grid'>",
        unsafe_allow_html=True
    )

    header_cols = st.columns(7)

    for i, d in enumerate(weekdays):

        header_cols[i].markdown(
            f"### {d}"
        )

    for week in cal:

        cols = st.columns(7)

        for idx, day in enumerate(week):

            with cols[idx]:

                if day == 0:

                    st.empty()
                    continue

                target_date = datetime(
                    year,
                    month,
                    day
                ).date()

                target_str = str(target_date)

                day_events = [

                    e for e in events

                    if e.get("status") == "scheduled"
                    and e.get("date") == target_str

                ]

                day_ng = [

                    n for n in ng_dates
                    if n.get("date") == target_str

                ]

                with st.container():

                    st.markdown(
                        "<div class='calendar-card'>",
                        unsafe_allow_html=True
                    )

                    if target_date == today:

                        st.markdown(
                            f"""
                            <div class='today-circle'>
                            {day}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    else:

                        st.markdown(f"### {day}")

                    for ev in day_events[:3]:

                        st.markdown(
                            f"""
                            <div class='event-pill'>
                            📍 {ev['title']}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    for ng in day_ng[:2]:

                        st.markdown(
                            f"""
                            <div class='ng-pill'>
                            🚫 {ng.get('reason','NG')}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    if day_events or day_ng:

                        with st.expander("詳細"):

                            for ev in day_events:

                                st.write(
                                    f"""
                                    📍
                                    {ev.get('time','時間未定')}
                                    - {ev['title']}
                                    """
                                )

                            for ng in day_ng:

                                st.write(
                                    f"""
                                    🚫
                                    {ng.get('time','時間未定')}
                                    - {ng.get('reason','')}
                                    """
                                )

                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True
                    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )
