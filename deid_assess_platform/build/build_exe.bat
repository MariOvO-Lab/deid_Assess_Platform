@echo off

rem 安装依赖
pip install -r requirements.txt

rem 安装 PyInstaller
pip install pyinstaller

rem 打包应用程序
pyinstaller --onefile --windowed --name deid_assess_tool ..\main.py

rem 复制配置文件和模板
mkdir -p dist\configkdir -p dist\templateskdir -p dist\data

copy ..\config\rules.json dist\config\
copy ..\templates\* dist\templates\

echo 构建完成！可执行文件位于 dist 目录
pause
