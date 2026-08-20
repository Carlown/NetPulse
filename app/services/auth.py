"""目标授权管理：压测目标必须先通过授权确认。"""
import re
import time
import uuid

from app.services.logger import log
from app.services.settings import settings
from app.ui.i18n import L


def normalize_host(target: str) -> str:
    """提取主机名：去掉协议、路径、端口。"""
    t = (target or "").strip()
    t = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", t)
    t = t.split("/")[0]
    t = t.split(":")[0]
    return t.lower().strip()


def is_authorized(host: str) -> bool:
    return any(a.get("host") == host for a in settings.authorized)


def add_authorized(host: str, note: str = ""):
    if not host:
        return
    if is_authorized(host):
        return
    settings.authorized.append({"id": uuid.uuid4().hex[:8], "host": host,
                                "note": note, "ts": time.time()})
    settings.save()
    log.info(L(f"新增授权目标: {host}", f"Target authorized: {host}"))


def remove_authorized(host: str):
    settings.authorized = [a for a in settings.authorized if a.get("host") != host]
    settings.save()
    log.info(L(f"移除授权目标: {host}", f"Target authorization removed: {host}"))


def is_private_target(host: str) -> bool:
    """本机/内网地址视为低风险目标。"""
    return (host in ("localhost", "127.0.0.1", "::1", "0.0.0.0")
            or host.startswith("192.168.") or host.startswith("10.")
            or host.startswith("172.16.") or host.startswith("172.17.")
            or host.startswith("172.18.") or host.startswith("172.19.")
            or host.endswith(".local") or host.endswith(".lan"))
