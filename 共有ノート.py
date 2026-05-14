import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta, timezone
import calendar
import requests
from dateutil.relativedelta import relativedelta

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
    st.session_state.period_data = {"start_date": None, "end_date": None, "cycle": 28}
# 積み立て設定用
if "saving_config" not in st.session_state:
    st.session_state.saving_config = {"amount": 0, "day": 1}

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

# ==========================================
# 2. コールバック関数 (更新処理)
# ==========================================

# 行きたい場所の更新
def update_wish_callback(wish_id):
    get_events_ref().document(wish_id).update({
        "title": st.session_state.get(f"ew_t_{wish_id}"),
        "url": st.session_state.get(f"ew_u_{wish_id}"),
        "memo": st.session_state.get(f"ew_m_{wish_id}")
    })

def add_wish_callback():
    title = st.session_state.get("input_title_wish")
    if title:
        get_events_ref().add({
            "roomKey": st.session_state.room_key,
            "title": title, 
            "url": st.session_state.get("input_url_wish"),
            "memo": st.session_state.get("input_memo_wish"),
            "status": "wishlist", "comments": [], "time": st.session_state.get("t_type_wish_add"),
            "createdAt": get_jst_now().isoformat()
        })
        st.session_state.input_title_wish = ""; st.session_state.input_url_wish = ""; st.session_state.input_memo_wish = ""

def update_ng_callback(ng_id):
    get_ng_ref().document(ng_id).update({
        "date": str(st.session_state.get(f"eng_d_{ng_id}")),
        "memo": st.session_state.get(f"eng_m_{ng_id}")
    })

def add_ng_callback():
    get_ng_ref().add({
        "roomKey": st.session_state.room_key, "userName": st.session_state.user_name,
        "date": str(st.session_state.get("ng_in")), "memo": st.session_state.get("ng_memo_in"),
        "createdAt": get_jst_now().isoformat()
    })
    st.session_state.ng_memo_in = ""

def add_expense_callback():
    amount = st.session_state.get("ex_amount")
    if amount > 0:
        get_finances_ref().add({
            "roomKey": st.session_state.room_key, "date": str(st.session_state.get("ex_date")),
            "amount": amount, "memo": st.session_state.get("ex_memo"), "createdAt": get_jst_now().isoformat()
        })
        st.session_state.ex_amount = 0; st.session_state.ex_memo = ""

# 設定保存
def save_app_settings():
    if st.session_state.get("room_key"):
        get_rooms_ref().document(st.session_state.room_key).set({
            "settings": {
                "font_size": st.session_state.font_size,
                "user_colors": st.session_state.room_user_colors,
                "period_data": {k: str(v) if v else None for k,v in st.session_state.period_data.items()},
                "saving_config": st.session_state.saving_config
            }
        }, merge=True)

# 設定読込
def load_app_settings(room_key):
    doc = get_rooms_ref().document(room_key).get()
    if doc.exists:
        s = doc.to_dict().get("settings", {})
        st.session_state.font_size = s.get("font_size", 14)
        st.session_state.room_user_colors = s.get("user_colors", {})
        st.session_state.saving_config = s.get("saving_config", {"amount": 0, "day": 1})
        if st.session_state.user_name in st.session_state.room_user_colors:
            st.session_state.user_color = st.session_state.room_user_colors[st.session_state.user_name]

# --- 共通UI: 時間選択 ---
def time_selector_ui(key_prefix, default_val="カスタム"):
    options = ["終日", "午前中", "午後", "カスタム"]
    idx = options.index(default_val) if default_val in options else 3
    t_type = st.selectbox("時間指定", options, index=idx, key=f"t_type_{key_prefix}")
    if t_type == "カスタム":
        col_c1, col_c2 = st.columns(2)
        t_start = col_c1.time_input("開始", value=datetime.strptime("10:00", "%H:%M").time(), key=f"t_start_{key_prefix}")
        t_end = col_c2.time_input("終了", value=datetime.strptime("12:00", "%H:%M").time(), key=f"t_end_{key_prefix}")
        return f"{t_start.strftime('%H:%M')}～{t_end.strftime('%H:%M')}"
    return t_type

# 天気API
@st.cache_data(ttl=3600)
def get_shinjuku_weather():
    try:
        res = requests.get("https://api.open-meteo.com/v1/forecast?latitude=35.6895&longitude=139.7005&daily=weathercode&timezone=Asia%2FTokyo").json()
        return {d: code for d, code in zip(res['daily']['time'], res['daily']['weathercode'])}
    except: return {}

