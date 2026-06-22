#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取福彩双色球历史数据
API来源: https://gdwechat.daguoxiaoxian.com/api/lottery-results/list
"""

import requests
import json
import time
from datetime import datetime, timedelta

API_URL = "https://gdwechat.daguoxiaoxian.com/api/lottery-results/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Referer": "https://gdwechat.daguoxiaoxian.com/frontend/#/pages/historySSQ/index?v=2"
}

LIMIT = 30  # 每页数量

def fetch_page(page):
    """获取单页数据"""
    params = {
        "type": 1,
        "limit": LIMIT,
        "page": page
    }
    try:
        response = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"请求第{page}页失败: {e}")
        return None

def parse_record(record):
    """解析单条记录，只保留期号、开奖日期、开奖号码"""
    return {
        "期号": record.get("issue_number", ""),
        "开奖日期": record.get("lottery_date", ""),
        "开奖号码": record.get("win_code", "")
    }

def get_all_data():
    """获取所有历史数据"""
    all_records = []
    page = 1

    # 十年大约需要的数据量估算（每年约150期，每周2-3期）
    max_records = 2000
    max_pages = (max_records // LIMIT) + 2

    while page <= max_pages:
        print(f"正在获取第 {page} 页...")
        data = fetch_page(page)

        if data is None or data.get("code") != 1:
            print(f"API返回异常: {data}")
            break

        records = data.get("data", {}).get("list", [])
        if not records:
            print("没有更多数据了")
            break

        for record in records:
            parsed = parse_record(record)
            all_records.append(parsed)

        # 检查数据是否超过10年
        if records:
            latest_date = records[0].get("awardTime", "")
            if latest_date:
                try:
                    record_date = datetime.strptime(latest_date.split(" ")[0], "%Y-%m-%d")
                    ten_years_ago = datetime.now() - timedelta(days=365*10)
                    if record_date < ten_years_ago:
                        print("已超过10年数据，停止获取")
                        break
                except:
                    pass

        # 如果返回的数据少于limit，说明是最后一页
        if len(records) < LIMIT:
            break

        page += 1
        time.sleep(0.5)  # 避免请求过快

    return all_records

def save_to_file(records, filename="ssq_history.json"):
    """保存数据到JSON文件"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到 {filename}，共 {len(records)} 条记录")

def save_to_csv(records, filename="ssq_history.csv"):
    """保存数据到CSV文件"""
    import csv
    if not records:
        return
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["期号", "开奖日期", "开奖号码"])
        writer.writeheader()
        writer.writerows(records)
    print(f"数据已保存到 {filename}，共 {len(records)} 条记录")

def main():
    print("=" * 50)
    print("开始获取福彩双色球历史数据（近10年）")
    print("=" * 50)

    records = get_all_data()

    if records:
        save_to_file(records, "ssq_history.json")
        save_to_csv(records, "ssq_history.csv")

        print("\n前5条数据预览:")
        for r in records[:5]:
            print(r)
    else:
        print("未能获取到数据")

if __name__ == "__main__":
    main()
