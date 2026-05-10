import React, { useState, useEffect } from 'react';
import { initializeApp } from 'firebase/app';
import { 
  getAuth, 
  signInAnonymously, 
  onAuthStateChanged,
  signInWithCustomToken
} from 'firebase/auth';
import { 
  getFirestore, 
  collection, 
  onSnapshot, 
  addDoc, 
  updateDoc, 
  deleteDoc, 
  doc, 
  setDoc,
  query
} from 'firebase/firestore';
import { 
  Calendar as CalendarIcon, 
  MapPin, 
  Link as LinkIcon, 
  Plus, 
  Trash2, 
  ArrowRight, 
  Smile, 
  Meh, 
  Frown, 
  MessageCircle, 
  CalendarOff, 
  X, 
  Send, 
  AlertCircle, 
  ShieldCheck,
  Copy,
  CheckCircle2,
  Lock,
  Key,
  LogOut
} from 'lucide-react';

// --- Firebase Initialization ---
const firebaseConfig = JSON.parse(__firebase_config);
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const appId = typeof __app_id !== 'undefined' ? __app_id : 'couple-secure-v2';

// --- Utility: 29-Digit Secure Key Generator ---
const generateSecureKey = () => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  const parts = [];
  // 4桁 × 7ブロック = 28桁
  for (let i = 0; i < 7; i++) {
    let part = '';
    for (let j = 0; j < 4; j++) {
      part += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    parts.push(part);
  }
  // 最後に1桁足して合計29桁にする
  const lastChar = chars.charAt(Math.floor(Math.random() * chars.length));
  return parts.join('-') + '-' + lastChar;
};