weather_data = get_shinjuku_weather()

# CSS
st.markdown(f"""
<style>
    html, body, [class*="st-"] {{ font-size: {st.session_state.font_size}px !important; }}
    .cal-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; width: 100%; }}
    .cal-box {{ border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 4px; padding: 4px; min-height: 80px; position: relative; }}
    .cal-today {{ border: 2px solid {st.session_state.user_color} !important; background-color: rgba(244, 63, 94, 0.05); }}
    .cal-dot {{ font-size: 0.75em; padding: 1px 4px; border-radius: 3px; margin-bottom: 2px; }}
    .event-dot {{ background-color: #3b82f622; color: #3b82f6; }}
    .ng-dot {{ background-color: #ef444411; color: #ef4444; }}
    .memo-text {{ font-size: 0.85em; color: gray; background: #8881; padding: 5px; border-radius: 4px; margin: 5px 0; }}
</style>
""", unsafe_allow_html=True)

# ログイン処理
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

if not st.session_state.get("is_logged"):
    st.title("🤝 Shared Note Sync")
    n_in = st.text_input("お名前")
    if n_in:
        c1, c2 = st.columns(2)
        if c1.button("新規作成"):
            new_k = '-'.join([''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4)) for _ in range(7)])
            get_rooms_ref().document(new_k).set({'createdAt': get_jst_now().isoformat()})
            login_action(new_k, n_in); st.rerun()
        k_in = st.text_input("秘密の鍵")
        if c2.button("参加") and len(k_in) > 20: login_action(k_in, n_in); st.rerun()
    st.stop()

# ==========================================
# 3. メインロジック
# ==========================================
room_doc = get_rooms_ref().document(st.session_state.room_key).get()
room_data = room_doc.to_dict()
events = [{"id": d.id, **d.to_dict()} for d in get_events_ref().where("roomKey", "==", st.session_state.room_key).stream()]
ng_dates = [{"id": d.id, **d.to_dict()} for d in get_ng_ref().where("roomKey", "==", st.session_state.room_key).stream()]
finances = [{"id": d.id, **d.to_dict()} for d in get_finances_ref().where("roomKey", "==", st.session_state.room_key).stream()]
today_jst = get_jst_now().date()
today_str = str(today_jst)

tab1, tab2, tab3, tab4 = st.tabs(["📍 行きたい", "📅 予定一覧", "🗓️ カレンダー", "🚫 NG日"])

# --- タブ1: 行きたい (メモ追加の明確化) ---
with tab1:
    with st.expander("＋ 新しい場所を追加"):
        st.text_input("場所/内容", key="input_title_wish")
        st.text_input("URL (任意)", key="input_url_wish")
        st.text_area("メモ (任意)", key="input_memo_wish") # ←ここに任意のメモ機能があります
        time_selector_ui("wish_add")
        st.button("リストに追加", type="primary", on_click=add_wish_callback)
    
    wish_items = [e for e in events if e.get("status") == "wishlist"]
    for item in sorted(wish_items, key=lambda x: x.get('createdAt',''), reverse=True):
        with st.container(border=True):
            st.markdown(f"### {item['title']}")
            if item.get("memo"): st.markdown(f'<div class="memo-text">📝 {item["memo"]}</div>', unsafe_allow_html=True)
            if item.get("url"): st.markdown(f"🔗 [参考リンク]({item['url']})")
            
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                with st.expander("💬 確定"):
                    sd = st.date_input("確定日", value=today_jst, key=f"sd_{item['id']}")
                    if st.button("予定を確定", key=f"fbtn_{item['id']}"):
                        get_events_ref().document(item['id']).update({"status": "scheduled", "date": str(sd)}); st.rerun()
            with c2:
                with st.expander("📝 編集"):
                    st.text_input("名称", value=item['title'], key=f"ew_t_{item['id']}")
                    st.text_input("URL", value=item.get('url',''), key=f"ew_u_{item['id']}")
                    st.text_area("メモ", value=item.get('memo',''), key=f"ew_m_{item['id']}")
                    st.button("更新", key=f"ubw_{item['id']}", on_click=update_wish_callback, args=(item['id'],))
            with c3:
                if st.button("🗑️ 削除", key=f"dbw_{item['id']}", use_container_width=True):
                    get_events_ref().document(item['id']).delete(); st.rerun()

