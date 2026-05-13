// --- 修正版：生理日管理設定コンポーネント ---

const PeriodManagementSettings = () => {
  // 1. タイトルの修正：「設定を復元」などの不適切な名称から適切な名称へ
  const pageTitle = "生理日管理設定";

  // 文字サイズ設定用の状態管理
  const [fontSize, setFontSize] = React.useState(14);

  // 【復元】予定一覧の編集機能用の状態管理
  const [schedules, setSchedules] = React.useState([
    { id: 1, text: "病院" },
    { id: 2, text: "買い物" }
  ]);
  const [newSchedule, setNewSchedule] = React.useState("");

  // 保存処理（文字サイズ）
  const handleSaveFontSize = () => {
    console.log(`文字サイズを ${fontSize}px で保存しました。`);
    alert("文字サイズを保存しました。");
  };

  // 【復元】予定の追加処理
  const handleAddSchedule = () => {
    if (newSchedule.trim() === "") return;
    const newId = schedules.length > 0 ? Math.max(...schedules.map(s => s.id)) + 1 : 1;
    setSchedules([...schedules, { id: newId, text: newSchedule }]);
    setNewSchedule("");
  };

  // 【復元】予定の削除処理
  const handleDeleteSchedule = (id) => {
    setSchedules(schedules.filter(s => s.id !== id));
  };

  return (
    <div className="settings-container">
      {/* タイトル部分 */}
      <h1>{pageTitle}</h1>

      {/* 【復元】予定一覧の編集機能 */}
      <section className="schedule-edit-section" style={{ marginBottom: '20px' }}>
        <h2>予定一覧の編集</h2>
        <ul style={{ listStyleType: 'none', padding: 0 }}>
          {schedules.map(schedule => (
            <li key={schedule.id} style={{ marginBottom: '5px' }}>
              <button 
                onClick={() => handleDeleteSchedule(schedule.id)} 
                style={{ marginRight: '10px', cursor: 'pointer' }}
              >
                削除
              </button>
              {schedule.text}
            </li>
          ))}
        </ul>
        <div style={{ marginTop: '10px' }}>
          <input 
            type="text" 
            value={newSchedule} 
            onChange={(e) => setNewSchedule(e.target.value)} 
            placeholder="新しい予定を入力" 
            style={{ padding: '5px' }}
          />
          <button 
            onClick={handleAddSchedule} 
            style={{ marginLeft: '10px', padding: '5px 15px', cursor: 'pointer' }}
          >
            追加
          </button>
        </div>
      </section>

      <hr />

      {/* 文字サイズ設定セクション */}
      <section className="font-size-setting" style={{ marginTop: '20px', marginBottom: '20px' }}>
        <h2>表示設定</h2>
        <label htmlFor="fontSizeRange" style={{ marginRight: '10px' }}>文字サイズ</label>
        <input 
          id="fontSizeRange"
          type="range" 
          min="10" 
          max="24" 
          value={fontSize} 
          onChange={(e) => setFontSize(e.target.value)} 
        />
        <span style={{ marginLeft: '10px' }}>{fontSize}px</span>
        
        {/* 保存ボタン */}
        <button 
          className="save-button" 
          onClick={handleSaveFontSize}
          style={{ marginLeft: '15px', padding: '5px 15px', cursor: 'pointer' }}
        >
          保存
        </button>
      </section>

      <hr />

      {/* カレンダー設定のプレビューまたはロジック説明 */}
      <section className="calendar-preview" style={{ marginTop: '20px' }}>
        <h2>カレンダー表示設定</h2>
        <p>※視認性向上のため、生理日はテキストを非表示にし、添付画像の様な月のアイコンのみを表示します。</p>
        
        <div className="calendar-mock" style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
          {/* カレンダー反映ロジックの変更点 */}
          {/* 修正前: <span>生理日</span> 🩸 */}
          {/* 修正後: ラベルを削除し、S__183681042.jpg を参考にした月のアイコン(🌙)をピンク色でレンダリング */}
          <div className="calendar-day" style={{ border: '1px solid #e0e0e0', padding: '10px', width: '60px', textAlign: 'center' }}>
            <div style={{ color: '#333', marginBottom: '5px' }}>27</div>
            <div className="period-icon" title="生理予定" style={{ color: '#FF8DA1', fontSize: '24px', lineHeight: '1' }}>🌙</div>
          </div>
          <div className="calendar-day" style={{ border: '1px solid #e0e0e0', padding: '10px', width: '60px', textAlign: 'center' }}>
            <div style={{ color: '#333', marginBottom: '5px' }}>28</div>
            <div className="period-icon" title="生理予定" style={{ color: '#FF8DA1', fontSize: '24px', lineHeight: '1' }}>🌙</div>
          </div>
        </div>
      </section>
    </div>
  );
};

// --- カレンダー描画エンジンの修正（イメージ） ---
/*
  renderCalendarEvent(event) {
    if (event.type === 'PERIOD_LOG') {
      // 他の機能（日付計算や記録機能）は変えず、
      // 表示部分だけテキストを排除し、「ピンクの月のアイコンのみ」を返すように修正
      // ※OSの絵文字仕様によって色が上書きされる環境の場合はSVG画像に差し替えることも可能です。
      return `<span class="icon-only" style="color: #FF8DA1; font-size: 1.5em; display: inline-block; transform: scaleX(-1);">🌙</span>`; 
    }
    return `<span>${event.title}</span>`;
  }
*/
