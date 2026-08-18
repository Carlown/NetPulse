"""NetPulse 协同测试 - WebSocket 中继服务器

用法：
    pip install websockets
    python relay_server.py [--host 0.0.0.0] [--port 50506]

免费部署（Replit）：
    1. 去 replit.com 注册（用 Google 账号即可，无需信用卡）
    2. 创建 Python Repl，把本文件内容粘贴到 main.py
    3. 把 requirements.txt 改为：websockets
    4. 点击 Run，会得到一个 https://xxx.repl.co 的地址
    5. 在 NetPulse 设置里把中继地址改为这个地址（去掉 https://，加 :443）

协议说明：
    - 使用 WebSocket 连接（ws:// 或 wss://）
    - 所有消息均为 JSON 对象
    - 主控：连接后发送 {"type":"host","max_nodes":N}，收到 {"type":"hosted","code":"ABC123"}
    - 节点：连接后发送 {"type":"join","code":"ABC123","name":"node1"}，收到 {"type":"joined","node_id":"x"}
    - 主控广播：{"type":"broadcast","payload":{...}}
    - 节点上报：{"type":"stats","stats":{...}}
    - 节点退出：{"type":"leave"}
    - 心跳：{"type":"ping"} / {"type":"pong"}
"""
import argparse
import asyncio
import json
import random
import string
import time
from typing import Dict, Set

# 房间邀请码有效期（秒）
ROOM_TTL = 300
# 清理过期房间间隔（秒）
CLEANUP_INTERVAL = 30
# 心跳超时（秒）
HEARTBEAT_TIMEOUT = 60
# 房间邀请码字符集（去掉易混淆的 O/0/I/1）
CODE_CHARS = string.ascii_uppercase.replace("O", "").replace("I", "") + string.digits.replace("0", "").replace("1", "")


def gen_code(length=6) -> str:
    return "".join(random.choices(CODE_CHARS, k=length))


class Room:
    """一个主控房间，管理主控 WebSocket 和多个节点连接。"""

    def __init__(self, host_ws, max_nodes: int):
        self.code = gen_code()
        while self.code in RelayServer._rooms:
            self.code = gen_code()
        self.host_ws = host_ws
        self.max_nodes = max(1, min(max_nodes, 64))
        self.created_at = time.time()
        self.expires_at = self.created_at + ROOM_TTL
        self.nodes: Dict[str, dict] = {}  # node_id -> {ws, name}
        self._next_node_id = 1

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def add_node(self, ws, name: str) -> str:
        if self.node_count >= self.max_nodes:
            return ""
        nid = str(self._next_node_id)
        self._next_node_id += 1
        self.nodes[nid] = {"ws": ws, "name": name or nid}
        return nid

    def remove_node(self, nid: str):
        self.nodes.pop(nid, None)

    async def send_host(self, obj: dict):
        try:
            await self.host_ws.send(json.dumps(obj))
        except Exception:
            pass

    async def broadcast_to_nodes(self, obj: dict):
        msg = json.dumps(obj)
        dead = []
        for nid, node in self.nodes.items():
            try:
                await node["ws"].send(msg)
            except Exception:
                dead.append(nid)
        for nid in dead:
            self.nodes.pop(nid, None)

    async def shutdown(self):
        """关闭房间，通知所有节点。"""
        await self.broadcast_to_nodes({"type": "room_closed"})
        for node in list(self.nodes.values()):
            try:
                await node["ws"].close()
            except Exception:
                pass
        self.nodes.clear()


