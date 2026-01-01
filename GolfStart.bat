@echo off
echo Starting Golf App System...
echo Please enter your password...

REM Force start tailscaled in background (nohup) -> Connect -> Start App
wsl -d Ubuntu -e sh -c "sudo mkdir -p /var/run/tailscale && sudo pkill tailscaled; sudo nohup tailscaled > /dev/null 2>&1 & sleep 5; sudo tailscale up && cd /mnt/c/golf_app && sudo docker compose up -d"

echo.
echo =================================================
echo  Success!
echo  Connection should be stable now.
echo =================================================
pause