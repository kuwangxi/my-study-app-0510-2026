import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta, timezone
import calendar

# ==========================================
# 1. 初期設定とFirebase接続
# ==========================================

st.set_page_config(page_title="ふたりの共有ノート", page_icon="🤝", layout="centered")

# --- セッション状態の初期化 ---
if "font_size" not in st.session_state: st.session_state.font_size = 14
if "show_summary" not in st.session_state: st.session_state.show_summary = True
if "hide_empty_days" not in st.session_state: st.session_state.hide_empty_days = True
if "edit_id" not in st.session_state: st.session_state.edit_id = None

# テキスト入力リセット用
if "input_title" not in st.session_state: st.session_state.input_title = ""
if "input_url" not in st.session_state: st.session_state.input_url = ""
if "input_memo" not in st.session_state: st.session_state.input_memo = ""
if "ng_reason" not in st.session_state: st.session_state.ng_reason = ""
if "clear_wish_inputs" not in st.session_state: st.session_state.clear_wish_inputs = False
if "clear_ng_inputs" not in st.session_state: st.session_state.clear_ng_inputs = False

# 入力クリア処理
if st.session_state.clear_wish_inputs:
    st.session_state.input_title = ""
    st.session_state.input_url = ""
    st.session_state.input_memo = ""
    st.session_state.clear_wish_inputs = False

if st.session_state.clear_ng_inputs:
    st.session_state.ng_reason = ""
    st.session_state.clear_ng_inputs = False

def get_jst_now():
    return datetime.now(timezone(timedelta(hours=9)))

def get_weekday_jp(dt):
    w_list = ['月', '火', '水', '木', '金', '土', '日']
    return w_list[dt.weekday()]

# Firebase初期化
if not firebase_admin._apps:
    try:
        cred_dict = dict(st.secrets["firebase"])

        if "private_key" in cred_dict:
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

    except Exception as e:
        st.error(f"Firebaseの認証エラー: {e}")
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

        get_rooms_ref().document(st.session_state.room_key).set({

            "settings": {

                "font_size": st.session_state.font_size,
                "show_summary": st.session_state.show_summary,
                "hide_empty_days": st.session_state.hide_empty_days

            }

        }, merge=True)

def load_app_settings(room_key):

    doc = get_rooms_ref().document(room_key).get()

    if doc.exists:

        data = doc.to_dict()

        if "settings" in data:

            s = data["settings"]

            st.session_state.font_size = s.get("font_size", 14)
            st.session_state.show_summary = s.get("show_summary", True)
            st.session_state.hide_empty_days = s.get("hide_empty_days", True)

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

.calendar-card {{
    background-color: rgba(128, 128, 128, 0.1);
    border-radius: 8px;
    padding: 8px 2px;
    text-align: center;
    border: 1px solid rgba(128, 128, 128, 0.3);
    margin-bottom: 5px;
}}

.calendar-date {{
    font-weight: bold;
    color: #f43f5e;
    font-size: 0.9em;
}}

.calendar-today {{
    background-color: rgba(244, 63, 94, 0.2);
    border: 2px solid #f43f5e;
}}

.time-badge {{
    background-color: rgba(128, 128, 128, 0.2);
    padding: 2px 5px;
    border-radius: 4px;
    font-size: 0.8em;
}}

.new-badge {{
    background: #ef4444;
    color: white;
    padding: 2px 6px;
    border-radius: 999px;
    font-size: 11px;
    margin-left: 6px;
}}

.calendar-day-box {{
    border: 1px solid rgba(128,128,128,0.2);
    border-radius: 10px;
    padding: 8px;
    min-height: 90px;
    margin-bottom: 6px;
    background: rgba(255,255,255,0.03);
}}

.calendar-day-header {{
    font-weight: bold;
    margin-bottom: 6px;
}}

.calendar-event-count {{
    font-size: 12px;
    color: #f43f5e;
}}

.calendar-ng-count {{
    font-size: 12px;
    color: #6366f1;
}}

</style>

