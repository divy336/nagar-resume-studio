from flask import session, url_for, render_template, request, redirect, jsonify
from admin import admin
import mysql.connector
import smtplib
from email.message import EmailMessage
import random
import json
import os

# ==================================
# DATABASE CONNECTION
# ==================================
def get_db():
    db = mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT", 3306)),
        connection_timeout=30,
        autocommit=False
    )
    cursor = db.cursor(dictionary=True)
    return db, cursor


# ==================================
# EMAIL CONFIG
# ==================================
SUPER_ADMIN_EMAIL = "nagardivya73@gmail.com"
SENDER_EMAIL = "nagardivya73@gmail.com"
SENDER_PASSWORD = "your_app_password"


# ==================================
# SEND EMAIL
# ==================================
def send_otp_email(to_email, otp, subject="OTP Verification"):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg.set_content(f"Your OTP is: {otp}")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)


# ==================================
# LOGIN LOG
# ==================================
def log_login(username, email, status):
    try:
        db, cursor = get_db()

        cursor.execute(
            "INSERT INTO admin_login(username,email) VALUES(%s,%s)",
            (f"{status}:{username}", email)
        )

        db.commit()
        cursor.close()
        db.close()

    except:
        pass


# ==================================
# ADMIN SIGNUP
# ==================================
@admin.route("/admin_signup", methods=["GET", "POST"])
def admin_signup():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not all([username, email, password, confirm]):
            return render_template("admin_signup.html", error="All fields required")

        if password != confirm:
            return render_template("admin_signup.html", error="Passwords do not match")

        db, cursor = get_db()

        cursor.execute(
            "SELECT id FROM admin_signup WHERE email=%s",
            (email,)
        )

        if cursor.fetchone():
            cursor.close()
            db.close()
            return render_template("admin_signup.html", error="Email already exists")

        cursor.execute(
            "INSERT INTO admin_signup(username,email,password,is_verified) VALUES(%s,%s,%s,0)",
            (username, email, password)
        )

        otp = str(random.randint(100000, 999999))

        cursor.execute(
            "INSERT INTO admin_otp(email,otp,is_used) VALUES(%s,%s,0)",
            (email, otp)
        )

        db.commit()
        cursor.close()
        db.close()

        send_otp_email(SUPER_ADMIN_EMAIL, otp, f"Admin Approval OTP ({email})")

        session["otp_email"] = email

        return redirect(url_for("admin.admin_otp"))

    return render_template("admin_signup.html")


# ==================================
# ADMIN OTP VERIFY
# ==================================
@admin.route("/admin_otp", methods=["GET", "POST"])
def admin_otp():

    email = session.get("otp_email")

    if request.method == "POST":

        otp = request.form.get("otp", "").strip()

        db, cursor = get_db()

        cursor.execute("""
            SELECT id FROM admin_otp
            WHERE email=%s AND otp=%s AND is_used=0
            ORDER BY id DESC LIMIT 1
        """, (email, otp))

        row = cursor.fetchone()

        if not row:
            cursor.close()
            db.close()
            return render_template("admin_otp.html", error="Invalid OTP")

        cursor.execute(
            "UPDATE admin_otp SET is_used=1 WHERE id=%s",
            (row["id"],)
        )

        cursor.execute(
            "UPDATE admin_signup SET is_verified=1 WHERE email=%s",
            (email,)
        )

        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for("admin.admin_login"))

    return render_template("admin_otp.html")


# ==================================
# ADMIN LOGIN
# ==================================
@admin.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db, cursor = get_db()

        cursor.execute("""
            SELECT id, username, email
            FROM admin_signup
            WHERE email=%s AND password=%s AND is_verified=1
        """, (email, password))

        row = cursor.fetchone()

        cursor.close()
        db.close()

        if not row:
            log_login("UNKNOWN", email, "FAILED")
            return render_template("admin_login.html", error="Invalid Login")

        session["admin_id"] = row["id"]
        session["admin_name"] = row["username"]
        session["admin_email"] = row["email"]

        log_login(row["username"], row["email"], "SUCCESS")

        return redirect(url_for("admin.admin_dashboard"))

    return render_template("admin_login.html")


