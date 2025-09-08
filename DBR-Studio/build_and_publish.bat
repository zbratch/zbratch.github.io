@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Move working directory to the folder this .bat lives in
pushd "%~dp0"

echo === DBR Studio Build ^& Publish (Python) ===

REM --- config / paths ---
set "SCRIPT=scripts\build_from_tsv.py"
set "OUTFILE=posts\posts.json"

REM --- sanity: python runner ---
where python >nul 2>nul
if %errorlevel%==0 (set "RUNNER=python") else (
  where py >nul 2>nul
  if %errorlevel%==0 (set "RUNNER=py") else (
    echo [ERROR] Python not found on PATH. Install from https://python.org and try again.
    pause & popd & exit /b 1
  )
)

REM --- sanity: script present ---
if not exist "%SCRIPT%" (
  echo [ERROR] Missing "%SCRIPT%".
  echo Put build_from_tsv.py at: %cd%\scripts\build_from_tsv.py
  pause & popd & exit /b 1
)

echo.
echo [1/3] Building %OUTFILE% from data\submissions.tsv ...
"%RUNNER%" "%SCRIPT%"
if errorlevel 1 (
  echo.
  echo [ERROR] Build failed. See messages above.
  pause & popd & exit /b 1
)

echo.
set /p DO_PUSH="[2/3] Commit and push changes to GitHub now? (Y/N): "
if /I not "%DO_PUSH%"=="Y" if /I not "%DO_PUSH%"=="YES" (
  echo Skipping git push. Done.
  pause & popd & exit /b 0
)

REM --- sanity: git repo ---
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo [ERROR] This folder is not a Git repository.
  echo Open a shell in your repo root or move this dbr-studio folder into your repo.
  pause & popd & exit /b 1
)

echo.
echo [3/3] Staging changes...
git add "%OUTFILE%" photos

set "MSG=Publish DBR Studio posts.json"
set /p USERMSG="Commit message (Enter for default): "
if not "%USERMSG%"=="" set "MSG=%USERMSG%"

git commit -m "%MSG%"
if errorlevel 1 (
  echo [INFO] Nothing to commit (no changes).
) else (
  git push
  if errorlevel 1 (
    echo [ERROR] Push failed. Check your remote/credentials and try again.
    pause & popd & exit /b 1
  )
)

echo.
echo Done. %OUTFILE% is up to date.
pause
popd
