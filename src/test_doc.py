import sys
sys.path.append('/home/app/.local/lib/python3.11/site-packages')
from docopt import docopt

with open('populate.py', encoding='utf-8') as f:
    text = f.read()

doc = text.split('\"\"\"')[1]
try:
    print(docopt(doc, ['-v', '-n', '-e', '--historical', '-f']))
except Exception as e:
    print("Exception:", e)
