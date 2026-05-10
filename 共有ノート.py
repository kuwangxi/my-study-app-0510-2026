import streamlit as st
import uuid
import secrets
import string
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# --- ページ設定 (モバイル・PC両対応) ---
st.set_page_config(page_title="Ultra Secure Pair Note", layout="centered")

# --- 1. Firebase初期化 (永続化と共有の基盤) ---
# ※ service-account.json は同じフォルダに配置してください
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate('service-account.json')
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("設定ファイル 'service-account.json' が見つかりません。")
        st.stop()

db = firestore.client()

# --- 2. セキュリティ & データロジック ---

def generate_29char_key():
    """英数字大文字小文字を含む29桁の完全ランダムキーを生成"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(29))

def sync_data(room_key):
    """Firestoreから最新データを取得"""
    events = [doc.to_dict() | {'id': doc.id} for doc in 
              db.collection('events').where('roomKey', '==', room_key).stream()]
    ngs = [doc.to_dict() | {'id': doc.id} for doc in 
           db.collection('ng_dates').where('roomKey', '==', room_key).stream()]
    return events, ngs

# --- 3. セッション管理 ---
if 'is_logged' not in st.session_state:
    st.session_state.is_logged = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]

# --- UI: ログイン/鍵作成 ---
if not st.session_state.is_logged:
    st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>🔐 Secure Pair Note</h1>", unsafe_allow_html=True)
    
    with st.container(border=True):
        if st.button("➕ 新しいノートを作る (29桁の鍵を発行)", use_container_width=True, type="primary"):
            st.session_state.room_key = generate_29char_key()
            st.session_state.is_logged = True
            st.rerun()
            
        st.divider()
        input_key = st.text_input("🔑 29桁の秘密鍵で入る", type="password", placeholder="英数字29文字を入力")
        if st.button("ノートを開く", use_container_width=True):
            if len(input_key) == 29:
                st.session_state.room_key = input_key
                st.session_state.is_logged = True
                st.rerun()
            else:
                st.warning("鍵は正確に29桁である必要があります。")

# --- UI: メインアプリ (ログイン後) ---
else:
    room_key = st.session_state.room_key
    events, ng_dates = sync_data(room_key)

    # ヘッダー
    h_col1, h_col2 = st.columns([4, 1])
    h_col1.caption(f"🗝️ KEY: `{room_key}`")
    if h_col2.button("退出"):
        st.session_state.is_logged = False
        st.rerun()

    tab_wish, tab_sched, tab_ng = st.tabs(["📍 行きたい", "📅 予定表", "🚫 NG日"])

    # --- タブ1: 行きたい場所 (Wishlist) ---
    with tab_wish:
        with st.expander("➕ 新しい場所を追加"):
            with st.form("add_form", clear_on_submit=True):
                t = st.text_input("どこに行きたい？*")
                u = st.text_input("URL (任意)")
                m = st.text_area("メモ")
                if st.form_submit_button("保存") and t:
                    db.collection('events').add({
                        'roomKey': room_key, 'title': t, 'url': u, 'memo': m,
                        'status': 'wishlist', 'preferences': {}, 'comments': [],
                        'createdAt': datetime.now().isoformat()
                    })
                    st.rerun()

        for item in sorted(events, key=lambda x: x.get('createdAt', ''), reverse=True):
            if item['status'] == 'wishlist':
                with st.container(border=True):
                    st.markdown(f"### {item['title']}")
                    if item['url']: st.link_button("🔗 リンク", item['url'])
                    if item['memo']: st.caption(item['memo'])

                    # 気分タグ
                    my_id = st.session_state.user_id
                    prefs = item.get('preferences', {})
                    c1, c2, c3 = st.columns(3)
                    if c1.button("😍", key=f"w_{item['id']}", type="primary" if prefs.get(my_id)=="want" else "secondary"):
                        prefs[my_id] = "want"; db.collection('events').document(item['id']).update({'preferences': prefs}); st.rerun()
                    if c2.button("😐", key=f"n_{item['id']}", type="primary" if prefs.get(my_id)=="neutral" else "secondary"):
                        prefs[my_id] = "neutral"; db.collection('events').document(item['id']).update({'preferences': prefs}); st.rerun()
                    if c3.button("🗑️", key=f"del_{item['id']}"):
                        db.collection('events').document(item['id']).delete(); st.rerun()

                    # 個別チャット
                    with st.expander(f"💬 相談 ({len(item.get('comments', []))})"):
                        for chat in item.get('comments', []):
                            st.markdown(f"**{'自分' if chat['userId']==my_id else '相手'}:** {chat['text']}")
                        c_msg = st.text_input("メッセージを入力...", key=f"in_{item['id']}")
                        if st.button("送信", key=f"sb_{item['id']}"):
                            new_comments = item.get('comments', []) + [{'userId': my_id, 'text': c_msg}]
                            db.collection('events').document(item['id']).update({'comments': new_comments})
                            st.rerun()

                    # 日程確定 (NGチェック)
                    with st.expander("📅 行く日を決める"):
                        sel_d = st.date_input("予定日", key=f"sd_{item['id']}")
                        sel_t = st.selectbox("時間帯", ["終日", "午前", "午後"], key=f"st_{item['id']}")
                        
                        # NG重複判定
                        d_str = str(sel_d)
                        t_map = {"終日":"all", "午前":"morning", "午後":"afternoon"}
                        overlap = [ng for ng in ng_dates if ng['date'] == d_str]
                        blocked = any(ng['timeType'] == 'all' or ng['timeType'] == t_map[sel_t] for ng in overlap)
                        
                        for ng in overlap:
                            st.warning(f"⚠️ {'自分' if ng['userId']==my_id else '相手'}がNGにしています ({ng['timeType']})")
                        
                        if st.button("この日で確定", key=f"cf_{item['id']}", disabled=blocked, type="primary"):
                            db.collection('events').document(item['id']).update({'status': 'scheduled', 'date': d_str, 'timeType': t_map[sel_t]})
                            st.rerun()

    # --- タブ2: 予定表 ---
    with tab_sched:
        sched_items = sorted([e for e in events if e['status'] == 'scheduled'], key=lambda x: x['date'])
        for item in sched_items:
            with st.container(border=True):
                st.write(f"📅 **{item['date']}** ({item['timeType']})")
                st.subheader(item['title'])
                if st.button("リストに戻す", key=f"rev_{item['id']}"):
                    db.collection('events').document(item['id']).update({'status': 'wishlist', 'date': None})
                    st.rerun()

    # --- タブ3: NG日 ---
    with tab_ng:
        st.write("### 🚫 無理な日を登録")
        with st.form("ng_form"):
            nd = st.date_input("この日は空いていません")
            nt = st.selectbox("いつ？", ["終日", "午前", "午後"])
            if st.form_submit_button("NGを登録"):
                t_val = "all" if nt == "終日" else "morning" if nt == "午前" else "afternoon"
                db.collection('ng_dates').add({'roomKey': room_key, 'userId': st.session_state.user_id, 'date': str(nd), 'timeType': t_val})
                st.rerun()
        
        for ng in sorted(ng_dates, key=lambda x: x['date']):
            with st.container(border=True):
                c_n1, c_n2 = st.columns([4, 1])
                c_n1.write(f"❌ {ng['date']} ({ng['timeType']}) - {'自分' if ng['userId']==my_id else '相手'}")
                if ng['userId'] == my_id:
                    if c_n2.button("🗑️", key=f"ndel_{ng['id']}"):
                        db.collection('ng_dates').document(ng['id']).delete(); st.rerun()
