@echo off
setlocal

if not defined TT_WSL_DISTRO set "TT_WSL_DISTRO=Ubuntu-22.04"
if not defined TT_PROJECT_DIR set "TT_PROJECT_DIR=/home/gus/tt"

wsl.exe -d %TT_WSL_DISTRO% bash -lc "cd '%TT_PROJECT_DIR%' && exec python3 tt.py --quick"
