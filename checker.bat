@ECHO OFF
ECHO Put Netflix Id here :
set /p MPD=

ECHO Quality Select :
set /p qu=
NFripper.py %MPD% -o Downloads -q %qu% --check

echo
pause


@ECHO OFF