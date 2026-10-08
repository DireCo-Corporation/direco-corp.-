from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'direco_rahasia_super_aman'

# Konfigurasi Folder Gudang Upload
app.config['UPLOAD_FOLDER_FILES'] = 'static/uploads/files'
app.config['UPLOAD_FOLDER_COVERS'] = 'static/uploads/covers'
app.config['UPLOAD_FOLDER_PROFILES'] = 'static/uploads/profiles'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Rute Beranda Utama
@app.route('/')
def home():
    conn = get_db_connection()
    files = conn.execute('SELECT * FROM files').fetchall()
    
    current_user = None
    if 'user_id' in session:
        current_user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        
    conn.close()
    return render_template('index.html', files=files, current_user=current_user)

# Rute Login Aman dengan Password Terenkripsi
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        
        # Pengalihan Cerdas Berdasarkan Peran (Role)
        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('home'))
    else:
        return "Username atau Password salah! Silakan kembali."

# Rute Pendaftaran Akun Publik Baru (Register)
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    raw_password = request.form.get('password')
    
    hashed_password = generate_password_hash(raw_password)
    
    conn = get_db_connection()
    existing_user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    
    if existing_user:
        conn.close()
        return "Username sudah terdaftar! Silakan gunakan nama lain."
    
    conn.execute('INSERT INTO users (username, password, role, profile_pic, bio) VALUES (?, ?, ?, ?, ?)',
                 (username, hashed_password, 'user', 'default.png', 'Pengguna baru DireCo Corp.'))
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))

# Rute Pembaruan Profil (Bio & Avatar)
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' in session:
        user_id = session['user_id']
        new_bio = request.form.get('bio')
        avatar_obj = request.files.get('avatar_upload')
        
        conn = get_db_connection()
        
        if avatar_obj and avatar_obj.filename != '':
            avatar_name = secure_filename(avatar_obj.filename)
            avatar_obj.save(os.path.join(app.config['UPLOAD_FOLDER_PROFILES'], avatar_name))
            
            conn.execute('UPDATE users SET bio = ?, profile_pic = ? WHERE id = ?', 
                         (new_bio, avatar_name, user_id))
        else:
            conn.execute('UPDATE users SET bio = ? WHERE id = ?', (new_bio, user_id))
                         
        conn.commit()
        conn.close()
        
        return redirect(url_for('home'))
    return "Silakan login terlebih dahulu!"

# --- RUTE KHUSUS ADMIN ---
@app.route('/admin')
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        conn = get_db_connection()
        files = conn.execute('SELECT * FROM files').fetchall()
        users = conn.execute('SELECT * FROM users').fetchall()
        conn.close()
        return render_template('admin.html', files=files, users=users)
    else:
        return "Akses Ditolak! Anda bukan Admin."

# Rute Upload Berkas & Konten Baru
@app.route('/add_item', methods=['POST'])
def add_item():
    if 'role' in session and session['role'] == 'admin':
        title = request.form.get('title')
        category = request.form.get('category')
        description = request.form.get('description')
        
        file_obj = request.files.get('file_upload')
        cover_obj = request.files.get('cover_upload')
        
        file_path_name = ""
        cover_image_name = ""
        
        if file_obj and file_obj.filename != '':
            file_path_name = secure_filename(file_obj.filename)
            file_obj.save(os.path.join(app.config['UPLOAD_FOLDER_FILES'], file_path_name))
            
        if cover_obj and cover_obj.filename != '':
            cover_image_name = secure_filename(cover_obj.filename)
            cover_obj.save(os.path.join(app.config['UPLOAD_FOLDER_COVERS'], cover_image_name))
            
        conn = get_db_connection()
        conn.execute('INSERT INTO files (title, category, description, cover_image, file_path) VALUES (?, ?, ?, ?, ?)', 
                     (title, category, description, cover_image_name, file_path_name))
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_dashboard'))
    return "Akses Ditolak!"

# Rute Hapus Konten / Berkas
@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'role' in session and session['role'] == 'admin':
        conn = get_db_connection()
        conn.execute('DELETE FROM files WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    return "Akses Ditolak!"

# Rute Hapus Pengguna (Manajemen User Admin)
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'role' in session and session['role'] == 'admin':
        conn = get_db_connection()
        # Cegah admin menghapus akunnya sendiri
        if user_id != session.get('user_id'):
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    return "Akses Ditolak!"

# Rute Keluar (Logout)
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
