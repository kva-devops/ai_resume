from pathlib import Path
import sqlite3
root=Path(__file__).resolve().parent.parent
db=sqlite3.connect(root/'app.db')
row=db.execute("SELECT value FROM settings WHERE key='system_prompt'").fetchone()
if row:
    (root/'benchmark'/'system_prompt_v2_applied.txt').write_text(row[0],encoding='utf-8')
prompt=(root/'benchmark'/'improved_system_prompt_v3.txt').read_text(encoding='utf-8')
db.execute("INSERT INTO settings(key,value,updated_at) VALUES('system_prompt',?,CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP",(prompt,))
db.commit();db.close();print('applied v3')
