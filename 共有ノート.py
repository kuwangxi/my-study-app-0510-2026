import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
import calendar
from datetime import datetime, timedelta, timezone

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
    "show_summary": True,
    "hide_empty_days": True,
    "edit_id": None,
    "input_title": "",
    "input_url": "",
    "input_memo": "",
    "ng_reason": "",
    "clear_wish_inputs": False,
    "clear_ng_inputs": False,
    "is_logged": False,
    "user_color": "#22c55e"
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
# JST
# ==========================================

JST = timezone(timedelta(hours=9))

def get_jst_now():
    return datetime.now(JST)

def get_weekday_jp(dt):
    w_list = ['月', '火', '水', '木', '金', '土', '日']
    return w_list[dt.weekday()]

# ==========================================
# Firebase
# ==========================================

if not firebase_admin._apps:

    try:

        cred_dict = dict(st.secrets["firebase"])

        if "private_key" in cred_dict:
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")

        cred = credentials.Certificate(cred_dict)

        firebase_admin.initialize_app(cred)

    except Exception as e:

        st.error(f"Firebase認証エラー: {e}")
        st.stop()

db = firestore.client()

APP_ID = "couple-secure-v2"

def get_events_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_events')

def get_ng_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_ng_dates')

def get_rooms_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_rooms')

# ==========================================
# 設定保存
# ==========================================

def save_app_settings():

    if st.session_state.get("room_key"):

        get_rooms_ref().document(
            st.session_state.room_key
        ).set({

            "settings": {

                "font_size": st.session_state.font_size,
                "show_summary": st.session_state.show_summary,
                "hide_empty_days": st.session_state.hide_empty_days,
                "user_color": st.session_state.user_color

            }

        }, merge=True)

# ==========================================
# 設定読み込み
# ==========================================

def load_app_settings(room_key):

    doc = get_rooms_ref().document(room_key).get()

    if doc.exists:

        data = doc.to_dict()

        if "settings" in data:

            s = data["settings"]

            st.session_state.font_size = s.get("font_size", 14)
            st.session_state.show_summary = s.get("show_summary", True)
            st.session_state.hide_empty_days = s.get("hide_empty_days", True)
            st.session_state.user_color = s.get("user_color", "#22c55e")

# ==========================================
# CSS
# ==========================================

