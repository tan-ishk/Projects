// ─── Init ─────────────────────────────────────────────────────────────────────
const socket = io();

const username = sessionStorage.getItem('username');
const startRoom = sessionStorage.getItem('room') || 'general';
if (!username) { window.location.href = '/'; }

let currentRoom = startRoom;
let pendingMessage = null;   // for OTP hold
let pendingMedia   = null;   // { url, type, name }
let attachedFile   = null;   // file object waiting to upload
let typingTimer    = null;
let allUsers       = [];

// ─── DOM refs ─────────────────────────────────────────────────────────────────
const $messages      = document.getElementById('messages');
const $input         = document.getElementById('messageInput');
const $sendBtn       = document.getElementById('sendBtn');
const $currentRoom   = document.getElementById('currentRoom');
const $roomList      = document.getElementById('roomList');
const $userList      = document.getElementById('userList');
const $typingInd     = document.getElementById('typingIndicator');
const $connStatus    = document.getElementById('connectionStatus');
const $fileInput     = document.getElementById('fileInput');
const $filePreview   = document.getElementById('filePreview');
const $filePreviewNm = document.getElementById('filePreviewName');
const $fileClear     = document.getElementById('filePreviewClear');
const $newRoomInput  = document.getElementById('newRoomInput');
const $createRoom    = document.getElementById('createRoomBtn');

// OTP modal
const $otpModal   = document.getElementById('otpModal');
const $otpPreview = document.getElementById('otpPreview');
const $otpConfirm = document.getElementById('otpConfirm');
const $otpCancel  = document.getElementById('otpCancel');

// Troll toast
const $trollToast = document.getElementById('trollToast');
const $trollMsg   = document.getElementById('trollMsg');

// DM panel
const $dmToggle  = document.getElementById('dmToggle');
const $dmPanel   = document.getElementById('dmPanel');
const $dmClose   = document.getElementById('dmClose');
const $dmTarget  = document.getElementById('dmTarget');
const $dmText    = document.getElementById('dmText');
const $dmSend    = document.getElementById('dmSend');

// ─── Private-info detector (mirrors server) ───────────────────────────────────
const PRIVATE_RE = [
  /\b\d{4,8}\b/,
  /\b(?:\d{4}[- ]?){3}\d{4}\b/,
  /\b\d{3}-\d{2}-\d{4}\b/,
  /password\s*[:=]\s*\S+/i,
  /otp\s*[:=\s]\s*\d{4,}/i
];
function hasPrivateInfo(text) {
  return text && PRIVATE_RE.some(r => r.test(text));
}

// ─── Join ──────────────────────────────────────────────────────────────────────
socket.emit('join', { username, room: currentRoom });

socket.on('join_error', msg => {
  alert(msg);
  window.location.href = '/';
});

socket.on('joined', ({ room }) => {
  currentRoom = room;
  updateRoomUI();
});

// ─── Messages ─────────────────────────────────────────────────────────────────
socket.on('room_history', msgs => {
  $messages.innerHTML = '';
  msgs.forEach(renderMessage);
  scrollBottom();
});

socket.on('message', msg => {
  renderMessage(msg);
  scrollBottom();
});

