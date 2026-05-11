import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. 初期設定とFirebase接続
# ==========================================
st.set_page_config(page_title="ふたりの共有ノート", page_icon="🤝", layout="centered")

# セッション状態の初期化
if "font_size" not in st.session_state: st.session_state.font_size = 14
if "show_summary" not in st.session_state: st.session_state.show_summary = True
if "hide_empty_days" not in st.session_state: st.session_state.hide_empty_days = False
if "edit_id" not in st.session_state: st.session_state.edit_id = None

# --- 追加：テキスト入力リセット用のセッション管理 ---
if "input_title" not in st.session_state: st.session_state.input_title = ""
if "input_url" not in st.session_state: st.session_state.input_url = ""
if "input_memo" not in st.session_state: st.session_state.input_memo = ""
if "ng_reason" not in st.session_state: st.session_state.ng_reason = ""

# CSSの定義
st.markdown(f"""
<style>
    html, body, [class*="st-"] {{
        font-size: {st.session_state.font_size}px !important;
    }}
    .past-item {{ color: #9e9e9e; }}
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
</style>
""", unsafe_allow_html=True)

def get_jst_now():
    return datetime.now(timezone(timedelta(hours=9)))

def get_weekday_jp(dt):
    w_list = ['月', '火', '水', '木', '金', '土', '日']
    return w_list[dt.weekday()]

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

def get_events_ref(): return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_events')
def get_ng_ref(): return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_ng_dates')
def get_rooms_ref(): return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_rooms')

# 時間選択用UI
def time_selector_ui(key_prefix):
    t_type = st.selectbox("時間指定", ["指定なし", "午前中", "午後", "終日", "カスタム"], key=f"t_type_{key_prefix}")
    if t_type == "カスタム":
        col_c1, col_c2 = st.columns(2)
        t_start = col_c1.time_input("開始", value=get_jst_now().time(), key=f"t_start_{key_prefix}")
        t_end = col_c2.time_input("終了", value=(get_jst_now() + timedelta(hours=2)).time(), key=f"t_end_{key_prefix}")
        return f"{t_start.strftime('%H:%M')}～{t_end.strftime('%H:%M')}"
    elif t_type == "指定なし":
        return None
    else:
        return t_type

# ==========================================
# 2. セッション管理
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

if "user_name" not in st.session_state: st.session_state.user_name = ""
if "room_key" not in st.session_state: st.session_state.room_key = ""

def login_action(room, user):
    st.session_state.room_key, st.session_state.user_name, st.session_state.is_logged = room, user, True
    st.query_params["room"], st.query_params["user"] = room, user

def logout():
    st.session_state.is_logged = False
    st.query_params.clear()
    st.rerun()

# ==========================================
# 3. サイドバー
# ==========================================
if st.session_state.is_logged:
    st.sidebar.title("⚙️ アプリ設定")
    new_size = st.sidebar.slider("テキストの大きさ", 10, 24, value=st.session_state.font_size)
    if st.sidebar.button("サイズを確定する", key="btn_confirm_font_main"):
        st.session_state.font_size = new_size
        st.rerun()
    
    st.sidebar.divider()
    st.session_state.show_summary = st.sidebar.checkbox("カレンダーサマリーを表示", value=st.session_state.show_summary)
    if st.session_state.show_summary:
        st.session_state.hide_empty_days = st.sidebar.checkbox("予定がある日のみ表示", value=st.session_state.hide_empty_days)
    
    st.sidebar.divider()
    st.sidebar.caption(f"User: {st.session_state.user_name}")
    st.sidebar.caption(f"Key: {st.session_state.room_key}")
    if st.sidebar.button("ログアウト", use_container_width=True): logout()

# ==========================================
# 4. ログイン画面
# ==========================================
if not st.session_state.is_logged or not st.session_state.user_name:
    st.markdown("<h1 style='text-align: center; color: #f43f5e;'>Shared Note Sync</h1>", unsafe_allow_html=True)
    name_input = st.text_input("表示名を入力してください", value=st.session_state.user_name)
    if name_input:
        st.session_state.user_name = name_input
        col1, col2 = st.columns(2)
        with col1:
            if st.button("新しいノートを作る", use_container_width=True):
                new_key = '-'.join([''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4)) for _ in range(7)])
                get_rooms_ref().document(new_key).set({'createdAt': get_jst_now().isoformat(), 'creator': name_input})
                login_action(new_key, name_input); st.rerun()
        with col2:
            input_key = st.text_input("秘密鍵(29桁)を入力", placeholder="XXXX-XXXX...")
            if st.button("参加する", use_container_width=True) and len(input_key) >= 29:
                login_action(input_key, name_input); st.rerun()
    st.stop()

