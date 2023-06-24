echo off
set GIT_PYTHON_GIT_EXECUTABLE=git\\bin\\git.exe

echo 访问喵手AI资源站 
echo http://resource.miaoshouai.com 获取更多资源
set GIT_PYTHON_REFRESH=quiet
call update.bat

python\python.exe webui.py --autolaunch --api --xformers --medvram --deepdanbooru
pause