#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取体彩超级大乐透开奖数据
API来源: https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry

用法:
    python dlt_fetcher.py --latest    # 获取最新一期
    python dlt_fetcher.py --history   # 获取近10年历史数据
"""

import argparse
import csv
import gzip
import json
import random
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

API_URL = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Referer": "https://m.lottery.gov.cn/mkjdlt/",
    "Accept-Encoding": "gzip, deflate, br",
}

GAME_NO = "85"
PAGE_SIZE = 30


def _decode_body(resp):
    raw = resp.read()
    encoding = resp.headers.get("Content-Encoding") or resp.headers.get("content-encoding")
    if encoding and "gzip" in encoding.lower():
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    return raw


def fetch_page(page_no, timeout=15):
    params = urllib.parse.urlencode({
        "gameNo": GAME_NO,
        "provinceId": "0",
        "pageSize": str(PAGE_SIZE),
        "isVerify": "1",
        "termLimits": "0",
        "pageNo": str(page_no),
    })
    url = f"{API_URL}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = _decode_body(resp)
        return json.loads(body.decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"请求第{page_no}页失败: {e}")
        return None


def parse_record(record):
    result = record.get("lotteryDrawResult") or ""
    parts = result.strip().split() if result else []
    front = parts[:5]
    back = parts[5:7]
    return {
        "期号": record.get("lotteryDrawNum", ""),
        "开奖日期": record.get("lotteryDrawTime", ""),
        "开奖号码": result,
        "前区": " ".join(front),
        "后区": " ".join(back)
    }


def get_latest():
    data = fetch_page(1)
    if data and data.get("success"):
        items = (data.get("value") or {}).get("list", [])
        if items:
            return parse_record(items[0])
    return None


def get_all_data():
    all_records = []
    page = 1
    max_records = 2000
    max_pages = (max_records // PAGE_SIZE) + 2

    while page <= max_pages:
        print(f"正在获取第 {page} 页...")
        data = fetch_page(page)

        if data is None or not data.get("success"):
            print(f"API返回异常: {data}")
            time.sleep(1.0)
            data = fetch_page(page)
            if data is None or not data.get("success"):
                print(f"跳过第 {page} 页")
                page += 1
                continue

        records = (data.get("value") or {}).get("list", [])
        if not records:
            print("没有更多数据了")
            break

        for record in records:
            parsed = parse_record(record)
            all_records.append(parsed)

        if records:
            latest_date = records[0].get("lotteryDrawTime", "")
            if latest_date:
                try:
                    record_date = datetime.strptime(latest_date[:10], "%Y-%m-%d")
                    ten_years_ago = datetime.now() - timedelta(days=365 * 10)
                    if record_date < ten_years_ago:
                        print("已超过10年数据，停止获取")
                        break
                except:
                    pass

        if len(records) < PAGE_SIZE:
            break

        page += 1
        time.sleep(random.uniform(5, 20))

    return sorted(all_records, key=lambda x: (x.get("开奖日期") or "", x.get("期号") or ""))


def save_to_file(records, filename="dlt_history.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到 {filename}，共 {len(records)} 条记录")


def save_to_csv(records, filename="dlt_history.csv"):
    if not records:
        return
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["期号", "开奖日期", "开奖号码"])
        writer.writeheader()
        writer.writerows(records)
    print(f"数据已保存到 {filename}，共 {len(records)} 条记录")


def main():
    parser = argparse.ArgumentParser(description="获取大乐透开奖数据")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true", help="获取最新一期数据")
    group.add_argument("--history", action="store_true", help="获取近10年历史数据")
    args = parser.parse_args()

    print("=" * 50)
    if args.latest:
        print("获取大乐透最新一期数据")
        record = get_latest()
        if record:
            print(json.dumps(record, ensure_ascii=False, indent=2))
        else:
            print("未能获取到最新数据")
    else:
        print("获取大乐透近10年历史数据")
        print("=" * 50)
        records = get_all_data()
        if records:
            save_to_file(records, "dlt_history.json")
            save_to_csv(records, "dlt_history.csv")
            print("\n前5条数据预览:")
            for r in records[:5]:
                print(r)
        else:
            print("未能获取到数据")
    print("=" * 50)


if __name__ == "__main__":
    main()
