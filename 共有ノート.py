import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta, timezone, time
import calendar

# ==========================================
# 1. 初期設定とFirebase接続
# ==========================================
st.set_page_config(page_title="ふたりの共有ノート", page_icon="🤝", layout="wide")

# --- セッション状態の初期化 ---
if "font_size" not in st.session_state: st.session_state.font_size = 14
if "current_month" not in st.session_state: st.session_state.current_month = datetime.now(timezone(timedelta(hours=9))).date().replace(day=1)
if "user_color" not in st.session_state: st.session_state.user_color = "#f43f5e" 
if "room_user_colors" not in st.session_state: st.session_state.room_user_colors = {}
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
def get_rooms_ref(): return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_rooms')
def get_ng_data_ref(): return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_ng_dates')

# --- 設定の保存・読込 ---
def save_app_settings():
    if st.session_state.get("room_key"):
        colors = st.session_state.room_user_colors
        colors[st.session_state.user_name] = st.session_state.user_color
        p_save = st.session_state.period_data.copy()
        if p_save["start_date"]: p_save["start_date"] = str(p_save["start_date"])
        if p_save["end_date"]: p_save["end_date"] = str(p_save["end_date"])
        get_rooms_ref().document(st.session_state.room_key).set({
            "settings": {"font_size": st.session_state.font_size, "user_colors": colors, "period_data": p_save}
        }, merge=True)

def load_app_settings(room_key):
    doc = get_rooms_ref().document(room_key).get()
    if doc.exists:
        data = doc.to_dict()
        if "settings" in data:
            s = data["settings"]
            st.session_state.font_size = s.get("font_size", 14)
            st.session_state.room_user_colors = s.get("user_colors", {})
            p_data = s.get("period_data", {})
            if p_data:
                if p_data.get("start_date") and p_data["start_date"] != "None":
                    try: st.session_state.period_data["start_date"] = datetime.strptime(p_data["start_date"], "%Y-%m-%d").date()
                    except: pass
                if p_data.get("end_date") and p_data["end_date"] != "None":
                    try: st.session_state.period_data["end_date"] = datetime.strptime(p_data["end_date"], "%Y-%m-%d").date()
                    except: pass
                st.session_state.period_data.update({k: v for k, v in p_data.items() if k not in ["start_date", "end_date"]})
            if st.session_state.user_name in st.session_state.room_user_colors:
                st.session_state.user_color = st.session_state.room_user_colors[st.session_state.user_name]

