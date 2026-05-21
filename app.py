from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os

app = Flask(__name__)

# ================= APP CONFIG =================

app.secret_key = "bookmyplay_secret_key"

app.config['SESSION_COOKIE_SECURE'] = False

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/bookmyplay'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================= MODELS =================

class Ground(db.Model):

    __tablename__ = "grounds"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))

    sport_type = db.Column(db.String(50))

    location = db.Column(db.String(200))

    price_per_hour = db.Column(db.Integer)

    image = db.Column(db.String(255))

    description = db.Column(db.Text)

    available_slots = db.Column(db.Integer)

    manager_name = db.Column(db.String(100))

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(100), unique=True)

    phone = db.Column(db.String(15), unique=True)

    password = db.Column(db.String(200))


class Booking(db.Model):

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)

    user = db.Column(db.String(100))

    venue = db.Column(db.String(100))

    game = db.Column(db.String(50))

    booking_date = db.Column(db.String(50))

    booking_time = db.Column(db.String(50))

    amount = db.Column(db.Integer)

    status = db.Column(db.String(50))


class Transaction(db.Model):

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)

    user = db.Column(db.String(100))

    venue = db.Column(db.String(100))

    game = db.Column(db.String(50))

    booking_time = db.Column(db.String(50))

    amount = db.Column(db.Integer)

    payment_method = db.Column(db.String(50))

    status = db.Column(db.String(50))


# ================= CREATE DATABASE =================

with app.app_context():
    db.create_all()

# ================= GOOGLE LOGIN =================

google_bp = make_google_blueprint(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    redirect_to="google_login"
)

app.register_blueprint(
    google_bp,
    url_prefix="/google-login"
)

# ================= HOME =================

@app.route('/')
def home():
    return render_template('splash.html')


@app.route('/index')
def index():
    return render_template('index.html')

# ================= LOGIN =================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        user_input = request.form.get('email')

        password = request.form.get('password')

        user = User.query.filter(
            (User.email == user_input) |
            (User.phone == user_input)
        ).first()

        if user and check_password_hash(user.password, password):

            session['user'] = user.email

            return redirect('/dashboard')

        else:

            return render_template(
                'login.html',
                error="Invalid login"
            )

    return render_template('login.html')

# ================= SIGNUP =================

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        email = request.form.get('email')

        phone = request.form.get('phone')

        password = request.form.get('password')

        existing = User.query.filter(
            (User.email == email) |
            (User.phone == phone)
        ).first()

        if existing:

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

        return redirect('/login')

    return render_template('signup.html')

# ================= OTP LOGIN =================

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

        entered_otp = request.form.get('otp')

        if entered_otp == session.get('otp'):

            session['user'] = session.get('phone')

            return redirect('/dashboard')

        else:

            return render_template(
                'verify-otp.html',
                error="Invalid OTP"
            )

    return render_template('verify-otp.html')

# ================= GOOGLE LOGIN =================

@app.route('/login/google')
def google_login():

    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")

    info = resp.json()

    session['user'] = info["email"]

    session['name'] = info.get("name")

    session['profile_pic'] = info.get("picture")

    return redirect('/dashboard')

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

# ================= VENUES =================

@app.route('/venues')
def venues():

    grounds = Ground.query.all()

    return render_template(
        'venues.html',
        grounds=grounds
    )

# ================= VENUE DETAILS =================

@app.route('/venue-details/<int:id>')
def venue_details(id):

    ground = db.session.get(Ground, id)

    if not ground:
        return "Ground not found"

    return render_template(
        'venue-details.html',
        ground=ground
    )

# ================= CHECK SLOTS =================

@app.route('/check-slots')
def check_slots():

    try:

        game = request.args.get('game')

        date = request.args.get('date')

        bookings = Booking.query.filter_by(
            game=game,
            booking_date=date
        ).all()

        booked_times = []

        for booking in bookings:

            booked_times.append(
                booking.booking_time
            )

        return jsonify({
            "booked": booked_times
        })

    except Exception as e:

        print("SLOTS ERROR:", e)

        return jsonify({
            "booked": []
        })
