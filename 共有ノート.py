import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta, timezone
import calendar
import requests

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

# --- 生理管理用の初期値 ---
if "period_data" not in st.session_state:
    st.session_state.period_data = {
        "start_date": None, "end_date": None, "cycle": 28,
        "show_period": True, "show_ovulation": False, "show_fertility": False, "show_pms": False
    }

def get_jst_now(): return datetime.now(timezone(timedelta(hours=9)))

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
def get_finances_ref(): return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_finances')

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

# --- 共通UI: 時間選択 ---
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

# --- 天気予報取得 (新宿) ---
@st.cache_data(ttl=3600)
def get_shinjuku_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=35.6895&longitude=139.7005&daily=weathercode,windspeed_10m_max&timezone=Asia%2FTokyo&past_days=7&forecast_days=14"
        res = requests.get(url).json()
        w_map = {}
        for i, date_str in enumerate(res['daily']['time']):
            code = res['daily']['weathercode'][i]; wind = res['daily']['windspeed_10m_max'][i]
            if wind > 20.0: mark = "💨"
            elif code in [0, 1]: mark = "☀️"
            elif code in [2, 3]: mark = "☁️"
            elif code in [45, 48]: mark = "🌫️"
            elif code in [51,53,55,56,57,61,63,65,66,67,80,81,82]: mark = "☔"
            elif code in [71,73,75,77,85,86]: mark = "⛄"
            elif code in [95,96,99]: mark = "⚡"
            else: mark = ""
            w_map[date_str] = mark
        return w_map
    except: return {}

weather_data = get_shinjuku_weather()

