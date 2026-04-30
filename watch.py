#!/usr/bin/env python3
"""
heddmann.com 更新監視スクリプト
お知らせ欄の最新日付が変わったらLINE Messaging APIで通知する。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import requests

URL = "https://www.heddmann.com/"
STATE_FILE = Path("last_seen.json")
LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"


def fetch_page() -> str:
    """ヘッドマンサイトを取得しEUC-JPでデコードして返す。"""
    resp = requests.get(
        URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; HeddmannWatcher/1.0)"},
    )
    resp.raise_for_status()
    # shop-pro.jp は EUC-JP 固定
    resp.encoding = "euc_jp"
    return resp.text


def extract_latest_notice(html: str) -> tuple[str | None, str | None]:
    """お知らせ欄から最新日付と要約を抽出。

    Returns:
        (date_str, snippet_text) もしくは見つからなければ (None, None)
    """
    # 「お知らせ」セクションだけを切り出す
    section_match = re.search(
        r"お知らせ(.*?)(?=新着商品|オススメ商品|<footer|</main)",
        html,
        re.DOTALL,
    )
    if not section_match:
        return None, None

    section = section_match.group(1)

    # この区間で最初に登場する YYYY/M/D が最新エントリ
    date_match = re.search(r"(20\d{2}/\d{1,2}/\d{1,2})", section)
    if not date_match:
        return None, None
    latest_date = date_match.group(1)

    # 日付以降のテキストを抜き出してHTMLタグ・Markdownリンクを除去
    after = section[date_match.start():]
    text = re.sub(r"<[^>]+>", " ", after)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    snippet = text[:250]

    return latest_date, snippet


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def send_line(text: str) -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    user_id = os.environ["LINE_USER_ID"]
    resp = requests.post(
        LINE_PUSH_ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "to": user_id,
            "messages": [{"type": "text", "text": text}],
        },
        timeout=30,
    )
    if resp.status_code >= 300:
        print(f"LINE API error {resp.status_code}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()


def main() -> int:
    html = fetch_page()
    latest_date, snippet = extract_latest_notice(html)

    if latest_date is None:
        print("ERROR: お知らせ欄を解析できませんでした", file=sys.stderr)
        return 1

    print(f"検出した最新日付: {latest_date}")
    print(f"内容（抜粋）: {snippet}")

    state = load_state()
    prev_date = state.get("latest_date")

    if prev_date == latest_date:
        print("変更なし。")
        return 0

    print(f"変更検知: {prev_date} → {latest_date}")

    # 初回実行時は通知せずベースラインだけ作る
    if prev_date is None:
        print("初回実行: 通知はスキップしてベースラインを保存します。")
    else:
        message = (
            "🎣 HEDDMANN 更新検知\n"
            f"日付: {latest_date}\n\n"
            f"{snippet}\n\n"
            f"{URL}"
        )
        send_line(message)
        print("LINE通知送信完了。")

    save_state({"latest_date": latest_date, "snippet": snippet})
    return 0


if __name__ == "__main__":
    sys.exit(main())