# --- 【修正済み】時間選択UI (TypeError防止とUI改善) ---
def time_selector_ui(key_prefix, default_val="カスタム"):
    # default_valがNoneや空文字の場合のガード
    if not default_val:
        default_val = "カスタム"
        
    options = ["終日", "午前中", "午後", "カスタム"]
    
    # 選択肢の初期値を決定
    current_idx = 3 # デフォルトはカスタム
    if default_val in options:
        current_idx = options.index(default_val)
    elif "～" in str(default_val):
        current_idx = 3
    
    t_type = st.selectbox("時間指定", options, index=current_idx, key=f"t_type_{key_prefix}")
    
    if t_type == "カスタム":
        col_c1, col_c2 = st.columns(2)
        # 既存の時間(HH:MM～HH:MM)があれば分解して初期値にする
        start_def = time(10, 0)
        end_def = time(12, 0)
        if "～" in str(default_val):
            try:
                parts = str(default_val).split("～")
                start_def = datetime.strptime(parts[0], "%H:%M").time()
                end_def = datetime.strptime(parts[1], "%H:%M").time()
            except: pass
            
        t_start = col_c1.time_input("開始", value=start_def, key=f"t_start_{key_prefix}", step=900)
        t_end = col_c2.time_input("終了", value=end_def, key=f"t_end_{key_prefix}", step=900)
        return f"{t_start.strftime('%H:%M')}～{t_end.strftime('%H:%M')}"
    return t_type

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
    .period-dot {{ background-color: transparent !important; color: #FF8DA1; border: none !important; font-weight: bold; text-align: center; margin-top: 4px; }}
    .ng-dot {{ background: repeating-linear-gradient(45deg, rgba(128,128,128,0.1), rgba(128,128,128,0.1) 5px, rgba(150,150,150,0.2) 5px, rgba(150,150,150,0.2) 10px); color: var(--text-color); border: 1px solid rgba(128,128,128,0.3); }}
    .time-badge {{ background-color: rgba(128, 128, 128, 0.2); padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }}
</style>
""", unsafe_allow_html=True)

# ログイン・認証
if "is_logged" not in st.session_state:
    q_room, q_user = st.query_params.get("room"), st.query_params.get("user")
    if q_room and q_user:
        st.session_state.room_key, st.session_state.user_name, st.session_state.is_logged = q_room, q_user, True
        load_app_settings(q_room)
    else: st.session_state.is_logged = False

if st.session_state.get("is_logged"):
    st.sidebar.title("🎨 ユーザー設定")
    p_color = st.sidebar.color_picker("テーマカラー", value=st.session_state.user_color)
    if p_color != st.session_state.user_color:
        st.session_state.user_color = p_color; save_app_settings(); st.rerun()
    
    st.sidebar.divider()
    with st.sidebar.expander("🩸 生理日管理設定"):
        p = st.session_state.period_data
        p_start = st.date_input("開始日", value=p.get("start_date") or get_jst_now().date())
        p_end = st.date_input("最終日", value=p.get("end_date") or (p_start + timedelta(days=5)))
        p_cycle = st.selectbox("生理周期", options=list(range(7, 121)), index=list(range(7, 121)).index(p.get("cycle", 28)))
        s_per = st.toggle("生理予定", value=p.get("show_period", True))
        if st.button("設定を保存", use_container_width=True):
            st.session_state.period_data.update({"start_date": p_start, "end_date": p_end, "cycle": p_cycle, "show_period": s_per})
            save_app_settings(); st.rerun()

    st.sidebar.divider()
    st.session_state.font_size = st.sidebar.slider("文字サイズ", 10, 24, value=st.session_state.font_size)
    if st.sidebar.button("ログアウト", use_container_width=True): 
        st.session_state.is_logged = False; st.query_params.clear(); st.rerun()

if not st.session_state.get("is_logged"):
    st.markdown("<h1 style='text-align: center; color: #f43f5e;'>Shared Note Sync</h1>", unsafe_allow_html=True)
    name_in = st.text_input("名前を入力")
    if name_in:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("新しく作る", use_container_width=True):
                k = '-'.join([''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4)) for _ in range(7)])
                get_rooms_ref().document(k).set({'createdAt': get_jst_now().isoformat()})
                st.session_state.room_key, st.session_state.user_name, st.session_state.is_logged = k, name_in, True
                st.query_params["room"], st.query_params["user"] = k, name_in; st.rerun()
        with c2:
            input_k = st.text_input("秘密の鍵を入力")
            if st.button("参加する", use_container_width=True) and len(input_k) >= 29:
                st.session_state.room_key, st.session_state.user_name, st.session_state.is_logged = input_k, name_in, True
                st.query_params["room"], st.query_params["user"] = input_k, name_in; load_app_settings(input_k); st.rerun()
    st.stop()

# データ取得
room_key = st.session_state.room_key
events = [{"id": d.id, **d.to_dict()} for d in get_events_ref().where("roomKey", "==", room_key).stream()]
ng_data = [{"id": d.id, **d.to_dict()} for d in get_ng_data_ref().where("roomKey", "==", room_key).stream()]
today_jst = get_jst_now().date()

# 生理予測 (🌙)
period_dates = {}
p = st.session_state.period_data
if p.get("start_date") and p.get("show_period"):
    for i in range(-1, 4):
        ps = p["start_date"] + timedelta(days=p["cycle"] * i)
        pe = ps + timedelta(days=5)
        curr = ps
        while curr <= pe:
            period_dates.setdefault(str(curr), []).append('<span style="display: inline-block; transform: scaleX(-1); font-size: 1.5em;">🌙</span>')
            curr += timedelta(days=1)

tab1, tab2, tab3, tab4 = st.tabs(["📍 行きたい", "📅 予定一覧", "🗓️ カレンダー", "🚫 NG日"])

# --- タブ1: 行きたい ---
with tab1:
    with st.expander("＋ 追加"):
        t = st.text_input("場所/内容", key="wish_t")
        wt = time_selector_ui("wish_add")
        if st.button("リストに追加", type="primary"):
            if t:
                get_events_ref().add({"roomKey": room_key, "title": t, "status": "wishlist", "time": wt, "createdAt": get_jst_now().isoformat()})
                st.rerun()
    for item in [e for e in events if e.get("status") == "wishlist"]:
        with st.container(border=True):
            st.markdown(f"### {item['title']}")
            if item.get("time"): st.markdown(f"<span class='time-badge'>⏰ {item['time']}</span>", unsafe_allow_html=True)
            with st.expander("💬 相談・確定"):
                sd = st.date_input("確定日", value=today_jst, key=f"sd_{item['id']}")
                st_time = time_selector_ui(f"fix_{item['id']}", default_val=item.get("time", "カスタム"))
                if st.button("確定する", key=f"fbtn_{item['id']}", use_container_width=True):
                    get_events_ref().document(item['id']).update({"status": "scheduled", "date": str(sd), "time": st_time}); st.rerun()

# --- タブ2: 予定一覧 (編集・復元・削除) ---
with tab2:
    sched_items = sorted([e for e in events if e.get("status") == "scheduled"], key=lambda x: x.get("date", ""))
    for item in sched_items:
        with st.container(border=True):
            st.write(f"📅 {item.get('date','')} {item.get('time','')} \n**{item['title']}**")
            
            with st.expander("予定の編集・削除"):
                # 日付変更
                try: current_date = datetime.strptime(item.get('date', str(today_jst)), "%Y-%m-%d").date()
                except: current_date = today_jst
                new_d = st.date_input("日付変更", value=current_date, key=f"edate_{item['id']}")
                
                # 【追加】時間帯変更
                new_t = time_selector_ui(f"etime_{item['id']}", default_val=item.get("time", "カスタム"))
                
                if st.button("変更を保存", key=f"save_{item['id']}", use_container_width=True):
                    get_events_ref().document(item['id']).update({"date": str(new_d), "time": new_t})
                    st.rerun()
                
                st.divider()
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("リストに戻す", key=f"back_{item['id']}", use_container_width=True):
                    get_events_ref().document(item['id']).update({"status": "wishlist", "date": firestore.DELETE_FIELD})
                    st.rerun()
                if col_btn2.button("完全に削除", key=f"del_{item['id']}", use_container_width=True):
                    get_events_ref().document(item['id']).delete(); st.rerun()

# --- タブ3: カレンダー ---
with tab3:
    c_m = st.session_state.current_month
    cm1, cm2, cm3 = st.columns([1, 2, 1])
    if cm1.button("◀ 前月"): st.session_state.current_month = (c_m - timedelta(days=1)).replace(day=1); st.rerun()
    cm2.markdown(f"<center><h3>{c_m.strftime('%Y年 %m月')}</h3></center>", unsafe_allow_html=True)
    if cm3.button("次月 ▶"): st.session_state.current_month = (c_m + timedelta(days=32)).replace(day=1); st.rerun()

    cal_html = '<div class="cal-grid">'
    for w in ["月", "火", "水", "木", "金", "土", "日"]: cal_html += f'<div class="cal-header-item">{w}</div>'
    for week in calendar.Calendar(0).monthdayscalendar(c_m.year, c_m.month):
        for day in week:
            if day == 0: cal_html += '<div></div>'
            else:
                this_d = c_m.replace(day=day); d_str = str(this_d)
                inner = f'<div class="cal-date">{day}</div>'
                for icon in period_dates.get(d_str, []): inner += f'<div class="cal-dot period-dot">{icon}</div>'
                for e in [e for e in events if e.get("date") == d_str]: inner += f'<div class="cal-dot event-dot">📍 {e["title"]}</div>'
                for n in [n for n in ng_data if n.get("date") == d_str]: inner += f'<div class="cal-dot ng-dot">🚫 {n.get("userName")}</div>'
                cal_html += f'<div class="cal-box {"cal-today" if this_d == today_jst else ""}">{inner}</div>'
    st.markdown(cal_html + '</div>', unsafe_allow_html=True)

# --- タブ4: NG日 ---
with tab4:
    nd = st.date_input("日付", value=today_jst, key="ng_in")
    nt = time_selector_ui("ng_time_in")
    if st.button("登録する", type="primary", use_container_width=True):
        get_ng_data_ref().add({"roomKey": room_key, "userName": st.session_state.user_name, "date": str(nd), "time": nt, "createdAt": get_jst_now().isoformat()})
        st.rerun()
