"""Search a small, reviewed index of official client documentation."""

import re
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class ClientGuide:
    title: str
    url: str
    filename: str

    @property
    def facts(self):
        return (Path(__file__).with_name("client_guides") / self.filename).read_text(encoding="utf-8").strip()


HAPP_ROUTING = ClientGuide(
    "Happ · маршрутизация",
    "https://www.happ.su/main/dev-docs/routing",
    "happ_routing.md",
)
INCY_ROUTING = ClientGuide(
    "INCY · маршрутизация",
    "https://docs.incy.cc/routing/",
    "incy_routing.md",
)
INCY_IMPORT = ClientGuide(
    "INCY · импорт подписки",
    "https://docs.incy.cc/deep-links/",
    "incy_import.md",
)
HAPP_START = ClientGuide(
    "Happ · версии приложения",
    "https://www.happ.su/main",
    "happ_start.md",
)

_CLIENT = re.compile(r"\b(happ|хапп?|incy|инси)\b", re.IGNORECASE)
_ROUTING = re.compile(r"geosite|geoip|геофайл|xray\s*core|маршрутиз", re.IGNORECASE)
_SETUP = re.compile(r"импорт|установ|обнов|добав.{0,24}подписк|подписк.{0,24}добав", re.IGNORECASE)


def identify_client(messages):
    for row in reversed(messages):
        if row["sender"] != "user":
            continue
        names = {"happ" if name in {"happ", "хап", "хапп"} else "incy" for name in _CLIENT.findall(row["body"].lower())}
        if names:
            return next(iter(names)) if len(names) == 1 else None
    return None


def find_client_guide(messages):
    """Match a client and current topic without calling an external search engine."""
    client = identify_client(messages)
    if not client:
        return None
    latest = messages[-1]["body"]
    if _ROUTING.search(latest):
        return HAPP_ROUTING if client == "happ" else INCY_ROUTING
    if _SETUP.search(latest):
        return HAPP_START if client == "happ" else INCY_IMPORT
    return None
