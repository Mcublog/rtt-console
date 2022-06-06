echo "====> Create environment ====>"
py -m venv env

echo "====> Activate it ====>"
. .\env\Scripts\activate
$env:PYTHONPATH="$(pwd)"
echo "====> Install requirements ====>"
pip install -r requirements.txt

echo "====> Build exe files ====>"
pyinstaller --noconfirm --onefile --console --name "rtt-console"`
-F ".\src\rtt_console\console.py" `
--distpath "bin"

echo "====> Check bin directory"
