@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo 初回セットアップ中... 数分かかることがあります
  python -m venv .venv || goto :error
)
rem 前回のインストールが失敗していた場合や requirements.lock が更新された場合に備えて毎回確認する
.venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check -r requirements.lock || goto :error
.venv\Scripts\python.exe -m streamlit run app.py
pause
exit /b 0

:error
echo セットアップに失敗しました。上のメッセージを確認してください。
pause
exit /b 1
