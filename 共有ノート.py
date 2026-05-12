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

# --- 生理管理用の初期値 ---
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

# CSS (視認性向上のためテーマ変数を使用)
st.markdown(f"""
<style>
    html, body, [class*="st-"] {{ font-size: {st.session_state.font_size}px !important; }}
    
    /* カレンダー全体のグリッド設定 */
    .cal-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; width: 100%; margin-top: 10px; }}
    
    /* ヘッダー(曜日)部分: テーマに応じた背景色と文字色 */
    .cal-header-item {{ 
        text-align: center; font-weight: bold; font-size: 0.8em; padding: 5px 0; 
        background-color: var(--secondary-background-color); 
        color: var(--text-color);
        border-radius: 4px; 
    }}
    
    /* 日付ボックス: 背景色をテーマに合わせ、枠線を薄いグレーに */
    .cal-box {{ 
        border: 1px solid rgba(128, 128, 128, 0.3); 
        border-radius: 4px; padding: 4px; min-height: 85px; 
        background-color: var(--background-color); 
        color: var(--text-color);
        position: relative; overflow-y: auto; 
    }}
    
    .cal-date {{ font-size: 0.8em; font-weight: bold; margin-bottom: 2px; color: var(--text-color); }}
    
    /* 今日のハイライト */
    .cal-today {{ 
        border: 2px solid {st.session_state.user_color} !important; 
        background-color: var(--secondary-background-color) !important; 
    }}
    
    .cal-dot {{ font-size: 0.7em; margin-bottom: 1px; border-radius: 2px; padding: 1px 2px; line-height: 1.1; }}
    
    /* 生理関連: 背景なし、文字色のみ固定 */
    .period-dot {{ background-color: transparent !important; color: #f43f5e; border: none !important; font-weight: bold; }}
    .ovulation-dot {{ background-color: transparent !important; color: #a855f7; border: none !important; font-weight: bold; }}
    .pms-dot {{ background-color: transparent !important; color: #eab308; border: none !important; font-weight: bold; }}
    .fertility-dot {{ background-color: transparent !important; color: #22c55e; border: none !important; font-weight: bold; }}
    
    /* NG日: 背景をテーマに関わらず視認可能な薄いストライプに */
    .ng-dot {{ 
        background: repeating-linear-gradient(45deg, rgba(128,128,128,0.1), rgba(128,128,128,0.1) 5px, rgba(150,150,150,0.15) 5px, rgba(150,150,150,0.15) 10px);
        color: var(--text-color); 
        border: 1px solid rgba(128, 128, 128, 0.3);
        opacity: 0.8;
    }}

    .last-comment {{ font-size: 0.85em; border-left: 4px solid; padding-left: 10px; margin-top: 10px; margin-bottom: 10px; line-height: 1.4; }}
    .time-badge {{ background-color: rgba(128, 128, 128, 0.2); padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ログイン・メインロジック
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
    
    with st.sidebar.expander("🩸 生理管理"):
        p = st.session_state.period_data
        p_start = st.date_input("開始日", value=p.get("start_date") or get_jst_now().date())
        p_end = st.date_input("最終日", value=p.get("end_date") or (p_start + timedelta(days=5)))
        cycle_options = list(range(7, 121))
        p_cycle = st.selectbox("周期", options=cycle_options, index=cycle_options.index(p.get("cycle", 28)))
        s_per = st.toggle("生理予定", value=p.get("show_period", True))
        s_ovu = st.toggle("排卵日", value=p.get("show_ovulation", False))
        if st.button("保存", use_container_width=True):
            st.session_state.period_data.update({"start_date": p_start, "end_date": p_end, "cycle": p_cycle, "show_period": s_per, "show_ovulation": s_ovu})
            save_app_settings(); st.rerun()

    st.session_state.font_size = st.sidebar.slider("文字サイズ", 10, 24, value=st.session_state.font_size)
    if st.sidebar.button("ログアウト", use_container_width=True): 
        st.session_state.is_logged = False; st.query_params.clear(); st.rerun()

if not st.session_state.get("is_logged"):
    st.title("Shared Note Sync")
    name_input = st.text_input("名前")
    if name_input:
        if st.button("新しく作る"):
            new_key = '-'.join([''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4)) for _ in range(7)])
            get_rooms_ref().document(new_key).set({'createdAt': get_jst_now().isoformat()})
            login_action(new_key, name_input); st.rerun()
        input_key = st.text_input("鍵を入力")
        if st.button("参加する") and len(input_key) >= 29:
            login_action(input_key, name_input); st.rerun()
    st.stop()

# データの取得と描画
room_key, user_name = st.session_state.room_key, st.session_state.user_name
events = [{"id": d.id, **d.to_dict()} for d in get_events_ref().where("roomKey", "==", room_key).stream()]
ng_dates = [{"id": d.id, **d.to_dict()} for d in get_ng_ref().where("roomKey", "==", room_key).stream()]
today_jst = get_jst_now().date()

# 生理計算(一部略)
period_dates = {}
p = st.session_state.period_data
if p.get("start_date"):
    for i in range(-1, 3):
        ps = p["start_date"] + timedelta(days=p["cycle"] * i)
        if p["show_period"]:
            for d in range(5): period_dates[str(ps + timedelta(days=d))] = [("period", "🩸")]

tab1, tab2, tab3, tab4 = st.tabs(["📍 行きたい", "📅 予定一覧", "🗓️ カレンダー", "🚫 NG日"])

with tab1:
    with st.expander("＋ 追加"):
        t = st.text_input("場所", key="wish_t")
        wt = time_selector_ui("wish_add") # デフォルトカスタム
        if st.button("追加", type="primary"):
            get_events_ref().add({"roomKey": room_key, "title": t, "status": "wishlist", "time": wt, "comments": [], "createdAt": get_jst_now().isoformat()})
            st.rerun()
    for item in [e for e in events if e.get("status") == "wishlist"]:
        with st.container(border=True):
            st.write(f"**{item.get('time','')} {item['title']}**")
            sd = st.date_input("確定日", key=f"d_{item['id']}")
            st_time = time_selector_ui(f"f_{item['id']}")
            if st.button("確定", key=f"b_{item['id']}"):
                get_events_ref().document(item['id']).update({"status": "scheduled", "date": str(sd), "time": st_time}); st.rerun()

with tab2:
    for item in sorted([e for e in events if e.get("status") == "scheduled"], key=lambda x: x["date"]):
        st.write(f"{item['date']} : {item['title']} ({item.get('time','')})")

with tab3:
    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    if col_c1.button("◀ 前月"): st.session_state.current_month = (st.session_state.current_month - timedelta(days=1)).replace(day=1); st.rerun()
    col_c2.markdown(f"<center><h4>{st.session_state.current_month.strftime('%Y年 %m月')}</h4></center>", unsafe_allow_html=True)
    if col_c3.button("次月 ▶"): st.session_state.current_month = (st.session_state.current_month + timedelta(days=32)).replace(day=1); st.rerun()

    cal_html = '<div class="cal-grid">'
    for w in ["月", "火", "水", "木", "金", "土", "日"]: cal_html += f'<div class="cal-header-item">{w}</div>'
    
    cal_obj = calendar.Calendar(firstweekday=0)
    days = cal_obj.monthdayscalendar(st.session_state.current_month.year, st.session_state.current_month.month)
    for week in days:
        for day in week:
            if day == 0: cal_html += '<div></div>'
            else:
                d_str = str(st.session_state.current_month.replace(day=day))
                is_today = (d_str == str(today_jst))
                inner = f'<div class="cal-date">{day}</div>'
                for p_type, p_lab in period_dates.get(d_str, []): inner += f'<div class="cal-dot {p_type}-dot">{p_lab}</div>'
                for e in [e for e in events if e.get("date") == d_str]: inner += f'<div class="cal-dot" style="color:#60a5fa;">📍 {e["title"]}</div>'
                for n in [n for n in ng_dates if n.get("date") == d_str]: inner += f'<div class="cal-dot ng-dot">🚫 {n.get("userName")}</div>'
                cal_html += f'<div class="cal-box {"cal-today" if is_today else ""}">{inner}</div>'
    st.markdown(cal_html + '</div>', unsafe_allow_html=True)

with tab4:
    nd = st.date_input("行けない日")
    nt = time_selector_ui("ng_add")
    if st.button("NG登録"):
        get_ng_ref().add({"roomKey": room_key, "userName": user_name, "date": str(nd), "time": nt}); st.rerun()