function renderMessage(msg) {
  const li = document.createElement('li');

  if (msg.type === 'system') {
    li.className = 'msg msg--system';
    li.innerHTML = `<span>${escHtml(msg.text)}</span>`;
  } else if (msg.type === 'dm') {
    li.className = 'msg msg--dm';
    const dir = msg.from === username ? 'You → ' : `${escHtml(msg.from)} → you`;
    li.innerHTML = `
      <div class="msg-header">
        <span class="dm-tag">DM</span>
        <span class="msg-from">${dir}</span>
        <span class="msg-time">${fmtTime(msg.ts)}</span>
      </div>
      <div class="msg-body">${escHtml(msg.text)}</div>`;
  } else {
    const isMine = msg.from === username;
    li.className = `msg msg--chat${isMine ? ' msg--mine' : ''}`;
    let mediaHtml = '';
    if (msg.mediaUrl) {
      if (msg.mediaType && msg.mediaType.startsWith('video/')) {
        mediaHtml = `<video class="msg-media" src="${msg.mediaUrl}" controls></video>`;
      } else {
        mediaHtml = `<img class="msg-media" src="${msg.mediaUrl}" alt="${escHtml(msg.mediaName || 'image')}" loading="lazy">`;
      }
    }
    li.innerHTML = `
      <div class="msg-header">
        <span class="msg-from" style="color:${msg.color}">${escHtml(msg.from)}</span>
        <span class="msg-time">${fmtTime(msg.ts)}</span>
      </div>
      <div class="msg-body">${msg.text ? escHtml(msg.text) : ''}${mediaHtml}</div>`;
  }

  $messages.appendChild(li);
}

// ─── Send message ─────────────────────────────────────────────────────────────
async function sendMessage() {
  const text = $input.value.trim();
  if (!text && !attachedFile) return;

  let mediaUrl = null, mediaType = null, mediaName = null;

  // Upload file if any
  if (attachedFile) {
    const fd = new FormData();
    fd.append('media', attachedFile);
    try {
      const res = await fetch('/upload', { method: 'POST', body: fd });
      const data = await res.json();
      mediaUrl  = data.url;
      mediaType = data.type;
      mediaName = data.name;
    } catch (e) {
      appendSystemLocal('Upload failed. Try again.');
      return;
    }
    clearFilePreview();
  }

  // OTP check — only for group (room) messages
  if (hasPrivateInfo(text)) {
    pendingMessage = { text, mediaUrl, mediaType, mediaName };
    $otpPreview.textContent = text;
    $otpModal.style.display = 'flex';
    return;
  }

  doSend(text, mediaUrl, mediaType, mediaName);
}

function doSend(text, mediaUrl, mediaType, mediaName) {
  socket.emit('chat_message', { text, mediaUrl, mediaType, mediaName });
  $input.value = '';
  socket.emit('typing', false);
  clearTimeout(typingTimer);
}

$sendBtn.addEventListener('click', sendMessage);
$input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

// OTP modal actions
$otpConfirm.addEventListener('click', () => {
  if (pendingMessage) {
    const { text, mediaUrl, mediaType, mediaName } = pendingMessage;
    doSend(text, mediaUrl, mediaType, mediaName);
    pendingMessage = null;
  }
  $otpModal.style.display = 'none';
});
$otpCancel.addEventListener('click', () => {
  pendingMessage = null;
  $otpModal.style.display = 'none';
});

// ─── Troll warning ────────────────────────────────────────────────────────────
socket.on('troll_warning', ({ soothing, count }) => {
  $trollMsg.textContent = soothing;
  $trollToast.style.display = 'flex';
  setTimeout(() => { $trollToast.style.display = 'none'; }, 5000);
});

// ─── Typing ───────────────────────────────────────────────────────────────────
let activeTypers = {};

$input.addEventListener('input', () => {
  socket.emit('typing', true);
  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => socket.emit('typing', false), 1500);
});

socket.on('user_typing', ({ username: u, isTyping }) => {
  if (isTyping) activeTypers[u] = true;
  else delete activeTypers[u];
  const typers = Object.keys(activeTypers);
  $typingInd.textContent = typers.length
    ? `${typers.join(', ')} ${typers.length === 1 ? 'is' : 'are'} typing…`
    : '';
});

// ─── Rooms ────────────────────────────────────────────────────────────────────
function updateRoomUI() {
  $currentRoom.textContent = currentRoom;
  $input.placeholder = `Message #${currentRoom}…`;
  document.querySelectorAll('.room-item').forEach(el => {
    el.classList.toggle('active', el.dataset.room === currentRoom);
  });
  // clear typers on room switch
  activeTypers = {};
  $typingInd.textContent = '';
}

