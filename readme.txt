# 先建立虛擬環境
python -m venv .venv
source .venv/Scripts/activate

# 安裝相關依賴
pip install -r requirements.txt

# 設定.env參數
複製.env.sample的內容到.env
修改裡面的內容

# 執行
uvicorn main:app --reload --port 8080