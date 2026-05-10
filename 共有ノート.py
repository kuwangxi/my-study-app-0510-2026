import streamlit as st
import uuid
from datetime import datetime

# --- 初期設定とデータ構造の準備 ---
# Firebaseの代わりに、アプリのメモリ上にデータを保存します
if 'is_logged' not in st.session_state:
    st.session_state.is_logged = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'room_key' not in st.session_state:
    st.session_state.room_key = ""
if 'events' not in st.session_state:
    st.session_state.events = []
if 'ng_dates' not in st.session_state:
    st.session_state.ng_dates = []

def generate_secure_key():
    import random
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    return f"LOV-{'-'.join(parts)}"

# --- アクション用コールバック関数 ---
def create_room():
    st.session_state.room_key = generate_secure_key()
    st.session_state.user_id = str(uuid.uuid4()) # 擬似的なユーザーID
    st.session_state.is_logged = True

def join_room(input_key):
    if input_key.startswith("LOV-"):
        st.session_state.room_key = input_key
        st.session_state.user_id = str(uuid.uuid4())
        st.session_state.is_logged = True

def logout():
    st.session_state.is_logged = False
    st.session_state.room_key = ""
    st.session_state.events = []
    st.session_state.ng_dates = []

def add_event(title, url, memo):
    if title:
        st.session_state.events.append({
            'id': str(uuid.uuid4()),
            'roomKey': st.session_state.room_key,
            'title': title,
            'url': url,
            'memo': memo,
            'status': 'wishlist',
            'date': None,
            'timeType': None,
            'customTime': '',
            'preferences': {},
            'comments': [],
            'createdAt': datetime.now().isoformat()
        })

def delete_event(event_id):
    st.session_state.events = [e for e in st.session_state.events if e['id'] != event_id]

def update_preference(event_id, pref):
    for e in st.session_state.events:
        if e['id'] == event_id:
            e['preferences'][st.session_state.user_id] = pref

def add_comment(event_id, text):
    if text:
        for e in st.session_state.events:
            if e['id'] == event_id:
                e['comments'].append({
                    'userId': st.session_state.user_id,
                    'text': text,
                    'createdAt': datetime.now().isoformat()
                })

def move_to_schedule(event_id, date, time_type, custom_time):
    for e in st.session_state.events:
        if e['id'] == event_id:
            e['status'] = 'scheduled'
            e['date'] = str(date)
            e['timeType'] = time_type
            e['customTime'] = custom_time

def back_to_wishlist(event_id):
    for e in st.session_state.events:
        if e['id'] == event_id:
            e['status'] = 'wishlist'
            e['date'] = None
            e['timeType'] = None
            e['customTime'] = ''

def add_ng_date(date, time_type):
    if date:
        st.session_state.ng_dates.append({
            'id': str(uuid.uuid4()),
            'roomKey': st.session_state.room_key,
            'userId': st.session_state.user_id,
            'date': str(date),
            'timeType': time_type,
            'createdAt': datetime.now().isoformat()
        })

def delete_ng_date(ng_id):
    st.session_state.ng_dates = [ng for ng in st.session_state.ng_dates if ng['id'] != ng_id]


# ==========================================
# UI 描画部分
# ==========================================

