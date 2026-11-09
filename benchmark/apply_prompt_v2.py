from pathlib import Path
import sqlite3

root = Path(__file__).resolve().parent.parent
db_path = root / "app.db"
new_prompt = (root / "benchmark" / "improved_system_prompt_v2.txt").read_text(encoding="utf-8")
con = sqlite3.connect(db_path)
row = con.execute("SELECT value FROM settings WHERE key='system_prompt'").fetchone()
if row:
    (root / "benchmark" / "system_prompt_before_v2.txt").write_text(row[0], encoding="utf-8")
con.execute("INSERT INTO settings(key,value,updated_at) VALUES('system_prompt',?,CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP", (new_prompt,))
con.commit()
con.close()
print("system prompt updated")