# ==========================================
# 5. メイン画面
# ==========================================
room_key, user_name = st.session_state.room_key, st.session_state.user_name
events = [{"id": d.id, **d.to_dict()} for d in get_events_ref().where("roomKey", "==", room_key).stream()]
ng_dates = [{"id": d.id, **d.to_dict()} for d in get_ng_ref().where("roomKey", "==", room_key).stream()]
today_str = str(get_jst_now().date())

tab1, tab2, tab3 = st.tabs(["📍 行きたい", "📅 予定", "🚫 NG日"])

# --- タブ1: 行きたいリスト ---
with tab1:
    with st.expander("＋ 追加する"):
        # セッション状態と紐付けることでリセットを可能にする
        t = st.text_input("場所/内容", key="input_title")
        u = st.text_input("URL", key="input_url")
        m = st.text_area("メモ", key="input_memo")
        wt = time_selector_ui("wish")
        
        if st.button("追加", use_container_width=True, type="primary", key="wish_add_btn"):
            if t:
                get_events_ref().add({
                    "roomKey": room_key, "title": t, "url": u, "memo": m, 
                    "userName": user_name, "status": "wishlist", "comments": [], 
                    "time": wt, "createdAt": get_jst_now().isoformat()
                })
                # 追加後にセッション変数を空にしてリセット
                st.session_state.input_title = ""
                st.session_state.input_url = ""
                st.session_state.input_memo = ""
                st.rerun()
            else:
                st.warning("場所/内容を入力してください")

    for item in [e for e in events if e.get("status") == "wishlist"]:
        with st.container(border=True):
            if st.session_state.edit_id == item["id"]:
                et = st.text_input("編集: タイトル", item["title"], key=f"et_{item['id']}")
                eu = st.text_input("編集: URL", item.get("url",""), key=f"eu_{item['id']}")
                em = st.text_area("編集: メモ", item.get("memo",""), key=f"em_{item['id']}")
                eti = st.text_input("編集: 時間 (自由入力)", item.get("time","") if item.get("time") else "", key=f"eti_{item['id']}")
                c1, c2, c3 = st.columns(3)
                if c1.button("保存", key=f"sv_{item['id']}", use_container_width=True, type="primary"):
                    get_events_ref().document(item["id"]).update({"title":et, "url":eu, "memo":em, "time":eti if eti else None})
                    st.session_state.edit_id = None; st.rerun()
                if c2.button("キャンセル", key=f"cn_{item['id']}", use_container_width=True):
                    st.session_state.edit_id = None; st.rerun()
                if c3.button("削除", key=f"del_w_{item['id']}", use_container_width=True):
                    get_events_ref().document(item["id"]).delete()
                    st.session_state.edit_id = None; st.rerun()
            else:
                c1, c2 = st.columns([5,1])
                time_disp = f"<span class='time-badge'>⏰ {item['time']}</span> " if item.get("time") else ""
                c1.markdown(f"### {time_disp}{item['title']}", unsafe_allow_html=True)
                if c2.button("📝", key=f"ed_{item['id']}"): st.session_state.edit_id = item["id"]; st.rerun()
                if item.get("url"): st.markdown(f"[🔗 リンク]({item['url']})")
                if item.get("memo"): st.info(item["memo"])
                with st.expander("💬 相談・確定"):
                    for c in item.get("comments", []): st.write(f"**{c['userName']}**: {c['text']}")
                    with st.form(key=f"comment_form_{item['id']}", clear_on_submit=True):
                        cc1, cc2 = st.columns([3,1])
                        new_c = cc1.text_input("メッセージ", placeholder="メッセージを入力...")
                        if cc2.form_submit_button("送信", use_container_width=True) and new_c:
                            get_events_ref().document(item["id"]).update({"comments": firestore.ArrayUnion([{"userName": user_name, "text": new_c, "createdAt": get_jst_now().isoformat()}])})
                            st.rerun()
                    st.divider()
                    st.write("確定情報を入力してください")
                    sd = st.date_input("確定日", value=get_jst_now().date(), key=f"sd_{item['id']}")
                    st_time = time_selector_ui(f"fix_{item['id']}")
                    if st.button("この日で確定", key=f"fix_btn_{item['id']}"):
                        get_events_ref().document(item['id']).update({"status": "scheduled", "date": str(sd), "time": st_time})
                        st.rerun()

