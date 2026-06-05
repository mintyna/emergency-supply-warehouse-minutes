@echo off
echo ========================================
echo 应急物资储备库布局优化会议系统
echo ========================================
echo.

echo [1/2] 启动后端服务...
cd backend
start "Backend Server" uvicorn main:app --reload --host 0.0.0.0 --port 8000

timeout /t 3

echo [2/2] 启动前端服务...
cd ../frontend
start "Frontend Server" python -m http.server 8080

echo.
echo ========================================
echo 服务启动完成！
echo 后端API: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo 前端界面: http://localhost:8080
echo ========================================
echo.
pause
