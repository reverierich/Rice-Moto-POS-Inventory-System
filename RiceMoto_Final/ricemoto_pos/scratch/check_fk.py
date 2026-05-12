import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', password='', database='ricemoto')
cur = conn.cursor()

cur.execute("""
    SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
    FROM information_schema.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = 'ricemoto' AND REFERENCED_TABLE_NAME IS NOT NULL
    ORDER BY TABLE_NAME, COLUMN_NAME
""")
rows = cur.fetchall()

print(f"Total FK connections: {len(rows)}\n")
for r in rows:
    print(f"  {r[0]}.{r[1]}  -->  {r[3]}.{r[4]}  ({r[2]})")

conn.close()
