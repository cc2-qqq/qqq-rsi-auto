import os
import pandas as pd
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Google Sheets API 인증
GCP_CREDENTIALS = os.environ["GCP_CREDENTIALS"]
with open("credentials.json", "w") as f:
    f.write(GCP_CREDENTIALS)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# ✅ Google Sheets 파일 및 워크시트 설정
spreadsheet = client.open("QQQ RSI Tracker")  # Google Sheets 이름
worksheet = spreadsheet.sheet1  # 첫 번째 시트 선택

# ✅ Yahoo Finance에서 QQQ 데이터 다운로드
qqq = yf.download("QQQ", period="1y", interval="1wk")

# ✅ RSI 계산 함수
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

qqq["RSI"] = calculate_rsi(qqq["Close"])

# ✅ 매매 모드 판별 함수
def determine_mode(rsi_series):
    modes = []
    current_mode = "보류"
    
    for i in range(2, len(rsi_series)):
        prev_prev_rsi = rsi_series[i - 2]
        prev_rsi = rsi_series[i - 1]

        if prev_prev_rsi > 65 and prev_rsi < prev_prev_rsi:
            current_mode = "매도"
        elif prev_prev_rsi < 50 and prev_rsi >= 50:
            current_mode = "매수"

        modes.append(current_mode)

    return ["보류", "보류"] + modes  # 앞 두 개의 값을 '보류'로 설정

qqq["Mode"] = determine_mode(qqq["RSI"].fillna(50))

# ✅ Google Sheets 업데이트 (G열을 소수점 한 자리로 변환)
qqq = qqq.reset_index()  # 날짜 인덱스를 컬럼으로 변환
qqq["RSI"] = qqq["RSI"].round(1)  # RSI 값을 소수점 한 자리로 변환
qqq["Close"] = qqq["Close"].round(1)  # 종가도 소수점 한 자리로 변환 (선택)

# ✅ Google Sheets 데이터 클리어 후 업데이트
worksheet.clear()
header = ["Date", "Close", "RSI", "Mode"]
data = qqq[["Date", "Close", "RSI", "Mode"]].astype(str).values.tolist()
worksheet.update([header] + data)

print("✅ Google Sheets 업데이트 완료!")
