from flask import request, render_template, redirect, url_for, session
import mysql.connector
import random
import smtplib
from email.message import EmailMessage
from auth import auth
import os

db = mysql.connector.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE"),
    port=int(os.getenv("MYSQLPORT", 3306)),
        connection_timeout=30,
        autocommit=True

)

cursor = db.cursor(dictionary=True)


# ---------------- EMAIL OTP ----------------
def send_email(to_email, otp):
    sender_email = "yourgmail@gmail.com"
    sender_password = "your_app_password"

    msg = EmailMessage()
    msg["Subject"] = "OTP Verification"
    msg["From"] = sender_email
    msg["To"] = to_email

    msg.set_content(f"Your OTP is: {otp}")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)


# ---------------- SIGNUP ----------------
@auth.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        db.ping(reconnect=True, attempts=3, delay=2)
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if not all([username, email, password, confirm]):
            return render_template("signup.html", error="All fields required")

        if password != confirm:
            return render_template("signup.html", error="Passwords do not match")

        cursor.execute("SELECT id FROM register WHERE email=%s", (email,))
        if cursor.fetchone():
            return render_template("signup.html", error="Email already registered")

        cursor.execute(
            "INSERT INTO register (username,email,password,is_verified) VALUES (%s,%s,%s,0)",
            (username, email, password)
        )
        db.commit()

        otp = str(random.randint(100000, 999999))

        cursor.execute(
            "INSERT INTO otp_verify (email,otp,is_used) VALUES (%s,%s,0)",
            (email, otp)
        )
        db.commit()

        send_email(email, otp)

        return redirect(url_for("auth.verify_otp", email=email))

    return render_template("signup.html")


# ---------------- VERIFY OTP ----------------
@auth.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    email = request.args.get("email")

    if request.method == "POST":
        db.ping(reconnect=True, attempts=3, delay=2)
        otp = request.form.get("otp")

        cursor.execute(
            "SELECT id FROM otp_verify WHERE email=%s AND otp=%s AND is_used=0",
            (email, otp)
        )

        row = cursor.fetchone()

        if not row:
            return render_template("otp.html", error="Invalid OTP", email=email)

        cursor.execute(
            "UPDATE otp_verify SET is_used=1 WHERE id=%s",
            (row["id"],)
        )

        cursor.execute(
            "UPDATE register SET is_verified=1 WHERE email=%s",
            (email,)
        )

        db.commit()

        return redirect(url_for("auth.login"))

    return render_template("otp.html", email=email)


# ---------------- LOGIN ----------------
@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        db.ping(reconnect=True, attempts=3, delay=2)

        email = request.form.get("email").strip()
        password = request.form.get("password").strip()

        cursor.execute(
            "SELECT id,username,is_verified FROM register WHERE email=%s AND password=%s",
            (email, password)
        )

        user = cursor.fetchone()

        if not user:
            return render_template("login.html", error="Invalid email or password")

        if user["is_verified"] == 0:
            return render_template("login.html", error="Please verify account first")

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect(url_for("resume.dashbord"))

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
        db.ping(reconnect=True, attempts=3, delay=2)
        email = request.form.get("email")
        cursor.execute("SELECT id FROM register WHERE email=%s", (email,))
        if not cursor.fetchone():
            return render_template("forgot_password.html", error="Email not found")

        otp = str(random.randint(100000, 999999))

        cursor.execute(
            "INSERT INTO otp_verify (email,otp,is_used) VALUES (%s,%s,0)",
            (email, otp)
        )
        db.commit()

        send_email(email, otp)

        return redirect(url_for("auth.reset_otp", email=email))

    return render_template("forgot_password.html")


# ---------------- RESET OTP ----------------
@auth.route("/reset-otp", methods=["GET", "POST"])
def reset_otp():

    email = request.args.get("email")

    if request.method == "POST":
        db.ping(reconnect=True, attempts=3, delay=2)
        otp = request.form.get("otp")

        cursor.execute(
            "SELECT id FROM otp_verify WHERE email=%s AND otp=%s AND is_used=0",
            (email, otp)
        )

        row = cursor.fetchone()

        if not row:
            return render_template("reset_otp.html", error="Invalid OTP", email=email)

        cursor.execute(
            "UPDATE otp_verify SET is_used=1 WHERE id=%s",
            (row["id"],)
        )
        db.commit()

        return redirect(url_for("auth.reset_password", email=email))

    return render_template("reset_otp.html", email=email)


# ---------------- RESET PASSWORD ----------------
@auth.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    email = request.args.get("email")

    if request.method == "POST":
        db.ping(reconnect=True, attempts=3, delay=2)
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if password != confirm:
            return render_template(
                "reset_password.html",
                error="Passwords do not match",
                email=email
            )

        cursor.execute(
            "UPDATE register SET password=%s WHERE email=%s",
            (password, email)
        )
        db.commit()

        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", email=email)