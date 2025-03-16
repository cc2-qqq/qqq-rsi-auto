import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import yfinance as yf

# ✅ Google Sheets API 인증 설정
scope = ["https://spreadsheets.google.com/feeds", 
         "https://www.googleapis.com/auth/spreadsheets", 
         "https://www.googleapis.com/auth/drive.file", 
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# ✅ Google Sheets 열기 (파일명 설정 필요)
spreadsheet = client.open("QQQ RSI Tracker")  # Google Sheets 파일명
worksheet = spreadsheet.sheet1

# ✅ QQQ 주간 데이터 가져오기 (1년치)
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
    current_mode = "안전"  # 기본 모드

    for i in range(2, len(rsi_series)):
        prev_prev_rsi = rsi_series[i - 2]
        prev_rsi = rsi_series[i - 1]

        condition_safe_1 = prev_prev_rsi >= 65 and prev_rsi < prev_prev_rsi
        condition_safe_2 = (40 <= prev_prev_rsi <= 50) and prev_rsi < prev_prev_rsi
        condition_safe_3 = prev_prev_rsi >= 50 and prev_rsi < 50

        condition_attack_1 = prev_prev_rsi < 50 and prev_rsi >= 50
        condition_attack_2 = (50 <= prev_prev_rsi <= 60) and prev_rsi > prev_prev_rsi
        condition_attack_3 = prev_prev_rsi <= 35 and prev_rsi > prev_rsi

        if condition_safe_1 or condition_safe_2 or condition_safe_3:
            current_mode = "안전"
        elif condition_attack_1 or condition_attack_2 or condition_attack_3:
            current_mode = "공세"

        modes.append(current_mode)

    return ["안전", "안전"] + modes  # 데이터 길이 맞추기

qqq["Mode"] = determine_mode(qqq["RSI"].fillna(50))

# ✅ Google Sheets 업데이트 (기존 데이터 삭제 후 새 데이터 입력)
worksheet.clear()
worksheet.update([qqq.columns.values.tolist()] + qqq.reset_index().values.tolist())

print("✅ Google Sheets 업데이트 완료!")
