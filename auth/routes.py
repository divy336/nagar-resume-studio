from flask import request, render_template, redirect, url_for, session
import mysql.connector
from mysql.connector import pooling
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from threading import Thread
from auth import auth
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Database Connection Pool
db_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE"),
    port=int(os.getenv("MYSQLPORT", 3306)),
    autocommit=True
)

def get_db_connection():
    """Get database connection from pool"""
    return db_pool.get_connection()


# ---------------- PROFESSIONAL EMAIL TEMPLATES ----------------


import requests


# ==========================================
# OTP EMAIL TEMPLATE
# ==========================================
def get_otp_email_template(otp, purpose="verification"):

    if purpose == "verification":
        title = "Verify Your Account"
        msg = "Use this OTP to verify your account."
    else:
        title = "Reset Password"
        msg = "Use this OTP to reset your password."

    return f"""
    <html>
    <body style="font-family:Arial;background:#f4f4f4;padding:30px;">

        <div style="
            max-width:600px;
            margin:auto;
            background:white;
            padding:30px;
            border-radius:12px;
            box-shadow:0 0 10px rgba(0,0,0,.08);
        ">

            <h1 style="color:#4f46e5;text-align:center;">
                Resume Studio
            </h1>

            <h2 style="text-align:center;">
                {title}
            </h2>

            <p style="text-align:center;font-size:16px;">
                {msg}
            </p>

            <div style="
                background:#4f46e5;
                color:white;
                font-size:34px;
                font-weight:bold;
                text-align:center;
                padding:18px;
                border-radius:10px;
                letter-spacing:8px;
                margin:25px 0;
            ">
                {otp}
            </div>

            <p style="text-align:center;">
                OTP valid for 10 minutes.
            </p>

            <hr>

            <p style="
                text-align:center;
                color:#888;
                font-size:13px;
            ">
                © 2026 Resume Studio
            </p>

        </div>

    </body>
    </html>
    """


# ==========================================
# SEND EMAIL (BREVO)
# ==========================================
def send_email(to_email, otp, purpose="verification"):

    api_key = os.getenv("BREVO_API_KEY")

    if not api_key:
        print("❌ BREVO_API_KEY missing")
        return

    html = get_otp_email_template(otp, purpose)

    payload = {
        "sender": {
            "name": "Resume Studio",
            "email": "nagardivya73@gmail.com"
        },
        "to": [
            {
                "email": to_email
            }
        ],
        "subject": "Resume Studio OTP Code",
        "htmlContent": html
    }

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=20
        )

        print("Email Status:", response.status_code)
        print("Response:", response.text)

        if response.status_code == 201:
            print("✅ Email Sent Successfully")
        else:
            print("❌ Email Failed")

    except Exception as e:
        print("❌ Email Error:", e)
# ---------------- SIGNUP ----------------
# ---------------- SIGNUP ----------------
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

        # Validation
        if not all([username, email, password, confirm]):
            return render_template("signup.html", error="All fields are required")

        if len(password) < 6:
            return render_template("signup.html", error="Password must be at least 6 characters")

        if password != confirm:
            return render_template("signup.html", error="Passwords do not match")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        try:
            # Check if email already exists
            cursor.execute("SELECT id FROM register WHERE email=%s", (email,))
            if cursor.fetchone():
                return render_template("signup.html", error="Email already registered")

            # Hash password
            hashed_password = generate_password_hash(password)

            # Insert user
            cursor.execute(
                "INSERT INTO register (username, email, password, is_verified) VALUES (%s, %s, %s, 0)",
                (username, email, hashed_password)
            )

            # Generate OTP
            otp = str(random.randint(100000, 999999))

            # Store OTP
            cursor.execute(
                "INSERT INTO otp_verify (email, otp, is_used) VALUES (%s, %s, 0)",
                (email, otp)
            )

            # Send email in background
            send_email(email, otp, purpose="verification")

            return redirect(url_for("auth.verify_otp", email=email))

        except Exception as e:
            print(f"Signup error: {e}")
            return render_template("signup.html", error="Registration failed. Please try again.")
        finally:
            cursor.close()
            db.close()

    return render_template("signup.html")