$roomList.addEventListener('click', e => {
  const item = e.target.closest('.room-item');
  if (!item) return;
  const room = item.dataset.room;
  if (room === currentRoom) return;
  currentRoom = room;
  socket.emit('switch_room', room);
  $messages.innerHTML = '';
  updateRoomUI();
});

$createRoom.addEventListener('click', () => {
  const name = $newRoomInput.value.trim().toLowerCase().replace(/\s+/g, '-');
  if (!name) return;
  socket.emit('create_room', name);
  $newRoomInput.value = '';
});
$newRoomInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') $createRoom.click();
});

socket.on('room_created', room => {
  socket.emit('switch_room', room);
  currentRoom = room;
  $messages.innerHTML = '';
  updateRoomUI();
});

socket.on('room_switched', ({ room }) => {
  currentRoom = room;
  updateRoomUI();
});

socket.on('rooms_updated', rooms => {
  // Add any new room items
  rooms.forEach(r => {
    if (!document.querySelector(`.room-item[data-room="${r}"]`)) {
      const li = document.createElement('li');
      li.className = 'room-item';
      li.dataset.room = r;
      li.innerHTML = `<span class="hash">#</span><span>${r}</span>`;
      $roomList.appendChild(li);
    }
  });
  updateRoomUI();
});

// ─── Users ────────────────────────────────────────────────────────────────────
socket.on('user_list', users => {
  $userList.innerHTML = users.map(u =>
    `<li class="user-item">
      <span class="user-dot" style="background:${u.color}"></span>
      <span>${escHtml(u.username)}</span>
    </li>`
  ).join('');
});

socket.on('all_users', users => {
  allUsers = users.filter(u => u.username !== username);
  // Update DM dropdown
  $dmTarget.innerHTML = `<option value=''>Select user…</option>` +
    allUsers.map(u => `<option value="${escHtml(u.username)}">${escHtml(u.username)}</option>`).join('');
});

// ─── DM ───────────────────────────────────────────────────────────────────────
$dmToggle.addEventListener('click', () => {
  $dmPanel.style.display = $dmPanel.style.display === 'none' ? 'flex' : 'none';
});
$dmClose.addEventListener('click', () => { $dmPanel.style.display = 'none'; });
$dmSend.addEventListener('click', sendDM);
$dmText.addEventListener('keydown', e => { if (e.key === 'Enter') sendDM(); });

function sendDM() {
  const to   = $dmTarget.value;
  const text = $dmText.value.trim();
  if (!to || !text) return;
  socket.emit('private_message', { toUsername: to, text });
  $dmText.value = '';
  $dmPanel.style.display = 'none';
}

// ─── File attachment ──────────────────────────────────────────────────────────
$fileInput.addEventListener('change', () => {
  const file = $fileInput.files[0];
  if (!file) return;
  attachedFile = file;
  $filePreviewNm.textContent = file.name;
  $filePreview.style.display = 'flex';
  $fileInput.value = '';
});
$fileClear.addEventListener('click', clearFilePreview);
function clearFilePreview() {
  attachedFile = null;
  $filePreview.style.display = 'none';
  $filePreviewNm.textContent = '';
}

// ─── Connection status ────────────────────────────────────────────────────────
socket.on('connect',    () => { $connStatus.className = 'dot dot--green'; });
socket.on('disconnect', () => { $connStatus.className = 'dot dot--red';   });

socket.on('error_msg', msg => appendSystemLocal(msg));

// ─── Helpers ──────────────────────────────────────────────────────────────────
function scrollBottom() {
  const wrap = $messages.parentElement;
  wrap.scrollTop = wrap.scrollHeight;
}

function fmtTime(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escHtml(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function appendSystemLocal(text) {
  renderMessage({ type: 'system', text, ts: Date.now() });
  scrollBottom();
}
