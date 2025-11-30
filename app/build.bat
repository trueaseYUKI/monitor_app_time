@echo off
echo 正在打包应用程序...
pyinstaller --onefile --windowed --clean --noconfirm ^
  --exclude PyQt5 ^
  main.py

echo 打包完成！
echo 可执行文件位于 dist\main.exe
pause
