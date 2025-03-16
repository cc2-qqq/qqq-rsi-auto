import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import yfinance as yf

# GCP credentials 불러오기
gcp_credentials = os.environ["GCP_CREDENTIALS"]

# credentials.json 저장
with open("credentials.json", "w") as f:
    f.write(gcp_credentials)

# Google Sheets API 인증
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)

# Google Sheets 파일 열기
spreadsheet = client.open("QQQ RSI Tracker")
worksheet = spreadsheet.sheet1

# Yahoo Finance에서 QQQ 데이터 가져오기
qqq = yf.download("QQQ", period="1y", interval="1wk")

# RSI 계산 함수
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

qqq["RSI"] = calculate_rsi(qqq["Close"])

# "상승", "하락" 모드 판단 함수
def determine_mode(rsi_series):
    modes = []
    current_mode = "보합"

    for i in range(2, len(rsi_series)):
        prev_prev_rsi = rsi_series[i - 2]
        prev_rsi = rsi_series[i - 1]

        if prev_prev_rsi < 65 and prev_rsi < prev_prev_rsi:
            current_mode = "하락"
        elif prev_prev_rsi > 50 and prev_rsi >= 50:
            current_mode = "상승"

        modes.append(current_mode)

    return ["보합", "보합"] + modes

qqq["Mode"] = determine_mode(qqq["RSI"].fillna(50))

# Google Sheets 업데이트
worksheet.clear()  # 기존 데이터 삭제

index_name = qqq.index.name if qqq.index.name else "Date"
header = [index_name] + list(qqq.columns)

# 데이터 변환 (빈 값 채우기 및 문자열 변환)
data = qqq.reset_index().fillna("N/A").astype(str).values.tolist()

# 빈 데이터가 있으면 기본값 설정
if not data:
    data = [["No Data"] * len(header)]

worksheet.update([header] + data)

print("✅ Google Sheets 업데이트 완료!")