# --- タブ2: 予定 ---
with tab2:
    if st.session_state.show_summary:
        col_dur1, col_dur2 = st.columns([2,1])
        with col_dur1: st.markdown("#### 🗓️ カレンダーサマリー")
        duration = col_dur2.selectbox("表示期間", ["1週間", "2週間", "1ヶ月"], index=0)
        days_count = {"1週間": 7, "2週間": 14, "1ヶ月": 30}[duration]
        
        display_days = []
        for i in range(days_count):
            target_date = get_jst_now().date() + timedelta(days=i)
            t_str = str(target_date)
            day_events = [e for e in events if e.get("date") == t_str]
            day_ng = [n for n in ng_dates if n.get("date") == t_str]
            if st.session_state.hide_empty_days and not day_events and not day_ng: continue
            display_days.append((target_date, t_str, day_events, day_ng, i == 0))

        if not display_days: st.caption("表示期間内に予定はありません")
        else:
            cols = st.columns(7)
            for idx, (target_date, t_str, day_events, day_ng, is_today) in enumerate(display_days):
                with cols[idx % 7]:
                    bg_cls = "calendar-today" if is_today else ""
                    content = "・"
                    if day_events: content = "📍"
                    if day_ng: content = "🚫"
                    if day_events and day_ng: content = "⚠️"
                    date_label = f"{target_date.strftime('%m/%d')}({get_weekday_jp(target_date)})"
                    st.markdown(f'<div class="calendar-card {bg_cls}"><div class="calendar-date">{date_label}</div><div>{content}</div></div>', unsafe_allow_html=True)
        st.divider()

    sched = [e for e in events if e.get("status") == "scheduled"]
    upcoming = sorted([e for e in sched if e["date"] >= today_str], key=lambda x: (x["date"], x.get("time") or "99:99"))
    past = sorted([e for e in sched if e["date"] < today_str], key=lambda x: (x["date"], x.get("time") or "99:99"), reverse=True)

    def show_event_item(item, is_past=False):
        cls = "past-item" if is_past else ""
        with st.container(border=True):
            if st.session_state.edit_id == item["id"]:
                new_date = st.date_input("日付変更", value=datetime.strptime(item["date"], "%Y-%m-%d").date(), key=f"nd_edit_{item['id']}")
                new_time = st.text_input("時間変更", item.get("time","") if item.get("time") else "", key=f"nt_edit_time_{item['id']}")
                new_title = st.text_input("タイトル", item["title"], key=f"nt_edit_{item['id']}")
                c1, c2, c3 = st.columns(3)
                if c1.button("保存", key=f"ups_{item['id']}", use_container_width=True, type="primary"):
                    get_events_ref().document(item["id"]).update({"date":str(new_date), "title":new_title, "time":new_time if new_time else None})
                    st.session_state.edit_id = None; st.rerun()
                if c2.button("キャンセル", key=f"cn_s_{item['id']}", use_container_width=True):
                    st.session_state.edit_id = None; st.rerun()
                if c3.button("削除", key=f"del_s_{item['id']}", use_container_width=True):
                    get_events_ref().document(item["id"]).delete()
                    st.session_state.edit_id = None; st.rerun()
            else:
                c1, c2, c3 = st.columns([3, 4, 1])
                dt_obj = datetime.strptime(item["date"], "%Y-%m-%d")
                date_with_day = f"{item['date']}({get_weekday_jp(dt_obj)})"
                time_str = f" {item['time']}" if item.get("time") else ""
                c1.markdown(f"<p class='{cls}'><b>📅 {date_with_day}{time_str}</b></p>", unsafe_allow_html=True)
                c2.markdown(f"<p class='{cls}'><b>{item['title']}</b></p>", unsafe_allow_html=True)
                if c3.button("📝", key=f"ed_s_{item['id']}"): st.session_state.edit_id = item["id"]; st.rerun()
                col_b1, col_b2 = st.columns(2)
                if col_b1.button("💬 履歴", key=f"hist_{item['id']}", use_container_width=True):
                    st.info("\n".join([f"{c['userName']}: {c['text']}" for c in item.get("comments", [])]) or "やり取りはありません")
                if col_b2.button("「行きたい」に戻す", key=f"rev_{item['id']}", use_container_width=True):
                    get_events_ref().document(item["id"]).update({"status":"wishlist", "date":None}); st.rerun()

    st.subheader("🚀 これからの予定")
    if not upcoming: st.write("予定はありません")
    for item in upcoming: show_event_item(item)
    if past:
        with st.expander("⌛ 終わった予定を表示"):
            for item in past: show_event_item(item, is_past=True)

