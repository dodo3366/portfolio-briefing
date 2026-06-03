"""
포트폴리오 데일리 브리핑 자동화 스크립트
- pykrx: 국내 주식 (삼성전자, 현대자동차)
- yfinance: 미국 주식 (NVIDIA, Tesla)
- Anthropic API (web_search): 최신 뉴스 수집 및 브리핑 생성
- Gmail SMTP: 풀 브리핑 이메일 발송
"""

import os
import json
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from pykrx import stock
import yfinance as yf


# ── 환경변수 ──────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
GMAIL_USER         = os.environ["GMAIL_USER"]          # 발신 Gmail 주소
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]  # Gmail 앱 비밀번호
RECIPIENT_EMAIL    = os.environ["RECIPIENT_EMAIL"]     # 수신 이메일 주소


# ── 1. 주가 수집 ──────────────────────────────────────────
def fetch_prices() -> dict:
    today = datetime.date.today().strftime("%Y%m%d")
    start = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y%m%d")

    prices = {}

    # 국내 주식 (pykrx)
    kr_stocks = {"삼성전자": "005930", "현대자동차": "005380"}
    for name, ticker in kr_stocks.items():
        try:
            df = stock.get_market_ohlcv_by_date(start, today, ticker)
            if not df.empty:
                row  = df.iloc[-1]
                prev = df.iloc[-2]["종가"] if len(df) >= 2 else row["종가"]
                chg  = (row["종가"] - prev) / prev * 100
                prices[name] = {
                    "ticker": ticker, "market": "KRX",
                    "price": int(row["종가"]), "currency": "원",
                    "open": int(row["시가"]), "high": int(row["고가"]),
                    "low": int(row["저가"]), "volume": int(row["거래량"]),
                    "change_pct": round(chg, 2),
                    "date": df.index[-1].strftime("%Y-%m-%d"),
                }
        except Exception as e:
            prices[name] = {"error": str(e)}

    # 미국 주식 (yfinance)
    us_stocks = {"엔비디아": "NVDA", "테슬라": "TSLA"}
    for name, ticker in us_stocks.items():
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if not hist.empty:
                row  = hist.iloc[-1]
                prev = hist.iloc[-2]["Close"] if len(hist) >= 2 else row["Close"]
                chg  = (row["Close"] - prev) / prev * 100
                prices[name] = {
                    "ticker": ticker, "market": "NASDAQ",
                    "price": round(row["Close"], 2), "currency": "USD",
                    "open": round(row["Open"], 2), "high": round(row["High"], 2),
                    "low": round(row["Low"], 2), "volume": int(row["Volume"]),
                    "change_pct": round(chg, 2),
                    "date": hist.index[-1].strftime("%Y-%m-%d"),
                }
        except Exception as e:
            prices[name] = {"error": str(e)}

    return prices


# ── 2. Claude API로 뉴스 수집 + 브리핑 HTML 생성 ──────────
def fetch_briefing(prices: dict) -> dict:
    price_summary = "\n".join(
        f"- {name}: {info.get('price', 'N/A')}{info.get('currency', '')} "
        f"({'+' if info.get('change_pct', 0) >= 0 else ''}{info.get('change_pct', '?')}%)"
        for name, info in prices.items()
    )
    today_str = datetime.date.today().strftime("%Y년 %m월 %d일")

    prompt = f"""오늘은 {today_str}입니다.

[오늘 주가]
{price_summary}

아래 작업을 순서대로 수행해주세요.

1. 웹 검색으로 다음 종목의 오늘 최신 뉴스를 각 2~3건씩 수집하세요:
   삼성전자(005930), 현대자동차(005380), NVIDIA(NVDA), Tesla(TSLA)
   영어 뉴스는 반드시 한국어로 번역하세요.

2. 수집한 내용을 바탕으로 아래 JSON을 JSON만 반환하세요 (마크다운 코드블록 없이):

{{
  "email_subject": "이메일 제목 (예: [포트폴리오 브리핑] 2026.06.03)",
  "email_html": "종가 요약 테이블 + 종목별 뉴스 2~3건을 포함한 풀 브리핑 HTML. 인라인 CSS로 깔끔하게 스타일링. 한국어로 작성."
}}"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "tools": [{"type": "web_search_20250305", "name": "web_search"}],
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()

    full_text = "".join(
        block["text"] for block in data["content"] if block["type"] == "text"
    )

    full_text = full_text.strip()
    if full_text.startswith("```"):
        full_text = full_text.split("```")[1]
        if full_text.startswith("json"):
            full_text = full_text[4:]

    return json.loads(full_text.strip())


# ── 3. Gmail 발송 ─────────────────────────────────────────
def send_email(subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
    print("✅ Gmail 전송 완료")


# ── 메인 ─────────────────────────────────────────────────
def main():
    print("📊 주가 수집 중...")
    prices = fetch_prices()
    print("prices:", json.dumps(prices, ensure_ascii=False, indent=2))

    print("🤖 Claude 브리핑 생성 중...")
    briefing = fetch_briefing(prices)

    print("📧 Gmail 전송 중...")
    send_email(briefing["email_subject"], briefing["email_html"])

    print("🎉 전송 완료!")


if __name__ == "__main__":
    main()
