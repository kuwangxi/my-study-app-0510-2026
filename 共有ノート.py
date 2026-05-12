# =====================================================
# タブ
# =====================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📍 行きたい",
    "📅 予定",
    "🚫 NG日",
    "🗓️ カレンダー"
])

# =====================================================
# 行きたい
# =====================================================

with tab1:

    with st.expander("＋追加"):

        t = st.text_input("場所", key="input_title")

        u = st.text_input("URL", key="input_url")

        time_mode = st.selectbox(
            "時間設定",
            [
                "終日",
                "午前",
                "午後",
                "カスタム"
            ],
            key="time_mode"
        )

        start_time = None
        end_time = None

        if time_mode == "カスタム":

            c1, c2 = st.columns(2)

            with c1:
                start_time = st.time_input(
                    "開始",
                    key="start_time"
                )

            with c2:
                end_time = st.time_input(
                    "終了",
                    key="end_time"
                )

            time_text = (
                f"{start_time.strftime('%H:%M')}〜"
                f"{end_time.strftime('%H:%M')}"
            )

        else:

            time_text = time_mode

        m = st.text_area("メモ", key="input_memo")

        if st.button("追加", type="primary"):

            if t:

                get_events_ref().add({
                    "roomKey": room_key,
                    "title": t,
                    "url": u,
                    "memo": m,
                    "time": time_text,
                    "status": "wishlist",
                    "userName": user_name,
                    "createdAt": get_jst_now().isoformat(),
                    "comments": []
                })

                st.rerun()
