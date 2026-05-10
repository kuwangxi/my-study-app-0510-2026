import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
import uuid
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. 初期設定とFirebase接続
# ==========================================
st.set_page_config(page_title="ふたりの共有ノート", page_icon="🤝", layout="centered")

# 日本時間(JST)を取得するための関数
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
else:
    firebase_admin.get_app()

db = firestore.client()
APP_ID = "couple-secure-v2"

# データベース参照関数
def get_events_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_events')

def get_ng_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_ng_dates')

def get_rooms_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_rooms')

# ==========================================
# 2. セッション管理 & コールバック
# ==========================================
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

if "room_key" not in st.session_state:
    st.session_state.room_key = ""

if "is_logged" not in st.session_state:
    st.session_state.is_logged = False

# 相談送信用のコールバック関数
def send_comment_callback(item_id, input_key, user_name):
    new_comment = st.session_state.get(input_key)
    if new_comment:
        get_events_ref().document(item_id).update({
            "comments": firestore.ArrayUnion([{
                "userName": user_name, 
                "text": new_comment, 
                "createdAt": get_jst_now().isoformat()
            }])
        })
        # 送信後に中身を空にする
        st.session_state[input_key] = ""

def generate_secure_key():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    parts = [''.join(random.choices(chars, k=4)) for _ in range(7)]
    return '-'.join(parts) + '-' + random.choice(chars)

def logout():
    st.session_state.is_logged = False
    st.session_state.room_key = ""
    st.session_state.user_name = ""
    st.rerun()

# ==========================================
# 3. ログイン / 名前入力 / ルーム作成画面
# ==========================================
if not st.session_state.is_logged or not st.session_state.user_name:
    st.markdown("<h1 style='text-align: center; color: #f43f5e;'>Shared Note Sync</h1>", unsafe_allow_html=True)
    st.write("---")
    
    st.subheader("ユーザー設定")
    name_input = st.text_input("あなたの表示名を入力してください", value=st.session_state.user_name, placeholder="例：ゆー")
    
    if name_input:
        st.session_state.user_name = name_input
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("新しいノートを作る")
            if st.button("発行する", use_container_width=True):
                new_key = generate_secure_key()
                get_rooms_ref().document(new_key).set({
                    'title': 'ふたりの共有ノート',
                    'createdAt': get_jst_now().isoformat(),
                    'creator': st.session_state.user_name
                })
                st.session_state.room_key = new_key
                st.session_state.is_logged = True
                st.rerun()

        with col2:
            st.subheader("既存のノートに参加")
            input_key_login = st.text_input("29桁の秘密鍵を入力", placeholder="XXXX-XXXX...")
            if st.button("参加する", use_container_width=True):
                if len(input_key_login.strip()) >= 29:
                    st.session_state.room_key = input_key_login.strip()
                    st.session_state.is_logged = True
                    st.rerun()
                else:
                    st.warning("正しい29桁の鍵を入力してください。")
    else:
        st.info("利用を開始するには名前を入力してください。")
    st.stop()

# ==========================================
# 4. メイン画面 (ログイン後)
# ==========================================
room_key = st.session_state.room_key
user_name = st.session_state.user_name

st.sidebar.title("🤝 共有ノート")
st.sidebar.write(f"ログイン名: **{user_name}**")
st.sidebar.caption(f"キー: `{room_key}`")
if st.sidebar.button("ログアウト"):
    logout()

# データ取得
events_docs = get_events_ref().where("roomKey", "==", room_key).stream()
events = [{"id": doc.id, **doc.to_dict()} for doc in events_docs]

ng_docs = get_ng_ref().where("roomKey", "==", room_key).stream()
ng_dates = [{"id": doc.id, **doc.to_dict()} for doc in ng_docs]

tab1, tab2, tab3 = st.tabs(["📍 行きたい", "📅 予定", "🚫 NG日"])

