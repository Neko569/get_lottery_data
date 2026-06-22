#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取过去 10 年体彩超级大乐透开奖数据，并存为 CSV 与 JSON。
数据接口：
  https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry
    ?gameNo=85&provinceId=0&pageSize=30&isVerify=1&termLimits=0&pageNo={n}
"""

import csv
import gzip
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


API_URL = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
    ),
    "Referer": "https://m.lottery.gov.cn/mkjdlt/",
    "Accept-Encoding": "gzip, deflate, br",
}

GAME_NO = "85"
PAGE_SIZE = 30

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(OUTPUT_DIR, "daletou_history.csv")
JSON_PATH = os.path.join(OUTPUT_DIR, "daletou_history.json")


def _decode_body(resp: "urllib.request._UrlopenRet") -> bytes:
    raw = resp.read()
    encoding = resp.headers.get("Content-Encoding") or resp.headers.get("content-encoding")
    if encoding and "gzip" in encoding.lower():
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    return raw


def fetch_page(page_no: int, timeout: int = 15) -> Optional[Dict[str, Any]]:
    """抓取一页数据，失败返回 None。"""
    params = urllib.parse.urlencode(
        {
            "gameNo": GAME_NO,
            "provinceId": "0",
            "pageSize": str(PAGE_SIZE),
            "isVerify": "1",
            "termLimits": "0",
            "pageNo": str(page_no),
        }
    )
    url = f"{API_URL}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = _decode_body(resp)
        data = json.loads(body.decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] pageNo={page_no} 请求失败: {exc}")
        return None

    if not data or not data.get("success"):
        print(f"[WARN] pageNo={page_no} 返回非成功: {data}")
        return None
    return data


def parse_numbers(result_str: str):
    """解析前 5 位 + 后 2 位号码。大乐透格式: '03 11 12 21 22 06 10'。"""
    if not result_str:
        return [], []
    parts = result_str.strip().split()
    front = parts[:5]
    back = parts[5:7]
    return front, back


def normalize_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """把原始接口 record 展平成干净的 dict。"""
    result = raw.get("lotteryDrawResult") or ""
    front, back = parse_numbers(result)

    prize_summary: Dict[str, Dict[str, Any]] = {}
    for p in raw.get("prizeLevelList") or []:
        level_name = p.get("prizeLevel") or ""
        if not level_name:
            continue
        prize_summary[level_name] = {
            "stakeCount": p.get("stakeCount"),
            "stakeAmount": p.get("stakeAmount"),
            "stakeAmountFormat": p.get("stakeAmountFormat"),
            "totalPrizeamount": p.get("totalPrizeamount"),
        }

    return {
        "term": raw.get("lotteryDrawNum"),
        "draw_time": raw.get("lotteryDrawTime"),
        "draw_result": result,
        "front_numbers": front,
        "back_numbers": back,
        "pool_balance_after_draw": raw.get("poolBalanceAfterdraw"),
        "pool_balance": raw.get("poolBalance"),
        "total_sale_amount": raw.get("totalSaleAmount"),
        "flow_fund": raw.get("drawFlowFund"),
        "equipment_count": raw.get("lotteryEquipmentCount"),
        "pdf_url": raw.get("drawPdfUrl"),
        "game_name": raw.get("lotteryGameName"),
        "verify": raw.get("verify"),
        "draw_status": raw.get("lotteryDrawStatus"),
        "notice": raw.get("lotteryNotice"),
        "sale_begin_time": raw.get("lotterySaleBeginTime"),
        "sale_end_time": raw.get("lotterySaleEndtime"),
        "paid_begin_time": raw.get("lotteryPaidBeginTime"),
        "paid_end_time": raw.get("lotteryPaidEndTime"),
        "prize_levels": prize_summary,
        "raw": raw,
    }


def should_keep(item: Dict[str, Any], earliest: datetime) -> bool:
    """根据开奖时间判断是否保留。"""
    dt = item.get("draw_time")
    if not dt:
        return False
    try:
        return datetime.strptime(dt[:10], "%Y-%m-%d") >= earliest
    except ValueError:
        return False


def fetch_all_history(years: int = 10, max_pages: int = 200, sleep: float = 0.6) -> List[Dict[str, Any]]:
    """按页抓取，直到遇到 10 年前的记录或空页。"""
    earliest = datetime.now() - timedelta(days=years * 365 + 2)
    print(f"[INFO] 目标时间范围: {earliest.strftime('%Y-%m-%d')} 至今 (约 {years} 年)")

    collected: Dict[str, Dict[str, Any]] = {}
    reached_end = False

    for page_no in range(1, max_pages + 1):
        raw = fetch_page(page_no)
        if not raw:
            # 重试一次
            time.sleep(1.0)
            raw = fetch_page(page_no)
        if not raw:
            print(f"[WARN] 跳过第 {page_no} 页，继续尝试下一页…")
            continue

        items = (raw.get("value") or {}).get("list") or []
        if not items:
            print(f"[INFO] 第 {page_no} 页为空，抓取结束。")
            reached_end = True
            break

        stopped_this_page = False
        for raw_item in items:
            item = normalize_item(raw_item)
            term = item.get("term") or item.get("draw_time")
            if not term:
                continue
            if term in collected:
                continue
            if not should_keep(item, earliest):
                stopped_this_page = True
                break
            collected[term] = item

        first_on_page = items[0].get("lotteryDrawTime") if items else None
        last_on_page = items[-1].get("lotteryDrawTime") if items else None
        print(
            f"[INFO] pageNo={page_no:<3} 本期={len(items):>3} 条, "
            f"时间范围: {first_on_page} ~ {last_on_page}, 累计={len(collected)}"
        )

        if stopped_this_page:
            print(f"[INFO] 已触及 {years} 年范围边界，停止抓取。")
            reached_end = True
            break

        time.sleep(sleep)

    if not reached_end:
        print(f"[WARN] 已达最大页数 ({max_pages})，仍可能有更早数据未抓取。")

    # 按期号（升序，历史→最新）排序
    sorted_items = sorted(
        collected.values(),
        key=lambda x: (
            x.get("draw_time") or "",
            x.get("term") or "",
        ),
    )
    return sorted_items


# -------- 写入 --------

JSON_LITE_FIELDS = [
    "term",
    "draw_time",
    "draw_result",
    "front_numbers",
    "back_numbers",
]

CSV_HEADERS = [
    "term",
    "draw_time",
    "front_1", "front_2", "front_3", "front_4", "front_5",
    "back_1", "back_2",
]

def build_csv_row(item: Dict[str, Any]) -> List[str]:
    front = item.get("front_numbers") or []
    back = item.get("back_numbers") or []
    while len(front) < 5:
        front.append("")
    while len(back) < 2:
        back.append("")

    return [
        item.get("term") or "",
        item.get("draw_time") or "",
        front[0], front[1], front[2], front[3], front[4],
        back[0], back[1],
    ]


def write_csv(items: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        for item in items:
            writer.writerow(build_csv_row(item))
    print(f"[OK] CSV 已写入: {path}  共 {len(items)} 行")


def write_json(items: List[Dict[str, Any]], path: str) -> None:
    lite_items = []
    for item in items:
        lite = {k: item.get(k) for k in JSON_LITE_FIELDS}
        lite_items.append(lite)
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "sporttery.cn",
        "game": "超级大乐透",
        "game_no": GAME_NO,
        "total": len(lite_items),
        "items": lite_items,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON 已写入: {path}  共 {len(items)} 条")


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    items = fetch_all_history(years=10)
    if not items:
        print("[ERROR] 未能抓取到任何数据。")
        return

    print(
        f"[INFO] 数据时间范围: "
        f"{items[0].get('draw_time')} ~ {items[-1].get('draw_time')}"
    )

    write_csv(items, CSV_PATH)
    write_json(items, JSON_PATH)


if __name__ == "__main__":
    main()
