@ECHO OFF
ECHO Put Netflix Id here :
set /p MPD=

ECHO Season No :
set /p se=

ECHO Quality Select :
set /p qu=
NFripper.py %MPD% -o Downloads -q %qu% -s %se% --main --prv ca-tor.pvdata.host --alang hin eng

echo
pause


@ECHO OFF