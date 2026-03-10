const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');
const multer = require('multer');
const fs = require('fs');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Multer
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const dir = path.join(__dirname, 'public/uploads');
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    cb(null, dir);
  },
  filename: (req, file, cb) => {
    const unique = Date.now() + '-' + Math.round(Math.random() * 1e6);
    cb(null, unique + path.extname(file.originalname));
  }
});
const upload = multer({ storage, limits: { fileSize: 50 * 1024 * 1024 } });

// App Config
app.set('view engine', 'pug');
app.set('views', path.join(__dirname, 'views'));
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ─── State ────────────────────────────────────────────────────────────────────
// users: { socketId: { username, room, color } }
const users = {};
// rooms: Set of room names
const rooms = new Set(['general']);
// roomHistory: { roomName: [ message, ... ] }
const roomHistory = {};
// trollWarnings: { socketId: count }
const trollWarnings = {};

// ─── Troll Detection ──────────────────────────────────────────────────────────
const TROLL_PATTERNS = [
  /\b(idiot|stupid|dumb|loser|moron|shut up|go away|hate you|worthless)\b/i,
  /\b(kys|kill yourself)\b/i,
  /(!!{3,}|\?{3,})/,           // excessive punctuation
  /[A-Z\s]{10,}/               // lots of CAPS
];
const SOOTHING_RESPONSES = [
  "Hey, let's keep the chat a happy place! Take a breath — we're all here to connect.",
  "Seems like tensions are high! Maybe step away for a moment and come back refreshed ?",
  "This convo is getting heated. Let's cool it down — everyone deserves respect here. ",
  "Disagreements are okay, but let's keep it kind. You're better than this! ",
  "The vibes are off right now — let's reset and chat with empathy, yeah?"
];

function detectTroll(text) {
  return TROLL_PATTERNS.some(p => p.test(text));
}

function soothingMessage() {
  return SOOTHING_RESPONSES[Math.floor(Math.random() * SOOTHING_RESPONSES.length)];
}

// OTP/Private Info Detection
const PRIVATE_PATTERNS = [
  /\b\d{4,8}\b/,                                   // 4–8 digit OTP
  /\b(?:\d{4}[- ]?){3}\d{4}\b/,                   // credit card-like
  /\b\d{3}-\d{2}-\d{4}\b/,                         // SSN
  /password\s*[:=]\s*\S+/i,
  /otp\s*[:=\s]\s*\d{4,}/i
];

function detectPrivate(text) {
  return PRIVATE_PATTERNS.some(p => p.test(text));
}

// Routes
app.get('/', (req, res) => res.render('login'));

app.get('/chat', (req, res) => {
  res.render('chat', { rooms: [...rooms] });
});

// File upload endpoint
app.post('/upload', upload.single('media'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file' });
  res.json({ url: '/uploads/' + req.file.filename, name: req.file.originalname, type: req.file.mimetype });
});

// ─── Socket.IO ────────────────────────────────────────────────────────────────
io.on('connection', (socket) => {
  console.log(`[connect] ${socket.id}`);

  // Join with username
  socket.on('join', ({ username, room }) => {
    // Validate
    const taken = Object.values(users).find(u => u.username === username);
    if (taken) {
      socket.emit('join_error', 'Username already taken. Pick another!');
      return;
    }

    const color = `hsl(${Math.floor(Math.random() * 360)}, 65%, 55%)`;
    users[socket.id] = { username, room, color };
    socket.join(room);

    // Send room history
    const history = roomHistory[room] || [];
    socket.emit('room_history', history);

    // Announce
    const systemMsg = { type: 'system', text: `${username} joined #${room}`, ts: Date.now() };
    io.to(room).emit('message', systemMsg);

    // Update user list
    broadcastUserList(room);
    socket.emit('joined', { username, room, color, rooms: [...rooms] });
  });

  // Switch room
  socket.on('switch_room', (newRoom) => {
    const user = users[socket.id];
    if (!user) return;
    const oldRoom = user.room;

    socket.leave(oldRoom);
    user.room = newRoom;
    if (!rooms.has(newRoom)) rooms.add(newRoom);
    socket.join(newRoom);

    io.to(oldRoom).emit('message', { type: 'system', text: `${user.username} left #${oldRoom}`, ts: Date.now() });
    broadcastUserList(oldRoom);

    const history = roomHistory[newRoom] || [];
    socket.emit('room_history', history);

    io.to(newRoom).emit('message', { type: 'system', text: `${user.username} joined #${newRoom}`, ts: Date.now() });
    broadcastUserList(newRoom);
    socket.emit('room_switched', { room: newRoom });
  });

  // Create new room
  socket.on('create_room', (roomName) => {
    const clean = roomName.trim().toLowerCase().replace(/\s+/g, '-');
    if (!clean) return;
    rooms.add(clean);
    io.emit('rooms_updated', [...rooms]);
    socket.emit('room_created', clean);
  });

  // Chat message (broadcast to room)
  socket.on('chat_message', ({ text, mediaUrl, mediaType, mediaName }) => {
    const user = users[socket.id];
    if (!user) return;

    // Troll check
    if (text && detectTroll(text)) {
      trollWarnings[socket.id] = (trollWarnings[socket.id] || 0) + 1;
      socket.emit('troll_warning', {
        soothing: soothingMessage(),
        count: trollWarnings[socket.id]
      });
      if (trollWarnings[socket.id] >= 30) {
        socket.emit('message', {
          type: 'system',
          text: ' Ebar Besi Barabari hocche',
          ts: Date.now()
        });
        return; // block message
      }
      // still deliver but warn
    }

    const msg = {
      type: 'chat',
      from: user.username,
      color: user.color,
      text,
      mediaUrl,
      mediaType,
      mediaName,
      room: user.room,
      ts: Date.now()
    };

    // Store in history (cap at 100)
    if (!roomHistory[user.room]) roomHistory[user.room] = [];
    roomHistory[user.room].push(msg);
    if (roomHistory[user.room].length > 100) roomHistory[user.room].shift();

    io.to(user.room).emit('message', msg);
  });

  // Direct (private) message
  socket.on('private_message', ({ toUsername, text }) => {
    const sender = users[socket.id];
    if (!sender) return;
    const target = Object.entries(users).find(([, u]) => u.username === toUsername);
    if (!target) {
      socket.emit('error_msg', `User "${toUsername}" not found or offline.`);
      return;
    }
    const [targetId] = target;
    const dm = {
      type: 'dm',
      from: sender.username,
      to: toUsername,
      color: sender.color,
      text,
      ts: Date.now()
    };
    socket.emit('message', dm);
    io.to(targetId).emit('message', dm);
  });

  // Typing indicator
  socket.on('typing', (isTyping) => {
    const user = users[socket.id];
    if (!user) return;
    socket.to(user.room).emit('user_typing', { username: user.username, isTyping });
  });

  // Disconnect
  socket.on('disconnect', () => {
    const user = users[socket.id];
    if (user) {
      io.to(user.room).emit('message', { type: 'system', text: `${user.username} left the chat`, ts: Date.now() });
      delete users[socket.id];
      delete trollWarnings[socket.id];
      broadcastUserList(user.room);
    }
  });

  function broadcastUserList(room) {
    const roomUsers = Object.values(users).filter(u => u.room === room);
    io.to(room).emit('user_list', roomUsers.map(u => ({ username: u.username, color: u.color })));
    // Also send all online users
    io.emit('all_users', Object.values(users).map(u => ({ username: u.username, color: u.color })));
  }
});

// ─── Start ────────────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => console.log(`Chat server running → http://localhost:${PORT}`));
