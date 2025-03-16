import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import yfinance as yf
import os
import json

# Google Cloud Credentials 환경변수에서 가져오기
gcp_credentials = os.environ["GCP_CREDENTIALS"]

# credentials.json 파일로 저장
with open("credentials.json", "w") as f:
    f.write(gcp_credentials)

# Google Sheets API 인증
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)

# Google Sheets 열기
spreadsheet = client.open("QQQ RSI Tracker")
worksheet = spreadsheet.sheet1

# QQQ 데이터 다운로드 (1년치, 주간 데이터)
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

# 매매 시그널 모드 계산 함수
def determine_mode(rsi_series):
    modes = []
    current_mode = "-"

    for i in range(2, len(rsi_series)):
        prev_prev_rsi = rsi_series.iloc[i - 2]
        prev_rsi = rsi_series.iloc[i - 1]

        if prev_prev_rsi > 65 and prev_rsi < prev_prev_rsi:
            current_mode = "매도"
        elif prev_prev_rsi < 30 and prev_rsi >= 50:
            current_mode = "매수"
        else:
            current_mode = "-"

        modes.append(current_mode)

    return ["-"] * 2 + modes  # 처음 두 개의 값은 빈 값 대신 "-" 추가

qqq["Mode"] = determine_mode(qqq["RSI"].fillna(50))

# Google Sheets에 업데이트할 데이터 준비
index_name = "Date" if qqq.index.name is None else qqq.index.name
header = [index_name, "Close", "RSI", "Mode"]
data = qqq.reset_index().fillna("-").astype(str).values.tolist()

# 🟢 헤더가 없으면 자동 추가
existing_header = worksheet.row_values(1)
if not existing_header:
    worksheet.append_row(header)

# 🟢 기존 데이터 삭제 후 한 줄씩 추가
worksheet.clear()
worksheet.append_row(header)  # 다시 헤더 추가

for row in data:
    worksheet.append_row(row)

print("✅ Google Sheets 데이터 업데이트 완료!")
