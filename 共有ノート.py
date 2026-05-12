# ==========================================
# 追加import
# ==========================================

import calendar

# ==========================================
# CSSをこのまま追加
# st.markdown("""<style> ... </style>""")
# の中に追加してください
# ==========================================

.calendar-root {
    margin-top: 10px;
}

.calendar-week-header {
    text-align: center;
    font-weight: bold;
    color: #999;
    margin-bottom: 8px;
}

.calendar-cell {
    border: 1px solid rgba(255,255,255,0.05);
    min-height: 120px;
    border-radius: 12px;
    padding: 6px;
    margin-bottom: 8px;
    background: rgba(255,255,255,0.02);
}

.calendar-day-number {
    font-size: 15px;
    font-weight: bold;
    margin-bottom: 8px;
}

.calendar-today-number {
    background: white;
    color: black;
    width: 28px;
    height: 28px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.calendar-event-pill {
    background: #16a34a;
    color: white;
    padding: 3px 8px;
    border-radius: 6px;
    margin-bottom: 4px;
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.calendar-ng-pill {
    background: #dc2626;
    color: white;
    padding: 3px 8px;
    border-radius: 6px;
    margin-bottom: 4px;
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.calendar-more {
    color: #aaa;
    font-size: 11px;
    margin-top: 4px;
}

.new-badge {
    background: #ef4444;
    color: white;
    padding: 2px 6px;
    border-radius: 999px;
    font-size: 11px;
    margin-left: 6px;
}

# ==========================================
# タブ変更
# 現在の
# tab1, tab2, tab3 = st.tabs(...)
# をこれに置換
# ==========================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📍 行きたい",
    "📅 予定",
    "🚫 NG日",
    "🗓️ カレンダー"
])

# ==========================================
# 「行きたい」並び順変更
# この部分
#
# for item in [e for e in events if e.get("status") == "wishlist"]:
#
# を全部これに変更
# ==========================================

wishlist_items = [e for e in events if e.get("status") == "wishlist"]

def get_last_activity(item):

    comments = item.get("comments", [])

    if comments:

        latest_comment = max(
            comments,
            key=lambda x: x.get("createdAt", "")
        )

        return latest_comment.get("createdAt", "")

    return item.get("createdAt", "")

wishlist_items = sorted(
    wishlist_items,
    key=lambda x: get_last_activity(x),
    reverse=True
)

for item in wishlist_items:

# ==========================================
# 行きたい NEWバッジ
# この部分
#
# c1.markdown(f"### {time_disp}{item['title']}", unsafe_allow_html=True)
#
# をこれに変更
# ==========================================

comments = item.get("comments", [])

new_badge = ""

if comments:

    latest_comment = max(
        comments,
        key=lambda x: x.get("createdAt", "")
    )

    latest_user = latest_comment.get("userName", "")

    if latest_user != user_name:
        new_badge = "<span class='new-badge'>NEW</span>"

c1.markdown(
    f"### {time_disp}{item['title']} {new_badge}",
    unsafe_allow_html=True
)

# ==========================================
# 「予定」タブからカレンダー削除
#
# with tab2:
#
# の中にある
#
# if st.session_state.show_summary:
#
# から
#
# st.divider()
#
# まで全部削除してください
# ==========================================

# ==========================================
# 新しいカレンダータブ追加
# 一番下に追加してください
# ==========================================

with tab4:

    current_date = get_jst_now().date()

    selected_month = st.date_input(
        "表示月",
        value=current_date,
        key="calendar_month_picker"
    )

    year = selected_month.year
    month = selected_month.month

    st.markdown(f"# {year}年{month}月")

    cal = calendar.monthcalendar(year, month)

    weekday_labels = ["月", "火", "水", "木", "金", "土", "日"]

    st.markdown("<div class='calendar-root'>", unsafe_allow_html=True)

    header_cols = st.columns(7)

    for i, day_name in enumerate(weekday_labels):

        header_cols[i].markdown(
            f"<div class='calendar-week-header'>{day_name}</div>",
            unsafe_allow_html=True
        )

    for week in cal:

        cols = st.columns(7)

        for idx, day in enumerate(week):

            with cols[idx]:

                if day == 0:
                    st.empty()
                    continue

                target_date = datetime(year, month, day).date()
                target_str = str(target_date)

                is_today = target_date == current_date

                day_events = [

                    e for e in events

                    if e.get("status") == "scheduled"
                    and e.get("date") == target_str

                ]

                day_ng = [

                    n for n in ng_dates

                    if n.get("date") == target_str

                ]

                day_html = ""

                if is_today:

                    day_html += f"""
                    <div class='calendar-day-number'>
                        <div class='calendar-today-number'>
                            {day}
                        </div>
                    </div>
                    """

                else:

                    day_html += f"""
                    <div class='calendar-day-number'>
                        {day}
                    </div>
                    """

                visible_count = 0

                sorted_events = sorted(
                    day_events,
                    key=lambda x: x.get("time") or ""
                )

                for ev in sorted_events[:3]:

                    title = ev.get("title", "")

                    day_html += f"""
                    <div class='calendar-event-pill'>
                        {title}
                    </div>
                    """

                    visible_count += 1

                for ng in day_ng[:2]:

                    reason = ng.get("reason", "NG")

                    day_html += f"""
                    <div class='calendar-ng-pill'>
                        🚫 {reason}
                    </div>
                    """

                    visible_count += 1

                total_items = len(day_events) + len(day_ng)

                if total_items > visible_count:

                    remain = total_items - visible_count

                    day_html += f"""
                    <div class='calendar-more'>
                        +{remain}件
                    </div>
                    """

                st.markdown(

                    f"""
                    <div class='calendar-cell'>
                        {day_html}
                    </div>
                    """,

                    unsafe_allow_html=True

                )

                if day_events or day_ng:

                    with st.expander(f"{month}/{day} の詳細"):

                        if day_events:

                            st.markdown("### 📍予定")

                            for ev in sorted_events:

                                t = ev.get("time", "時間未定")

                                st.write(
                                    f"• {t} - {ev.get('title','')}"
                                )

                        if day_ng:

                            st.markdown("### 🚫 NG")

                            for ng in day_ng:

                                t = ng.get("time", "時間未定")

                                st.write(
                                    f"• {t} - {ng.get('userName','')} : {ng.get('reason','')}"
                                )

    st.markdown("</div>", unsafe_allow_html=True)