with tab1:

    with st.expander("＋追加"):

        t = st.text_input("場所", key="input_title")

        u = st.text_input("URL", key="input_url")

        time_mode = st.selectbox(
            "時間設定",
            [
                "終日",
                "午前",
                "午後",
                "カスタム"
            ],
            key="time_mode"
        )

        start_time = None
        end_time = None

        if time_mode == "カスタム":

            c1, c2 = st.columns(2)

            with c1:
                start_time = st.time_input(
                    "開始",
                    key="start_time"
                )

            with c2:
                end_time = st.time_input(
                    "終了",
                    key="end_time"
                )

            time_text = (
                f"{start_time.strftime('%H:%M')}〜"
                f"{end_time.strftime('%H:%M')}"
            )

        else:

            time_text = time_mode

        m = st.text_area("メモ", key="input_memo")

        if st.button("追加", type="primary"):

            if t:

                get_events_ref().add({
                    "roomKey": room_key,
                    "title": t,
                    "url": u,
                    "memo": m,
                    "time": time_text,
                    "status": "wishlist",
                    "userName": user_name,
                    "createdAt": get_jst_now().isoformat(),
                    "comments": []
                })

                st.rerun()

    wishlist = [
        e for e in events
        if e.get("status") == "wishlist"
    ]

    wishlist = sorted(
        wishlist,
        key=lambda x: x.get("createdAt", ""),
        reverse=True
    )

    for item in wishlist:

        with st.container(border=True):

            top1, top2 = st.columns([8,1])

            with top1:
                st.markdown(f"## 📍 {item['title']}")

            with top2:

                if st.button(
                    "✏️",
                    key=f"edit_{item['id']}"
                ):
                    st.session_state.edit_id = item["id"]
                    st.rerun()

            # =====================================================
            # 編集モード
            # =====================================================

            if st.session_state.edit_id == item["id"]:

                edit_title = st.text_input(
                    "場所",
                    value=item.get("title", ""),
                    key=f"edit_title_{item['id']}"
                )

                edit_url = st.text_input(
                    "URL",
                    value=item.get("url", ""),
                    key=f"edit_url_{item['id']}"
                )

                current_time = item.get("time", "終日")

                edit_mode = st.selectbox(
                    "時間",
                    [
                        "終日",
                        "午前",
                        "午後",
                        "カスタム"
                    ],
                    index=3 if "〜" in current_time else
                    (
                        0 if current_time == "終日" else
                        1 if current_time == "午前" else
                        2 if current_time == "午後" else
                        0
                    ),
                    key=f"edit_mode_{item['id']}"
                )

                edit_time_text = edit_mode

                if edit_mode == "カスタム":

                    default_start = datetime.strptime(
                        "10:00",
                        "%H:%M"
                    ).time()

                    default_end = datetime.strptime(
                        "12:00",
                        "%H:%M"
                    ).time()

                    if "〜" in current_time:

                        try:

                            s, e = current_time.split("〜")

                            default_start = datetime.strptime(
                                s,
                                "%H:%M"
                            ).time()

                            default_end = datetime.strptime(
                                e,
                                "%H:%M"
                            ).time()

                        except:
                            pass

                    c1, c2 = st.columns(2)

                    with c1:

                        edit_start = st.time_input(
                            "開始",
                            value=default_start,
                            key=f"edit_start_{item['id']}"
                        )

                    with c2:

                        edit_end = st.time_input(
                            "終了",
                            value=default_end,
                            key=f"edit_end_{item['id']}"
                        )

                    edit_time_text = (
                        f"{edit_start.strftime('%H:%M')}〜"
                        f"{edit_end.strftime('%H:%M')}"
                    )

                edit_memo = st.text_area(
                    "メモ",
                    value=item.get("memo", ""),
                    key=f"edit_memo_{item['id']}"
                )

                c1, c2, c3 = st.columns(3)

                if c1.button(
                    "保存",
                    key=f"save_{item['id']}"
                ):

                    get_events_ref().document(item["id"]).update({
                        "title": edit_title,
                        "url": edit_url,
                        "memo": edit_memo,
                        "time": edit_time_text
                    })

                    st.session_state.edit_id = None

                    st.rerun()

                if c2.button(
                    "キャンセル",
                    key=f"cancel_{item['id']}"
                ):

                    st.session_state.edit_id = None

                    st.rerun()

                if c3.button(
                    "削除",
                    key=f"delete_{item['id']}"
                ):

                    get_events_ref().document(item["id"]).delete()

                    st.session_state.edit_id = None

                    st.rerun()

            # =====================================================
            # 通常表示
            # =====================================================

            else:

                if item.get("time"):
                    st.write(f"🕒 {item['time']}")

                if item.get("url"):
                    st.markdown(
                        f"[🔗 リンク]({item['url']})"
                    )

                if item.get("memo"):
                    st.info(item["memo"])

                comments = item.get("comments", [])

                if comments:

                    last_comment = comments[-1]

                    color = last_comment.get("color", "#666")

                    st.markdown(
                        f"""
<div class='last-message'
style='border-left:5px solid {color};'>
<b>{last_comment['userName']}</b><br>
{last_comment['text']}
</div>
""",
                        unsafe_allow_html=True
                    )

                with st.expander("💬 コメント"):

                    for c in comments:

                        color = c.get("color", "#666")

                        st.markdown(
                            f"""
<div class='comment-box'
style='border-left:5px solid {color};'>
<b>{c['userName']}</b><br>
{c['text']}
</div>
""",
                            unsafe_allow_html=True
                        )

                    with st.form(
                        key=f"comment_form_{item['id']}",
                        clear_on_submit=True
                    ):

                        new_comment = st.text_input("コメント")

                        submitted = st.form_submit_button("送信")

                        if submitted and new_comment:

                            get_events_ref().document(item["id"]).update({
                                "comments": firestore.ArrayUnion([
                                    {
                                        "userName": user_name,
                                        "text": new_comment,
                                        "createdAt": get_jst_now().isoformat(),
                                        "color": st.session_state.user_color
                                    }
                                ])
                            })

                            st.rerun()

                st.divider()

                fix_date = st.date_input(
                    "予定日",
                    key=f"fix_date_{item['id']}"
                )

                if st.button(
                    "📅 予定に追加",
                    key=f"fix_btn_{item['id']}"
                ):

                    get_events_ref().document(item["id"]).update({
                        "status": "scheduled",
                        "date": str(fix_date)
                    })

                    st.rerun()
