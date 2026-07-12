import pandas as pd
import sqlite3
import os

DATA = r'd:\New folder\futurepath\data'

# Read Excel sheets
xl = pd.ExcelFile(os.path.join(DATA, 'career_counseling_full_dataset.xlsx'))
print('=== EXCEL SHEETS ===')
print('Sheets:', xl.sheet_names)
for sheet in xl.sheet_names:
    df = xl.parse(sheet)
    print(f'\n--- Sheet: {sheet} ---  Shape:{df.shape}')
    print('  Cols:', list(df.columns))
    print(df.head(2).to_string())

# Read SQLite DB
print('\n=== SQLITE DB ===')
conn = sqlite3.connect(os.path.join(DATA, 'career_counseling.db'))
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])
for t in tables:
    df2 = pd.read_sql(f'SELECT * FROM {t[0]} LIMIT 3', conn)
    print(f'\n--- Table: {t[0]} ---')
    print('  Cols:', list(df2.columns))
    print(df2.head(2).to_string())
conn.close()

# Check for Reference_Roadmaps CSV
print('\n=== DATA DIR FILES ===')
for f in os.listdir(DATA):
    size = os.path.getsize(os.path.join(DATA, f))
    print(f'  {f}  ({size/1024:.1f} KB)')
