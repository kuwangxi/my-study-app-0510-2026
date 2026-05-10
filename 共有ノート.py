import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
import uuid
from datetime import datetime

# ==========================================
# 1. 初期設定とFirebase接続
# ==========================================
st.set_page_config(page_title="ふたりの共有ノート", page_icon="🤝", layout="centered")

# Firebase初期化 (エラー回避のための修正版)
if not firebase_admin._apps:
    try:
        # Secretsから情報を取得
        cred_dict = dict(st.secrets["firebase"])
        
        # 秘密鍵の改行コードを適切に処理
        if "private_key" in cred_dict:
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebaseの認証エラー: {e}")
        st.stop()
else:
    # すでに初期化されている場合は、既存のアプリをそのまま使う
    firebase_admin.get_app()

db = firestore.client()
APP_ID = "couple-secure-v2"

# データベースの参照パスを取得する関数
def get_events_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_events')

def get_ng_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_ng_dates')

def get_rooms_ref():
    return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('secure_rooms')

# ==========================================
# 2. セッション・ユーティリティ関数
# ==========================================
if "uid" not in st.session_state:
    st.session_state.uid = str(uuid.uuid4())

if "room_key" not in st.session_state:
    st.session_state.room_key = ""

if "is_logged" not in st.session_state:
    st.session_state.is_logged = False

def generate_secure_key():
    """29桁のセキュリティキー生成"""
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    parts = [''.join(random.choices(chars, k=4)) for _ in range(7)]
    last_char = random.choice(chars)
    return '-'.join(parts) + '-' + last_char

def logout():
    st.session_state.is_logged = False
    st.session_state.room_key = ""
    st.rerun()

# ==========================================
# 3. ログイン / ルーム作成画面
# ==========================================
if not st.session_state.is_logged:
    st.markdown("<h1 style='text-align: center; color: #f43f5e;'>29-Digit Secure Sync</h1>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("新しいノートを作る")
        if st.button("発行する", use_container_width=True):
            new_key = generate_secure_key()
            get_rooms_ref().document(new_key).set({
                'title': 'ふたりの共有ノート',
                'createdAt': datetime.now().isoformat(),
                'creator': st.session_state.uid
            })
            st.session_state.room_key = new_key
            st.session_state.is_logged = True
            st.rerun()

    with col2:
        st.subheader("既存のノートに参加")
        input_key = st.text_input("29桁の秘密鍵を入力", placeholder="XXXX-XXXX...")
        if st.button("参加する", use_container_width=True):
            if len(input_key.strip()) >= 29:
                st.session_state.room_key = input_key.strip()
                st.session_state.is_logged = True
                st.rerun()
            else:
                st.warning("正しい29桁の鍵を入力してください。")
    st.stop()

# ==========================================
# 4. メイン画面 (ログイン後)
# ==========================================
room_key = st.session_state.room_key
uid = st.session_state.uid

st.sidebar.title("🤝 共有ノート")
st.sidebar.caption(f"現在のキー: `{room_key}`")
if st.sidebar.button("ログアウト"):
    logout()

# データ取得
events_docs = get_events_ref().where("roomKey", "==", room_key).stream()
events = [{"id": doc.id, **doc.to_dict()} for doc in events_docs]

ng_docs = get_ng_ref().where("roomKey", "==", room_key).stream()
ng_dates = [{"id": doc.id, **doc.to_dict()} for doc in ng_docs]

# タブの作成
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
                    "status": "wishlist", "date": None, "timeType": None,
                    "preferences": {}, "comments": [],
                    "createdAt": datetime.now().isoformat()
                })
                st.rerun()

    wishlist_items = [e for e in events if e.get("status") == "wishlist"]
    wishlist_items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

    for item in wishlist_items:
        st.markdown(f"### {item['title']}")
        if item.get("url"):
            st.markdown(f"[🔗 参考リンク]({item['url']})")
        if item.get("memo"):
            st.caption(item["memo"])

        prefs = item.get("preferences", {})
        my_pref = prefs.get(uid, "")
        partner_uid = next((k for k in prefs.keys() if k != uid), None)
        partner_pref = prefs.get(partner_uid, "") if partner_uid else None

        c1, c2, c3 = st.columns(3)
        def update_pref(pref_val, item_id=item["id"]):
            get_events_ref().document(item_id).set({f"preferences": {uid: pref_val}}, merge=True)
            st.rerun()

        if c1.button("😍 行きたい", key=f"want_{item['id']}", type="primary" if my_pref=="want" else "secondary"): update_pref("want")
        if c2.button("😐 どっちでも", key=f"neutral_{item['id']}", type="primary" if my_pref=="neutral" else "secondary"): update_pref("neutral")
        if c3.button("🙅‍♂️ うーん", key=f"no_{item['id']}", type="primary" if my_pref=="no" else "secondary"): update_pref("no")

        if partner_pref:
            partner_icon = "😍" if partner_pref == "want" else "😐" if partner_pref == "neutral" else "🙅‍♂️"
            st.info(f"相手の気分: {partner_icon}")

        with st.expander("💬 メッセージ相談 / 📅 日程を決める"):
            comments = item.get("comments", [])
            for c in comments:
                who = "あなた" if c["userId"] == uid else "相手"
                st.caption(f"**{who}**: {c['text']}")
            
            col_c, col_b = st.columns([3, 1])
            new_comment = col_c.text_input("相談する...", key=f"c_in_{item['id']}")
            if col_b.button("送信", key=f"c_btn_{item['id']}") and new_comment:
                get_events_ref().document(item["id"]).update({
                    "comments": firestore.ArrayUnion([{"userId": uid, "text": new_comment, "createdAt": datetime.now().isoformat()}])
                })
                st.rerun()

            st.write("---")
            st.write("**日程を確定して予定に移動**")
            sel_date = st.date_input("日付を選択", key=f"d_in_{item['id']}")
            ng_on_date = [n for n in ng_dates if n["date"] == str(sel_date)]
            if ng_on_date:
                st.warning("⚠️ この日はNG予定が登録されています！（相手またはあなた）")

            time_type = st.selectbox("時間帯", ["all", "morning", "afternoon", "custom"], 
                                     format_func=lambda x: {"all":"終日", "morning":"午前", "afternoon":"午後", "custom":"時間指定"}[x],
                                     key=f"t_in_{item['id']}")
            custom_time = ""
            if time_type == "custom":
                custom_time = st.text_input("時間を入力 (例: 13:00〜15:00)", key=f"ct_in_{item['id']}")

            if st.button("予定を確定する", key=f"sch_btn_{item['id']}", type="primary"):
                get_events_ref().document(item["id"]).update({
                    "status": "scheduled",
                    "date": str(sel_date),
                    "timeType": time_type,
                    "customTime": custom_time
                })
                st.rerun()
        st.divider()

