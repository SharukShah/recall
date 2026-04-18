@echo off
echo Installing pgvector to PostgreSQL 16...
copy "%TEMP%\pgvector\vector.dll" "C:\Program Files\PostgreSQL\16\lib\vector.dll"
copy "%TEMP%\pgvector\vector.control" "C:\Program Files\PostgreSQL\16\share\extension\vector.control"
copy "%TEMP%\pgvector\sql\vector--0.8.0.sql" "C:\Program Files\PostgreSQL\16\share\extension\vector--0.8.0.sql"
copy "%TEMP%\pgvector\sql\vector.sql" "C:\Program Files\PostgreSQL\16\share\extension\vector.sql"
echo Restarting PostgreSQL...
net stop postgresql-x64-16
net start postgresql-x64-16
echo Done! pgvector installed.
pause