st.markdown(f"""

<style>

html, body, [class*="st-"] {{
    font-size: {st.session_state.font_size}px !important;
}}

.past-item {{
    color: #9e9e9e;
}}

.time-badge {{
    background-color: rgba(128,128,128,0.2);
    padding: 2px 6px;
    border-radius: 6px;
    font-size: 11px;
}}

.chat-preview {{
    padding: 8px;
    border-radius: 10px;
    margin-top: 10px;
    color: white;
    font-size: 13px;
}}

.calendar-box {{
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 8px;
    min-height: 130px;
    background: rgba(255,255,255,0.03);
}}

.today-box {{
    background: rgba(244,63,94,0.2);
    border: 2px solid #f43f5e;
}}

.calendar-date {{
    font-weight: bold;
    margin-bottom: 8px;
}}

.event-pill {{
    background: #16a34a;
    color: white;
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 11px;
    margin-bottom: 4px;
}}

.ng-pill {{
    background: #dc2626;
    color: white;
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 11px;
    margin-bottom: 4px;
}}

@media (max-width: 768px) {{

    .calendar-scroll {{
        overflow-x: auto;
    }}

    .calendar-inner {{
        min-width: 900px;
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
        key=f"t_type_{key_prefix}"
    )

    if t_type == "カスタム":

        c1, c2 = st.columns(2)

        t_start = c1.time_input(
            "開始",
            value=get_jst_now().time(),
            key=f"t_start_{key_prefix}"
        )

        t_end = c2.time_input(
            "終了",
            value=(get_jst_now() + timedelta(hours=2)).time(),
            key=f"t_end_{key_prefix}"
        )

        return f"{t_start.strftime('%H:%M')}～{t_end.strftime('%H:%M')}"

    return None if t_type == "指定なし" else t_type

# ==========================================
# ログイン維持
# ==========================================

if not st.session_state.is_logged:

    q_room = st.query_params.get("room")
    q_user = st.query_params.get("user")

    if q_room and q_user:

        st.session_state.room_key = q_room
        st.session_state.user_name = q_user
        st.session_state.is_logged = True

        load_app_settings(q_room)

# ==========================================
# ログイン
# ==========================================

def login_action(room, user):

    st.session_state.room_key = room
    st.session_state.user_name = user
    st.session_state.is_logged = True

    st.query_params["room"] = room
    st.query_params["user"] = user

    load_app_settings(room)

def logout():

    st.session_state.is_logged = False

    st.query_params.clear()

    st.rerun()

# ==========================================
# サイドバー
# ==========================================

if st.session_state.is_logged:

    st.sidebar.title("⚙️ アプリ設定")

    new_size = st.sidebar.slider(
        "文字サイズ",
        10,
        30,
        value=st.session_state.font_size
    )

    new_show_summary = st.sidebar.checkbox(
        "サマリー表示",
        value=st.session_state.show_summary
    )

    new_hide_empty = st.sidebar.checkbox(
        "予定がある日のみ",
        value=st.session_state.hide_empty_days
    )

    new_color = st.sidebar.color_picker(
        "自分の色",
        value=st.session_state.user_color
    )

    if (
        new_size != st.session_state.font_size
        or new_show_summary != st.session_state.show_summary
        or new_hide_empty != st.session_state.hide_empty_days
        or new_color != st.session_state.user_color
    ):

        st.session_state.font_size = new_size
        st.session_state.show_summary = new_show_summary
        st.session_state.hide_empty_days = new_hide_empty
        st.session_state.user_color = new_color

        save_app_settings()

        st.rerun()

    st.sidebar.divider()

    st.sidebar.caption(f"User : {st.session_state.user_name}")
    st.sidebar.caption(f"Key : {st.session_state.room_key}")

    if st.sidebar.button("ログアウト", use_container_width=True):
        logout()

# ==========================================
# ログイン画面
# ==========================================

if not st.session_state.get("is_logged"):

    st.title("🤝 Shared Note Sync")

    name_input = st.text_input("表示名")

    if name_input:

        st.session_state.user_name = name_input

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "新しいノートを作る",
                use_container_width=True
            ):

                new_key = '-'.join([

                    ''.join(random.choices(
                        'ABCDEFGHJKLMNPQRSTUVWXYZ23456789',
                        k=4
                    ))

                    for _ in range(7)

                ])

                get_rooms_ref().document(new_key).set({

                    'createdAt': get_jst_now().isoformat(),

                    'creator': name_input,

                    'settings': {
                        "font_size": 14,
                        "show_summary": True,
                        "hide_empty_days": True,
                        "user_color": "#22c55e"
                    }

                })

                login_action(new_key, name_input)

                st.rerun()

        with col2:

            input_key = st.text_input(
                "秘密鍵",
                placeholder="XXXX-XXXX..."
            )

            if st.button(
                "参加する",
                use_container_width=True
            ) and len(input_key) >= 29:

                login_action(input_key, name_input)

                st.rerun()

    st.stop()

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

today_str = str(get_jst_now().date())

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

        if st.button(
            "追加",
            use_container_width=True,
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

                st.session_state.clear_wish_inputs = True

                st.rerun()

    wishlist = [

        e for e in events
        if e.get("status") == "wishlist"

    ]

    def get_last_activity(item):

        comments = item.get("comments", [])

        if comments:
            return comments[-1].get("createdAt", "")

        return item.get("createdAt", "")

    wishlist = sorted(
        wishlist,
        key=lambda x: get_last_activity(x),
        reverse=True
    )

    for item in wishlist:

        comments = item.get("comments", [])

        latest_color = "#666"

        if comments:
            latest_color = comments[-1].get(
                "color",
                "#666"
            )

        with st.container(border=True):

            c1, c2 = st.columns([5,1])

            time_disp = ""

            if item.get("time"):

                time_disp = f"""
                <span class='time-badge'>
                ⏰ {item['time']}
                </span>
                """

            c1.markdown(
                f"""
                <div style="
                    border-left:8px solid {latest_color};
                    padding-left:10px;
                ">
                <h3>{time_disp} {item['title']}</h3>
                </div>
                """,
                unsafe_allow_html=True
            )

            if c2.button(
                "📝",
                key=f"ed_{item['id']}"
            ):

                st.session_state.edit_id = item["id"]

                st.rerun()

            # 編集

            if st.session_state.edit_id == item["id"]:

                et = st.text_input(
                    "編集タイトル",
                    item["title"],
                    key=f"et_{item['id']}"
                )

                eu = st.text_input(
                    "編集URL",
                    item.get("url",""),
                    key=f"eu_{item['id']}"
                )

                em = st.text_area(
                    "編集メモ",
                    item.get("memo",""),
                    key=f"em_{item['id']}"
                )

                c_a, c_b, c_c = st.columns(3)

                if c_a.button(
                    "保存",
                    key=f"sv_{item['id']}",
                    use_container_width=True
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

                if c_b.button(
                    "キャンセル",
                    key=f"cn_{item['id']}",
                    use_container_width=True
                ):

                    st.session_state.edit_id = None

                    st.rerun()

                if c_c.button(
                    "削除",
                    key=f"del_{item['id']}",
                    use_container_width=True
                ):

                    get_events_ref().document(
                        item["id"]
                    ).delete()

                    st.session_state.edit_id = None

                    st.rerun()

            if item.get("url"):
                st.markdown(f"[🔗 リンク]({item['url']})")

            if item.get("memo"):
                st.info(item["memo"])

            # 最新メッセージ1件

            if comments:

                last_msg = comments[-1]

                st.markdown(
                    f"""
                    <div class='chat-preview'
                    style='background:{last_msg.get("color","#666")}'>
                    <b>{last_msg["userName"]}</b><br>
                    {last_msg["text"]}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with st.expander("💬 相談・確定"):

                for c in comments:

                    st.markdown(
                        f"""
                        <div style="
                            background:{c.get('color','#666')};
                            color:white;
                            padding:10px;
                            border-radius:10px;
                            margin-bottom:8px;
                        ">
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

                    cc1, cc2 = st.columns([5,1])

                    new_c = cc1.text_input(
                        "メッセージ"
                    )

                    send = cc2.form_submit_button("送信")

                    if send and new_c:

                        get_events_ref().document(
                            item["id"]
                        ).update({

                            "comments":
                            firestore.ArrayUnion([{

                                "userName": user_name,
                                "text": new_c,
                                "color": st.session_state.user_color,
                                "createdAt":
                                get_jst_now().isoformat()

                            }])

                        })

                        st.rerun()

                st.divider()

                sd = st.date_input(
                    "確定日",
                    value=get_jst_now().date(),
                    key=f"sd_{item['id']}"
                )

                st_time = time_selector_ui(
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
                        "date": str(sd),
                        "time": st_time

                    })

                    st.rerun()

# ==========================================
# 予定
# ==========================================

with tab2:

    st.subheader("🚀 これからの予定")

    sched = [

        e for e in events
        if e.get("status") == "scheduled"

    ]

    upcoming = sorted(
        sched,
        key=lambda x: (
            x.get("date",""),
            x.get("time") or ""
        )
    )

    if not upcoming:
        st.write("予定はありません")

    for item in upcoming:

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
# NG日
# ==========================================

with tab3:

    st.subheader("🚫 NG日")

    nd = st.date_input(
        "行けない日",
        value=get_jst_now().date(),
        key="ng_date_input"
    )

    nt_str = time_selector_ui("ng_add")

    nr = st.text_input(
        "理由",
        key="ng_reason"
    )

    if st.button(
        "NG登録",
        use_container_width=True,
        type="primary"
    ):

        get_ng_ref().add({

            "roomKey": room_key,
            "userName": user_name,
            "date": str(nd),
            "reason": nr,
            "time": nt_str

        })

        st.session_state.clear_ng_inputs = True

        st.rerun()

    st.divider()

    for n in sorted(
        ng_dates,
        key=lambda x: x.get("date","")
    ):

        with st.container(border=True):

            st.write(f"📅 {n.get('date','')}")
            st.write(f"⏰ {n.get('time','時間未定')}")
            st.write(f"🚫 {n.get('reason','')}")

# ==========================================
# カレンダー
# ==========================================

with tab4:

    now = get_jst_now()

    year = now.year
    month = now.month

    st.markdown(f"## {year}年 {month}月")

    cal = calendar.monthcalendar(year, month)

    weekdays = [
        "月", "火", "水",
        "木", "金", "土", "日"
    ]

    st.markdown(
        "<div class='calendar-scroll'>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='calendar-inner'>",
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

                today_cls = ""

                if target_date == get_jst_now().date():
                    today_cls = "today-box"

                st.markdown(
                    f"""
                    <div class='calendar-box {today_cls}'>
                    <div class='calendar-date'>
                    {day}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

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
