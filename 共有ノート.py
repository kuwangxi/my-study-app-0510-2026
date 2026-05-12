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
# セッション
# ==========================================

if "font_size" not in st.session_state:
    st.session_state.font_size = 14

if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

if "is_logged" not in st.session_state:
    st.session_state.is_logged = False

if "input_title" not in st.session_state:
    st.session_state.input_title = ""

if "input_url" not in st.session_state:
    st.session_state.input_url = ""

if "input_memo" not in st.session_state:
    st.session_state.input_memo = ""

if "ng_reason" not in st.session_state:
    st.session_state.ng_reason = ""

# ==========================================
# 共通関数
# ==========================================

def get_jst_now():
    return datetime.now(timezone(timedelta(hours=9)))

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

            cred_dict["private_key"] = cred_dict["private_key"].replace(
                "\\n",
                "\n"
            )

        cred = credentials.Certificate(cred_dict)

        firebase_admin.initialize_app(cred)

    except Exception as e:

        st.error(f"Firebase認証エラー: {e}")
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

.past-item {{
    color: #9e9e9e;
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

.calendar-root {{
    margin-top: 10px;
}}

.calendar-week-header {{
    text-align: center;
    font-weight: bold;
    color: #999;
    margin-bottom: 8px;
}}

.calendar-cell {{
    border: 1px solid rgba(255,255,255,0.05);
    min-height: 120px;
    border-radius: 12px;
    padding: 6px;
    margin-bottom: 8px;
    background: rgba(255,255,255,0.02);
}}

.calendar-day-number {{
    font-size: 15px;
    font-weight: bold;
    margin-bottom: 8px;
}}

.calendar-today-number {{
    background: white;
    color: black;
    width: 28px;
    height: 28px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
}}

.calendar-event-pill {{
    background: #16a34a;
    color: white;
    padding: 3px 8px;
    border-radius: 6px;
    margin-bottom: 4px;
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.calendar-ng-pill {{
    background: #dc2626;
    color: white;
    padding: 3px 8px;
    border-radius: 6px;
    margin-bottom: 4px;
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.calendar-more {{
    color: #aaa;
    font-size: 11px;
    margin-top: 4px;
}}

</style>

""", unsafe_allow_html=True)

# ==========================================
# 時間選択
# ==========================================

def time_selector_ui(key_prefix):

    t_type = st.selectbox(
        "時間指定",
        ["指定なし", "午前中", "午後", "終日", "カスタム"],
        key=f"t_type_{key_prefix}"
    )

    if t_type == "カスタム":

        col1, col2 = st.columns(2)

        t_start = col1.time_input(
            "開始",
            value=get_jst_now().time(),
            key=f"t_start_{key_prefix}"
        )

        t_end = col2.time_input(
            "終了",
            value=(get_jst_now() + timedelta(hours=2)).time(),
            key=f"t_end_{key_prefix}"
        )

        return f"{t_start.strftime('%H:%M')}～{t_end.strftime('%H:%M')}"

    return None if t_type == "指定なし" else t_type

# ==========================================
# ログイン
# ==========================================

if not st.session_state.is_logged:

    st.title("🤝 Shared Note Sync")

    user_name = st.text_input("表示名")

    room_key = st.text_input("ルームキー")

    col1, col2 = st.columns(2)

    with col1:

        if st.button("新規作成", use_container_width=True):

            if user_name:

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
                st.session_state.user_name = user_name
                st.session_state.is_logged = True

                st.rerun()

    with col2:

        if st.button("参加", use_container_width=True):

            if user_name and room_key:

                st.session_state.room_key = room_key
                st.session_state.user_name = user_name
                st.session_state.is_logged = True

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

    with st.expander("＋追加"):

        t = st.text_input("場所/内容")

        u = st.text_input("URL")

        m = st.text_area("メモ")

        wt = time_selector_ui("wish")

        if st.button("追加", type="primary"):

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

                st.rerun()

    wishlist_items = [
        e for e in events
        if e.get("status") == "wishlist"
    ]

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

            if item.get("url"):

                st.markdown(f"[🔗 リンク]({item['url']})")

            if item.get("memo"):

                st.info(item["memo"])

            with st.expander("💬 相談・確定"):

                for c in comments:

                    st.write(f"**{c['userName']}** : {c['text']}")

                with st.form(
                    key=f"comment_form_{item['id']}",
                    clear_on_submit=True
                ):

                    cc1, cc2 = st.columns([3,1])

                    new_c = cc1.text_input("メッセージ")

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

                if st.button(
                    "この日で確定",
                    key=f"fix_btn_{item['id']}"
                ):

                    get_events_ref().document(item["id"]).update({

                        "status": "scheduled",
                        "date": str(sd),
                        "time": st_time

                    })

                    st.rerun()

# ==========================================
# 予定
# ==========================================

with tab2:

    sched = [

        e for e in events
        if e.get("status") == "scheduled"

    ]

    upcoming = sorted(

        sched,

        key=lambda x: (
            x.get("date", ""),
            x.get("time") or ""
        )

    )

    st.subheader("📅 予定一覧")

    if not upcoming:

        st.write("予定はありません")

    for item in upcoming:

        with st.container(border=True):

            date_str = item.get("date", "")

            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")

            date_with_day = f"{date_str}({get_weekday_jp(dt_obj)})"

            time_str = item.get("time", "時間未定")

            st.markdown(f"### 📅 {date_with_day}")
            st.write(f"⏰ {time_str}")
            st.write(f"📍 {item.get('title','')}")

# ==========================================
# NG日
# ==========================================

with tab3:

    st.subheader("🚫 NG日登録")

    nd = st.date_input(
        "行けない日",
        value=get_jst_now().date()
    )

    nt = time_selector_ui("ng")

    nr = st.text_input("理由")

    if st.button("NG登録", type="primary"):

        get_ng_ref().add({

            "roomKey": room_key,
            "userName": user_name,
            "date": str(nd),
            "reason": nr,
            "time": nt

        })

        st.rerun()

    st.divider()

    upcoming_ng = sorted(

        ng_dates,

        key=lambda x: (
            x.get("date", ""),
            x.get("time") or ""
        )

    )

    for n in upcoming_ng:

        with st.container(border=True):

            st.write(f"📅 {n.get('date','')}")
            st.write(f"⏰ {n.get('time','時間未定')}")
            st.write(f"🚫 {n.get('reason','')}")

# ==========================================
# カレンダー
# ==========================================

with tab4:

    current_date = get_jst_now().date()

    selected_month = st.date_input(
        "表示月",
        value=current_date,
        key="calendar_month_picker"
    )

    year = selected_month.year
    month = selected_month.month

    st.markdown(f"# {year}年{month}月")

    cal = calendar.monthcalendar(year, month)

    weekday_labels = ["月", "火", "水", "木", "金", "土", "日"]

    header_cols = st.columns(7)

    for i, day_name in enumerate(weekday_labels):

        header_cols[i].markdown(
            f"<div class='calendar-week-header'>{day_name}</div>",
            unsafe_allow_html=True
        )

    for week in cal:

        cols = st.columns(7)

        for idx, day in enumerate(week):

            with cols[idx]:

                if day == 0:

                    st.empty()
                    continue

                target_date = datetime(year, month, day).date()

                target_str = str(target_date)

                is_today = target_date == current_date

                day_events = [

                    e for e in events

                    if e.get("status") == "scheduled"
                    and e.get("date") == target_str

                ]

                day_ng = [

                    n for n in ng_dates

                    if n.get("date") == target_str

                ]

                day_html = ""

                if is_today:

                    day_html += f"""
                    <div class='calendar-day-number'>
                        <div class='calendar-today-number'>
                            {day}
                        </div>
                    </div>
                    """

                else:

                    day_html += f"""
                    <div class='calendar-day-number'>
                        {day}
                    </div>
                    """

                visible_count = 0

                sorted_events = sorted(
                    day_events,
                    key=lambda x: x.get("time") or ""
                )

                for ev in sorted_events[:3]:

                    title = ev.get("title", "")

                    day_html += f"""
                    <div class='calendar-event-pill'>
                        {title}
                    </div>
                    """

                    visible_count += 1

                for ng in day_ng[:2]:

                    reason = ng.get("reason", "NG")

                    day_html += f"""
                    <div class='calendar-ng-pill'>
                        🚫 {reason}
                    </div>
                    """

                    visible_count += 1

                total_items = len(day_events) + len(day_ng)

                if total_items > visible_count:

                    remain = total_items - visible_count

                    day_html += f"""
                    <div class='calendar-more'>
                        +{remain}件
                    </div>
                    """

                st.markdown(

                    f"""
                    <div class='calendar-cell'>
                        {day_html}
                    </div>
                    """,

                    unsafe_allow_html=True

                )

                if day_events or day_ng:

                    with st.expander(f"{month}/{day} の詳細"):

                        if day_events:

                            st.markdown("### 📍予定")

                            for ev in sorted_events:

                                t = ev.get("time", "時間未定")

                                st.write(
                                    f"• {t} - {ev.get('title','')}"
                                )

                        if day_ng:

                            st.markdown("### 🚫 NG")

                            for ng in day_ng:

                                t = ng.get("time", "時間未定")

                                st.write(
                                    f"• {t} - {ng.get('userName','')} : {ng.get('reason','')}"
                                )
