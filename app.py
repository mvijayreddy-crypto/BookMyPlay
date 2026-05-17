from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "bookmyplay_secret_key"
app.config['SESSION_COOKIE_SECURE'] = False

# ================= DATABASE =================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))
    game = db.Column(db.String(50))
    booking_date = db.Column(db.String(50))
    booking_time = db.Column(db.String(50))

# ================= USER MODEL =================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(15), unique=True)
    password = db.Column(db.String(200))

# Create DB automatically
with app.app_context():
    db.create_all()

# ================= GOOGLE LOGIN =================
google_bp = make_google_blueprint(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    redirect_to="google_login"
)

app.register_blueprint(google_bp, url_prefix="/login")

@app.route('/book-slot', methods=['POST'])
def book_slot():
    data = request.get_json()

    game = data.get('game')
    date = data.get('date')
    time = data.get('time')
    user = session.get('user')

    existing = Booking.query.filter_by(
        game=game,
        booking_date=date,
        booking_time=time
    ).first()

    if existing:
        return "Already booked ❌"

    new_booking = Booking(
        user=user,
        game=game,
        booking_date=date,
        booking_time=time
    )

    db.session.add(new_booking)
    db.session.commit()

    return "Booked Successfully ✅"

@app.route('/check-slots')
def check_slots():

    game = request.args.get('game')
    date = request.args.get('date')

    bookings = Booking.query.filter_by(
        game=game,
        booking_date=date
    ).all()

    booked_times = []

    for booking in bookings:
        booked_times.append(booking.booking_time)

    return {
        "booked": booked_times
    }
# ================= HOME =================
@app.route('/')
def home():
    return render_template('splash.html')

@app.route('/index')
def index():
    return render_template('index.html')

# ================= OTP LOGIN =================
import random

@app.route('/otp-login', methods=['GET', 'POST'])
def otp_login():
    if request.method == 'POST':
        phone = request.form.get('phone')

        otp = str(random.randint(1000, 9999))
        session['otp'] = otp
        session['phone'] = phone

        print("OTP:", otp)

        return redirect('/verify-otp')

    return render_template('otp-login.html')


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form.get('otp')

        if user_otp == session.get('otp'):
            session['user'] = session.get('phone')
            return redirect('/dashboard')
        else:
            return render_template('verify-otp.html', error="Invalid OTP")

    return render_template('verify-otp.html')

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        user_input = request.form.get('email')
        password = request.form.get('password')

        if not user_input or not password:
            return render_template(
                'login.html',
                error="Please fill all fields"
            )

        # CHECK USER
        user = User.query.filter(
            (User.email == user_input) |
            (User.phone == user_input)
        ).first()

        print("USER FOUND:", user)

        if user and check_password_hash(user.password, password):

            session['user'] = user.email if user.email else user.phone

            return redirect('/dashboard')

        else:
            return render_template(
                'login.html',
                error="Wrong email or password"
            )

    return render_template('login.html')

# ================= SIGNUP =================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':

        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        if not email or not phone or not password:
            return render_template(
                'signup.html',
                error="All fields required"
            )

        existing_user = User.query.filter(
            (User.email == email) |
            (User.phone == phone)
        ).first()

        if existing_user:
            return render_template(
                'signup.html',
                error="User already exists"
            )

        hashed_password = generate_password_hash(password)

        new_user = User(
            email=email,
            phone=phone,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        print("USER CREATED SUCCESSFULLY")

        return redirect('/login')

    return render_template('signup.html')

# ================= GOOGLE LOGIN =================
@app.route('/login/google')
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    user_info = resp.json()

    session['user'] = user_info["email"]
    session['name'] = user_info.get("name")
    session['profile_pic'] = user_info.get("picture")

    return redirect('/dashboard')

# ================= FORGOT PASSWORD =================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        return "Reset link sent (demo)"
    return render_template('forgot-password.html')

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect('/login')

    return render_template(
        'dashboard.html',
        user=session.get('user'),
        name=session.get('name'),
        profile=session.get('profile_pic')
    )

# ================= OTHER ROUTES =================
@app.route('/venues')
def venues():
    return render_template('venues.html')

@app.route('/venue-details')
def venue_details():
    venue = {
        "name": "Premium Sports Arena",
        "price": "₹500/hr"
    }
    return render_template('venue-details.html', venue=venue)

@app.route('/booking')
def booking():
    return render_template('booking.html')

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/manage')
def manage():
    return render_template('manage.html')

@app.route("/admin")
def admin():
    return render_template("admin.html")

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route("/notifications")
def notifications():
    return render_template("notifications.html")

@app.route("/support")
def support():
    return render_template("support.html")

@app.route("/tournaments")
def tournaments():
    return render_template("tournaments.html")

# ================= RUN =================
import os

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))