# --- タブ2: 予定 ---
with tab2:
    st.subheader("確定した予定リスト")
    scheduled_items = [e for e in events if e.get("status") == "scheduled"]
    scheduled_items.sort(key=lambda x: x.get("date", ""))

    if not scheduled_items:
        st.info("まだ確定した予定はありません。")

    for item in scheduled_items:
        time_label = "終日"
        if item.get("timeType") == "morning": time_label = "午前"
        elif item.get("timeType") == "afternoon": time_label = "午後"
        elif item.get("timeType") == "custom": time_label = item.get("customTime", "")

        col_date, col_info = st.columns([1, 4])
        with col_date:
            st.markdown(f"**{item['date']}**")
            st.caption(time_label)
        with col_info:
            st.markdown(f"**{item['title']}**")
            c1, c2 = st.columns(2)
            if c1.button("リストに戻す", key=f"rev_{item['id']}"):
                get_events_ref().document(item["id"]).update({"status": "wishlist", "date": None, "timeType": None})
                st.rerun()
            if c2.button("削除", key=f"del_sch_{item['id']}"):
                get_events_ref().document(item["id"]).delete()
                st.rerun()
        st.divider()

# --- タブ3: NG日 ---
with tab3:
    st.subheader("NG予定の登録")
    with st.form("add_ng_form", clear_on_submit=True):
        ng_date = st.date_input("日付を選択")
        ng_time = st.selectbox("時間帯", ["all", "morning", "afternoon"], format_func=lambda x: {"all":"終日", "morning":"午前", "afternoon":"午後"}[x])
        if st.form_submit_button("NG日を追加する", type="primary"):
            get_ng_ref().add({
                "roomKey": room_key, "userId": uid, "date": str(ng_date),
                "timeType": ng_time, "createdAt": datetime.now().isoformat()
            })
            st.rerun()
    
    st.write("---")
    st.subheader("登録済みのNG日")
    ng_dates.sort(key=lambda x: x.get("date", ""))
    
    for n in ng_dates:
        who = "あなた" if n["userId"] == uid else "相手"
        time_label = {"all":"終日", "morning":"午前", "afternoon":"午後"}.get(n.get("timeType"), "")
        
        c1, c2 = st.columns([4, 1])
        with c1:
            if who == "相手":
                st.error(f"📅 {n['date']} ({time_label}) - {who}")
            else:
                st.info(f"📅 {n['date']} ({time_label}) - {who}")
        with c2:
            if who == "あなた" and st.button("削除", key=f"del_ng_{n['id']}"):
                get_ng_ref().document(n["id"]).delete()
                st.rerun()
