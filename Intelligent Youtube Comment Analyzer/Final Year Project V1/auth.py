# auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import Database
from functools import wraps
import base64

auth = Blueprint('auth', __name__)
db = Database()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))  # Changed from 'login' to 'auth.login'
        return f(*args, **kwargs)
    return decorated_function

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        success, user = db.verify_user(email, password)
        if success:
            session['user'] = user['username']
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid email or password")
    
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1) grab basic form fields
        username = request.form.get('username')
        email    = request.form.get('email')
        password = request.form.get('password')

        # 2) handle optional profile image
        image_file = request.files.get('profile_image')
        image_b64  = None
        if image_file and image_file.filename:
            raw_bytes = image_file.read()
            image_b64 = base64.b64encode(raw_bytes).decode('utf-8')

        # 3) call your DB layer (now expecting 4th arg)
        success, message = db.register_user(
            username,
            email,
            password,
            profile_image_b64=image_b64
        )

        if success:
            return redirect(url_for('auth.login'))
        else:
            return render_template('register.html', error=message)

    # GET => just show form
    return render_template('register.html')

@auth.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('auth.login'))  # Changed from 'login' to 'auth.login'

@auth.route('/history')
def history():
    """Displays the analysis history for the logged-in user."""
    user_id = session.get('user')
    profile_image_b64 = db.get_user_profile_image(session.get('user'))
    history_data = db.get_user_analysis_history(user_id)
    return render_template('History_model.html', username=session.get('user'), history_data=history_data, profile=profile_image_b64)

@auth.route('/profile_settings', methods=['GET', 'POST'])
def profile_settings():
    # 1) Must be logged in
    username = session.get('user')
    if not username:
        return redirect(url_for('auth.login'))

    # 2) Handle form submit
    if request.method == 'POST':
        # new username + optional image + new password
        new_username = request.form['username']
        new_password = request.form.get('new_password') or None

        image_file = request.files.get('profile_image')
        profile_b64 = None
        if image_file and image_file.filename:
            profile_b64 = base64.b64encode(image_file.read()).decode('utf-8')

        # call your DB update function
        success, msg = db.update_user_profile(
            old_username=username,
            new_username=new_username,
            new_password=new_password,
            profile_image_b64=profile_b64
        )
        if not success:
            return render_template(
                'profile_settings.html',
                username=username,
                profile=profile_b64 or db.get_user_profile_image(username),
                error=msg
            )
        # if username changed, update the session
        session['user'] = new_username
        username = new_username

    # 3) On GET (or after successful POST) fetch current values
    profile_b64 = db.get_user_profile_image(username)
    return render_template(
        'profile_settings.html',
        username=username,
        profile=profile_b64
    )