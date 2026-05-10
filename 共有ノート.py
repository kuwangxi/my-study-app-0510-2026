import streamlit as st
import uuid
import random
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(page_title="Secure Pair Note", layout="centered")

# --- 1. データ構造と状態の初期化 (st.session_state) ---
# 本来のFirebaseの代わりに、アプリが動いている間データを保持する仕組みです
if 'is_logged' not in st.session_state:
    st.session_state.is_logged = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = "USER-" + str(uuid.uuid4())[:8]
if 'room_key' not in st.session_state:
    st.session_state.room_key = ""
if 'events' not in st.session_state:
    st.session_state.events = []
if 'ng_dates' not in st.session_state:
    st.session_state.ng_dates = []

# --- 2. 補助関数 (ロジック部分) ---

def generate_secure_key():
    """LOV-XXXX-XXXX-XXXX 形式の鍵を生成"""
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    return f"LOV-{' '.join(parts)}"

def logout():
    """状態をリセットしてログアウト"""
    st.session_state.is_logged = False
    st.session_state.room_key = ""
    st.rerun()

# --- 3. メインUI ---

# --- A. ログイン・部屋作成画面 ---
if not st.session_state.is_logged:
    st.markdown("<h1 style='text-align: center; color: #f43f5e;'>Secure Pair Note</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>秘密鍵による共有空間</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("➕ 新しいノートを作る", use_container_width=True, type="primary"):
            st.session_state.room_key = generate_secure_key()
            st.session_state.is_logged = True
            st.rerun()
            
        st.divider()
        
        input_key = st.text_input("🔑 秘密鍵で入る", placeholder="LOV-XXXX-XXXX-XXXX").strip().upper()
        if st.button("参加する", use_container_width=True, disabled=not input_key.startswith('LOV-')):
            st.session_state.room_key = input_key
            st.session_state.is_logged = True
            st.rerun()

# --- B. アプリ本体画面 ---
else:
    # ヘッダー
    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        st.subheader("🔒 ふたりの共有ノート")
    with h_col2:
        if st.button("ログアウト", key="logout_btn"):
            logout()
    
    st.info(f"このノートの鍵: **{st.session_state.room_key}** (パートナーに教えて共有しましょう)")

    # タブ設定
    tab_wish, tab_sched, tab_ng = st.tabs(["📍 行きたい", "📅 予定", "🚫 NG日"])

    # --- タブ1: 行きたい (Wishlist) ---
    with tab_wish:
        # 新規追加フォーム
        with st.expander("➕ 新しい場所を追加"):
            # required=Trueを使わずに、ボタン側で制御します
            with st.form("add_form", clear_on_submit=True):
                new_title = st.text_input("どこに行きたい？*")
                new_url = st.text_input("URL (任意)")
                new_memo = st.text_area("メモ...")
                
                submitted = st.form_submit_button("追加する", type="primary")
                if submitted:
                    if not new_title:
                        st.error("タイトルを入力してください！")
                    else:
                        st.session_state.events.append({
                            'id': str(uuid.uuid4()),
                            'title': new_title,
                            'url': new_url,
                            'memo': new_memo,
                            'status': 'wishlist',
                            'date': None,
                            'timeType': None,
                            'customTime': '',
                            'preferences': {},
                            'comments': [],
                            'createdAt': datetime.now().isoformat()
                        })
                        st.rerun()

        # リスト表示
        wish_items = [e for e in st.session_state.events if e['status'] == 'wishlist']
        for item in reversed(wish_items):
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"### {item['title']}")
                    if item['url']:
                        st.markdown(f"[🔗 参考リンク]({item['url']})")
                    if item['memo']:
                        st.caption(item['memo'])
                with c2:
                    if st.button("🗑️", key=f"del_{item['id']}"):
                        st.session_state.events = [e for e in st.session_state.events if e['id'] != item['id']]
                        st.rerun()

                # --- Mood (気分タグ) ---
                st.write("▼ Your Mood")
                my_id = st.session_state.user_id
                my_pref = item['preferences'].get(my_id)
                
                m1, m2, m3 = st.columns(3)
                with m1:
                    if st.button("😍 行きたい", key=f"w_{item['id']}", type="primary" if my_pref=="want" else "secondary", use_container_width=True):
                        item['preferences'][my_id] = "want"; st.rerun()
                with m2:
                    if st.button("😐 どっちでも", key=f"n_{item['id']}", type="primary" if my_pref=="neutral" else "secondary", use_container_width=True):
                        item['preferences'][my_id] = "neutral"; st.rerun()
                with m3:
                    if st.button("🙅 うーん", key=f"no_{item['id']}", type="primary" if my_pref=="no" else "secondary", use_container_width=True):
                        item['preferences'][my_id] = "no"; st.rerun()

                # 相手の気分表示 (自分以外のデータがあれば表示)
                partner_pref = next((v for k, v in item['preferences'].items() if k != my_id), None)
                if partner_pref:
                    p_text = '😍 行きたい！' if partner_pref == 'want' else '😐 どっちでも' if partner_pref == 'neutral' else '🙅‍♂️ うーん'
                    st.info(f"相手の気分: {p_text}")

                # --- メッセージ相談 ---
                with st.expander(f"💬 メッセージ相談 ({len(item['comments'])})"):
                    for c in item['comments']:
                        role = "user" if c['userId'] == my_id else "assistant"
                        st.chat_message(role).write(c['text'])
                    
                    c_input = st.text_input("相談を送る...", key=f"ci_{item['id']}")
                    if st.button("送信", key=f"cb_{item['id']}"):
                        if c_input:
                            item['comments'].append({'userId': my_id, 'text': c_input})
                            st.rerun()

                # --- 日程設定 (NGチェック付き) ---
                with st.expander("📅 行く日をきめる"):
                    sel_date = st.date_input("予定日", key=f"sd_{item['id']}")
                    sel_time = st.selectbox("時間帯", ["終日", "午前", "午後", "カスタム"], key=f"st_{item['id']}")
                    c_time = st.text_input("具体的な時間", key=f"sc_{item['id']}") if sel_time == "カスタム" else ""
                    
                    # NG重複チェック
                    date_str = str(sel_date)
                    time_map = {"終日":"all", "午前":"morning", "午後":"afternoon", "カスタム":"custom"}
                    sel_time_val = time_map[sel_time]
                    
                    overlapping = [ng for ng in st.session_state.ng_dates if ng['date'] == date_str]
                    is_blocked = any(ng['timeType'] == 'all' or ng['timeType'] == sel_time_val for ng in overlapping)
                    
                    if overlapping:
                        for ng in overlapping:
                            who = "あなた" if ng['userId'] == my_id else "相手"
                            st.warning(f"⚠️ {who}に予定が入っています")

                    if st.button("この日で確定", key=f"conf_{item['id']}", disabled=is_blocked, type="primary"):
                        item['status'] = 'scheduled'
                        item['date'] = date_str
                        item['timeType'] = sel_time_val
                        item['customTime'] = c_time
                        st.rerun()

    # --- タブ2: 予定 (Schedule) ---
    with tab_sched:
        sched_items = sorted([e for e in st.session_state.events if e['status'] == 'scheduled'], key=lambda x: x['date'])
        if not sched_items:
            st.write("まだ確定した予定はありません。")
        for item in sched_items:
            with st.container(border=True):
                col_date, col_main = st.columns([1, 4])
                with col_date:
                    dt = datetime.strptime(item['date'], '%Y-%m-%d')
                    st.markdown(f"## {dt.day}")
                    st.caption(f"{dt.month}月")
                with col_main:
                    st.markdown(f"**{item['title']}**")
                    t_show = "終日" if item['timeType'] == 'all' else "午前" if item['timeType'] == 'morning' else "午後" if item['timeType'] == 'afternoon' else item['customTime']
                    st.caption(f"🕒 {t_show}")
                    if st.button("リストに戻す", key=f"rev_{item['id']}"):
                        item['status'] = 'wishlist'; st.rerun()

    # --- タブ3: NG日 ---
    with tab_ng:
        st.markdown("### 🚫 NG予定を登録")
        with st.form("ng_form", clear_on_submit=True):
            ng_d = st.date_input("この日は無理！")
            ng_t = st.selectbox("いつ？", ["終日", "午前", "午後"])
            if st.form_submit_button("NGリストに追加"):
                t_val = "all" if ng_t == "終日" else "morning" if ng_t == "午前" else "afternoon"
                st.session_state.ng_dates.append({
                    'id': str(uuid.uuid4()),
                    'userId': st.session_state.user_id,
                    'date': str(ng_d),
                    'timeType': t_val
                })
                st.rerun()
        
        st.divider()
        for ng in sorted(st.session_state.ng_dates, key=lambda x: x['date']):
            c_n1, c_n2 = st.columns([4, 1])
            with c_n1:
                who = "🔴 相手" if ng['userId'] != st.session_state.user_id else "🔵 自分"
                t_disp = "終日" if ng['timeType'] == 'all' else "午前" if ng['timeType'] == 'morning' else "午後"
                st.write(f"{who}: {ng['date']} ({t_disp})")
            with c_n2:
                if ng['userId'] == st.session_state.user_id:
                    if st.button("🗑️", key=f"ngdel_{ng['id']}"):
                        st.session_state.ng_dates = [n for n in st.session_state.ng_dates if n['id'] != ng['id']]
                        st.rerun()

# フッター
st.markdown("---")
st.caption("※データはブラウザをリロードしたり閉じたりするとリセットされます（メモリ保存版）。")
