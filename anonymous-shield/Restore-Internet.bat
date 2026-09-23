@echo off
REM Anonymous Shield - Restore default internet (run as ADMINISTRATOR)
REM Undoes: WinINET proxy pointing to 127.0.0.1 + AnonShield-BlockAll/Allow firewall.
REM Use on a PC with no internet: copy this .bat via USB stick and right-click > Run as administrator.

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [WARNING] No administrator: proxy will be restored, but firewall may persist.
  echo           Close and run again as administrator.
  echo.
)

echo [1/2] Restoring Windows proxy to direct...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /f >nul 2>&1
echo       OK - proxy off.

echo [2/2] Deleting firewall kill-switch rules...
netsh advfirewall firewall delete rule name="AnonShield-BlockAll" >nul 2>&1
netsh advfirewall firewall delete rule name="AnonShield-Allow" >nul 2>&1
netsh advfirewall firewall delete rule name="TorShield-BlockAll" >nul 2>&1
netsh advfirewall firewall delete rule name="TorShield-Allow" >nul 2>&1
netsh advfirewall firewall delete rule name="TorShield" >nul 2>&1
echo       OK - rules deleted (if they existed).

echo.
echo Done. Test: open the browser and visit a website.
echo If it still fails, reboot the PC (rules were already deleted).
pause