# --- タブ2: 予定一覧 (終わった予定の最小化維持) ---
with tab2:
    sched_items = sorted([e for e in events if e.get("status") == "scheduled"], key=lambda x: x["date"])
    future = [e for e in sched_items if e["date"] >= today_str]
    past = [e for e in sched_items if e["date"] < today_str]
    
    st.subheader("🚀 これからの予定")
    for item in future:
        with st.container(border=True):
            st.write(f"📅 {item['date']} | **{item['title']}**")
            with st.expander("編集・削除"):
                if st.button("🗑️ 削除", key=f"del_f_{item['id']}"): get_events_ref().document(item['id']).delete(); st.rerun()

    if past:
        st.divider()
        # ↓終わった予定はここ（最小化されたエキスパンダーの中）にまとまります
        with st.expander("✅ 終わった予定・過去のログを表示 (削除不可)"):
            for item in sorted(past, key=lambda x: x["date"], reverse=True):
                st.markdown(f"・ **{item['date']}**: {item['title']}")

# --- タブ3: カレンダー & 家計簿 (積立貯金機能維持) ---
with tab3:
    cm1, cm2, cm3 = st.columns([1, 2, 1])
    if cm1.button("◀ 前月"): st.session_state.current_month -= relativedelta(months=1); st.rerun()
    cm2.markdown(f"<center><h3>{st.session_state.current_month.strftime('%Y年 %m月')}</h3></center>", unsafe_allow_html=True)
    if cm3.button("次月 ▶"): st.session_state.current_month += relativedelta(months=1); st.rerun()
    
    st.info("カレンダー表示中")

    st.divider()
    with st.expander("💰 共有貯金・家計簿", expanded=True):
        conf = st.session_state.saving_config
        create_at_str = room_data.get('createdAt', today_str)
        start_date = datetime.fromisoformat(create_at_str).date()
        
        diff = relativedelta(today_jst, start_date)
        total_months = diff.years * 12 + diff.months + 1
        
        sc1, sc2 = st.columns(2)
        conf["amount"] = sc1.number_input("毎月の積立額 (円)", value=conf["amount"], step=1000)
        conf["day"] = sc2.number_input("毎月の積立日 (日)", value=conf["day"], min_value=1, max_value=31)
        if st.button("積立設定を保存"): save_app_settings(); st.rerun()
        
        total_saved = total_months * conf["amount"]
        total_expense = sum([f['amount'] for f in finances])
        balance = total_saved - total_expense
        
        st.markdown(f"""
        <div style="background:#10b98122; padding:15px; border-radius:10px; border:1px solid #10b981;">
            <h2 style="margin:0; color:#10b981;">現在の総貯金額: ¥{balance:,}</h2>
            <p style="margin:0; font-size:0.8em; color:gray;">(積立合計: ¥{total_saved:,} - 支出合計: ¥{total_expense:,})</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("---")
        st.markdown("**💸 支出を記録**")
        ec1, ec2, ec3 = st.columns([2,2,3])
        ec1.date_input("使った日", value=today_jst, key="ex_date")
        ec2.number_input("金額", min_value=0, step=100, key="ex_amount")
        ec3.text_input("メモ", key="ex_memo")
        st.button("支出を記録", use_container_width=True, on_click=add_expense_callback)

# --- タブ4: NG日 (編集機能維持) ---
with tab4:
    st.subheader("🚫 NG登録")
    st.date_input("日付", value=today_jst, key="ng_in")
    st.text_input("メモ", key="ng_memo_in")
    st.button("登録", on_click=add_ng_callback)
    
    for n in sorted(ng_dates, key=lambda x: x["date"]):
        with st.expander(f"🚫 {n['date']} - {n.get('userName')}"):
            st.date_input("日付修正", value=datetime.strptime(n['date'], "%Y-%m-%d").date(), key=f"eng_d_{n['id']}")
            st.text_input("メモ修正", value=n.get('memo',''), key=f"eng_m_{n['id']}")
            st.button("保存", key=f"un_{n['id']}", on_click=update_ng_callback, args=(n['id'],))
            if st.button("🗑️ 削除", key=f"dn_{n['id']}"): get_ng_ref().document(n['id']).delete(); st.rerun()