# CSS
st.markdown(f"""
<style>
    html, body, [class*="st-"] {{ font-size: {st.session_state.font_size}px !important; }}
    .cal-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; width: 100%; margin-top: 10px; }}
    .cal-header-item {{ text-align: center; font-weight: bold; font-size: 0.8em; padding: 5px 0; background-color: var(--secondary-background-color); color: var(--text-color); border-radius: 4px; }}
    .cal-box {{ border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 4px; padding: 4px; min-height: 85px; background-color: var(--background-color); position: relative; overflow-y: auto; }}
    .cal-date {{ font-size: 0.8em; font-weight: bold; margin-bottom: 2px; color: var(--text-color); }}
    .cal-today {{ border: 2px solid {st.session_state.user_color} !important; background-color: var(--secondary-background-color) !important; }}
    .cal-dot {{ font-size: 0.7em; margin-bottom: 1px; border-radius: 2px; padding: 1px 2px; line-height: 1.1; }}
    .event-dot {{ background-color: rgba(59, 130, 246, 0.2) !important; color: #60a5fa !important; }}
    .period-dot {{ background-color: transparent !important; color: #f43f5e; border: none !important; font-weight: bold; font-size: 1.1em; }}
    .ovulation-dot {{ background-color: transparent !important; color: #a855f7; border: none !important; font-weight: bold; font-size: 1.1em; }}
    .pms-dot {{ background-color: transparent !important; color: #eab308; border: none !important; font-weight: bold; font-size: 1.1em; }}
    .fertility-dot {{ background-color: transparent !important; color: #22c55e; border: none !important; font-weight: bold; font-size: 1.1em; }}
    .ng-dot {{ background: repeating-linear-gradient(45deg, rgba(128, 128, 128, 0.1), rgba(128, 128, 128, 0.1) 5px, rgba(150, 150, 150, 0.2) 5px, rgba(150, 150, 150, 0.2) 10px); color: var(--text-color); border: 1px solid rgba(128, 128, 128, 0.3); }}
    .last-comment {{ font-size: 0.85em; border-left: 4px solid; padding-left: 10px; margin-top: 10px; margin-bottom: 10px; line-height: 1.4; }}
    .time-badge {{ background-color: rgba(128, 128, 128, 0.2); padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }}
    .weather-bg {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 3em; opacity: 0.15; pointer-events: none; z-index: 0; }}
    .expense-dot {{ background-color: transparent !important; color: #ef4444; border: none !important; font-weight: bold; font-size: 0.75em; text-align: right; }}
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
    st.sidebar.title("🎨 設定")
    picked_color = st.sidebar.color_picker("テーマカラー", value=st.session_state.user_color)
    if picked_color != st.session_state.user_color:
        st.session_state.user_color = picked_color; save_app_settings(); st.rerun()
    st.sidebar.divider()
    st.sidebar.title("🩸 生理日管理")
    with st.sidebar.expander("生理管理設定"):
        p = st.session_state.period_data
        p_start = st.date_input("開始日", value=p.get("start_date") or get_jst_now().date())
        p_end = st.date_input("最終日", value=p.get("end_date") or (p_start + timedelta(days=5)))
        p_cycle = st.selectbox("生理周期", options=list(range(7, 121)), index=list(range(7, 121)).index(p.get("cycle", 28)))
        if st.button("設定を保存", use_container_width=True):
            st.session_state.period_data.update({"start_date": p_start, "end_date": p_end, "cycle": p_cycle})
            save_app_settings(); st.rerun()
    st.sidebar.divider()
    st.session_state.font_size = st.sidebar.slider("文字サイズ", 10, 24, value=st.session_state.font_size)
    if st.sidebar.button("ログアウト", use_container_width=True): st.session_state.is_logged = False; st.query_params.clear(); st.rerun()

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

# --- 生理予測ロジック ---
period_dates = {}
def calculate_period_logic():
    p = st.session_state.period_data
    if not p.get("start_date"): return
    base_start = p["start_date"]; duration = (p["end_date"] - p["start_date"]).days + 1 if p.get("end_date") else 5
    for i in range(-1, 4):
        p_start = base_start + timedelta(days=p["cycle"] * i)
        for d in range(duration): period_dates.setdefault(str(p_start + timedelta(days=d)), []).append(("period", "🌙"))
        ovulation_day = (p_start + timedelta(days=p["cycle"])) - timedelta(days=14)
        period_dates.setdefault(str(ovulation_day), []).append(("ovulation", "🥚"))

calculate_period_logic()

def get_latest_activity_time(item):
    comments = item.get("comments", []); return max([c.get('createdAt', '') for c in comments]) if comments else item.get('createdAt', '')

def render_thread_info(item):
    comments = item.get("comments", [])
    if comments:
        last = sorted(comments, key=lambda x: x.get('createdAt', ''))[-1]; color = st.session_state.room_user_colors.get(last['userName'], "#999999")
        st.markdown(f'<div class="last-comment" style="border-color: {color};"><span style="color: {color}; font-weight: bold;">{last["userName"]}</span>: {last["text"]}</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📍 行きたい", "📅 予定一覧", "🗓️ カレンダー", "🚫 NG日"])

# --- タブ1: 行きたい (コメントを左に、編集を右に入れ替え) ---
with tab1:
    with st.expander("＋ 新しい場所を追加"):
        t = st.text_input("場所/内容", key="input_title_wish")
        u = st.text_input("URL (任意)", key="input_url_wish")
        wt = time_selector_ui("wish_add")
        if st.button("リストに追加", type="primary"):
            if t:
                get_events_ref().add({"roomKey": room_key, "title": t, "url": u, "status": "wishlist", "comments": [], "time": wt, "createdAt": get_jst_now().isoformat()}); st.rerun()
    
    wish_items = [e for e in events if e.get("status") == "wishlist"]
    for item in sorted(wish_items, key=get_latest_activity_time, reverse=True):
        with st.container(border=True):
            st.markdown(f"### {item['title']}")
            if item.get("url"): st.link_button("🔗 サイトを見る", item["url"])
            if item.get("time"): st.markdown(f"<span class='time-badge'>⏰ {item['time']}</span>", unsafe_allow_html=True)
            render_thread_info(item)
            
            # --- ここでカラム順を入れ替え ---
            c_msg, c_edit = st.columns(2) 
            
            with c_msg: # 左側：コメントと確定
                with st.expander("💬 コメント・確定"):
                    for c in sorted(item.get("comments", []), key=lambda x: x.get('createdAt', '')):
                        c_user = c.get('userName', '不明'); c_color = st.session_state.room_user_colors.get(c_user, "#999999")
                        st.markdown(f'<div style="font-size: 0.9em; margin-bottom: 5px;"><span style="color: {c_color}; font-weight: bold;">{c_user}</span>: {c.get("text", "")}</div>', unsafe_allow_html=True)
                    c_col1, c_col2 = st.columns([3, 1])
                    new_c = c_col1.text_input("コメント", key=f"nc_{item['id']}", label_visibility="collapsed")
                    if c_col2.button("送信", key=f"ncb_{item['id']}", use_container_width=True):
                        if new_c:
                            c_obj = {"userName": user_name, "text": new_c, "createdAt": get_jst_now().isoformat()}
                            get_events_ref().document(item['id']).update({"comments": firestore.ArrayUnion([c_obj])}); st.rerun()
                    st.divider()
                    st.write("📅 予定を確定する")
                    sd, st_time = st.date_input("確定日", value=today_jst, key=f"sd_{item['id']}"), time_selector_ui(f"fix_{item['id']}")
                    if st.button("カレンダーへ確定", key=f"fbtn_{item['id']}", use_container_width=True):
                        get_events_ref().document(item['id']).update({"status": "scheduled", "date": str(sd), "time": st_time}); st.rerun()

            with c_edit: # 右側：編集と削除
                with st.expander("📝 項目を編集・削除"):
                    et = st.text_input("名称修正", value=item['title'], key=f"etw_{item['id']}")
                    eu = st.text_input("URL修正", value=item.get('url',''), key=f"euw_{item['id']}")
                    if st.button("更新を保存", key=f"ubw_{item['id']}", use_container_width=True):
                        get_events_ref().document(item['id']).update({"title": et, "url": eu}); st.rerun()
                    st.write("---")
                    if st.button("🗑️ この場所を削除", key=f"dbw_{item['id']}", use_container_width=True):
                        get_events_ref().document(item['id']).delete(); st.rerun()

# --- タブ2: 予定一覧 ---
with tab2:
    sched_items = sorted([e for e in events if e.get("status") == "scheduled"], key=lambda x: x["date"])
    for item in sched_items:
        with st.container(border=True):
            st.write(f"📅 {item['date']} {item.get('time','')}")
            st.markdown(f"**{item['title']}**")
            with st.expander("📝 編集・削除"):
                new_title = st.text_input("内容", value=item['title'], key=f"edit_t_{item['id']}")
                new_date = st.date_input("日付", value=datetime.strptime(item['date'], "%Y-%m-%d").date(), key=f"edit_d_{item['id']}")
                new_time = time_selector_ui(f"edit_tm_{item['id']}", default_val=item.get('time', 'カスタム'))
                c_u, c_d = st.columns(2)
                if c_u.button("更新", key=f"save_{item['id']}", use_container_width=True):
                    get_events_ref().document(item['id']).update({"title": new_title, "date": str(new_date), "time": new_time}); st.rerun()
                if c_d.button("🗑️ 削除", key=f"del_{item['id']}", use_container_width=True):
                    get_events_ref().document(item['id']).delete(); st.rerun()

# --- タブ3: カレンダー ---
with tab3:
    finances = [{"id": d.id, **d.to_dict()} for d in get_finances_ref().where("roomKey", "==", room_key).stream()]
    cm1, cm2, cm3 = st.columns([1, 2, 1])
    if cm1.button("◀ 前月"): st.session_state.current_month = (st.session_state.current_month - timedelta(days=1)).replace(day=1); st.rerun()
    cm2.markdown(f"<center><h3>{st.session_state.current_month.strftime('%Y年 %m月')}</h3></center>", unsafe_allow_html=True)
    if cm3.button("次月 ▶"): st.session_state.current_month = (st.session_state.current_month + timedelta(days=32)).replace(day=1); st.rerun()
    
    cal_html = '<div class="cal-grid">'
    for w in ["月", "火", "水", "木", "金", "土", "日"]: cal_html += f'<div class="cal-header-item">{w}</div>'
    month_days = calendar.Calendar(0).monthdayscalendar(st.session_state.current_month.year, st.session_state.current_month.month)
    for week in month_days:
        for day in week:
            if day == 0: cal_html += '<div></div>'
            else:
                this_date = st.session_state.current_month.replace(day=day); date_str = str(this_date)
                inner = f'<div class="cal-date">{day}</div>'
                w_mark = weather_data.get(date_str, ""); 
                if w_mark: inner += f'<div class="weather-bg">{w_mark}</div>'
                for p_type, p_label in period_dates.get(date_str, []): inner += f'<div class="cal-dot {p_type}-dot">{p_label}</div>'
                for e in [e for e in events if e.get("date") == date_str]: inner += f'<div class="cal-dot event-dot">📍 {e["title"]}</div>'
                for n in [n for n in ng_dates if n.get("date") == date_str]: inner += f'<div class="cal-dot ng-dot">🚫 {n.get("userName")}</div>'
                day_expenses = [f['amount'] for f in finances if f.get('date') == date_str]
                if day_expenses: inner += f'<div class="cal-dot expense-dot">💸 -{sum(day_expenses):,}円</div>'
                cal_html += f'<div class="cal-box {"cal-today" if this_date == today_jst else ""}">{inner}</div>'
    st.markdown(cal_html + '</div>', unsafe_allow_html=True)

    # --- 家計簿エリア ---
    st.divider()
    with st.expander("💰 共有貯金・家計簿 (修正・削除もこちら)", expanded=False):
        room_doc = get_rooms_ref().document(room_key).get()
        f_settings = room_doc.to_dict().get("finance_settings", {}) if room_doc.exists else {}
        f_start_date = f_settings.get("start_date", str(today_jst.replace(day=1)))
        f_add_day = f_settings.get("add_day", 1); f_amount = f_settings.get("monthly_amount", 0)
        
        total_added = 0
        if f_amount > 0:
            start_dt = datetime.strptime(f_start_date, "%Y-%m-%d").date(); curr = start_dt.replace(day=1)
            while curr <= today_jst.replace(day=1):
                try: target_date = curr.replace(day=f_add_day)
                except ValueError: target_date = curr.replace(day=28)
                if start_dt <= target_date <= today_jst: total_added += f_amount
                curr = (curr + timedelta(days=32)).replace(day=1)
        
        total_expense = sum([f['amount'] for f in finances]); current_balance = total_added - total_expense
        st.markdown(f"<h3 style='color: #10b981;'>現在の残高: ¥{current_balance:,}</h3>", unsafe_allow_html=True)
        
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("**支出を記録**")
            ex_date = st.date_input("使った日", value=today_jst, key="ex_date")
            ex_amount = st.number_input("金額", min_value=0, step=100, key="ex_amount")
            ex_memo = st.text_input("メモ", key="ex_memo")
            if st.button("記録する", use_container_width=True):
                if ex_amount > 0:
                    get_finances_ref().add({"roomKey": room_key, "date": str(ex_date), "amount": ex_amount, "memo": ex_memo, "createdAt": get_jst_now().isoformat()}); st.rerun()
        with fc2:
            st.markdown("**積立設定**")
            set_start = st.date_input("開始日", value=datetime.strptime(f_start_date, "%Y-%m-%d").date(), key="set_start")
            set_day = st.number_input("毎月の加算日", 1, 28, value=f_add_day, key="set_day")
            set_amount = st.number_input("毎月の積立額", 0, step=1000, value=f_amount, key="set_amount")
            if st.button("設定保存", use_container_width=True):
                get_rooms_ref().document(room_key).set({"finance_settings": {"start_date": str(set_start), "add_day": set_day, "monthly_amount": set_amount}}, merge=True); st.rerun()
                
        st.markdown("**支出の履歴・修正**")
        for f in sorted(finances, key=lambda x: x['date'], reverse=True):
            with st.expander(f"💸 {f['date']} : -{f['amount']:,}円 ({f.get('memo', 'メモなし')})"):
                ed = st.date_input("日付修正", value=datetime.strptime(f['date'], "%Y-%m-%d").date(), key=f"edf_{f['id']}")
                ea = st.number_input("金額修正", value=f['amount'], step=100, key=f"eaf_{f['id']}")
                em = st.text_input("メモ修正", value=f.get('memo',''), key=f"emf_{f['id']}")
                col_u, col_d = st.columns(2)
                if col_u.button("更新", key=f"ubf_{f['id']}", use_container_width=True):
                    get_finances_ref().document(f['id']).update({"date": str(ed), "amount": ea, "memo": em}); st.rerun()
                if col_d.button("削除", key=f"dbf_{f['id']}", use_container_width=True):
                    get_finances_ref().document(f['id']).delete(); st.rerun()

# --- タブ4: NG日 ---
with tab4:
    nd, nt = st.date_input("日付", value=today_jst, key="ng_in"), time_selector_ui("ng_time_in")
    if st.button("NG登録", type="primary", use_container_width=True):
        get_ng_ref().add({"roomKey": room_key, "userName": user_name, "date": str(nd), "time": nt, "createdAt": get_jst_now().isoformat()}); st.rerun()
