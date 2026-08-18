/**
 * NetPulse 协同测试 - Cloudflare Workers 中继服务器
 * 
 * 完全免费部署：
 * 1. 去 https://dash.cloudflare.com/ 注册（免费，不用信用卡）
 * 2. 进入 Workers & Pages → Create application → Create Worker
 * 3. 把本文件内容全部粘贴替换掉默认代码
 * 4. 点击 Deploy，就会得到一个 https://xxx.xxx.workers.dev 的地址
 * 5. 在 NetPulse 设置里把中继地址改为这个地址（去掉 https://，直接填 xxx.xxx.workers.dev）
 */

const ROOM_TTL = 300; // 房间有效期 5 分钟
const CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // 去掉易混淆的 O/0/I/1

function genCode() {
  let code = '';
  for (let i = 0; i < 6; i++) {
    code += CODE_CHARS[Math.floor(Math.random() * CODE_CHARS.length)];
  }
  return code;
}

/** @type {Map<string, Room>} */
const rooms = new Map();

class Room {
  constructor(hostWs, maxNodes) {
    this.code = genCode();
    while (rooms.has(this.code)) {
      this.code = genCode();
    }
    this.hostWs = hostWs;
    this.maxNodes = Math.max(1, Math.min(maxNodes, 64));
    this.expiresAt = Date.now() + ROOM_TTL * 1000;
    /** @type {Map<string, {ws: WebSocket, name: string}>} */
    this.nodes = new Map();
    this.nextNodeId = 1;
    rooms.set(this.code, this);
  }

  addNode(ws, name) {
    if (this.nodes.size >= this.maxNodes) return null;
    const nid = String(this.nextNodeId++);
    this.nodes.set(nid, { ws, name: name || nid });
    return nid;
  }

  sendHost(obj) {
    try {
      this.hostWs.send(JSON.stringify(obj));
    } catch (e) {}
  }

  broadcastToNodes(obj) {
    const msg = JSON.stringify(obj);
    const dead = [];
    for (const [nid, node] of this.nodes) {
      try {
        node.ws.send(msg);
      } catch (e) {
        dead.push(nid);
      }
    }
    dead.forEach(nid => this.nodes.delete(nid));
  }

  shutdown() {
    this.broadcastToNodes({ type: 'room_closed' });
    for (const node of this.nodes.values()) {
      try { node.ws.close(); } catch (e) {}
    }
    this.nodes.clear();
    rooms.delete(this.code);
  }
}

// 定期清理过期房间
setInterval(() => {
  const now = Date.now();
  for (const [code, room] of rooms) {
    if (now > room.expiresAt) {
      room.shutdown();
    }
  }
}, 30000);

async function handleHost(ws, msg) {
  const maxNodes = parseInt(msg.max_nodes || '8', 10);
  const room = new Room(ws, maxNodes);
  
  ws.send(JSON.stringify({ type: 'hosted', code: room.code, ttl: ROOM_TTL }));
  console.log(`[host] Room created: ${room.code}`);

  ws.addEventListener('message', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'broadcast') {
        room.broadcastToNodes(data.payload || {});
      } else if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }));
      } else if (data.type === 'extend') {
        room.expiresAt = Date.now() + ROOM_TTL * 1000;
        ws.send(JSON.stringify({ type: 'extended', ttl: ROOM_TTL }));
      }
    } catch (e) {}
  });

  ws.addEventListener('close', () => {
    if (rooms.has(room.code) && rooms.get(room.code) === room) {
      rooms.delete(room.code);
    }
    room.shutdown();
    console.log(`[host] Room closed: ${room.code}`);
  });
}

async function handleNode(ws, msg) {
  const code = (msg.code || '').trim().toUpperCase();
  const name = (msg.name || 'node').trim().slice(0, 32);

  const room = rooms.get(code);
  if (!room) {
    ws.send(JSON.stringify({ type: 'error', msg: 'invite code not found or expired' }));
    ws.close();
    return;
  }

  if (Date.now() > room.expiresAt) {
    room.shutdown();
    ws.send(JSON.stringify({ type: 'error', msg: 'invite code expired' }));
    ws.close();
    return;
  }

  const nid = room.addNode(ws, name);
  if (!nid) {
    ws.send(JSON.stringify({ type: 'error', msg: 'room is full' }));
    ws.close();
    return;
  }

  ws.send(JSON.stringify({ type: 'joined', node_id: nid }));
  room.sendHost({ type: 'node_joined', node_id: nid, name: room.nodes.get(nid).name });
  console.log(`[node] Joined room ${code}: ${name}`);

  ws.addEventListener('message', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'stats') {
        room.sendHost({
          type: 'stats',
          node_id: nid,
          name: room.nodes.get(nid)?.name || nid,
          stats: data.stats || {},
        });
      } else if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }));
      } else if (data.type === 'leave') {
        ws.close();
      }
    } catch (e) {}
  });

  ws.addEventListener('close', () => {
    const node = room.nodes.get(nid);
    const nodeName = node ? node.name : name;
    room.nodes.delete(nid);
    room.sendHost({ type: 'node_left', node_id: nid, name: nodeName });
    console.log(`[node] Left room ${code}: ${nodeName}`);
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 健康检查
    if (url.pathname === '/' || url.pathname === '/health' || url.pathname === '/ping') {
      return new Response(JSON.stringify({ status: 'ok', rooms: rooms.size }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // WebSocket 升级
    if (request.headers.get('Upgrade') !== 'websocket') {
      return new Response('NetPulse Relay Server - Use WebSocket', { status: 400 });
    }

    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    server.accept();

    // 等待第一条消息确定角色
    const handleFirstMessage = async (event) => {
      try {
        const msg = JSON.parse(event.data);
        server.removeEventListener('message', handleFirstMessage);
        
        if (msg.type === 'host') {
          await handleHost(server, msg);
        } else if (msg.type === 'join') {
          await handleNode(server, msg);
        } else {
          server.send(JSON.stringify({ type: 'error', msg: 'first message must be host or join' }));
          server.close();
        }
      } catch (e) {
        try {
          server.send(JSON.stringify({ type: 'error', msg: String(e) }));
          server.close();
        } catch (e2) {}
      }
    };

    server.addEventListener('message', handleFirstMessage);

    // 30秒超时
    setTimeout(() => {
      try { server.close(); } catch (e) {}
    }, 30000);

    return new Response(null, {
      status: 101,
      webSocket: client,
    });
  },
};
