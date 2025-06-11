from app.main import app, db

with app.app_context():
    db.create_all()
    print("✅ 資料表已建立成功！")