# --- タブ3: NG日 ---
with tab3:
    st.subheader("🚫 NG日を登録")
    nd = st.date_input("行けない日", value=get_jst_now().date(), key="ng_date_input")
    nt_str = time_selector_ui("ng_add")
    nr = st.text_input("理由など(任意)", key="ng_reason") # リセット用keyに変更
    
    if st.button("NG登録", use_container_width=True, type="primary", key="ng_add_btn"):
        get_ng_ref().add({"roomKey": room_key, "userName": user_name, "date": str(nd), "reason": nr, "time": nt_str})
        st.session_state.ng_reason = "" # 登録後に理由を空に
        st.rerun()
    
    st.divider()
    upcoming_ng = sorted([n for n in ng_dates if n["date"] >= today_str], key=lambda x: (x["date"], x.get("time") or "00:00"))
    past_ng = sorted([n for n in ng_dates if n["date"] < today_str], key=lambda x: (x["date"], x.get("time") or "00:00"), reverse=True)

    def show_ng_item(n, is_past=False):
        cls = "past-item" if is_past else ""
        with st.container(border=True):
            if st.session_state.edit_id == n["id"]:
                nd2 = st.date_input("日付変更", value=datetime.strptime(n["date"], "%Y-%m-%d").date(), key=f"nd2_{n['id']}")
                nt2 = st.text_input("時間変更 (自由入力)", n.get("time","") if n.get("time") else "", key=f"nt2_{n['id']}")
                nr2 = st.text_input("理由変更", n.get("reason","") if n.get("reason") else "", key=f"nr2_{n['id']}")
                c1, c2, c3 = st.columns(3)
                if c1.button("保存", key=f"sv_ng_{n['id']}", use_container_width=True, type="primary"):
                    get_ng_ref().document(n["id"]).update({
                        "date": str(nd2), 
                        "reason": nr2, 
                        "time": nt2 if nt2 else None
                    })
                    st.session_state.edit_id = None; st.rerun()
                if c2.button("キャンセル", key=f"cn_ng_{n['id']}", use_container_width=True):
                    st.session_state.edit_id = None; st.rerun()
                if c3.button("削除", key=f"del_ng_{n['id']}", use_container_width=True):
                    get_ng_ref().document(n["id"]).delete()
                    st.session_state.edit_id = None; st.rerun()
            else:
                c1, c2, c3 = st.columns([3, 5, 1])
                dt_obj = datetime.strptime(n["date"], "%Y-%m-%d")
                date_with_day = f"{n['date']}({get_weekday_jp(dt_obj)})"
                n_time_str = f" <span class='time-badge'>{n['time']}</span>" if n.get("time") else ""
                c1.markdown(f"<span class='{cls}'><b>{date_with_day}{n_time_str}</b></span>", unsafe_allow_html=True)
                c2.markdown(f"<span class='{cls}'>{n.get('userName','')} : {n.get('reason','')}</span>", unsafe_allow_html=True)
                if c3.button("📝", key=f"ed_ng_{n['id']}"): st.session_state.edit_id = n["id"]; st.rerun()

    st.subheader("📍 今後のNG日")
    for n in upcoming_ng: show_ng_item(n)
    if past_ng:
        with st.expander("⌛ 過去のNG日"):
            for n in past_ng: show_ng_item(n, is_past=True)
