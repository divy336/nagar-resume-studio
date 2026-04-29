from flask import session, url_for, render_template, request, redirect, jsonify
from admin import admin
import mysql.connector
import smtplib
from email.message import EmailMessage
import random
import json
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


SUPER_ADMIN_EMAIL = "nagardivya73@gmail.com"
SENDER_EMAIL      = "nagardivya73@gmail.com"
SENDER_PASSWORD   = "gjgebkodbezyzoxr"


# ══════════════════════════════════════
#  EMAIL HELPERS
# ══════════════════════════════════════
def send_otp_email(to_email, otp, subject="OTP Verification"):
    """Send OTP to a given email address."""
    msg = EmailMessage()
    msg["Subject"] = f"🔐 {subject}"
    msg["From"]    = f"Resume Builder <{SENDER_EMAIL}>"
    msg["To"]      = to_email
    msg.set_content(f"Your OTP is: {otp}")
    msg.add_alternative(f"""
    <html><body style="font-family:Poppins,sans-serif;background:#f0f4fc;padding:30px;">
    <div style="max-width:480px;margin:auto;background:#fff;border-radius:16px;padding:32px;
                box-shadow:0 4px 24px rgba(37,99,235,.12);">
      <div style="text-align:center;margin-bottom:20px;">
        <div style="width:52px;height:52px;background:#eff6ff;border-radius:14px;
                    display:inline-flex;align-items:center;justify-content:center;font-size:24px;">🔐</div>
      </div>
      <h2 style="color:#1e293b;text-align:center;font-size:20px;margin-bottom:6px;">{subject}</h2>
      <p style="color:#64748b;text-align:center;font-size:13px;">Resume Builder Admin Panel</p>
      <div style="text-align:center;margin:28px 0;">
        <span style="font-size:34px;font-weight:700;letter-spacing:10px;
                     background:#eff6ff;padding:14px 28px;border-radius:12px;
                     color:#2563eb;display:inline-block;">{otp}</span>
      </div>
      <p style="color:#94a3b8;font-size:12px;text-align:center;">
        This OTP is valid for one-time use only. Do not share it with anyone.
      </p>
    </div>
    </body></html>
    """, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)




def log_login(username, email, ip, status):
    try:
        cursor.execute(
            "INSERT INTO admin_login (username, email) VALUES (%s, %s)",
            (f"{status}:{username}", email)
        )
        db.commit()
    except Exception as e:
        print(f"[Login Log Error] {e}")
        
        
@admin.route("/admin_signup", methods=["GET", "POST"])
def admin_signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        if not all([username, email, password, confirm]):
            return render_template("admin_signup.html", error="All fields are required")
        if password != confirm:
            return render_template("admin_signup.html", error="Passwords do not match")

        cursor.execute("SELECT id FROM admin_signup WHERE email=%s", (email,))
        if cursor.fetchone():
            return render_template("admin_signup.html", error="Email already registered")
        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute(
            "INSERT INTO admin_signup (username, email, password, is_verified) VALUES (%s,%s,%s,0)",
            (username, email, password)
        )
        db.commit()

        otp = str(random.randint(100000, 999999))
        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute(
            "INSERT INTO admin_otp (email, otp, is_used) VALUES (%s,%s,0)",
            (email, otp)
        )
        db.commit()
        send_otp_email(
    SUPER_ADMIN_EMAIL,
    otp,
    f"New Admin Signup Approval for {email}"
)
        session["otp_email"] = email
        return redirect(url_for("admin.admin_otp"))

    return render_template("admin_signup.html")



@admin.route("/admin_otp", methods=["GET", "POST"])
def admin_otp():
    email = session.get("otp_email")
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        if not otp:
            return render_template("admin_otp.html", error="Please enter OTP")
        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute("""
            SELECT id FROM admin_otp
            WHERE email=%s AND otp=%s AND is_used=0
            ORDER BY id DESC LIMIT 1
        """, (email, otp))
        row = cursor.fetchone()
        if not row:
            return render_template("admin_otp.html", error="Invalid or expired OTP")

        cursor.execute("UPDATE admin_otp SET is_used=1 WHERE id=%s", (row["id"],))
        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute("UPDATE admin_signup SET is_verified=1 WHERE email=%s", (email,))
        db.commit()
        return redirect(url_for("admin.admin_login"))

    return render_template("admin_otp.html")



@admin.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        ip = request.remote_addr or "Unknown"

        if not email or not password:
            return render_template("admin_login.html", error="All fields are required")
        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute("""
            SELECT id, username, email
            FROM admin_signup
            WHERE email=%s AND password=%s AND is_verified=1
        """, (email, password))

        row = cursor.fetchone()

        if not row:
            log_login("UNKNOWN", email, ip, "FAILED")
            return render_template(
                "admin_login.html",
                error="Invalid credentials or account not verified"
            )

        admin_id = row["id"]
        admin_name = row["username"]
        admin_mail = row["email"]

        session["admin_id"] = admin_id
        session["admin_name"] = admin_name
        session["admin_email"] = admin_mail

        log_login(admin_name, admin_mail, ip, "SUCCESS")

        return redirect(url_for("admin.admin_dashboard"))

    return render_template("admin_login.html")



