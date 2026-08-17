"""网络工具：公网 IP 探测、UPnP 自动端口映射、Windows 防火墙放行。

用于协同测试跨外网（非局域网）连接主控节点。
"""
import ctypes
import socket
import subprocess

import requests

PORT = 50505


def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def get_public_ip(timeout: float = 6):
    """通过公网服务探测本机出口 IP。"""
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://ip.3322.net"):
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent": "curl/8.0"})
            ip = r.text.strip()
            if r.status_code == 200 and 0 < len(ip) < 46:
                return ip
        except Exception:
            continue
    return None


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def add_firewall_rule(port: int = PORT) -> bool:
    """添加 Windows 防火墙入站放行规则（需管理员权限）。"""
    try:
        flags = 0x08000000  # CREATE_NO_WINDOW
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name=NetPulse Collab"],
            capture_output=True, creationflags=flags)
        r = subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule", "name=NetPulse Collab",
             "dir=in", "action=allow", "protocol=TCP", f"localport={port}"],
            capture_output=True, text=True, creationflags=flags)
        return r.returncode == 0
    except Exception:
        return False


def upnp_map(port: int = PORT):
    """尝试 UPnP 在路由器上自动做端口映射。返回 (成功, 外部IP或错误)。"""
    try:
        import miniupnpc
        u = miniupnpc.UPnP()
        u.discoverdelay = 2000
        if u.discover() < 1:
            return False, "未发现 UPnP 网关"
        u.selectigd()
        external = u.externalipaddress()
        try:
            u.deleteportmapping(port, "TCP")
        except Exception:
            pass
        u.addportmapping(port, "TCP", u.lanaddr, port, "NetPulse Collab", "")
        return True, external
    except Exception as e:
        return False, str(e)
