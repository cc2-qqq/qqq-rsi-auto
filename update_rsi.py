import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import yfinance as yf
import json
import os

# ✅ GitHub Secrets에서 환경 변수로 설정된 credentials.json 가져오기
gcp_credentials = os.environ["GCP_CREDENTIALS"]

# ✅ credentials.json 파일을 임시로 생성하여 사용
with open("credentials.json", "w") as f:
    f.write(gcp_credentials)

# ✅ Google Sheets API 인증 설정
scope = ["https://spreadsheets.google.com/feeds", 
         "https://www.googleapis.com/auth/spreadsheets", 
         "https://www.googleapis.com/auth/drive.file", 
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# ✅ Google Sheets 열기
spreadsheet = client.open("QQQ RSI Tracker")  
worksheet = spreadsheet.sheet1

# ✅ QQQ 주간 데이터 가져오기
qqq = yf.download('QQQ', period="1y", interval="1wk")

# ✅ RSI 계산 함수
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

qqq["RSI"] = calculate_rsi(qqq["Close"])

# ✅ "공세" & "안전" 모드 판별 함수
def determine_mode(rsi_series):
    modes = []
    current_mode = "안전"

    for i in range(2, len(rsi_series)):
        prev_prev_rsi = rsi_series[i - 2]
        prev_rsi = rsi_series[i - 1]

        if prev_prev_rsi >= 65 and prev_rsi < prev_prev_rsi:
            current_mode = "안전"
        elif prev_prev_rsi < 50 and prev_rsi >= 50:
            current_mode = "공세"

        modes.append(current_mode)

    return ["안전", "안전"] + modes  

qqq["Mode"] = determine_mode(qqq["RSI"].fillna(50))

# ✅ Google Sheets 업데이트
worksheet.clear()
worksheet.update([qqq.columns.values.tolist()] + qqq.reset_index().values.tolist())

print("✅ Google Sheets 업데이트 완료!")
