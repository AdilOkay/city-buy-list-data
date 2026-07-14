@echo off
REM ============================================================================
REM City Buy List - local price-data refresh.
REM
REM Rebuilds baseline / materials / toptraded / routes from AODP and pushes them
REM to this public repo, so the app's launcher pulls fresh averages on start.
REM
REM Runs HERE (your machine) on purpose: AODP throttles GitHub Actions' datacenter
REM IPs, so the CI refresh times out. Your home IP is not throttled - a full run
REM takes ~20-30 min and completes cleanly.
REM
REM Double-click to refresh now, or register it with Windows Task Scheduler (see
REM the SETUP note the assistant gave you). Output is appended to refresh.log.
REM ============================================================================
setlocal
cd /d "%~dp0"
set "LOG=%~dp0refresh.log"
echo ==== %DATE% %TIME% refresh start ==== >> "%LOG%"

call python scripts\build_baseline.py   >> "%LOG%" 2>&1
call python scripts\build_materials.py  >> "%LOG%" 2>&1
call python scripts\build_toptraded.py  >> "%LOG%" 2>&1
call python scripts\build_routes.py     >> "%LOG%" 2>&1

git add docs/data/baseline.json docs/data/materials.json docs/data/toptraded.json docs/data/routes.json
git diff --cached --quiet && ( echo no data changes, nothing to commit >> "%LOG%" & goto :done )
git commit -m "chore: local scheduled price data refresh" >> "%LOG%" 2>&1
git push >> "%LOG%" 2>&1 && ( echo pushed OK >> "%LOG%" ) || ( echo PUSH FAILED - check git credentials >> "%LOG%" )

:done
echo ==== %DATE% %TIME% refresh end ==== >> "%LOG%"
endlocal