@admin.route("/forgot_admin", methods=["GET", "POST"])
def forgot_admin():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            return render_template("forgot_admin.html", error="Email required")
        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute("SELECT id FROM admin_signup WHERE email=%s", (email,))
        if not cursor.fetchone():
            return render_template("forgot_admin.html", error="Email not registered")

        otp = str(random.randint(100000, 999999))
        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute("INSERT INTO admin_otp (email, otp, is_used) VALUES (%s,%s,0)", (email, otp))
        db.commit()
        send_otp_email(email, otp, "Password Reset OTP")
        session["reset_email"] = email
        return redirect(url_for("admin.forgot_admin_otp"))

    return render_template("forgot_admin.html")


@admin.route("/forgot_admin_otp", methods=["GET", "POST"])
def forgot_admin_otp():
    email = session.get("reset_email")
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        if not otp:
            return render_template("forgot_admin_otp.html", error="OTP required")
        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute("""
            SELECT id FROM admin_otp
            WHERE email=%s AND otp=%s AND is_used=0
            ORDER BY id DESC LIMIT 1
        """, (email, otp))
        row = cursor.fetchone()
        if not row:
            return render_template("forgot_admin_otp.html", error="Invalid OTP")
        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute("UPDATE admin_otp SET is_used=1 WHERE id=%s", (row["id"],))
        db.commit()
        return redirect(url_for("admin.admin_login"))

    return render_template("forgot_admin_otp.html")





@admin.route("/delete_admin/<int:admin_id>", methods=["POST"])
def delete_admin(admin_id):
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        # Get admin details
        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute("SELECT id, username, email FROM admin_signup WHERE id=%s", (admin_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Admin not found"}), 404

        deleted_id    = row["id"]
        deleted_name  = row["username"]
        deleted_email = row["email"]

        # ❌ BLOCK: Super Admin cannot be deleted
        if deleted_email == SUPER_ADMIN_EMAIL:
            return jsonify({
                "success": False,
                "message": "Super Admin cannot be deleted"
            }), 403

        # ❌ BLOCK: Self delete
        if deleted_id == session["admin_id"]:
            return jsonify({
                "success": False,
                "message": "You cannot delete your own account"
            }), 400

        db.ping(reconnect=True, attempts=3, delay=2)
        cursor.execute("DELETE FROM admin_signup WHERE id=%s", (admin_id,))
        cursor.execute("DELETE FROM admin_otp WHERE email=%s", (deleted_email,))
        db.commit()

        return jsonify({
            "success": True,
            "message": f"Admin '{deleted_name}' deleted successfully"
        })

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@admin.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))
    db.ping(reconnect=True, attempts=3, delay=2)
    cursor.execute("SELECT user_id, resume_data FROM user_resume")
    resume_rows = cursor.fetchall()

    users = []
    resumes = []

    for row in resume_rows:
        user_id = row["user_id"]

        try:
            r = json.loads(row["resume_data"]) if isinstance(row["resume_data"], str) else row["resume_data"]
        except:
            continue

        name = ((r.get("first_name","") + " " + r.get("last_name","")).strip()) or "No Name"

        users.append({
            "user_id": user_id,
            "name": name,
            "email": r.get("email","Not Provided"),
            "mobile": r.get("mobile","Not Provided"),
            "major": r.get("major","Not Provided"),
            "status": 1
        })

        resumes.append({
            "user_id": user_id,
            "name": name,
            "email": r.get("email","Not Provided"),
            "skills": ", ".join(r.get("skills", [])),
            "experience": len(r.get("experience", [])),
            "projects": len(r.get("projects", [])),
            "raw": r
        })

    # admins
    cursor.execute("SELECT id, username, email, is_verified, created_at FROM admin_signup")
    admin_rows = cursor.fetchall()

    admins = []
    for row in admin_rows:
        admins.append({
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "is_verified": bool(row["is_verified"]),
            "created_at": str(row["created_at"]),
            "is_self": row["id"] == session["admin_id"]
        })

    # login activity
    cursor.execute("SELECT id, username, email, created_at FROM admin_login ORDER BY created_at DESC LIMIT 50")
    login_rows = cursor.fetchall()

    login_activity = []
    for row in login_rows:
        login_activity.append({
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "login_time": str(row["created_at"])
        })

    cursor.execute("""
        SELECT COUNT(DISTINCT email) AS total
        FROM admin_login
        WHERE username LIKE 'SUCCESS:%'
    """)
    result = cursor.fetchone()
    successful_logins = result["total"]

    return render_template(
        "admin/dashbord_admin.html",
        users=users,
        resumes=resumes,
        admins=admins,
        login_activity=login_activity,
        total_users=len(users),
        total_resumes=len(resumes),
        verified_admins=sum(1 for a in admins if a["is_verified"]),
        successful_logins=successful_logins,
        admin_name=session.get("admin_name", "Admin"),
        admin_email=session.get("admin_email", ""),
        current_admin_id=session.get("admin_id"),
    )
@admin.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin.admin_login"))