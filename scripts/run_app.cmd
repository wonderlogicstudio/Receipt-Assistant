@echo off
cd /d "%~dp0\.."
echo Starting Receipt Assistant Streamlit app...
echo.
echo Keep this window open while testing.
echo Open this URL in your browser:
echo http://127.0.0.1:8501
echo.
python -m streamlit run app/main.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
echo.
echo Streamlit stopped.
pause