# --- タブ1: 行きたいリスト ---
with tab1:
    with st.expander("＋ 新しい場所を追加", expanded=False):
        with st.form("add_wishlist_form", clear_on_submit=True):
            title = st.text_input("どこに行きたい？ (必須)")
            url = st.text_input("URL (任意)")
            memo = st.text_area("メモ...")
            submit = st.form_submit_button("追加する")
            if submit and title:
                get_events_ref().add({
                    "roomKey": room_key, "title": title, "url": url, "memo": memo,
                    "userName": user_name, "status": "wishlist", "date": None,
                    "preferences": {}, "comments": [], "createdAt": get_jst_now().isoformat()
                })
                st.rerun()

    wishlist_items = [e for e in events if e.get("status") == "wishlist"]
    wishlist_items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

    for item in wishlist_items:
        with st.container(border=True):
            head_col, del_col = st.columns([5, 1])
            head_col.markdown(f"### {item['title']}")
            if del_col.button("🗑️", key=f"del_wish_{item['id']}", help="この場所を削除"):
                get_events_ref().document(item["id"]).delete()
                st.rerun()
                
            st.caption(f"追加: {item.get('userName', '不明')}")
            
            if item.get("memo"):
                st.info(f"📝 {item['memo']}")
                
            if item.get("url"): 
                st.markdown(f"[🔗 リンク]({item['url']})")
            
            prefs = item.get("preferences", {})
            my_pref = prefs.get(user_name, "")
            
            c1, c2, c3 = st.columns(3)
            def update_pref(p, i_id=item["id"]):
                get_events_ref().document(i_id).set({"preferences": {user_name: p}}, merge=True)
                st.rerun()

            if c1.button("😍", key=f"w_{item['id']}", type="primary" if my_pref=="want" else "secondary", use_container_width=True): update_pref("want")
            if c2.button("😐", key=f"n_{item['id']}", type="primary" if my_pref=="neutral" else "secondary", use_container_width=True): update_pref("neutral")
            if c3.button("🙅‍♂️", key=f"no_{item['id']}", type="primary" if my_pref=="no" else "secondary", use_container_width=True): update_pref("no")

            others = [f"{k}: {'😍' if v=='want' else '😐' if v=='neutral' else '🙅‍♂️'}" for k, v in prefs.items() if k != user_name]
            if others: st.caption(f"相手の反応: {', '.join(others)}")

            with st.expander("💬 相談・日程確定"):
                for c in item.get("comments", []):
                    c_time = c.get('createdAt', '')[11:16]
                    st.write(f"**{c.get('userName', '??')}** ({c_time}): {c['text']}")
                
                col_c, col_b = st.columns([3, 1])
                input_key = f"ci_{item['id']}"
                new_comment = col_c.text_input("相談...", key=input_key)
                
                col_b.button(
                    "送信", 
                    key=f"cb_{item['id']}", 
                    on_click=send_comment_callback, 
                    args=(item["id"], input_key, user_name)
                )

                st.write("---")
                sel_date = st.date_input("確定日", value=get_jst_now().date(), key=f"di_{item['id']}")
                if any(n["date"] == str(sel_date) for n in ng_dates):
                    st.warning("⚠️ この日はNGが入っています！")

                t_type = st.selectbox("時間", ["all", "morning", "afternoon", "custom"], 
                                     format_func=lambda x: {"all":"終日", "morning":"午前", "afternoon":"午後", "custom":"カスタム"}[x], key=f"ti_{item['id']}")
                c_time = st.text_input("カスタム時間入力", key=f"cti_{item['id']}") if t_type == "custom" else ""

                if st.button("予定を確定", key=f"fi_{item['id']}", type="primary", use_container_width=True):
                    get_events_ref().document(item["id"]).update({
                        "status": "scheduled", "date": str(sel_date), "timeType": t_type, "customTime": c_time
                    })
                    st.rerun()

# --- タブ2: 予定 ---
with tab2:
    st.subheader("確定した予定リスト")
    scheduled = [e for e in events if e.get("status") == "scheduled"]
    scheduled.sort(key=lambda x: x.get("date", ""))

    for item in scheduled:
        t_label = {"all":"終日", "morning":"午前", "afternoon":"午後", "custom": item.get("customTime", "")}.get(item.get("timeType"), "")
        
        with st.container(border=True):
            date_col, title_col = st.columns([1, 2])
            
            with date_col:
                st.markdown(f"#### 📅 {item['date']}")
                st.caption(f"⏰ {t_label}")
            
            with title_col:
                st.markdown(f"### {item['title']}")
                
                # ここでURLを表示するように追加
                if item.get("url"): 
                    st.markdown(f"[🔗 リンク]({item['url']})")
                    
                if item.get("memo"):
                    st.caption(f"📝 {item['memo']}")
                
                btn_col1, btn_col2 = st.columns(2)
                if btn_col1.button("リストに戻す", key=f"rev_{item['id']}", use_container_width=True):
                    get_events_ref().document(item["id"]).update({"status": "wishlist", "date": None})
                    st.rerun()
                if btn_col2.button("削除", key=f"del_sch_{item['id']}", use_container_width=True):
                    get_events_ref().document(item["id"]).delete()
                    st.rerun()

# --- タブ3: NG日 ---
with tab3:
    st.subheader("NG予定の登録")
    with st.form("ng_form", clear_on_submit=True):
        ng_d = st.date_input("NGな日", value=get_jst_now().date())
        ng_t = st.selectbox("時間帯", ["all", "morning", "afternoon", "custom"], 
                            format_func=lambda x: {"all":"終日", "morning":"午前", "afternoon":"午後", "custom":"カスタム時間"}[x])
        ng_ct = st.text_input("カスタム時間（例: 15時以降）") if ng_t == "custom" else ""
        ng_reason = st.text_input("理由（任意）", placeholder="予定内容など、書かなくてもOK")
        
        if st.form_submit_button("NG日を追加", use_container_width=True):
            get_ng_ref().add({
                "roomKey": room_key, "userName": user_name, "date": str(ng_d),
                "timeType": ng_t, "customTime": ng_ct, "reason": ng_reason,
                "createdAt": get_jst_now().isoformat()
            })
            st.rerun()
    
    st.divider()
    st.subheader("NGリスト")
    ng_dates.sort(key=lambda x: x.get("date", ""))
    
    for n in ng_dates:
        t_val = n.get("customTime") if n.get("timeType") == "custom" else {"all":"終日", "morning":"午前", "afternoon":"午後"}.get(n.get("timeType"), "")
        reason_txt = f"理由: {n['reason']}" if n.get("reason") else "理由なし"
        
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(f"**{n['date']} ({t_val})**")
                st.write(f"{n['userName']} - {reason_txt}")
            with c2:
                if n["userName"] == user_name:
                    if st.button("削除", key=f"del_ng_{n['id']}", use_container_width=True):
                        get_ng_ref().document(n["id"]).delete()
                        st.rerun()
