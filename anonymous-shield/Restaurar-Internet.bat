@echo off
REM Anonymous Shield - Restaurar internet padrao (rode como ADMINISTRADOR)
REM Desfaz: proxy WinINET apontando p/ 127.0.0.1 + firewall AnonShield-BlockAll/Allow.
REM Uso no PC sem internet: copie este .bat via pendrive e execute com botao direito > Executar como administrador.

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [AVISO] Sem administrador: o proxy sera restaurado, mas o firewall pode persistir.
  echo         Feche e rode novamente como administrador.
  echo.
)

echo [1/2] Restaurando proxy do Windows para direto...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f >nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /f >nul 2>&1
echo       OK - proxy desligado.

echo [2/2] Apagando regras de kill-switch do firewall...
netsh advfirewall firewall delete rule name="AnonShield-BlockAll" >nul 2>&1
netsh advfirewall firewall delete rule name="AnonShield-Allow" >nul 2>&1
netsh advfirewall firewall delete rule name="TorShield-BlockAll" >nul 2>&1
netsh advfirewall firewall delete rule name="TorShield-Allow" >nul 2>&1
netsh advfirewall firewall delete rule name="TorShield" >nul 2>&1
echo       OK - regras apagadas (se existiam).

echo.
echo Pronto. Teste: abra o navegador e acesse um site.
echo Se ainda falhar, reinicie o PC (as regras ja foram apagadas).
pause