# ---------------- VERIFY OTP ----------------
@auth.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    email = request.args.get("email")

    if not email:
        return redirect(url_for("auth.signup"))

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()

        if not otp:
            return render_template("otp.html", error="Please enter OTP", email=email)

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT id FROM otp_verify WHERE email=%s AND otp=%s AND is_used=0",
                (email, otp)
            )
            row = cursor.fetchone()

            if not row:
                return render_template("otp.html", error="Invalid or expired OTP", email=email)

            # Mark OTP as used
            cursor.execute("UPDATE otp_verify SET is_used=1 WHERE id=%s", (row["id"],))

            # Verify user
            cursor.execute("UPDATE register SET is_verified=1 WHERE email=%s", (email,))
            db.commit()

            return redirect(url_for("auth.login"))

        except Exception as e:
            print(f"OTP verification error: {e}")
            return render_template("otp.html", error="Verification failed", email=email)
        finally:
            cursor.close()
            db.close()

    return render_template("otp.html", email=email)


# ---------------- LOGIN ----------------
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not all([email, password]):
            return render_template("login.html", error="Email and password required")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT id, username, password, is_verified FROM register WHERE email=%s",
                (email,)
            )
            user = cursor.fetchone()

            if not user:
                return render_template("login.html", error="Invalid email or password")

            # Check password hash
            if not check_password_hash(user["password"], password):
                return render_template("login.html", error="Invalid email or password")

            if user["is_verified"] == 0:
                return render_template("login.html", error="Please verify your account first")

            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("resume.dashbord"))

        except Exception as e:
            print(f"Login error: {e}")
            return render_template("login.html", error="Login failed. Please try again.")
        finally:
            cursor.close()
            db.close()

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@auth.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


# ---------------- FORGOT PASSWORD ----------------
@auth.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            return render_template("forgot_password.html", error="Email is required")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        try:
            cursor.execute("SELECT id FROM register WHERE email=%s", (email,))
            if not cursor.fetchone():
                return render_template("forgot_password.html", error="Email not found")

            # Generate OTP
            otp = str(random.randint(100000, 999999))

            # Store OTP
            cursor.execute(
                "INSERT INTO otp_verify (email, otp, is_used) VALUES (%s, %s, 0)",
                (email, otp)
            )

            # Send email
            send_email(email, otp, purpose="reset")

            return redirect(url_for("auth.reset_otp", email=email))

        except Exception as e:
            print(f"Forgot password error: {e}")
            return render_template("forgot_password.html", error="Request failed. Please try again.")
        finally:
            cursor.close()
            db.close()

    return render_template("forgot_password.html")


# ---------------- RESET OTP ----------------
@auth.route("/reset-otp", methods=["GET", "POST"])
def reset_otp():
    email = request.args.get("email")

    if not email:
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()

        if not otp:
            return render_template("reset_otp.html", error="Please enter OTP", email=email)

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT id FROM otp_verify WHERE email=%s AND otp=%s AND is_used=0",
                (email, otp)
            )
            row = cursor.fetchone()

            if not row:
                return render_template("reset_otp.html", error="Invalid or expired OTP", email=email)

            # Mark OTP as used
            cursor.execute("UPDATE otp_verify SET is_used=1 WHERE id=%s", (row["id"],))

            return redirect(url_for("auth.reset_password", email=email))

        except Exception as e:
            print(f"Reset OTP error: {e}")
            return render_template("reset_otp.html", error="Verification failed", email=email)
        finally:
            cursor.close()
            db.close()

    return render_template("reset_otp.html", email=email)


# ---------------- RESET PASSWORD ----------------
@auth.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = request.args.get("email")

    if not email:
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

        if not all([password, confirm]):
            return render_template("reset_password.html", error="All fields required", email=email)

        if len(password) < 6:
            return render_template("reset_password.html", error="Password must be at least 6 characters", email=email)

        if password != confirm:
            return render_template("reset_password.html", error="Passwords do not match", email=email)

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        try:
            # Hash new password
            hashed_password = generate_password_hash(password)

            cursor.execute(
                "UPDATE register SET password=%s WHERE email=%s",
                (hashed_password, email)
            )

            return redirect(url_for("auth.login"))

        except Exception as e:
            print(f"Reset password error: {e}")
            return render_template("reset_password.html", error="Reset failed. Please try again.", email=email)
        finally:
            cursor.close()
            db.close()

    return render_template("reset_password.html", email=email)