if not st.session_state.is_logged:
    # ログイン画面
    st.markdown("<h1 style='text-align: center; color: #f43f5e;'>Secure Pair Note</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>秘密鍵による共有空間</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.button("➕ 新しいノートを作る", on_click=create_room, use_container_width=True, type="primary")
        st.divider()
        input_key = st.text_input("🔑 秘密鍵で入る", placeholder="LOV-XXXX-XXXX-XXXX")
        if st.button("参加する", use_container_width=True, disabled=not input_key.startswith('LOV-')):
            join_room(input_key)

else:
    # メイン画面
    # ヘッダー領域
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.subheader("🔒 ふたりの共有ノート")
    with col_h2:
        st.markdown(f"**KEY:** `{st.session_state.room_key}`")
    
    # タブの作成
    tab_wish, tab_sched, tab_ng = st.tabs(["📍 行きたい", "📅 予定", "🚫 NG日"])

    # ----------------------------------------
    # タブ1: 行きたい (Wishlist)
    # ----------------------------------------
    with tab_wish:
        with st.expander("➕ 新しい場所を追加"):
            with st.form("add_form", clear_on_submit=True):
                new_title = st.text_input("どこに行きたい？*", required=True)
                new_url = st.text_input("URL (任意)")
                new_memo = st.text_area("メモ...")
                if st.form_submit_button("追加する", type="primary"):
                    add_event(new_title, new_url, new_memo)
                    st.rerun()

        wishlist_items = [e for e in st.session_state.events if e['status'] == 'wishlist']
        
        for item in wishlist_items:
            st.markdown("---")
            col_t1, col_t2 = st.columns([4, 1])
            with col_t1:
                st.markdown(f"### {item['title']}")
                if item['url']:
                    st.markdown(f"[🔗 参考リンク]({item['url']})")
                if item['memo']:
                    st.caption(item['memo'])
            with col_t2:
                if st.button("🗑️", key=f"del_{item['id']}"):
                    delete_event(item['id'])
                    st.rerun()

            # Mood (気分)
            st.write("▼ Your Mood")
            my_pref = item['preferences'].get(st.session_state.user_id)
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("😍 行きたい", key=f"w_{item['id']}", type="primary" if my_pref=="want" else "secondary"):
                    update_preference(item['id'], "want")
                    st.rerun()
            with c2:
                if st.button("😐 どっちでも", key=f"n_{item['id']}", type="primary" if my_pref=="neutral" else "secondary"):
                    update_preference(item['id'], "neutral")
                    st.rerun()
            with c3:
                if st.button("🙅 うーん", key=f"no_{item['id']}", type="primary" if my_pref=="no" else "secondary"):
                    update_preference(item['id'], "no")
                    st.rerun()

            # 相手の気分（擬似的に表示確認するためのロジック）
            partner_uid = next((uid for uid in item['preferences'].keys() if uid != st.session_state.user_id), None)
            if partner_uid:
                p_pref = item['preferences'][partner_uid]
                pref_text = '😍 行きたい！' if p_pref == 'want' else '😐 どっちでも' if p_pref == 'neutral' else '🙅‍♂️ うーん'
                st.info(f"相手: {pref_text}")

            # コメント機能
            with st.expander(f"💬 メッセージ相談 ({len(item['comments'])})"):
                for c in item['comments']:
                    if c['userId'] == st.session_state.user_id:
                        st.chat_message("user", avatar="🙋").write(c['text'])
                    else:
                        st.chat_message("assistant", avatar="🤝").write(c['text'])
                
                # 新規コメント入力
                new_comment = st.text_input("相談する...", key=f"c_in_{item['id']}")
                if st.button("送信", key=f"c_btn_{item['id']}"):
                    add_comment(item['id'], new_comment)
                    st.rerun()

            # 日程設定（NGチェック付き）
            with st.expander("➡️ 行く日をきめる (日程設定)"):
                sel_date = st.date_input("日付を選択", key=f"d_{item['id']}")
                sel_time = st.selectbox("時間帯", ["終日", "午前", "午後", "時間指定"], key=f"t_{item['id']}")
                custom_t = st.text_input("時間指定 (例: 13:00〜17:00)", key=f"ct_{item['id']}") if sel_time == "時間指定" else ""
                
                # NG日重複チェック処理
                time_val = 'all' if sel_time == "終日" else 'morning' if sel_time == "午前" else 'afternoon' if sel_time == "午後" else 'custom'
                overlapping_ngs = [ng for ng in st.session_state.ng_dates if ng['date'] == str(sel_date)]
                is_all_day_ng = any(ng['timeType'] == 'all' for ng in overlapping_ngs)
                
                if overlapping_ngs:
                    ng_msgs = []
                    for ng in overlapping_ngs:
                        who = "あなた" if ng['userId'] == st.session_state.user_id else "相手"
                        t_lbl = "午前中" if ng['timeType'] == 'morning' else "午後" if ng['timeType'] == 'afternoon' else "終日"
                        ng_msgs.append(f"{who}に{t_lbl}の予定があります")
                    st.warning(" / ".join(ng_msgs))

                if st.button("確定する", key=f"conf_{item['id']}", type="primary", disabled=is_all_day_ng):
                    move_to_schedule(item['id'], sel_date, time_val, custom_t)
                    st.rerun()

    # ----------------------------------------
    # タブ2: 予定 (Schedule)
    # ----------------------------------------
    with tab_sched:
        scheduled_items = sorted([e for e in st.session_state.events if e['status'] == 'scheduled'], key=lambda x: x['date'])
        if not scheduled_items:
            st.write("確定した予定はありません。")
            
        for item in scheduled_items:
            # 視覚的なリスト表示
            with st.container(border=True):
                col_d, col_i = st.columns([1, 4])
                with col_d:
                    dt = datetime.strptime(item['date'], '%Y-%m-%d')
                    st.markdown(f"### {dt.day}")
                    st.caption(f"{dt.month}月")
                with col_i:
                    t_label = '午前中' if item['timeType'] == 'morning' else '午後' if item['timeType'] == 'afternoon' else item['customTime'] if item['timeType'] == 'custom' else '終日'
                    st.caption(f"🕒 {t_label}")
                    st.markdown(f"**{item['title']}**")
                    
                    c_btn1, c_btn2 = st.columns(2)
                    with c_btn1:
                        if st.button("リストに戻す", key=f"back_{item['id']}"):
                            back_to_wishlist(item['id'])
                            st.rerun()
                    with c_btn2:
                        if st.button("削除", key=f"sdel_{item['id']}"):
                            delete_event(item['id'])
                            st.rerun()

    # ----------------------------------------
    # タブ3: NG日
    # ----------------------------------------
    with tab_ng:
        with st.form("ng_form", clear_on_submit=True):
            st.markdown("**🚫 NG予定の登録**")
            col_ng1, col_ng2 = st.columns(2)
            with col_ng1:
                ng_d = st.date_input("日付")
            with col_ng2:
                ng_t_ja = st.selectbox("時間帯", ["終日", "午前", "午後"])
                ng_t = 'all' if ng_t_ja == "終日" else 'morning' if ng_t_ja == "午前" else 'afternoon'
            
            if st.form_submit_button("NG日を追加する", type="primary"):
                add_ng_date(ng_d, ng_t)
                st.rerun()

        st.markdown("---")
        sorted_ng = sorted(st.session_state.ng_dates, key=lambda x: x['date'])
        for ng in sorted_ng:
            c1, c2 = st.columns([4, 1])
            with c1:
                t_lbl = "終日" if ng['timeType'] == 'all' else "午前" if ng['timeType'] == 'morning' else "午後"
                who = "相手の予定" if ng['userId'] != st.session_state.user_id else ""
                st.write(f"📅 {ng['date'].replace('-', '/')}  |  ⏰ {t_lbl} {f'🔴{who}' if who else ''}")
            with c2:
                if ng['userId'] == st.session_state.user_id:
                    if st.button("🗑️", key=f"ng_del_{ng['id']}"):
                        delete_ng_date(ng['id'])
                        st.rerun()

    st.markdown("---")
    if st.button("ログアウト", on_click=logout):
        pass
