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

# ✅ 매매 모드 판별 함수 (안전 / 공세) - 동파법 적용
def determine_mode(rsi_series):
    modes = []
    current_mode = "안전"  # 초기 모드는 "안전"

    for i in range(2, len(rsi_series)):  # 2주 전과 비교
        prev_prev_rsi = rsi_series[i - 2]  # 2주 전 RSI
        prev_rsi = rsi_series[i - 1]  # 1주 전 RSI

        # 🔹 안전모드 전환 조건
        if (
            prev_prev_rsi >= 65 and prev_rsi < prev_prev_rsi  # RSI 65 이상에서 하락
            or 40 <= prev_prev_rsi <= 50 and prev_rsi < prev_prev_rsi  # RSI 40~50에서 하락
            or prev_prev_rsi >= 50 and prev_rsi < 50  # RSI 50 이상 → 50 미만 하락 돌파
        ):
            current_mode = "안전"

        # 🔹 공세모드 전환 조건
        elif (
            prev_prev_rsi <= 50 and prev_rsi > 50  # RSI 50 이하에서 50 초과 상승 돌파
            or 50 <= prev_prev_rsi <= 60 and prev_rsi > prev_prev_rsi  # RSI 50~60에서 상승
            or prev_prev_rsi <= 35 and prev_rsi > prev_prev_rsi  # RSI 35 이하에서 상승
        ):
            current_mode = "공세"

        # 변경된 모드를 리스트에 추가
        modes.append(current_mode)

    return ["안전", "안전"] + modes  # 앞 두 개의 값을 '안전'으로 설정

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
