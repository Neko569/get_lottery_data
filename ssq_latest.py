#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取最新一期双色球开奖号码
"""

import requests
import json
import sys

API_URL = "https://gdwechat.daguoxiaoxian.com/api/lottery-results/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Referer": "https://gdwechat.daguoxiaoxian.com/frontend/#/pages/historySSQ/index?v=2"
}

def get_latest():
    params = {"type": 1, "limit": 1, "page": 1}
    try:
        response = requests.get(API_URL, headers=HEADERS, params=params, timeout=15)
        data = response.json()
        if data.get("code") == 1 and data.get("data", {}).get("list"):
            record = data["data"]["list"][0]
            result = {
                "期号": record.get("issue_number", ""),
                "开奖日期": record.get("lottery_date", ""),
                "开奖号码": record.get("win_code", "")
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result
    except Exception as e:
        print(f"获取失败: {e}", file=sys.stderr)
    return None

if __name__ == "__main__":
    get_latest()