""", unsafe_allow_html=True)

# ==========================================
# 時間選択UI
# ==========================================

def time_selector_ui(key_prefix):

    t_type = st.selectbox(
        "時間指定",
        ["指定なし", "午前中", "午後", "終日", "カスタム"],
        key=f"t_type_{key_prefix}"
    )

    if t_type == "カスタム":

        col_c1, col_c2 = st.columns(2)

        t_start = col_c1.time_input(
            "開始",
            value=get_jst_now().time(),
            key=f"t_start_{key_prefix}"
        )

        t_end = col_c2.time_input(
            "終了",
            value=(get_jst_now() + timedelta(hours=2)).time(),
            key=f"t_end_{key_prefix}"
        )

        return f"{t_start.strftime('%H:%M')}～{t_end.strftime('%H:%M')}"

    return None if t_type == "指定なし" else t_type

# ==========================================
# ログイン管理
# ==========================================

if "is_logged" not in st.session_state:

    q_room = st.query_params.get("room")
    q_user = st.query_params.get("user")

    if q_room and q_user:

        st.session_state.room_key = q_room
        st.session_state.user_name = q_user
        st.session_state.is_logged = True

        load_app_settings(q_room)

    else:

        st.session_state.is_logged = False

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
        "テキストの大きさ",
        10,
        24,
        value=st.session_state.font_size
    )

    new_show_summary = st.sidebar.checkbox(
        "カレンダーサマリーを表示",
        value=st.session_state.show_summary
    )

    new_hide_empty = st.sidebar.checkbox(
        "予定がある日のみ表示",
        value=st.session_state.hide_empty_days
    )

    if (
        new_size != st.session_state.font_size
        or new_show_summary != st.session_state.show_summary
        or new_hide_empty != st.session_state.hide_empty_days
    ):

        st.session_state.font_size = new_size
        st.session_state.show_summary = new_show_summary
        st.session_state.hide_empty_days = new_hide_empty

        save_app_settings()
        st.rerun()

    st.sidebar.divider()

    st.sidebar.caption(f"User: {st.session_state.user_name}")
    st.sidebar.caption(f"Key: {st.session_state.room_key}")

    if st.sidebar.button("ログアウト", use_container_width=True):
        logout()

# ==========================================
# ログイン画面
# ==========================================

if not st.session_state.get("is_logged") or not st.session_state.get("user_name"):

    st.markdown(
        "<h1 style='text-align: center; color: #f43f5e;'>Shared Note Sync</h1>",
        unsafe_allow_html=True
    )

    name_input = st.text_input(
        "表示名を入力してください",
        value=st.session_state.get("user_name", "")
    )

    if name_input:

        st.session_state.user_name = name_input

        col1, col2 = st.columns(2)

        with col1:

            if st.button("新しいノートを作る", use_container_width=True):

                new_key = '-'.join([
                    ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4))
                    for _ in range(7)
                ])

                get_rooms_ref().document(new_key).set({

                    'createdAt': get_jst_now().isoformat(),
                    'creator': name_input,

                    'settings': {

                        "font_size": 14,
                        "show_summary": True,
                        "hide_empty_days": True

                    }

                })

                login_action(new_key, name_input)
                st.rerun()

        with col2:

            input_key = st.text_input(
                "秘密鍵(29桁)を入力",
                placeholder="XXXX-XXXX..."
            )

            if st.button("参加する", use_container_width=True) and len(input_key) >= 29:

                login_action(input_key, name_input)
                st.rerun()

    st.stop()

# ==========================================
# メイン
# ==========================================

room_key = st.session_state.room_key
user_name = st.session_state.user_name

events = [
    {"id": d.id, **d.to_dict()}
    for d in get_events_ref().where("roomKey", "==", room_key).stream()
]

ng_dates = [
    {"id": d.id, **d.to_dict()}
    for d in get_ng_ref().where("roomKey", "==", room_key).stream()
]

today_str = str(get_jst_now().date())

tab1, tab2, tab3 = st.tabs(["📍 行きたい", "📅 予定", "🚫 NG日"])

# ==========================================
# タブ1
# ==========================================

with tab1:

    with st.expander("＋ 追加する"):

        t = st.text_input("場所/内容", key="input_title")
        u = st.text_input("URL", key="input_url")
        m = st.text_area("メモ", key="input_memo")

        wt = time_selector_ui("wish")

        if st.button("追加", use_container_width=True, type="primary"):

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

            else:

                st.warning("場所/内容を入力してください")

    wishlist_items = [e for e in events if e.get("status") == "wishlist"]

    def get_last_activity(item):

        comments = item.get("comments", [])

        if comments:

            latest_comment = max(
                comments,
                key=lambda x: x.get("createdAt", "")
            )

            return latest_comment.get("createdAt", "")

        return item.get("createdAt", "")

    wishlist_items = sorted(
        wishlist_items,
        key=lambda x: get_last_activity(x),
        reverse=True
    )

    for item in wishlist_items:

        with st.container(border=True):

            c1, c2 = st.columns([5,1])

            time_disp = ""

            if item.get("time"):
                time_disp = f"<span class='time-badge'>⏰ {item['time']}</span> "

            comments = item.get("comments", [])

            new_badge = ""

            if comments:

                latest_comment = max(
                    comments,
                    key=lambda x: x.get("createdAt", "")
                )

                latest_user = latest_comment.get("userName", "")

                if latest_user != user_name:
                    new_badge = "<span class='new-badge'>NEW</span>"

            c1.markdown(
                f"### {time_disp}{item['title']} {new_badge}",
                unsafe_allow_html=True
            )

            if c2.button("📝", key=f"edit_{item['id']}"):
                st.session_state.edit_id = item["id"]
                st.rerun()

            if item.get("url"):
                st.markdown(f"[🔗 リンク]({item['url']})")

            if item.get("memo"):
                st.info(item["memo"])

            with st.expander("💬 相談・確定"):

                for c in item.get("comments", []):

                    st.write(f"**{c['userName']}**: {c['text']}")

                with st.form(key=f"comment_form_{item['id']}", clear_on_submit=True):

                    cc1, cc2 = st.columns([3,1])

                    new_c = cc1.text_input(
                        "メッセージ",
                        placeholder="メッセージを入力..."
                    )

                    if cc2.form_submit_button("送信") and new_c:

                        get_events_ref().document(item["id"]).update({

                            "comments": firestore.ArrayUnion([{

                                "userName": user_name,
                                "text": new_c,
                                "createdAt": get_jst_now().isoformat()

                            }])

                        })

                        st.rerun()

                st.divider()

                sd = st.date_input(
                    "確定日",
                    value=get_jst_now().date(),
                    key=f"sd_{item['id']}"
                )

                st_time = time_selector_ui(f"fix_{item['id']}")

                if st.button("この日で確定", key=f"fix_btn_{item['id']}"):

                    get_events_ref().document(item['id']).update({

                        "status": "scheduled",
                        "date": str(sd),
                        "time": st_time

                    })

                    st.rerun()

# ==========================================
# タブ2
# ==========================================

with tab2:

    current_date = get_jst_now().date()

    selected_month = st.date_input(
        "表示月",
        value=current_date,
        key="calendar_month_picker"
    )

    year = selected_month.year
    month = selected_month.month

    st.markdown(f"## 📅 {year}年 {month}月")

    cal = calendar.monthcalendar(year, month)

    weekday_labels = ["月", "火", "水", "木", "金", "土", "日"]

    cols = st.columns(7)

    for i, day_name in enumerate(weekday_labels):

        cols[i].markdown(f"### {day_name}")

    for week in cal:

        week_cols = st.columns(7)

        for idx, day in enumerate(week):

            with week_cols[idx]:

                if day == 0:
                    st.empty()
                    continue

                target_date = datetime(year, month, day).date()
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

                event_count = len(day_events)
                ng_count = len(day_ng)

                st.markdown(

                    f"""

                    <div class="calendar-day-box">

                        <div class="calendar-day-header">
                            {day}
                        </div>

                        <div class="calendar-event-count">
                            📍予定 {event_count}件
                        </div>

                        <div class="calendar-ng-count">
                            🚫NG {ng_count}件
                        </div>

                    </div>

                    """,

                    unsafe_allow_html=True

                )

                if event_count > 0 or ng_count > 0:

                    with st.expander(f"{month}/{day} の詳細"):

                        if day_events:

                            st.markdown("### 📍予定")

                            for ev in sorted(day_events, key=lambda x: x.get("time") or ""):

                                time_txt = ev.get("time", "時間未定")

                                st.write(f"• {time_txt} - {ev['title']}")

                        if day_ng:

                            st.markdown("### 🚫NG")

                            for ng in day_ng:

                                ng_time = ng.get("time", "時間未定")

                                st.write(
                                    f"• {ng_time} - {ng.get('userName','')} : {ng.get('reason','')}"
                                )

# ==========================================
# タブ3
# ==========================================

with tab3:

    st.subheader("🚫 NG日を登録")

    nd = st.date_input(
        "行けない日",
        value=get_jst_now().date(),
        key="ng_date_input"
    )

    nt_str = time_selector_ui("ng_add")

    nr = st.text_input("理由など(任意)", key="ng_reason")

    if st.button("NG登録", use_container_width=True, type="primary"):

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

    upcoming_ng = sorted(

        [n for n in ng_dates if n["date"] >= today_str],

        key=lambda x: (
            x["date"],
            x.get("time") or "00:00"
        )

    )

    st.subheader("📍 今後のNG日")

    for n in upcoming_ng:

        with st.container(border=True):

            c1, c2 = st.columns([3,5])

            dt_obj = datetime.strptime(n["date"], "%Y-%m-%d")

            date_with_day = f"{n['date']}({get_weekday_jp(dt_obj)})"

            n_time_str = ""

            if n.get("time"):
                n_time_str = f" <span class='time-badge'>{n['time']}</span>"

            c1.markdown(

                f"<b>{date_with_day}{n_time_str}</b>",
                unsafe_allow_html=True

            )

            c2.markdown(
                f"{n.get('userName','')} : {n.get('reason','')}"
            )
