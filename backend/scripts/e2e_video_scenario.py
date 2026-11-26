"""Сквозная проверка логики редактора по сценарию из видео ТЗ.

Запуск (backend на :8000, Keitaro доступен):
    python scripts/e2e_video_scenario.py
"""

import sys
import time
from pathlib import Path

import httpx

# Адрес и ключ Keitaro берём из backend/.env, а не храним в скрипте
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings  # noqa: E402

API = "http://localhost:8000/api"
KEITARO = get_settings().keitaro_base_url.rstrip("/")
KEY = get_settings().keitaro_api_key

client = httpx.Client(timeout=60)
failed = 0


def check(title: str, condition: bool, extra: str = "") -> None:
    global failed
    print(("OK   " if condition else "FAIL ") + title + (f"  [{extra}]" if extra else ""))
    if not condition:
        failed += 1


def shares(stream: dict, status: str = "active") -> dict[int, int]:
    return {o["offer_id"]: o["share"] for o in stream["offers"] if o["status"] == status}


def keitaro_offers(stream_id: int) -> dict[int, int]:
    data = client.get(f"{KEITARO}/streams/{stream_id}", headers={"Api-Key": KEY}).json()
    return {o["offer_id"]: o["share"] for o in data["offers"]}


def api(method: str, path: str, **kwargs) -> httpx.Response:
    return client.request(method, API + path, **kwargs)


name = f"e2e_video_{int(time.time())}"
created = api(
    "POST", "/campaigns", json={"name": name, "geo_code": "DE", "offer_ids": [18004, 18032, 18044]}
).json()
streams = {s["name"]: s for s in created["streams"]}
geo = next(s for s in created["streams"] if not s["editable"])
stream = next(s for s in created["streams"] if s["editable"])
sid, ksid = stream["id"], stream["keitaro_stream_id"]

check("гео-поток показан как поток без офферов", not geo["editable"] and geo["offers"] == [])
check("3 оффера, доли 34/33/33", sorted(shares(stream).values()) == [33, 33, 34], str(shares(stream)))
check("поток не грязный после создания", stream["dirty"] is False)

# Добавление: веса пересчитались, поток жёлтый, в Keitaro пока 3
s = api("POST", f"/streams/{sid}/offers", json={"offer_id": 18052}).json()
check("добавили 4-й: по 25%", set(shares(s).values()) == {25}, str(shares(s)))
check("поток жёлтый (dirty)", s["dirty"] is True)
check("в Keitaro всё ещё 3 оффера", len(keitaro_offers(ksid)) == 3)

# Cancel: добавленный оффер исчезает, поток снова чистый
s = api("POST", f"/streams/{sid}/cancel").json()
check("cancel: 3 оффера, не грязный", len(shares(s)) == 3 and not s["dirty"])
check("cancel: привязка удалена, в архиве пусто", shares(s, "removed") == {})

# Добавляем снова и публикуем
api("POST", f"/streams/{sid}/offers", json={"offer_id": 18052})
s = api("POST", f"/streams/{sid}/push").json()
check("push: не грязный", not s["dirty"])
check("push: в Keitaro 4 оффера по 25", set(keitaro_offers(ksid).values()) == {25} and len(keitaro_offers(ksid)) == 4)

# Remove: серый, 0%, поток жёлтый; после Push исчез из Keitaro, но остался в архиве
s = api("DELETE", f"/streams/{sid}/offers/18052").json()
removed = shares(s, "removed")
check("remove: оффер в статусе removed с 0%", removed == {18052: 0}, str(removed))
check("remove: остальные по 34/33/33", sorted(shares(s).values()) == [33, 33, 34])
check("remove: поток жёлтый", s["dirty"])
s = api("POST", f"/streams/{sid}/push").json()
check("push после remove: оффера нет в Keitaro", 18052 not in keitaro_offers(ksid))
check("push после remove: оффер остался в архиве", 18052 in shares(s, "removed"))

# Bring back + cancel возвращает в архив
s = api("POST", f"/streams/{sid}/offers/18052/restore").json()
check("bring back: оффер снова активен, поток жёлтый", 18052 in shares(s) and s["dirty"])
s = api("POST", f"/streams/{sid}/cancel").json()
check("cancel после bring back: оффер снова в архиве", 18052 in shares(s, "removed") and not s["dirty"])

# Bring back + push
api("POST", f"/streams/{sid}/offers/18052/restore")
s = api("POST", f"/streams/{sid}/push").json()
check("bring back + push: оффер вернулся в Keitaro", 18052 in keitaro_offers(ksid))

# Удалили оффер руками в Keitaro -> Fetch streams переводит его в removed
rest = [{"offer_id": k, "share": 100 // 3 + (1 if i == 0 else 0), "state": "active"}
        for i, k in enumerate([18004, 18032, 18044])]
client.put(f"{KEITARO}/streams/{ksid}", headers={"Api-Key": KEY}, json={"offers": rest})
detail = api("POST", f"/campaigns/{created['id']}/fetch").json()
s = next(x for x in detail["streams"] if x["editable"])
check("fetch: удалённый в Keitaro оффер стал removed", 18052 in shares(s, "removed"), str(shares(s, "removed")))
check("fetch: остальные активны, поток не грязный", len(shares(s)) == 3 and not s["dirty"])

# Пин: 18004 = 25%, остальные делят 75%; добавление/возврат не трогают пин
s = api("PATCH", f"/streams/{sid}/offers/18004", json={"share": 25}).json()
pinned = next(o for o in s["offers"] if o["offer_id"] == 18004)
check("пин 25% у 18004", pinned["pinned"] and pinned["share"] == 25)
check("остальные делят 75%", sum(shares(s).values()) == 100, str(shares(s)))
s = api("POST", f"/streams/{sid}/offers/18052/restore").json()
check("после возврата оффера пин остался 25%", shares(s)[18004] == 25, str(shares(s)))
check("сумма 100, остальные поровну", sum(shares(s).values()) == 100 and shares(s)[18032] in (25, 26), str(shares(s)))
s = api("POST", f"/streams/{sid}/push").json()
check("push: в Keitaro пин 25% и сумма 100", keitaro_offers(ksid)[18004] == 25 and sum(keitaro_offers(ksid).values()) == 100, str(keitaro_offers(ksid)))

# Невалидные пины
bad = api("PATCH", f"/streams/{sid}/offers/18032", json={"share": 90})
check("пины > 100% отклоняются (400)", bad.status_code == 400, bad.text[:120])
s = api("GET", f"/campaigns/{created['id']}").json()
check("после ошибки состояние не изменилось", not next(x for x in s["streams"] if x["editable"])["dirty"])

print("\nПровалено:", failed)
sys.exit(1 if failed else 0)
