# app/__init__.py

# 這個檔案的目的是告訴 Python，'app' 這個資料夾是一個可以被匯入的套件。
# 我們從 app/main.py 中匯入 app 和 db 物件，這樣 Flask 才能找到它們。
# 注意：這裡不應該有 db.create_all() 或其他會操作資料庫的程式碼。

from app.main import app, db

