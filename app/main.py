from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
from datetime import datetime
import os
from sqlalchemy import func, or_
from functools import wraps
from datetime import datetime, timedelta
from PIL import Image
import base64
import io
from dotenv import load_dotenv

# --- 設定 ---
load_dotenv()
# os.path.dirname(__file__) -> app/
# os.path.join(..., '..') -> database/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'templates')
STATIC_DIR = os.path.join(PROJECT_ROOT, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ.get("FLASK_SECRET", "dev_secret_key")

# 讓本地開發的 SQLite 資料庫檔案 'dev.db' 建立在專案根目錄下
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(PROJECT_ROOT, 'dev.db')}")
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
oauth = OAuth(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# === 資料庫模型  ===
class University(db.Model):
    __tablename__ = 'universities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    department = db.Column(db.String(100))
    profile_image_url = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)

class Review(db.Model):
    __tablename__ = 'reviews'
    review_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professors.id', ondelete='CASCADE'))
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id', ondelete='CASCADE'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image = db.relationship('LabImage', foreign_keys='LabImage.review_id', backref='review', uselist=False, cascade="all, delete-orphan")

class Professor(db.Model):
    __tablename__ = 'professors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    university_id = db.Column(db.Integer, db.ForeignKey('universities.id', ondelete='SET NULL'))
    university = db.relationship('University')
    reviews = db.relationship('Review', backref='professor', lazy=True, cascade="all, delete-orphan")

class Lab(db.Model):
    __tablename__ = 'labs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    university_id = db.Column(db.Integer, db.ForeignKey('universities.id', ondelete='SET NULL'))
    cover_image_url = db.Column(db.Text)
    university = db.relationship('University')
    reviews = db.relationship('Review', backref='lab', lazy=True, cascade="all, delete-orphan")
    images = db.relationship('LabImage', foreign_keys='LabImage.lab_id', backref='lab', lazy=True, cascade="all, delete-orphan")

class LabImage(db.Model):
    __tablename__ = 'lab_images'
    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id', ondelete='CASCADE'), nullable=False)
    uploader_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    image_url = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.review_id', ondelete='CASCADE'), unique=True, nullable=True)

class ReviewBackup(db.Model):
    __tablename__ = 'review_backup'
    backup_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    review_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)
    professor_id = db.Column(db.Integer)
    lab_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime)
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)
# 資料模型 END

@app.route('/')
def index():
    user = session.get('user')
    selected_uni_id = request.args.get('university_id', type=int)
    selected_dept = request.args.get('department', type=str)
    
    query = db.session.query(
        Review.review_id, Review.content, Review.rating, Review.timestamp,
        func.coalesce(Professor.name, Lab.name).label('target_name'),
        func.coalesce(Professor.department, Lab.department).label('department_name'),
        University.name.label('university_name'),
        LabImage.image_url.label('review_image_url'),
        Review.lab_id
    ).outerjoin(Professor, Review.professor_id == Professor.id) \
     .outerjoin(Lab, Review.lab_id == Lab.id) \
     .outerjoin(University, or_(Professor.university_id == University.id, Lab.university_id == University.id)) \
     .outerjoin(LabImage, Review.review_id == LabImage.review_id)

    if selected_uni_id:
        query = query.filter(or_(Professor.university_id == selected_uni_id, Lab.university_id == selected_uni_id))
    if selected_dept:
        query = query.filter(func.coalesce(Professor.department, Lab.department) == selected_dept)

    reviews = query.order_by(Review.timestamp.desc()).all()
    
    universities = University.query.order_by(University.name).all()
    departments_prof = db.session.query(Professor.department).filter(Professor.department.isnot(None)).distinct()
    departments_lab = db.session.query(Lab.department).filter(Lab.department.isnot(None)).distinct()
    all_departments = sorted(list(set([d[0] for d in departments_prof] + [d[0] for d in departments_lab])))

    return render_template('index.html', 
                             user=user, 
                             reviews=reviews,
                             universities=universities,
                             departments=all_departments,
                             selected_uni_id=selected_uni_id,
                             selected_dept=selected_dept)

