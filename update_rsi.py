import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import yfinance as yf
import os
import json

# Google API 인증 정보 불러오기
gcp_credentials = os.environ["GCP_CREDENTIALS"]
with open("credentials.json", "w") as f:
    f.write(gcp_credentials)

# Google Sheets API 설정
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)

# Google Sheets 불러오기
spreadsheet = client.open("QQQ RSI Tracker")
worksheet = spreadsheet.sheet1

# 데이터 가져오기
qqq = yf.download("QQQ", period="1y", interval="1wk")

# RSI 계산 함수
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

qqq["RSI"] = calculate_rsi(qqq["Close"]).fillna(50)  # NaN 값을 50으로 대체

# "진입" / "이탈" 모드 판별 함수
def determine_mode(rsi_series):
    modes = []
    current_mode = "보류"

    for i in range(2, len(rsi_series)):
        prev_prev_rsi = rsi_series.iloc[i - 2]  # iloc 사용하여 정확한 값 가져오기
        prev_rsi = rsi_series.iloc[i - 1]

        if prev_prev_rsi > 65 and prev_rsi < prev_prev_rsi:
            current_mode = "이탈"
        elif prev_prev_rsi < 30 and prev_rsi > 50:
            current_mode = "진입"

        modes.append(current_mode)

    return ["보류", "진입"] + modes[: len(rsi_series) - 2]  # 길이 조정

qqq["Mode"] = determine_mode(qqq["RSI"])

# Google Sheets에 데이터 업로드
worksheet.clear()

index_name = qqq.index.name if qqq.index.name else "Date"
header = [index_name] + list(qqq.columns)
data = qqq.reset_index().fillna("N/A").astype(str)  # NaN 방지

worksheet.update([header] + data.values.tolist())

print("✅ Google Sheets 업데이트 완료!")
