import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. 初期設定とFirebase接続
# ==========================================
st.set_page_config(page_title="ふたりの共有ノート", page_icon="🤝", layout="centered")

# CSSの定義
st.markdown("""
<style>
    .past-item { color: #9e9e9e; }
    .calendar-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 5px;
        text-align: center;
        border: 1px solid #ddd;
        font-size: 0.8rem;
    }
    .calendar-today {
        background-color: #ffe4e6;
        border: 2px solid #f43f5e;
    }
    .time-badge {
        background-color: #eee;
        padding: 2px 5px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

def get_jst_now():
    return datetime.now(timezone(timedelta(hours=9)))

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

# ==========================================
# 2. セッション管理 & 編集用ステート
# ==========================================
if "edit_id" not in st.session_state: st.session_state.edit_id = None
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
# 3. ログイン画面
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
# 4. メイン画面
# ==========================================
room_key, user_name = st.session_state.room_key, st.session_state.user_name
st.sidebar.caption(f"User: {user_name} / Key: {room_key}")
if st.sidebar.button("ログアウト"): logout()

# データ一括取得
events = [{"id": d.id, **d.to_dict()} for d in get_events_ref().where("roomKey", "==", room_key).stream()]
ng_dates = [{"id": d.id, **d.to_dict()} for d in get_ng_ref().where("roomKey", "==", room_key).stream()]
today_str = str(get_jst_now().date())

tab1, tab2, tab3 = st.tabs(["📍 行きたい", "📅 予定", "🚫 NG日"])

# --- タブ1: 行きたいリスト ---
with tab1:
    with st.expander("＋ 追加する"):
        with st.form("add_wish"):
            t = st.text_input("場所/内容")
            u = st.text_input("URL")
            m = st.text_area("メモ")
            col_t1, col_t2 = st.columns(2)
            has_time = col_t1.checkbox("時間を指定する")
            wt = col_t2.time_input("時間", value=get_jst_now().time()) if has_time else None
            
            if st.form_submit_button("追加") and t:
                get_events_ref().add({
                    "roomKey": room_key, "title": t, "url": u, "memo": m, 
                    "userName": user_name, "status": "wishlist", "comments": [], 
                    "time": wt.strftime("%H:%M") if wt else None,
                    "createdAt": get_jst_now().isoformat()
                })
                st.rerun()

    for item in [e for e in events if e.get("status") == "wishlist"]:
        with st.container(border=True):
            if st.session_state.edit_id == item["id"]:
                et = st.text_input("編集: タイトル", item["title"], key=f"et_{item['id']}")
                eu = st.text_input("編集: URL", item.get("url",""), key=f"eu_{item['id']}")
                em = st.text_area("編集: メモ", item.get("memo",""), key=f"em_{item['id']}")
                eti = st.text_input("編集: 時間 (HH:MM / 空白可)", item.get("time",""), key=f"eti_{item['id']}")
                
                c1, c2, c3 = st.columns(3)
                if c1.button("保存", key=f"sv_{item['id']}", use_container_width=True, type="primary"):
                    get_events_ref().document(item["id"]).update({"title":et, "url":eu, "memo":em, "time":eti})
                    st.session_state.edit_id = None; st.rerun()
                if c2.button("削除", key=f"del_w_{item['id']}", use_container_width=True):
                    get_events_ref().document(item["id"]).delete()
                    st.session_state.edit_id = None; st.rerun()
                if c3.button("中止", key=f"cn_{item['id']}", use_container_width=True):
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
                    cc1, cc2 = st.columns([3,1])
                    new_c = cc1.text_input("メッセージ", key=f"nc_{item['id']}")
                    if cc2.button("送信", key=f"nb_{item['id']}") and new_c:
                        get_events_ref().document(item["id"]).update({"comments": firestore.ArrayUnion([{"userName":user_name, "text":new_c, "createdAt":get_jst_now().isoformat()}])})
                        st.rerun()
                    st.divider()
                    sd = st.date_input("確定日", value=get_jst_now().date(), key=f"sd_{item['id']}")
                    st.button("この日で確定", key=f"fix_{item['id']}", on_click=lambda i=item, d=sd: get_events_ref().document(i["id"]).update({"status":"scheduled", "date":str(d)}))

# --- タブ2: 予定 ---
with tab2:
    col_dur1, col_dur2 = st.columns([2,1])
    with col_dur1: st.markdown("#### 🗓️ カレンダーサマリー")
    duration = col_dur2.selectbox("表示期間", ["1週間", "2週間", "1ヶ月"], index=0)
    
    days_map = {"1週間": 7, "2週間": 14, "1ヶ月": 30}
    days_count = days_map[duration]
    
    # 横スクロール対応のためにコンテナ化
    with st.container():
        # カレンダー表示 (列数が多すぎる場合はStreamlitが自動で折り返す)
        cols = st.columns(7) # 1行7日固定で表示
        for i in range(days_count):
            target_date = get_jst_now().date() + timedelta(days=i)
            t_str = str(target_date)
            is_today = (i == 0)
            day_events = [e for e in events if e.get("date") == t_str]
            day_ng = [n for n in ng_dates if n.get("date") == t_str]
            
            with cols[i % 7]:
                bg_cls = "calendar-today" if is_today else ""
                content = "・"
                if day_events: content = "📍"
                if day_ng: content = "🚫"
                if day_events and day_ng: content = "⚠️"
                st.markdown(f"""<div class="calendar-card {bg_cls}"><b>{target_date.strftime('%m/%d')}</b><br>{content}</div>""", unsafe_allow_html=True)
            if (i + 1) % 7 == 0 and i + 1 < days_count:
                st.write("") # 改行用

    st.divider()
    
    sched = [e for e in events if e.get("status") == "scheduled"]
    upcoming = sorted([e for e in sched if e["date"] >= today_str], key=lambda x: (x["date"], x.get("time", "99:99")))
    past = sorted([e for e in sched if e["date"] < today_str], key=lambda x: (x["date"], x.get("time", "99:99")), reverse=True)

    def show_event_item(item, is_past=False):
        cls = "past-item" if is_past else ""
        with st.container(border=True):
            if st.session_state.edit_id == item["id"]:
                # 編集モード
                new_date = st.date_input("日付変更", value=datetime.strptime(item["date"], "%Y-%m-%d").date(), key=f"nd_edit_{item['id']}")
                new_time = st.text_input("時間変更 (HH:MM)", item.get("time",""), key=f"nt_edit_time_{item['id']}")
                new_title = st.text_input("タイトル", item["title"], key=f"nt_edit_{item['id']}")
                
                c1, c2, c3 = st.columns(3)
                if c1.button("保存", key=f"ups_{item['id']}", use_container_width=True, type="primary"):
                    get_events_ref().document(item["id"]).update({"date":str(new_date), "title":new_title, "time":new_time})
                    st.session_state.edit_id = None; st.rerun()
                if c2.button("削除", key=f"del_s_{item['id']}", use_container_width=True):
                    get_events_ref().document(item["id"]).delete()
                    st.session_state.edit_id = None; st.rerun()
                if c3.button("キャンセル", key=f"cn_s_{item['id']}", use_container_width=True):
                    st.session_state.edit_id = None; st.rerun()
            else:
                # 通常モード
                c1, c2, c3 = st.columns([2, 5, 1])
                time_str = f" {item['time']}" if item.get("time") else ""
                c1.markdown(f"<p class='{cls}'><b>📅 {item['date']}{time_str}</b></p>", unsafe_allow_html=True)
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
    with st.form("add_ng"):
        nd = st.date_input("行けない日", value=get_jst_now().date())
        col_nt1, col_nt2 = st.columns(2)
        has_ntime = col_nt1.checkbox("時間を指定する")
        nt = col_nt2.time_input("時間", value=get_jst_now().time()) if has_ntime else None
        nr = st.text_input("理由など(任意)")
        if st.form_submit_button("NG登録", use_container_width=True):
            get_ng_ref().add({
                "roomKey": room_key, "userName": user_name, 
                "date": str(nd), "reason": nr,
                "time": nt.strftime("%H:%M") if nt else None
            })
            st.rerun()
    
    st.divider()
    upcoming_ng = sorted([n for n in ng_dates if n["date"] >= today_str], key=lambda x: (x["date"], x.get("time", "00:00")))
    past_ng = sorted([n for n in ng_dates if n["date"] < today_str], key=lambda x: (x["date"], x.get("time", "00:00")), reverse=True)

    def show_ng_item(n, is_past=False):
        cls = "past-item" if is_past else ""
        with st.container(border=True):
            if st.session_state.edit_id == n["id"]:
                # 編集モード
                nd2 = st.date_input("日付変更", value=datetime.strptime(n["date"], "%Y-%m-%d").date(), key=f"nd2_{n['id']}")
                nt2 = st.text_input("時間変更 (HH:MM)", n.get("time",""), key=f"nt2_{n['id']}")
                nr2 = st.text_input("理由変更", n.get("reason",""), key=f"nr2_{n['id']}")
                
                c1, c2, c3 = st.columns(3)
                if c1.button("保存", key=f"sv_ng_{n['id']}", use_container_width=True, type="primary"):
                    get_ng_ref().document(n["id"]).update({"date":str(nd2), "reason":nr2, "time":nt2})
                    st.session_state.edit_id = None; st.rerun()
                if c2.button("削除", key=f"del_ng_{n['id']}", use_container_width=True):
                    get_ng_ref().document(n["id"]).delete()
                    st.session_state.edit_id = None; st.rerun()
                if c3.button("中止", key=f"cn_ng_{n['id']}", use_container_width=True):
                    st.session_state.edit_id = None; st.rerun()
            else:
                # 通常モード
                c1, c2, c3 = st.columns([3, 5, 1])
                n_time_str = f" <span class='time-badge'>{n['time']}</span>" if n.get("time") else ""
                c1.markdown(f"<span class='{cls}'><b>{n['date']}{n_time_str}</b></span>", unsafe_allow_html=True)
                c2.markdown(f"<span class='{cls}'>{n.get('userName','')} : {n.get('reason','')}</span>", unsafe_allow_html=True)
                if c3.button("📝", key=f"ed_ng_{n['id']}"): st.session_state.edit_id = n["id"]; st.rerun()

    st.subheader("📍 今後のNG日")
    if not upcoming_ng: st.write("NG日の登録はありません")
    for n in upcoming_ng: show_ng_item(n)
    
    if past_ng:
        with st.expander("⌛ 過去のNG日"):
            for n in past_ng: show_ng_item(n, is_past=True)