# ================= BOOK SLOT =================

# ================= BOOK SLOT =================

@app.route('/book-slot', methods=['POST'])
def book_slot():

    if 'user' not in session:

        return jsonify({
            "message": "Login required"
        })

    data = request.get_json()

    venue = data.get('venue')

    game = data.get('game')

    date = data.get('date')

    time = data.get('time')

    amount = data.get('amount')

    existing = Booking.query.filter_by(
        venue=venue,
        booking_date=date,
        booking_time=time
    ).first()

    if existing:

        return jsonify({
            "message": "Slot already booked ❌"
        })

    booking = Booking(

        user=session['user'],

        venue=venue,

        game=game,

        booking_date=date,

        booking_time=time,

        amount=amount,

        status="Confirmed"

    )

    db.session.add(booking)

    # REDUCE AVAILABLE SLOTS

    ground = Ground.query.filter_by(
        name=venue
    ).first()

    if ground and ground.available_slots > 0:

        ground.available_slots -= 1

    db.session.commit()

    return jsonify({
        "message": "Booking Successful ✅"
    })
@app.route('/payment')
def payment():
    return render_template('payment.html')

# ================= SAVE TRANSACTION =================

@app.route('/save-transaction', methods=['POST'])
def save_transaction():

    try:

        data = request.get_json()

        transaction = Transaction(

            user=session.get('user'),

            venue=data.get('venue'),

            game=data.get('game'),

            booking_time=data.get('time'),

            amount=data.get('amount'),

            payment_method=data.get('method'),

            status="Paid"

        )

        db.session.add(transaction)

        db.session.commit()

        return jsonify({
            "message": "Transaction Saved"
        })

    except Exception as e:

        print("TRANSACTION ERROR:", e)

        return jsonify({
            "message": "Transaction Failed"
        }), 500
# ================= SUCCESS =================

@app.route('/success')
def success():
    return render_template('success.html')

# ================= HISTORY =================

@app.route('/history')
def history():

    if 'user' not in session:

        return redirect('/login')

    current_user = session.get('user')

    print("CURRENT USER:", current_user)

    bookings = Booking.query.filter_by(
        user=current_user
    ).all()

    print("BOOKINGS FOUND:", bookings)

    return render_template(
        'history.html',
        bookings=bookings
    )
# ================= CANCEL BOOKING =================

@app.route('/cancel-booking/<int:id>')
def cancel_booking(id):

    booking = Booking.query.get(id)

    if booking:

        db.session.delete(booking)

        db.session.commit()

    return redirect('/history')

# ================= EDIT BOOKING =================

@app.route('/edit-booking/<int:id>', methods=['GET', 'POST'])
def edit_booking(id):

    booking = Booking.query.get(id)

    if request.method == 'POST':

        booking.game = request.form.get('game')

        booking.booking_date = request.form.get('date')

        booking.booking_time = request.form.get('time')

        db.session.commit()

        return redirect('/history')

    return render_template(
        'edit-booking.html',
        booking=booking
    )# ================= EDIT BOOKING =================


# ================= PROFILE =================

@app.route('/profile')
def profile():
    return render_template('profile.html')

# ================= MANAGE =================

@app.route('/manage')
def manage():
    return render_template('manage.html')

# ================= ADMIN =================

@app.route('/admin')
def admin():
    return render_template('admin.html')

# ================= EXTRA PAGES =================

@app.route('/notifications')
def notifications():
    return render_template('notifications.html')


@app.route('/support')
def support():
    return render_template('support.html')


@app.route('/tournaments')
def tournaments():
    return render_template('tournaments.html')


@app.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html')


@app.route('/live-match')
def live_match():
    return render_template('live-match.html')

# ================= LOGOUT =================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

# ================= RUN =================

if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )