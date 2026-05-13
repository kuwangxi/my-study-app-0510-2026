import streamlit as st

import firebase_admin

from firebase_admin import credentials, firestore

import random

from datetime import datetime, timedelta, timezone

import calendar



# ==========================================

# 1. 初期設定とFirebase接続

# ==========================================

st.set_page_config(page_title="ふたりの共有ノート", page_icon="🤝", layout="wide")



# --- セッション状態の初期化 ---

if "font_size" not in st.session_state: st.session_state.font_size = 14

if "edit_id" not in st.session_state: st.session_state.edit_id = None

if "current_month" not in st.session_state: st.session_state.current_month = datetime.now(timezone(timedelta(hours=9))).date().replace(day=1)

if "user_color" not in st.session_state: st.session_state.user_color = "#f43f5e" 

if "room_user_colors" not in st.session_state: st.session_state.room_user_colors = {}

if "sort_option" not in st.session_state: st.session_state.sort_option = "コメント最新順"



# --- 生理管理用の初期値 (全項目復元) ---

if "period_data" not in st.session_state:

    st.session_state.period_data = {

        "start_date": None, "end_date": None, "cycle": 28,

        "show_period": True, "show_ovulation": False, "show_fertility": False, "show_pms": False

    }



# 入力リセット用

if "input_title" not in st.session_state: st.session_state.input_title = ""

if "input_url" not in st.session_state: st.session_state.input_url = ""

if "input_memo" not in st.session_state: st.session_state.input_memo = ""

if "clear_wish_inputs" not in st.session_state: st.session_state.clear_wish_inputs = False



if st.session_state.clear_wish_inputs:

    st.session_state.input_title = ""; st.session_state.input_url = ""; st.session_state.input_memo = ""

    st.session_state.clear_wish_inputs = False



def get_jst_now(): return datetime.now(timezone(timedelta(hours=9)))

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

        st.error(f"Firebaseの認証エラー: {e}"); st.stop()



db = firestore.client()

APP_ID = "couple-secure-v2"



def get_events_ref(): return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_events')

def get_ng_ref(): return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_ng_dates')

def get_rooms_ref(): return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_rooms')



# --- 設定の保存・読込 ---

def save_app_settings():

    if st.session_state.get("room_key"):

        colors = st.session_state.room_user_colors

        colors[st.session_state.user_name] = st.session_state.user_color

        p_save = st.session_state.period_data.copy()

        if p_save["start_date"]: p_save["start_date"] = str(p_save["start_date"])

        if p_save["end_date"]: p_save["end_date"] = str(p_save["end_date"])

        get_rooms_ref().document(st.session_state.room_key).set({

            "settings": {"font_size": st.session_state.font_size, "user_colors": colors, "sort_option": st.session_state.sort_option, "period_data": p_save}

        }, merge=True)



def load_app_settings(room_key):

    doc = get_rooms_ref().document(room_key).get()

    if doc.exists:

        data = doc.to_dict()

        if "settings" in data:

            s = data["settings"]

            st.session_state.font_size = s.get("font_size", 14)

            st.session_state.room_user_colors = s.get("user_colors", {})

            st.session_state.sort_option = s.get("sort_option", "コメント最新順")

            p_data = s.get("period_data", {})

            if p_data:

                if p_data.get("start_date") and p_data["start_date"] != "None":

                    p_data["start_date"] = datetime.strptime(p_data["start_date"], "%Y-%m-%d").date()

                else: p_data["start_date"] = None

                if p_data.get("end_date") and p_data["end_date"] != "None":

                    p_data["end_date"] = datetime.strptime(p_data["end_date"], "%Y-%m-%d").date()

                else: p_data["end_date"] = None

                st.session_state.period_data.update(p_data)

            if st.session_state.user_name in st.session_state.room_user_colors:

                st.session_state.user_color = st.session_state.room_user_colors[st.session_state.user_name]



# --- 共通UI: 時間選択 (デフォルトはカスタム) ---

def time_selector_ui(key_prefix, default_val="カスタム"):

    options = ["終日", "午前中", "午後", "カスタム"]

    idx = options.index(default_val) if default_val in options else 3

    t_type = st.selectbox("時間指定", options, index=idx, key=f"t_type_{key_prefix}")

    if t_type == "カスタム":

        col_c1, col_c2 = st.columns(2)

        t_start = col_c1.time_input("開始", value=get_jst_now().time(), key=f"t_start_{key_prefix}")

        t_end = col_c2.time_input("終了", value=(get_jst_now() + timedelta(hours=2)).time(), key=f"t_end_{key_prefix}")

        return f"{t_start.strftime('%H:%M')}～{t_end.strftime('%H:%M')}"

    return t_type



# CSS (視認性向上のためテーマ変数を使用しつつデザインを復元)

st.markdown(f"""

<style>

    html, body, [class*="st-"] {{ font-size: {st.session_state.font_size}px !important; }}

    

    .cal-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; width: 100%; margin-top: 10px; }}

    

    /* 曜日ヘッダー: ライトモードでの黒潰れを防止 */

    .cal-header-item {{ 

        text-align: center; font-weight: bold; font-size: 0.8em; padding: 5px 0; 

        background-color: var(--secondary-background-color); 

        color: var(--text-color);

        border-radius: 4px; 

    }}

    

    /* 日付ボックス: 背景と枠線をテーマに追従 */

    .cal-box {{ 

        border: 1px solid rgba(128, 128, 128, 0.3); 

        border-radius: 4px; padding: 4px; min-height: 85px; 

        background-color: var(--background-color); 

        position: relative; overflow-y: auto; 

    }}

    

    .cal-date {{ font-size: 0.8em; font-weight: bold; margin-bottom: 2px; color: var(--text-color); }}

    

    .cal-today {{ 

        border: 2px solid {st.session_state.user_color} !important; 

        background-color: var(--secondary-background-color) !important; 

    }}

    

    .cal-dot {{ font-size: 0.7em; margin-bottom: 1px; border-radius: 2px; padding: 1px 2px; line-height: 1.1; }}

    

    /* 📍予定の背景色を復元 */

    .event-dot {{

        background-color: rgba(59, 130, 246, 0.2) !important;

        color: #60a5fa !important;

    }}

    

    /* 生理関連: 背景色なし、文字色のみ */

    .period-dot {{ background-color: transparent !important; color: #f43f5e; border: none !important; font-weight: bold; }}

    .ovulation-dot {{ background-color: transparent !important; color: #a855f7; border: none !important; font-weight: bold; }}

    .pms-dot {{ background-color: transparent !important; color: #eab308; border: none !important; font-weight: bold; }}

    .fertility-dot {{ background-color: transparent !important; color: #22c55e; border: none !important; font-weight: bold; }}

    

    /* NG日: ストライプを復元しつつライトモード対応 */

    .ng-dot {{ 

        background: repeating-linear-gradient(

            45deg,

            rgba(128, 128, 128, 0.1),

            rgba(128, 128, 128, 0.1) 5px,

            rgba(150, 150, 150, 0.2) 5px,

            rgba(150, 150, 150, 0.2) 10px

        );

        color: var(--text-color); 

        border: 1px solid rgba(128, 128, 128, 0.3);

    }}



    .last-comment {{ font-size: 0.85em; border-left: 4px solid; padding-left: 10px; margin-top: 10px; margin-bottom: 10px; line-height: 1.4; }}

    .time-badge {{ background-color: rgba(128, 128, 128, 0.2); padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }}

</style>

""", unsafe_allow_html=True)



# ==========================================

# 2. ログイン処理

# ==========================================

if "is_logged" not in st.session_state:

    q_room, q_user = st.query_params.get("room"), st.query_params.get("user")

    if q_room and q_user:

        st.session_state.room_key, st.session_state.user_name, st.session_state.is_logged = q_room, q_user, True

        load_app_settings(q_room)

    else: st.session_state.is_logged = False



def login_action(room, user):

    st.session_state.room_key, st.session_state.user_name, st.session_state.is_logged = room, user, True

    st.query_params["room"], st.query_params["user"] = room, user

    load_app_settings(room)



if st.session_state.get("is_logged"):

    st.sidebar.title("🎨 ユーザー設定")

    picked_color = st.sidebar.color_picker("テーマカラー", value=st.session_state.user_color)

    if picked_color != st.session_state.user_color:

        st.session_state.user_color = picked_color; save_app_settings(); st.rerun()

    

    st.sidebar.divider()

    st.sidebar.title("🩸 生理日管理")

    with st.sidebar.expander("設定を復元"):

        p = st.session_state.period_data

        p_start = st.date_input("開始日", value=p.get("start_date") or get_jst_now().date())

        p_end = st.date_input("最終日", value=p.get("end_date") or (p_start + timedelta(days=5)))

        cycle_options = list(range(7, 121))

        p_cycle = st.selectbox("生理周期", options=cycle_options, index=cycle_options.index(p.get("cycle", 28)))

        

        s_per = st.toggle("生理予定", value=p.get("show_period", True))

        s_ovu = st.toggle("排卵日", value=p.get("show_ovulation", False))

        s_fer = st.toggle("妊娠可能性", value=p.get("show_fertility", False))

        s_pms = st.toggle("PMS期間", value=p.get("show_pms", False))

        

        if st.button("設定を保存", use_container_width=True):

            st.session_state.period_data.update({

                "start_date": p_start, "end_date": p_end, "cycle": p_cycle,

                "show_period": s_per, "show_ovulation": s_ovu, "show_fertility": s_fer, "show_pms": s_pms

            })

            save_app_settings(); st.rerun()



    st.sidebar.divider()

    st.session_state.font_size = st.sidebar.slider("文字サイズ", 10, 24, value=st.session_state.font_size)

    if st.sidebar.button("ログアウト", use_container_width=True): 

        st.session_state.is_logged = False; st.query_params.clear(); st.rerun()



if not st.session_state.get("is_logged"):

    st.markdown("<h1 style='text-align: center; color: #f43f5e;'>Shared Note Sync</h1>", unsafe_allow_html=True)

    name_input = st.text_input("名前を入力")

    if name_input:

        col1, col2 = st.columns(2)

        with col1:

            if st.button("新しく作る", use_container_width=True):

                new_key = '-'.join([''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4)) for _ in range(7)])

                get_rooms_ref().document(new_key).set({'createdAt': get_jst_now().isoformat()})

                login_action(new_key, name_input); st.rerun()

        with col2:

            input_key = st.text_input("秘密の鍵を入力")

            if st.button("参加する", use_container_width=True) and len(input_key) >= 29:

                login_action(input_key, name_input); st.rerun()

    st.stop()



# ==========================================

# 3. メイン処理

# ==========================================

room_key, user_name = st.session_state.room_key, st.session_state.user_name

events = [{"id": d.id, **d.to_dict()} for d in get_events_ref().where("roomKey", "==", room_key).stream()]

ng_dates = [{"id": d.id, **d.to_dict()} for d in get_ng_ref().where("roomKey", "==", room_key).stream()]

today_jst = get_jst_now().date()



# --- 生理予測計算ロジック (完全復元) ---

period_dates = {}

def calculate_period_logic():

    p = st.session_state.period_data

    if not p.get("start_date"): return

    base_start = p["start_date"]

    duration = (p["end_date"] - p["start_date"]).days + 1 if p.get("end_date") else 5

    for i in range(-1, 4):

        p_start = base_start + timedelta(days=p["cycle"] * i)

        p_end = p_start + timedelta(days=max(0, duration - 1))

        if p["show_period"]:

            curr = p_start

            while curr <= p_end:

                period_dates.setdefault(str(curr), []).append(("period", "🩸 生理予定"))

                curr += timedelta(days=1)

        if p["show_pms"]:

            for d in range(1, 8):

                pms_day = p_start - timedelta(days=d)

                period_dates.setdefault(str(pms_day), []).append(("pms", "🐥 PMS期間"))

        next_start = p_start + timedelta(days=p["cycle"])

        ovulation_day = next_start - timedelta(days=14)

        if p["show_ovulation"]:

            period_dates.setdefault(str(ovulation_day), []).append(("ovulation", "🥚 排卵日"))

        if p["show_fertility"]:

            for d in range(-5, 2):

                fer_day = ovulation_day + timedelta(days=d)

                period_dates.setdefault(str(fer_day), []).append(("fertility", "💖 妊娠可能性"))



calculate_period_logic()



def get_latest_activity_time(item):

    comments = item.get("comments", [])

    return max([c.get('createdAt', '') for c in comments]) if comments else item.get('createdAt', '')



def render_thread_info(item):

    comments = item.get("comments", [])

    if comments:

        last = sorted(comments, key=lambda x: x.get('createdAt', ''))[-1]

        color = st.session_state.room_user_colors.get(last['userName'], "#999999")

        st.markdown(f'<div class="last-comment" style="border-color: {color};"><span style="color: {color}; font-weight: bold;">{last["userName"]}</span>: {last["text"]}</div>', unsafe_allow_html=True)



tab1, tab2, tab3, tab4 = st.tabs(["📍 行きたい", "📅 予定一覧", "🗓️ カレンダー", "🚫 NG日"])



# --- タブ1: 行きたい ---

with tab1:

    with st.expander("＋ 追加"):

        t = st.text_input("場所/内容", key="input_title")

        wt = time_selector_ui("wish_add") # デフォルトカスタム

        if st.button("リストに追加", type="primary"):

            if t:

                get_events_ref().add({"roomKey": room_key, "title": t, "status": "wishlist", "comments": [], "time": wt, "createdAt": get_jst_now().isoformat()})

                st.rerun()

    wish_items = [e for e in events if e.get("status") == "wishlist"]

    for item in sorted(wish_items, key=get_latest_activity_time, reverse=True):

        with st.container(border=True):

            st.markdown(f"### {item['title']}")

            if item.get("time"): st.markdown(f"<span class='time-badge'>⏰ {item['time']}</span>", unsafe_allow_html=True)

            render_thread_info(item)

            with st.expander("💬 相談・確定"):

                sd, st_time = st.date_input("確定日", value=today_jst, key=f"sd_{item['id']}"), time_selector_ui(f"fix_{item['id']}")

                if st.button("確定する", key=f"fbtn_{item['id']}", use_container_width=True):

                    get_events_ref().document(item['id']).update({"status": "scheduled", "date": str(sd), "time": st_time}); st.rerun()



# --- タブ2: 予定一覧 ---

with tab2:

    sched_items = sorted([e for e in events if e.get("status") == "scheduled"], key=lambda x: x["date"])

    for item in sched_items:

        with st.container(border=True):

            st.write(f"📅 {item['date']} {item.get('time','')} \n**{item['title']}**")



# --- タブ3: カレンダー ---

with tab3:

    cm1, cm2, cm3 = st.columns([1, 2, 1])

    if cm1.button("◀ 前月"): st.session_state.current_month = (st.session_state.current_month - timedelta(days=1)).replace(day=1); st.rerun()

    cm2.markdown(f"<center><h3>{st.session_state.current_month.strftime('%Y年 %m月')}</h3></center>", unsafe_allow_html=True)

    if cm3.button("次月 ▶"): st.session_state.current_month = (st.session_state.current_month + timedelta(days=32)).replace(day=1); st.rerun()



    cal_html = '<div class="cal-grid">'

    for w in ["月", "火", "水", "木", "金", "土", "日"]: cal_html += f'<div class="cal-header-item">{w}</div>'

    

    cal_obj = calendar.Calendar(firstweekday=0)

    month_days = cal_obj.monthdayscalendar(st.session_state.current_month.year, st.session_state.current_month.month)

    

    for week in month_days:

        for day in week:

            if day == 0: cal_html += '<div></div>'

            else:

                this_date = st.session_state.current_month.replace(day=day)

                date_str = str(this_date)

                is_today = (this_date == today_jst)

                inner = f'<div class="cal-date">{day}</div>'

                # 生理情報の描画

                for p_type, p_label in period_dates.get(date_str, []):

                    inner += f'<div class="cal-dot {p_type}-dot">{p_label}</div>'

                # 📍予定の描画 (背景色ありを復元)

                for e in [e for e in events if e.get("date") == date_str]:

                    inner += f'<div class="cal-dot event-dot">📍 {e["title"]}</div>'

                # 🚫NG日の描画

                for n in [n for n in ng_dates if n.get("date") == date_str]:

                    inner += f'<div class="cal-dot ng-dot">🚫 {n.get("userName")}</div>'

                cal_html += f'<div class="cal-box {"cal-today" if is_today else ""}">{inner}</div>'

    st.markdown(cal_html + '</div>', unsafe_allow_html=True)



# --- タブ4: NG日 ---

with tab4:

    nd, nt = st.date_input("日付", value=today_jst, key="ng_in"), time_selector_ui("ng_time_in")

    if st.button("登録する", type="primary", use_container_width=True):

        get_ng_ref().add({"roomKey": room_key, "userName": user_name, "date": str(nd), "time": nt, "createdAt": get_jst_now().isoformat()}); st.rerun()