// --- WishlistItem Component (サブコンポーネント) ---
const WishlistItem = ({ item, userId, ngDates, onDelete, onUpdatePref, onAddComment, onMoveToSchedule }) => {
  const [showComments, setShowComments] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [isSelectingDate, setIsSelectingDate] = useState(false);
  const [selectedDate, setSelectedDate] = useState('');
  const [timeType, setTimeType] = useState('all');
  const [customTime, setCustomTime] = useState('');

  const prefs = item.preferences || {};
  const myPref = prefs[userId];
  const partnerUid = Object.keys(prefs).find(uid => uid !== userId);
  const partnerPref = partnerUid ? prefs[partnerUid] : null;
  const comments = item.comments || [];

  const handleCommentSubmit = (e) => {
    e.preventDefault();
    if (commentText.trim()) {
      onAddComment(commentText.trim());
      setCommentText('');
    }
  };

  const overlappingNgs = selectedDate ? ngDates.filter(nd => nd.date === selectedDate) : [];
  const isAllDayNg = overlappingNgs.some(nd => nd.timeType === 'all');
  
  const getNgStatusMessage = () => {
    if (overlappingNgs.length === 0) return null;
    return overlappingNgs.map(nd => {
      const who = nd.userId === userId ? "あなた" : "相手";
      const timeLabel = nd.timeType === 'morning' ? "午前中" : 
                        nd.timeType === 'afternoon' ? "午後" : 
                        nd.timeType === 'custom' ? `時間指定(${nd.customTime})` : "終日";
      return `${who}に${timeLabel}の予定があります`;
    }).join(' / ');
  };

  return (
    <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 relative mb-4 text-left">
      <button onClick={onDelete} className="absolute top-4 right-4 text-gray-300 hover:text-red-500 transition-colors">
        <Trash2 size={18} />
      </button>
      
      <h3 className="text-lg font-bold text-gray-800 pr-8">{item.title}</h3>
      
      {item.url && (
        <a href={item.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-blue-500 hover:underline mt-2 inline-block">
          <LinkIcon size={12} /> 参考リンク
        </a>
      )}

      <div className="mt-5 border-t border-gray-100 pt-4">
        <div className="flex gap-2 mb-3">
          {[
            { id: 'want', icon: Smile, label: '行きたい', color: 'rose' },
            { id: 'neutral', icon: Meh, label: 'どっちでも', color: 'amber' },
            { id: 'no', icon: Frown, label: 'うーん', color: 'slate' }
          ].map(p => (
            <button 
              key={p.id}
              onClick={() => onUpdatePref(p.id)} 
              className={`flex-1 py-2.5 rounded-xl flex justify-center items-center gap-1 text-xs font-bold transition-all ${myPref === p.id ? `bg-${p.color}-500 text-white shadow-md` : `bg-gray-50 text-gray-400 hover:bg-gray-100`}`}
            >
              <p.icon size={16}/> {p.label}
            </button>
          ))}
        </div>

        {partnerPref && (
          <div className="text-xs text-rose-600 mb-4 inline-flex items-center gap-1.5 bg-rose-50 px-3 py-1.5 rounded-full font-bold">
            相手: {partnerPref === 'want' ? '😍 行きたい！' : partnerPref === 'neutral' ? '😐 どっちでも' : '🙅‍♂️ うーん'}
          </div>
        )}

        <button onClick={() => setShowComments(!showComments)} className="flex items-center gap-1 text-sm font-bold text-gray-500 hover:text-gray-800 transition-colors bg-gray-50 px-4 py-2.5 rounded-xl w-full justify-between mb-4">
          <span className="flex items-center gap-2 text-xs uppercase tracking-tighter"><MessageCircle size={16}/> メッセージ相談</span>
          <span className="bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full text-[10px] font-bold">{comments.length}</span>
        </button>

        {showComments && (
          <div className="mb-4 bg-slate-50 p-3 rounded-xl border border-slate-100">
             <div className="space-y-3 max-h-48 overflow-y-auto mb-3 pr-1">
                {comments.map((c, i) => (
                  <div key={i} className={`flex flex-col ${c.userId === userId ? 'items-end' : 'items-start'}`}>
                    <div className={`px-3 py-2 rounded-2xl max-w-[85%] text-sm ${c.userId === userId ? 'bg-slate-800 text-white rounded-tr-sm' : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'}`}>
                      {c.text}
                    </div>
                  </div>
                ))}
             </div>
             <form onSubmit={handleCommentSubmit} className="flex gap-2">
               <input type="text" value={commentText} onChange={e => setCommentText(e.target.value)} className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-full outline-none focus:ring-2 focus:ring-rose-200" placeholder="相談する..." />
               <button type="submit" disabled={!commentText.trim()} className="bg-rose-500 text-white p-2 rounded-full disabled:opacity-50">
                  <Send size={16}/>
               </button>
             </form>
          </div>
        )}

        <div className="flex justify-end">
          {!isSelectingDate ? (
            <button onClick={() => setIsSelectingDate(true)} className="text-xs font-bold text-white bg-slate-800 hover:bg-slate-900 px-5 py-2.5 rounded-xl transition-all flex items-center gap-2">
              行く日をきめる <ArrowRight size={14} />
            </button>
          ) : (
            <div className="w-full p-4 bg-slate-100 rounded-2xl border border-slate-200">
              <div className="flex justify-between items-center mb-3 text-slate-700">
                <span className="text-xs font-bold">日程設定</span>
                <button onClick={() => { setIsSelectingDate(false); setSelectedDate(''); }} className="text-gray-400"><X size={18}/></button>
              </div>
              <div className="flex flex-col gap-3">
                 <input type="date" value={selectedDate} onChange={e => setSelectedDate(e.target.value)} className="w-full p-3 border border-gray-200 rounded-xl text-sm font-bold bg-white" />
                 
                 <div className="grid grid-cols-2 gap-2">
                   {['all', 'morning', 'afternoon', 'custom'].map(t => (
                     <button key={t} type="button" onClick={() => setTimeType(t)} className={`py-2 rounded-lg border text-[10px] font-bold ${timeType === t ? 'border-rose-500 bg-rose-50 text-rose-600' : 'border-gray-200 bg-white text-gray-400'}`}>
                       {t === 'all' ? '終日' : t === 'morning' ? '午前' : t === 'afternoon' ? '午後' : '時間指定'}
                     </button>
                   ))}
                 </div>

                 {timeType === 'custom' && (
                   <input type="text" value={customTime} onChange={e=>setCustomTime(e.target.value)} placeholder="13:00〜17:00" className="w-full p-2.5 border border-gray-200 rounded-lg text-xs bg-white font-medium" />
                 )}

                 {getNgStatusMessage() && (
                   <div className="text-[10px] text-amber-700 font-bold bg-amber-50 p-2 rounded-lg border border-amber-200 flex gap-1 items-center">
                     <AlertCircle size={12}/> {getNgStatusMessage()}
                   </div>
                 )}

                 <button 
                   onClick={() => { onMoveToSchedule(selectedDate, timeType, customTime); setIsSelectingDate(false); }} 
                   disabled={!selectedDate || isAllDayNg}
                   className="w-full bg-rose-500 text-white py-3 rounded-xl text-xs font-bold disabled:opacity-30"
                 >
                   確定する
                 </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// --- Main App Component ---
export default function App() {
  const [user, setUser] = useState(null);
  const [roomKey, setRoomKey] = useState('');
  const [isLogged, setIsLogged] = useState(false);
  const [roomTitle, setRoomTitle] = useState('ふたりの共有ノート');
  const [items, setItems] = useState([]);
  const [ngDates, setNgDates] = useState([]);
  const [activeTab, setActiveTab] = useState('wishlist');
  const [isAdding, setIsAdding] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState(false);

  const [inputKey, setInputKey] = useState('');
  const [title, setTitle] = useState('');
  const [url, setUrl] = useState('');
  const [memo, setMemo] = useState('');

  useEffect(() => {
    const initAuth = async () => {
      try {
        if (typeof __initial_auth_token !== 'undefined' && __initial_auth_token) {
          await signInWithCustomToken(auth, __initial_auth_token);
        } else {
          await signInAnonymously(auth);
        }
      } catch (error) {
        console.error("Auth initialization failed:", error);
      }
    };
    initAuth();

    const unsubscribeAuth = onAuthStateChanged(auth, (u) => {
      setUser(u);
      if (u) {
        const urlParams = new URLSearchParams(window.location.search);
        const keyInUrl = urlParams.get('key');
        const savedKey = localStorage.getItem('pair_note_key_v29');

        if (keyInUrl) {
          setRoomKey(keyInUrl);
          localStorage.setItem('pair_note_key_v29', keyInUrl);
          setIsLogged(true);
          window.history.replaceState({}, document.title, window.location.pathname);
        } else if (savedKey) {
          setRoomKey(savedKey);
          setIsLogged(true);
        }
      }
    });

    return () => unsubscribeAuth();
  }, []);

  useEffect(() => {
    if (!user || !isLogged || !roomKey) return;

    const eventsRef = collection(db, 'artifacts', appId, 'public', 'data', 'secure_events');
    const ngRef = collection(db, 'artifacts', appId, 'public', 'data', 'secure_ng_dates');
    const roomRef = doc(db, 'artifacts', appId, 'public', 'data', 'secure_rooms', roomKey);

    const unsubItems = onSnapshot(eventsRef, (snap) => {
      const filtered = snap.docs
        .map(doc => ({ id: doc.id, ...doc.data() }))
        .filter(i => i.roomKey === roomKey);
      setItems(filtered);
    });

    const unsubNg = onSnapshot(ngRef, (snap) => {
      const filtered = snap.docs
        .map(doc => ({ id: doc.id, ...doc.data() }))
        .filter(n => n.roomKey === roomKey);
      setNgDates(filtered);
    });

    const unsubRoom = onSnapshot(roomRef, (snap) => {
      if (snap.exists()) setRoomTitle(snap.data().title);
    });

    return () => {
      unsubItems();
      unsubNg();
      unsubRoom();
    };
  }, [user, isLogged, roomKey]);

  const handleCreateRoom = async () => {
    if (!user) return;
    const newKey = generateSecureKey();
    
    try {
      await setDoc(doc(db, 'artifacts', appId, 'public', 'data', 'secure_rooms', newKey), { 
        title: 'ふたりの共有ノート', 
        createdAt: new Date().toISOString(),
        creator: user.uid
      });
      setRoomKey(newKey);
      localStorage.setItem('pair_note_key_v29', newKey);
      setIsLogged(true);
    } catch (err) {
      console.error("Create room error:", err);
    }
  };

  const handleJoinRoom = () => {
    const trimmedKey = inputKey.trim();
    // 29桁の形式（ハイフン込みで36文字）をチェック
    if (trimmedKey.length >= 29) {
      setRoomKey(trimmedKey);
      localStorage.setItem('pair_note_key_v29', trimmedKey);
      setIsLogged(true);
    }
  };

  const invitePartner = () => {
    const url = `${window.location.origin}${window.location.pathname}?key=${roomKey}`;
    const textArea = document.createElement("textarea");
    textArea.value = url;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    
    setCopyFeedback(true);
    setTimeout(() => setCopyFeedback(false), 2000);
  };

  const handleAddItem = async (e) => {
    e.preventDefault();
    if (!title.trim() || !user) return;
    try {
      await addDoc(collection(db, 'artifacts', appId, 'public', 'data', 'secure_events'), {
        roomKey, title: title.trim(), url: url.trim(), memo: memo.trim(),
        status: 'wishlist', date: null, timeType: null, preferences: {}, comments: [],
        createdAt: new Date().toISOString()
      });
      setTitle(''); setUrl(''); setMemo(''); setIsAdding(false);
    } catch (err) {
      console.error("Add item error:", err);
    }
  };

  if (!isLogged) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6 text-white text-center font-sans">
        <div className="w-full max-w-sm space-y-8">
          <div className="space-y-4">
            <div className="bg-rose-500 w-20 h-20 rounded-3xl flex items-center justify-center mx-auto shadow-2xl">
              <ShieldCheck size={40} />
            </div>
            <h1 className="text-2xl font-black">29-Digit Secure Sync</h1>
            <p className="text-slate-400 text-sm">29桁の秘密鍵による強固な共有空間</p>
          </div>

          <div className="bg-slate-800 p-6 rounded-[2rem] border border-slate-700 shadow-xl space-y-6">
            <button onClick={handleCreateRoom} className="w-full bg-rose-500 hover:bg-rose-600 py-5 rounded-2xl font-black flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg">
              <Plus size={20}/> 新しいノートを作る
            </button>
            <div className="relative">
              <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-slate-700"></span></div>
              <div className="relative flex justify-center text-xs"><span className="bg-slate-800 px-3 text-slate-500 font-bold uppercase">Or Join</span></div>
            </div>
            <div className="space-y-3">
              <div className="relative">
                <Key className="absolute left-4 top-4 text-slate-500" size={18}/>
                <input 
                  type="text" placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-X" value={inputKey} onChange={e=>setInputKey(e.target.value.toUpperCase())}
                  className="w-full bg-slate-900 border border-slate-700 rounded-2xl py-4 pl-12 pr-4 text-[10px] font-mono focus:border-rose-500 outline-none transition-all"
                />
              </div>
              <button onClick={handleJoinRoom} disabled={inputKey.length < 29} className="w-full bg-slate-700 hover:bg-slate-600 disabled:opacity-30 py-4 rounded-2xl font-black text-sm transition-all">
                秘密鍵で同期する
              </button>
            </div>
          </div>
          {!user && <p className="text-rose-400 text-[10px] font-bold animate-pulse">サーバー接続を確立しています...</p>}
        </div>
      </div>
    );
  }

  const wishlistItems = items.filter(i => i.status === 'wishlist').sort((a,b) => new Date(b.createdAt) - new Date(a.createdAt));
  const scheduledItems = items.filter(i => i.status === 'scheduled').sort((a,b) => new Date(a.date) - new Date(b.date));

  return (
    <div className="min-h-screen bg-slate-50 pb-24 text-center font-sans">
      <header className="bg-white/80 backdrop-blur-md px-6 py-5 sticky top-0 z-20 border-b border-gray-100">
        <div className="max-w-2xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2 text-left">
            <Lock size={16} className="text-rose-500" />
            <h2 className="font-black text-xl tracking-tight text-slate-900">{roomTitle}</h2>
          </div>
          <button onClick={invitePartner} className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-black transition-all ${copyFeedback ? 'bg-green-500 text-white' : 'bg-slate-900 text-white'}`}>
            {copyFeedback ? <><CheckCircle2 size={14}/> コピー完了</> : <><Copy size={14}/> パートナーを招待</>}
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto p-4 space-y-6">
        <div className="flex bg-white rounded-2xl p-1 shadow-sm border border-gray-100">
          {[
            { id: 'wishlist', label: '行きたい', icon: MapPin },
            { id: 'schedule', label: '予定', icon: CalendarIcon },
            { id: 'ng', label: 'NG日', icon: CalendarOff }
          ].map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id)} className={`flex-1 py-3 px-2 rounded-xl text-xs font-black flex justify-center items-center gap-2 transition-all ${activeTab === t.id ? 'bg-slate-900 text-white' : 'text-gray-400 hover:bg-gray-50'}`}>
              <t.icon size={16} /> {t.label}
            </button>
          ))}
        </div>

        {activeTab === 'wishlist' && (
          <div className="space-y-4">
            {!isAdding ? (
              <button onClick={() => setIsAdding(true)} className="w-full bg-white border-2 border-dashed border-gray-200 text-gray-400 font-bold py-8 rounded-2xl hover:border-rose-300 hover:text-rose-500 transition-all flex flex-col items-center gap-2">
                <Plus size={24}/> <span className="text-sm">新しい場所を追加</span>
              </button>
            ) : (
              <div className="bg-white p-6 rounded-2xl shadow-lg border border-rose-100 text-left">
                <form onSubmit={handleAddItem} className="space-y-4">
                  <input type="text" placeholder="どこに行きたい？" value={title} onChange={e => setTitle(e.target.value)} className="w-full px-4 py-3 bg-gray-50 rounded-xl outline-none font-bold text-sm" required />
                  <input type="url" placeholder="URL (任意)" value={url} onChange={e => setUrl(e.target.value)} className="w-full px-4 py-3 bg-gray-50 rounded-xl outline-none text-xs" />
                  <textarea placeholder="メモ..." value={memo} onChange={e => setMemo(e.target.value)} className="w-full px-4 py-3 bg-gray-50 rounded-xl outline-none text-xs h-20 resize-none" />
                  <div className="flex gap-2">
                    <button type="button" onClick={() => setIsAdding(false)} className="flex-1 py-3 text-gray-400 text-xs font-bold">キャンセル</button>
                    <button type="submit" className="flex-1 py-3 bg-rose-500 text-white font-black rounded-xl text-xs">追加する</button>
                  </div>
                </form>
              </div>
            )}
            {wishlistItems.map(item => (
              <WishlistItem 
                key={item.id} item={item} userId={user?.uid} ngDates={ngDates}
                onDelete={() => deleteDoc(doc(db, 'artifacts', appId, 'public', 'data', 'secure_events', item.id))}
                onUpdatePref={pref => updateDoc(doc(db, 'artifacts', appId, 'public', 'data', 'secure_events', item.id), { [`preferences.${user?.uid}`]: pref })}
                onAddComment={text => updateDoc(doc(db, 'artifacts', appId, 'public', 'data', 'secure_events', item.id), { comments: [...(item.comments||[]), { userId: user?.uid, text, createdAt: new Date().toISOString() }] })}
                onMoveToSchedule={(date, timeType, customTime) => updateDoc(doc(db, 'artifacts', appId, 'public', 'data', 'secure_events', item.id), { status: 'scheduled', date, timeType, customTime })}
              />
            ))}
          </div>
        )}

        {activeTab === 'schedule' && (
          <div className="space-y-4 text-left">
            {scheduledItems.map(item => (
              <div key={item.id} className="bg-white rounded-2xl overflow-hidden flex border border-gray-100 shadow-sm">
                <div className="bg-slate-900 text-white p-4 flex flex-col items-center justify-center w-24 shrink-0">
                  <span className="text-[10px] font-black opacity-40 uppercase">Date</span>
                  <span className="text-2xl font-black">{item.date.split('-')[2]}</span>
                  <span className="text-[10px] font-bold">{item.date.split('-')[1]}月</span>
                </div>
                <div className="p-5 flex-1 relative">
                  <button onClick={() => deleteDoc(doc(db, 'artifacts', appId, 'public', 'data', 'secure_events', item.id))} className="absolute top-4 right-4 text-gray-200 hover:text-red-500 transition-colors"><Trash2 size={16}/></button>
                  <span className="text-[10px] bg-rose-50 text-rose-500 px-2 py-0.5 rounded font-black uppercase inline-block mb-1">
                    {item.timeType === 'morning' ? '午前中' : item.timeType === 'afternoon' ? '午後' : item.timeType === 'custom' ? item.customTime : '終日'}
                  </span>
                  <h3 className="font-bold text-slate-800">{item.title}</h3>
                  <button onClick={() => updateDoc(doc(db, 'artifacts', appId, 'public', 'data', 'secure_events', item.id), { status: 'wishlist', date: null, timeType: null })} className="text-[10px] font-bold text-gray-400 mt-3 hover:text-rose-500 uppercase">リストに戻す</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'ng' && (
          <div className="space-y-6 text-left">
             <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
                <h3 className="text-sm font-black mb-4 flex items-center gap-2"><CalendarOff size={18} className="text-rose-500"/> NG予定の登録</h3>
                <div className="space-y-4">
                   <div className="grid grid-cols-2 gap-3">
                      <input type="date" id="ng-date" className="p-3 bg-gray-50 rounded-xl text-xs font-bold border border-transparent focus:border-rose-200 outline-none" />
                      <select id="ng-time" className="p-3 bg-gray-50 rounded-xl text-xs font-bold border border-transparent focus:border-rose-200 outline-none">
                        <option value="all">終日</option>
                        <option value="morning">午前</option>
                        <option value="afternoon">午後</option>
                      </select>
                   </div>
                   <button 
                    onClick={async () => {
                      const d = document.getElementById('ng-date').value;
                      const t = document.getElementById('ng-time').value;
                      if(d && user) {
                        try {
                          await addDoc(collection(db, 'artifacts', appId, 'public', 'data', 'secure_ng_dates'), { roomKey, userId: user.uid, date: d, timeType: t, createdAt: new Date().toISOString() });
                        } catch (err) {
                          console.error("Add NG date error:", err);
                        }
                      }
                    }}
                    className="w-full bg-slate-900 text-white py-4 rounded-xl font-black text-xs shadow-lg active:scale-95 transition-all"
                   >
                     NG日を追加する
                   </button>
                </div>
             </div>
             <div className="space-y-2">
                {ngDates.sort((a,b) => new Date(a.date) - new Date(b.date)).map(n => (
                  <div key={n.id} className={`p-4 rounded-2xl flex justify-between items-center ${n.userId === user?.uid ? 'bg-white border border-gray-100 shadow-sm' : 'bg-slate-100 opacity-60'}`}>
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-sm">{n.date.replace(/-/g, '/')}</span>
                      <span className="text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded font-black">{n.timeType === 'all' ? '終日' : n.timeType === 'morning' ? '午前' : '午後'}</span>
                      {n.userId !== user?.uid && <span className="text-[10px] font-black text-rose-500">相手の予定</span>}
                    </div>
                    {n.userId === user?.uid && (
                      <button onClick={() => deleteDoc(doc(db, 'artifacts', appId, 'public', 'data', 'secure_ng_dates', n.id))} className="text-gray-300 hover:text-red-500"><Trash2 size={16}/></button>
                    )}
                  </div>
                ))}
             </div>
          </div>
        )}
      </main>

      <footer className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[calc(100%-3rem)] max-w-md bg-slate-900 text-slate-500 p-4 rounded-2xl flex justify-between items-center shadow-2xl border border-slate-800 z-30">
        <div className="flex items-center gap-2 overflow-hidden">
          <Lock size={12} className="text-rose-500 shrink-0"/>
          <span className="text-[9px] font-mono tracking-tighter uppercase truncate">SECURE KEY: {roomKey}</span>
        </div>
        <button onClick={() => { localStorage.clear(); window.location.reload(); }} className="text-[10px] font-black uppercase tracking-widest hover:text-white flex items-center gap-1 transition-colors shrink-0">
          <LogOut size={12}/> ログアウト
        </button>
      </footer>
    </div>
  );
}
