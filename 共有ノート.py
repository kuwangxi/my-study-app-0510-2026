import streamlit as st
import pandas as pd
from datetime import datetime

# --- アプリの設定 ---
st.set_page_config(page_title="Secure Pair Note", layout="centered")

# --- データの初期化（セッションが切れるとリセットされますが、まずは動かすことを優先します） ---
if 'wishlist' not in st.session_state:
    st.session_state.wishlist = []
if 'ng_dates' not in st.session_state:
    st.session_state.ng_dates = []

# --- サイドバー：設定 ---
with st.sidebar:
    st.title("🔐 設定")
    user_name = st.text_input("あなたの名前", value="ユーザー1")
    room_key = st.text_input("秘密鍵", value="LOV-XXXX", help="パートナーと同じ鍵を入力してください")
    st.divider()
    if st.button("全データをリセット"):
        st.session_state.wishlist = []
        st.session_state.ng_dates = []
        st.rerun()

# --- メイン画面 ---
st.title(f"🗒️ {user_name} の共有ノート")
st.caption(f"Room Key: {room_key}")

# タブの作成
tab1, tab2, tab3 = st.tabs(["📍 行きたい", "📅 予定", "🙅‍♂️ NG日"])

# --- TAB 1: 行きたいリスト ---
with tab1:
    st.subheader("新しい場所を追加")
    with st.form("add_wishlist", clear_on_submit=True):
        new_title = st.text_input("どこに行きたい？")
        new_url = st.text_input("参考URL（任意）")
        new_memo = st.text_area("メモ")
        if st.form_submit_button("リストに追加"):
            if new_title:
                st.session_state.wishlist.append({
                    "title": new_title,
                    "url": new_url,
                    "memo": new_memo,
                    "status": "wishlist",
                    "date": None
                })
                st.success("追加しました！")
            else:
                st.error("タイトルを入力してください")

    st.divider()
    for i, item in enumerate(st.session_state.wishlist):
        if item["status"] == "wishlist":
            with st.expander(f"✨ {item['title']}"):
                if item["url"]:
                    st.link_button("リンクを開く", item["url"])
                st.write(f"メモ: {item['memo']}")
                
                # 予定へ移動
                plan_date = st.date_input(f"行く日を決める ({item['title']})", key=f"date_{i}")
                if st.button(f"この日に決定！", key=f"btn_{i}"):
                    item["date"] = plan_date
                    item["status"] = "scheduled"
                    st.rerun()

# --- TAB 2: 予定リスト ---
with tab2:
    st.subheader("これからの予定")
    scheduled_items = [item for item in st.session_state.wishlist if item["status"] == "scheduled"]
    if not scheduled_items:
        st.info("まだ予定はありません。")
    else:
        for item in scheduled_items:
            st.info(f"📅 **{item['date']}** : {item['title']}")

# --- TAB 3: NG日リスト ---
with tab3:
    st.subheader("予定が合わない日を登録")
    with st.form("add_ng", clear_on_submit=True):
        ng_date = st.date_input("ダメな日")
        ng_reason = st.text_input("理由（任意）")
        if st.form_submit_button("NG日を登録"):
            st.session_state.ng_dates.append({"date": ng_date, "reason": ng_reason})
            st.rerun()
    
    st.divider()
    for ng in st.session_state.ng_dates:
        st.warning(f"❌ {ng['date']} ({ng['reason']})")
