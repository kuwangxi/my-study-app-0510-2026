# =====================================================
# 追加CSS
# 既存CSSの一番下へ追加
# =====================================================

.calendar-wrap {
    width:100%;
    overflow-x:auto;
}

.calendar-grid {
    display:grid;
    grid-template-columns:repeat(7, minmax(110px,1fr));
    gap:1px;
    background:#222;
    border:1px solid #222;
    border-radius:12px;
    overflow:hidden;
}

.calendar-head {
    background:#111;
    text-align:center;
    padding:10px 4px;
    font-weight:bold;
    color:#aaa;
}

.calendar-cell {
    background:#000;
    min-height:140px;
    padding:6px;
    position:relative;
}

.today-cell {
    background:#171717;
}

.day-number {
    font-size:18px;
    margin-bottom:6px;
    font-weight:bold;
}

.sat {
    color:#4d8dff;
}

.sun {
    color:#ff5b5b;
}

.other-month {
    opacity:0.35;
}

.calendar-event {
    font-size:11px;
    border-radius:6px;
    padding:3px 6px;
    margin-bottom:4px;
    overflow:hidden;
    white-space:nowrap;
    text-overflow:ellipsis;
    color:white;
}

.event-normal {
    background:#1f8f5f;
}

.event-ng {
    background:#b03b3b;
}

@media (max-width:768px){

    .calendar-grid{
        grid-template-columns:repeat(7, minmax(52px,1fr));
    }

    .calendar-cell{
        min-height:90px;
        padding:4px;
    }

    .day-number{
        font-size:13px;
    }

    .calendar-event{
        font-size:8px;
        padding:2px 4px;
    }
}

# =====================================================
# 行きたいタブ 修正版
# with tab1: の中を全部これに置換
# =====================================================

with tab1:

    with st.expander("＋追加"):

        t = st.text_input("場所", key="input_title")

        u = st.text_input("URL", key="input_url")

        tm = st.time_input("時間")

        m = st.text_area("メモ", key="input_memo")

        if st.button("追加", type="primary"):

            if t:

                get_events_ref().add({
                    "roomKey": room_key,
                    "title": t,
                    "url": u,
                    "memo": m,
                    "time": tm.strftime("%H:%M"),
                    "status": "wishlist",
                    "userName": user_name,
                    "createdAt": get_jst_now().isoformat(),
                    "comments": []
                })

                st.session_state.clear_wish_inputs = True

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

                edit_time = st.text_input(
                    "時間",
                    value=item.get("time", ""),
                    key=f"edit_time_{item['id']}"
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
                        "time": edit_time,
                        "memo": edit_memo
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

                    color = last_comment.get(
                        "color",
                        "#666"
                    )

                    st.markdown(
                        f'''
<div class="last-message"
style="border-left:5px solid {color};">
<b>{last_comment["userName"]}</b><br>
{last_comment["text"]}
</div>
''',
                        unsafe_allow_html=True
                    )

                with st.expander("💬 コメント"):

                    for c in comments:

                        color = c.get("color", "#666")

                        st.markdown(
                            f'''
<div class="comment-box"
style="border-left:5px solid {color};">
<b>{c["userName"]}</b><br>
{c["text"]}
</div>
''',
                            unsafe_allow_html=True
                        )

                    with st.form(
                        key=f"comment_{item['id']}",
                        clear_on_submit=True
                    ):

                        msg = st.text_input("コメント")

                        submit = st.form_submit_button("送信")

                        if submit and msg:

                            get_events_ref().document(item["id"]).update({
                                "comments": firestore.ArrayUnion([
                                    {
                                        "userName": user_name,
                                        "text": msg,
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

# =====================================================
# NGタブ修正版
# with tab3: の中を全部これに置換
# =====================================================

with tab3:

    st.subheader("🚫 NG日")

    nd = st.date_input("日付")

    nt = st.time_input("時間", key="ng_time")

    nr = st.text_input("理由", key="ng_reason")

    if st.button("NG登録"):

        get_ng_ref().add({
            "roomKey": room_key,
            "userName": user_name,
            "date": str(nd),
            "time": nt.strftime("%H:%M"),
            "reason": nr
        })

        st.session_state.clear_ng_inputs = True

        st.rerun()

    st.divider()

    for n in ng_dates:

        with st.container(border=True):

            st.write(
                f"🚫 {n['date']} {n.get('time','')} {n.get('reason','')}"
            )

# =====================================================
# カレンダー修正版
# with tab4: の中を全部これに置換
# =====================================================

with tab4:

    now = get_jst_now()

    year = now.year
    month = now.month
    today = now.day

    st.subheader(f"🗓️ {year}年{month}月")

    cal = calendar.Calendar(firstweekday=0)

    month_days = list(
        cal.monthdatescalendar(year, month)
    )

    week_names = [
        "月", "火", "水",
        "木", "金", "土", "日"
    ]

    st.markdown(
        "<div class='calendar-wrap'><div class='calendar-grid'>",
        unsafe_allow_html=True
    )

    for w in week_names:

        st.markdown(
            f"<div class='calendar-head'>{w}</div>",
            unsafe_allow_html=True
        )

    for week in month_days:

        for day in week:

            target = day.strftime("%Y-%m-%d")

            day_events = [
                e for e in events
                if e.get("date") == target
            ]

            day_ng = [
                n for n in ng_dates
                if n.get("date") == target
            ]

            classes = []

            if day.month != month:
                classes.append("other-month")

            if (
                day.day == today and
                day.month == month
            ):
                classes.append("today-cell")

            weekday = day.weekday()

            num_class = ""

            if weekday == 5:
                num_class = "sat"

            elif weekday == 6:
                num_class = "sun"

            html = f"""
<div class="calendar-cell {' '.join(classes)}">
<div class="day-number {num_class}">
{day.day}
</div>
"""

            for e in day_events[:3]:

                html += f"""
<div class="calendar-event event-normal">
{e.get("time","")} {e["title"]}
</div>
"""

            for n in day_ng[:2]:

                html += f"""
<div class="calendar-event event-ng">
🚫 {n.get("time","")}
</div>
"""

            html += "</div>"

            st.markdown(
                html,
                unsafe_allow_html=True
            )

    st.markdown(
        "</div></div>",
        unsafe_allow_html=True
    )
