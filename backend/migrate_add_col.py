import sqlite3
conn = sqlite3.connect('crossbot.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(listing_watches)')
cols = [row[1] for row in cursor.fetchall()]
if 'writeback_status' not in cols:
    cursor.execute("ALTER TABLE listing_watches ADD COLUMN writeback_status VARCHAR(20) DEFAULT 'none'")
    conn.commit()
    print('Added writeback_status column')
else:
    print('Column already exists')
conn.close()