# ==================================
# FORGOT PASSWORD
# ==================================
@admin.route("/forgot_admin", methods=["GET", "POST"])
def forgot_admin():

    if request.method == "POST":

        email = request.form.get("email", "").strip()

        db, cursor = get_db()

        cursor.execute(
            "SELECT id FROM admin_signup WHERE email=%s",
            (email,)
        )

        if not cursor.fetchone():
            cursor.close()
            db.close()
            return render_template("forgot_admin.html", error="Email not found")

        otp = str(random.randint(100000, 999999))

        cursor.execute(
            "INSERT INTO admin_otp(email,otp,is_used) VALUES(%s,%s,0)",
            (email, otp)
        )

        db.commit()
        cursor.close()
        db.close()

        send_otp_email(email, otp, "Password Reset OTP")

        session["reset_email"] = email

        return redirect(url_for("admin.forgot_admin_otp"))

    return render_template("forgot_admin.html")


# ==================================
# FORGOT OTP
# ==================================
@admin.route("/forgot_admin_otp", methods=["GET", "POST"])
def forgot_admin_otp():

    email = session.get("reset_email")

    if request.method == "POST":

        otp = request.form.get("otp", "").strip()

        db, cursor = get_db()

        cursor.execute("""
            SELECT id FROM admin_otp
            WHERE email=%s AND otp=%s AND is_used=0
            ORDER BY id DESC LIMIT 1
        """, (email, otp))

        row = cursor.fetchone()

        if not row:
            cursor.close()
            db.close()
            return render_template("forgot_admin_otp.html", error="Invalid OTP")

        cursor.execute(
            "UPDATE admin_otp SET is_used=1 WHERE id=%s",
            (row["id"],)
        )

        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for("admin.admin_login"))

    return render_template("forgot_admin_otp.html")


# ==================================
# ADMIN DASHBOARD
# ==================================
@admin.route("/admin_dashboard")
def admin_dashboard():

    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    db, cursor = get_db()

    cursor.execute("SELECT id, username, email, is_verified FROM admin_signup")
    admins = cursor.fetchall()

    cursor.execute("SELECT id, username, email FROM admin_login ORDER BY id DESC LIMIT 50")
    login_activity = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin/dashbord_admin.html",
        admins=admins,
        login_activity=login_activity,
        admin_name=session.get("admin_name"),
        admin_email=session.get("admin_email")
    )


# ==================================
# DELETE ADMIN
# ==================================
@admin.route("/delete_admin/<int:admin_id>", methods=["POST"])
def delete_admin(admin_id):

    if "admin_id" not in session:
        return jsonify({"success": False})

    db, cursor = get_db()

    cursor.execute(
        "SELECT id, username, email FROM admin_signup WHERE id=%s",
        (admin_id,)
    )

    row = cursor.fetchone()

    if not row:
        return jsonify({"success": False})

    if row["email"] == SUPER_ADMIN_EMAIL:
        return jsonify({"success": False, "message": "Super Admin protected"})

    if row["id"] == session["admin_id"]:
        return jsonify({"success": False, "message": "Cannot delete self"})

    cursor.execute("DELETE FROM admin_signup WHERE id=%s", (admin_id,))
    cursor.execute("DELETE FROM admin_otp WHERE email=%s", (row["email"],))

    db.commit()
    cursor.close()
    db.close()

    return jsonify({"success": True})


# ==================================
# LOGOUT
# ==================================
@admin.route("/admin_logout")
def admin_logout():

    session.pop("admin_id", None)
    session.pop("admin_name", None)
    session.pop("admin_email", None)

    return redirect(url_for("admin.admin_login"))