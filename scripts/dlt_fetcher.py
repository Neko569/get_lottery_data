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
import os
import random
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

# 获取脚本所在目录，并设置数据存储目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "../data")
os.makedirs(DATA_DIR, exist_ok=True)

# API配置
API_URL = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Referer": "https://m.lottery.gov.cn/mkjdlt/",
    "Accept-Encoding": "gzip, deflate, br",
}

GAME_NO = "85"  # 大乐透的游戏代码
PAGE_SIZE = 30  # 每页返回的记录数


def _decode_body(resp):
    """解码API响应内容，支持gzip压缩"""
    raw = resp.read()
    # 检查响应是否使用gzip压缩
    encoding = resp.headers.get("Content-Encoding") or resp.headers.get("content-encoding")
    if encoding and "gzip" in encoding.lower():
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    return raw


def fetch_page(page_no, timeout=15):
    """获取指定页码的数据"""
    # 构建API请求参数
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
    """解析单条开奖记录，提取并重组所需字段"""
    result = record.get("lotteryDrawResult") or ""
    parts = result.strip().split() if result else []
    # 分离前区(5个号码)和后区(2个号码)
    front_numbers = parts[:5]
    back_numbers = parts[5:7]
    return {
        "term": record.get("lotteryDrawNum", ""),
        "draw_time": record.get("lotteryDrawTime", ""),
        "draw_result": result,
        "front_numbers": front_numbers,
        "back_numbers": back_numbers
    }


def get_latest():
    """获取最新一期的开奖数据"""
    data = fetch_page(1)
    if data and data.get("success"):
        items = (data.get("value") or {}).get("list", [])
        if items:
            return parse_record(items[0])
    return None


def get_all_data(months=None):
    """
    获取历史开奖数据
    通过分页遍历获取数据，直到达到指定月份前的记录或达到最大页数
    months: 保留最近几个月的数据，None表示保留所有数据（最多10年）
    """
    all_records = []
    page = 1
    max_records = 2000
    max_pages = (max_records // PAGE_SIZE) + 2

    cutoff_date = None
    if months:
        cutoff_date = datetime.now() - timedelta(days=30 * months)
        print(f"仅保留最近 {months} 个月的数据")

    while page <= max_pages:
        print(f"正在获取第 {page} 页...")
        data = fetch_page(page)

        # 首次请求失败则重试一次
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

        # 解析并收集每条记录
        for record in records:
            parsed = parse_record(record)
            all_records.append(parsed)

        # 检查是否已达到截止日期
        if cutoff_date and records:
            latest_date = records[0].get("lotteryDrawTime", "")
            if latest_date:
                try:
                    record_date = datetime.strptime(latest_date[:10], "%Y-%m-%d")
                    if record_date < cutoff_date:
                        print(f"已超过 {months} 个月数据，停止获取")
                        break
                except:
                    pass

        # 数据不足一页说明已到末尾
        if len(records) < PAGE_SIZE:
            break

        page += 1
        # 随机延时，避免请求过快被限流
        time.sleep(random.uniform(5, 20))

    # 按日期和期号倒序排序，最新数据排在前面
    return sorted(all_records, key=lambda x: (x.get("draw_time") or "", x.get("term") or ""), reverse=True)


def save_to_file(records, filename="dlt_history.json"):
    """保存数据到JSON文件"""
    filepath = os.path.join(DATA_DIR, filename)
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "sporttery.cn",
        "game": "超级大乐透",
        "game_no": "85",
        "total": len(records),
        "items": records
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到 {filepath}，共 {len(records)} 条记录")


def save_to_csv(records, filename="dlt_history.csv"):
    """保存数据到CSV文件"""
    if not records:
        return
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["term", "draw_time", "draw_result", "front_numbers", "back_numbers"])
        writer.writeheader()
        writer.writerows(records)
    print(f"数据已保存到 {filepath}，共 {len(records)} 条记录")


def main():
    """主函数，处理命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(description="获取大乐透开奖数据")
    parser.add_argument("--latest", action="store_true", help="获取最新一期数据")
    parser.add_argument("--history", action="store_true", help="获取近10年历史数据")
    parser.add_argument("--recent", type=int, metavar="MONTHS", help="获取最近MONTHS个月的数据")
    parser.add_argument("--dry-run", action="store_true", help="仅输出不写入文件")
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
        months = args.recent if args.recent else None
        if months:
            print(f"获取大乐透最近 {months} 个月数据")
        else:
            print("获取大乐透近10年历史数据")
        print("=" * 50)
        records = get_all_data(months=months)
        if records:
            if args.dry_run:
                print(json.dumps(records, ensure_ascii=False, indent=2))
            else:
                save_to_file(records, "dlt_history.json")
                save_to_csv(records, "dlt_history.csv")
            print(f"\n共 {len(records)} 条记录")
        else:
            print("未能获取到数据")
    print("=" * 50)


if __name__ == "__main__":
    main()