class RelayServer:
    _rooms: Dict[str, Room] = {}

    def __init__(self):
        self.host_rooms: Dict[object, Room] = {}  # ws -> Room
        self.node_rooms: Dict[object, tuple] = {}  # ws -> (room, nid)
        self.last_ping: Dict[object, float] = {}  # ws -> last_pong_time

    async def handle_connection(self, websocket):
        """处理一个 WebSocket 连接（可能是主控也可能是节点）。"""
        self.last_ping[websocket] = time.time()
        try:
            # 等待第一条消息来确定角色
            raw = await asyncio.wait_for(websocket.recv(), timeout=30)
            msg = json.loads(raw)
            mtype = msg.get("type")

            if mtype == "host":
                await self._handle_host(websocket, msg)
            elif mtype == "join":
                await self._handle_node(websocket, msg)
            else:
                await websocket.send(json.dumps({"type": "error", "msg": f"unknown type: {mtype}"}))
        except asyncio.TimeoutError:
            pass
        except (json.JSONDecodeError, Exception) as e:
            try:
                await websocket.send(json.dumps({"type": "error", "msg": str(e)}))
            except Exception:
                pass
        finally:
            await self._cleanup(websocket)

    async def _handle_host(self, ws, msg: dict):
        """处理主控连接。"""
        max_nodes = int(msg.get("max_nodes", 8))
        room = Room(ws, max_nodes)
        self._rooms[room.code] = room
        self.host_rooms[ws] = room

        await ws.send(json.dumps({"type": "hosted", "code": room.code, "ttl": ROOM_TTL}))
        print(f"[host] Room created: {room.code} (max {max_nodes} nodes)")

        # 维持连接，处理后续消息
        try:
            async for raw in ws:
                self.last_ping[ws] = time.time()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                t = data.get("type")
                if t == "broadcast":
                    # 转发给所有节点，包装成 broadcast 消息
                    await room.broadcast_to_nodes(data.get("payload", {}))
                elif t == "ping":
                    await ws.send(json.dumps({"type": "pong"}))
                elif t == "extend":
                    room.expires_at = time.time() + ROOM_TTL
                    await ws.send(json.dumps({"type": "extended", "ttl": ROOM_TTL}))
        except Exception:
            pass
        finally:
            # 主控断开，关闭房间
            if room.code in self._rooms and self._rooms[room.code] is room:
                del self._rooms[room.code]
            self.host_rooms.pop(ws, None)
            await room.shutdown()
            print(f"[host] Room closed: {room.code}")

    async def _handle_node(self, ws, msg: dict):
        """处理节点连接。"""
        code = (msg.get("code") or "").strip().upper()
        name = (msg.get("name") or "node").strip()[:32]

        room = self._rooms.get(code)
        if not room:
            await ws.send(json.dumps({"type": "error", "msg": "invite code not found or expired"}))
            return

        if room.is_expired():
            del self._rooms[code]
            await room.shutdown()
            await ws.send(json.dumps({"type": "error", "msg": "invite code expired"}))
            return

        nid = room.add_node(ws, name)
        if not nid:
            await ws.send(json.dumps({"type": "error", "msg": "room is full"}))
            return

        self.node_rooms[ws] = (room, nid)
        await ws.send(json.dumps({"type": "joined", "node_id": nid}))
        await room.send_host({"type": "node_joined", "node_id": nid, "name": room.nodes[nid]["name"]})
        print(f"[node] Joined room {code}: {name} (id={nid})")

        # 维持连接，处理后续消息
        try:
            async for raw in ws:
                self.last_ping[ws] = time.time()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                t = data.get("type")
                if t == "stats":
                    await room.send_host({
                        "type": "stats",
                        "node_id": nid,
                        "name": room.nodes.get(nid, {}).get("name", nid),
                        "stats": data.get("stats", {}),
                    })
                elif t == "ping":
                    await ws.send(json.dumps({"type": "pong"}))
                elif t == "leave":
                    break
        except Exception:
            pass
        finally:
            # 节点断开
            room.remove_node(nid)
            self.node_rooms.pop(ws, None)
            await room.send_host({"type": "node_left", "node_id": nid, "name": name})
            print(f"[node] Left room {code}: {name}")

    async def _cleanup(self, ws):
        """清理一个断开的连接。"""
        self.last_ping.pop(ws, None)
        # host_rooms 和 node_rooms 的清理在各自的 handler 中做了

    async def cleanup_loop(self):
        """后台任务：定期清理过期房间和心跳超时的连接。"""
        while True:
            await asyncio.sleep(CLEANUP_INTERVAL)
            now = time.time()

            # 清理过期房间
            expired = [code for code, room in self._rooms.items() if room.is_expired()]
            for code in expired:
                room = self._rooms.pop(code, None)
                if room:
                    await room.shutdown()
                    print(f"[cleanup] Expired room: {code}")

            # 清理心跳超时的连接
            dead = [ws for ws, last in self.last_ping.items() if now - last > HEARTBEAT_TIMEOUT]
            for ws in dead:
                self.last_ping.pop(ws, None)
                try:
                    await ws.close()
                except Exception:
                    pass

    async def process_request(self, path, request_headers):
        """处理 HTTP 请求（用于健康检查）。"""
        if path in ("/health", "/healthz", "/ping", "/"):
            return (200, [("Content-Type", "application/json")],
                    json.dumps({"status": "ok", "rooms": len(self._rooms)}).encode())
        # WebSocket 升级请求交给默认处理
        return None


async def main():
    parser = argparse.ArgumentParser(description="NetPulse WebSocket Relay Server")
    parser.add_argument("--host", default="0.0.0.0", help="listen host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=50506, help="listen port (default: 50506)")
    args = parser.parse_args()

    try:
        import websockets
    except ImportError:
        print("Missing dependency: pip install websockets")
        return

    server = RelayServer()

    print(f"NetPulse WebSocket Relay Server starting on {args.host}:{args.port}...")
    async with websockets.serve(
        server.handle_connection,
        args.host,
        args.port,
        process_request=server.process_request,
        ping_interval=20,
        ping_timeout=30,
    ):
        await server.cleanup_loop()


if __name__ == "__main__":
    asyncio.run(main())