@app.route('/login')
def login():
    return google.authorize_redirect(redirect_uri=url_for('authorize', _external=True))

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    user_info = token['userinfo']
    user = User.query.filter_by(google_id=user_info['sub']).first()
    if not user:
        user = User(google_id=user_info['sub'], name=user_info['name'], email=user_info['email'])
        db.session.add(user)
        db.session.commit()
    session['user'] = {'id': user.id, 'name': user.name, 'email': user.email, 'is_admin': user.is_admin}
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/review')
def review_form():
    if 'user' not in session:
        return redirect(url_for('login'))
    professors = Professor.query.order_by(Professor.name).all()
    labs = Lab.query.order_by(Lab.name).all()
    universities = University.query.order_by(University.name).all()
    return render_template('review.html', professors=professors, labs=labs, universities=universities)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/review', methods=['POST'])
def submit_review():
    if 'user' not in session:
        flash('請先登入後再提交評價。', 'warning')
        return redirect(url_for('login'))
    
    target_id_type = request.form.get('target_id_type')
    content = request.form.get('content', '').strip()
    university_id = request.form.get('university_id')
    new_university_name = request.form.get('new_university_name', '').strip()
    lab_image_file = request.files.get('lab_image')

    try:
        rating = int(request.form.get('rating'))
        if not 1 <= rating <= 5: raise ValueError("評分不在範圍內")
    except (ValueError, TypeError):
        flash('評分必須是 1 到 5 之間的有效數字。', 'danger')
        return redirect(url_for('review_form'))

    if not content or not target_id_type or not university_id:
        flash('學校、評價對象和內容為必填欄位。', 'danger')
        return redirect(url_for('review_form'))
        
    base64_image_data = None
    if lab_image_file and allowed_file(lab_image_file.filename):
        try:
            image = Image.open(lab_image_file.stream)
            if image.mode in ("RGBA", "P"): image = image.convert("RGB")
            image.thumbnail((800, 800))
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            base64_image_data = f"data:image/jpeg;base64,{img_str}"
        except Exception as e:
            flash(f'圖片處理失敗: {e}', 'danger')
            return redirect(url_for('review_form'))
    
    try:
        if university_id == 'new':
            if not new_university_name:
                flash('新大學名稱不能為空。', 'danger')
                return redirect(url_for('review_form'))
            uni = University.query.filter_by(name=new_university_name).first()
            if not uni:
                uni = University(name=new_university_name)
                db.session.add(uni)
                db.session.flush()
            final_university_id = uni.id
        else:
            final_university_id = int(university_id)

        professor_id, lab_id = None, None
        
        if 'new' in target_id_type:
            department = request.form.get('new_department', '').strip() or None
            if target_id_type == 'prof-new':
                target_name = request.form.get('new_professor_name', '').strip()
                if not target_name: flash('新教授名稱不能為空。', 'danger'); return redirect(url_for('review_form'))
                prof = Professor.query.filter_by(name=target_name, university_id=final_university_id).first()
                if not prof: prof = Professor(name=target_name, department=department, university_id=final_university_id); db.session.add(prof); db.session.flush()
                professor_id = prof.id
            elif target_id_type == 'lab-new':
                target_name = request.form.get('new_lab_name', '').strip()
                if not target_name: flash('新實驗室名稱不能為空。', 'danger'); return redirect(url_for('review_form'))
                lab = Lab.query.filter_by(name=target_name, university_id=final_university_id).first()
                if not lab: lab = Lab(name=target_name, department=department, university_id=final_university_id); db.session.add(lab); db.session.flush()
                lab_id = lab.id
        else:
            target_type, target_id_str = target_id_type.split('-')
            target_id = int(target_id_str)
            if target_type == 'prof': professor_id = target_id
            elif target_type == 'lab': lab_id = target_id
            
        review = Review(user_id=None, content=content, rating=rating, professor_id=professor_id, lab_id=lab_id)
        db.session.add(review)

        if base64_image_data and lab_id:
            db.session.flush()
            new_image_record = LabImage(lab_id=lab_id, uploader_user_id=session['user']['id'], image_url=base64_image_data, review_id=review.review_id)
            db.session.add(new_image_record)

        db.session.commit()
        flash('您的評價已成功匿名提交！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'提交失敗，發生未知錯誤: {str(e)}', 'danger')
        import traceback
        traceback.print_exc()

    return redirect(url_for('index'))


@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    if not session.get('user') or not session['user'].get('is_admin'):
        return redirect('/')
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash(f'評價 (ID: {review_id}) 已被成功刪除。', 'info')
    return redirect(request.referrer or url_for('index'))

# 裝飾器：檢查是否為管理員
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user') or not session['user'].get('is_admin'):
            flash('您必須擁有管理者權限才能訪問此頁面。', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    user_count = db.session.query(func.count(User.id)).scalar()
    review_count = db.session.query(func.count(Review.review_id)).scalar()
    return render_template('admin_dashboard.html', user_count=user_count, review_count=review_count)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.id).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    reviews = db.session.query(
        Review.review_id, Review.content, Review.rating, Review.timestamp,
        func.coalesce(Professor.name, Lab.name).label('target_name')
    ).outerjoin(Professor, Professor.id == Review.professor_id) \
     .outerjoin(Lab, Lab.id == Review.lab_id) \
     .order_by(Review.timestamp.desc()).all()
    return render_template('admin_reviews.html', reviews=reviews)

@app.route('/admin/professors')
@admin_required
def admin_professors():
    professors = Professor.query.order_by(Professor.name).all()
    return render_template('admin_professors.html', professors=professors)

@app.route('/admin/labs')
@admin_required
def admin_labs():
    labs = Lab.query.order_by(Lab.name).all()
    return render_template('admin_labs.html', labs=labs)

@app.route('/admin/professor/delete/<int:prof_id>', methods=['POST'])
@admin_required
def delete_professor(prof_id):
    prof_to_delete = Professor.query.get_or_404(prof_id)
    existing_reviews = Review.query.filter_by(professor_id=prof_id).count()
    if existing_reviews > 0:
        flash(f'無法刪除教授 "{prof_to_delete.name}"，因為他仍有 {existing_reviews} 則關聯的評論。', 'danger')
    else:
        db.session.delete(prof_to_delete)
        db.session.commit()
        flash(f'教授 "{prof_to_delete.name}" 已被成功刪除。', 'success')
    return redirect(url_for('admin_professors'))

@app.route('/admin/lab/delete/<int:lab_id>', methods=['POST'])
@admin_required
def delete_lab(lab_id):
    lab_to_delete = Lab.query.get_or_404(lab_id)
    existing_reviews = Review.query.filter_by(lab_id=lab_id).count()
    if existing_reviews > 0:
        flash(f'無法刪除實驗室 "{lab_to_delete.name}"，因為它仍有 {existing_reviews} 則關聯的評論。', 'danger')
    else:
        db.session.delete(lab_to_delete)
        db.session.commit()
        flash(f'實驗室 "{lab_to_delete.name}" 已被成功刪除。', 'success')
    return redirect(url_for('admin_labs'))

# 手動執行備份
@app.route('/admin/backup', methods=['POST'])
@admin_required
def backup_reviews():
    # 設定備份期限
    # 例如超過 30 天的評論
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    
    reviews_to_backup = Review.query.filter(Review.timestamp < cutoff_date).all()
    
    if not reviews_to_backup:
        flash('沒有找到超過 30 天的舊評論可供備份。', 'info')
        return redirect(url_for('admin_dashboard'))

    try:
        backup_data = []
        for review in reviews_to_backup:
            backup_data.append({
                'review_id': review.review_id,
                'user_id': review.user_id,
                'content': review.content,
                'rating': review.rating,
                'professor_id': review.professor_id,
                'lab_id': review.lab_id,
                'timestamp': review.timestamp
            })
            db.session.delete(review)

        if backup_data:
            db.session.bulk_insert_mappings(ReviewBackup, backup_data)
        
        db.session.commit()
        flash(f'成功備份並刪除了 {len(reviews_to_backup)} 則舊評論。', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'備份過程中發生錯誤: {e}', 'danger')
        print(f"Backup Error: {e}")

    return redirect(url_for('admin_dashboard'))

@app.route('/seed-universities')
@admin_required
def seed_universities():
    """
    這是一個特殊的一次性路由，用於將台灣的大學列表加入到資料庫。
    只有管理者可以訪問此路由。
    """
    university_list = [
        '國立臺灣大學', '國立成功大學', '國立清華大學', '國立陽明交通大學',
        '國立臺灣師範大學', '國立中興大學', '國立中央大學', '國立中山大學',
        '國立政治大學', '國立臺灣科技大學', '國立臺北科技大學', '國立臺灣海洋大學',
        '國立中正大學', '國立東華大學', '國立暨南國際大學', '國立嘉義大學',
        '國立高雄大學', '國立臺北大學', '國立宜蘭大學', '國立聯合大學',
        '國立臺南大學', '國立臺東大學', '國立屏東大學', '國立金門大學',
        '臺北市立大學', '高雄市立大學', '國立臺灣藝術大學', '國立臺北藝術大學',
        '國立臺南藝術大學', '國立體育大學', '國立臺灣體育運動大學',
        '國立臺北教育大學', '國立臺中教育大學',
        '國立臺北護理健康大學', '國立高雄餐旅大學', '國立高雄科技大學',
        '東海大學', '輔仁大學', '東吳大學', '中原大學', '淡江大學',
        '逢甲大學', '靜宜大學', '長庚大學', '元智大學', '大同大學',
        '中國文化大學', '義守大學', '世新大學', '銘傳大學', '實踐大學',
        '朝陽科技大學', '南臺科技大學', '崑山科技大學', '嘉南藥理大學', '樹德科技大學',
        '龍華科技大學', '輔英科技大學', '明新科技大學', '健行科技大學', '正修科技大學',
        '萬能科技大學', '建國科技大學', '大仁科技大學', '聖約翰科技大學',
        '嶺東科技大學', '中國科技大學', '中臺科技大學', '臺北城市科技大學', '遠東科技大學',
        '元培醫事科技大學', '景文科技大學', '中華醫事科技大學', '東南科技大學', '德明財經科技大學',
        '明志科技大學', '大葉大學', '中華大學', '華梵大學', '玄奘大學',
        '亞洲大學', '開南大學', '佛光大學', '南華大學', '真理大學',
        '慈濟大學', '臺北醫學大學', '中山醫學大學', '中國醫藥大學', '高雄醫學大學',
        '長榮大學', '大同技術學院', '臺灣警察專科學校', '國防大學'
    ]
    
    try:
        count = 0
        for uni_name in university_list:
            # 檢查大學是否已經存在
            exists = University.query.filter_by(name=uni_name).first()
            if not exists:
                new_uni = University(name=uni_name)
                db.session.add(new_uni)
                count += 1
        
        db.session.commit()
        flash(f'資料庫填充成功！共新增了 {count} 所大學。', 'success')
        print(f"INFO: {count} universities were added to the database.")
    except Exception as e:
        db.session.rollback()
        flash(f'資料庫填充失敗：{str(e)}', 'danger')
        print(f"ERROR: Seeding failed: {e}")

    return redirect(url_for('admin_dashboard'))