import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import yfinance as yf

# Google Sheets API 인증
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Google Sheets 열기
spreadsheet = client.open("QQQ RSI Tracker")
worksheet = spreadsheet.sheet1

# 데이터 가져오기
qqq = yf.download('QQQ', period="1y", interval="1wk")

# RSI 계산 함수
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

qqq["RSI"] = calculate_rsi(qqq["Close"])

# Mode 결정 함수
def determine_mode(rsi_series):
    modes = []
    current_mode = "안전"  # 기본값

    for i in range(2, len(rsi_series)):
        prev_prev_rsi = rsi_series[i - 2]  # 전전주 RSI
        prev_rsi = rsi_series[i - 1]  # 전주 RSI
        current_rsi = rsi_series[i]  # 이번주 RSI

        if prev_rsi >= 65 and current_rsi < prev_rsi:
            current_mode = "안전"
        elif 40 <= prev_rsi <= 50 and current_rsi < prev_rsi:
            current_mode = "안전"
        elif prev_rsi >= 50 and current_rsi < 50:
            current_mode = "안전"
        elif prev_rsi <= 50 and current_rsi > 50:
            current_mode = "공세"
        elif 50 <= prev_rsi <= 60 and current_rsi > prev_rsi:
            current_mode = "공세"
        elif prev_rsi <= 35 and current_rsi > prev_rsi:
            current_mode = "공세"

        modes.append(current_mode)

    return ["안전"] + ["안전"] + modes  # 초기 2주는 기본값 유지

qqq["Mode"] = determine_mode(qqq["RSI"]).fillna("안전")  # NaN 발생 방지

# Google Sheets에 업데이트
worksheet.clear()
header = ["Date", "Close", "RSI", "Mode"]
data = qqq.reset_index()[["Date", "Close", "RSI", "Mode"]].fillna("").astype(str).values.tolist()

worksheet.update([header] + data)

print("✅ Google Sheets 업데이트 완료!")
