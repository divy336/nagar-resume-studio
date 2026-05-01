import email

from flask import session, url_for, render_template, request, redirect, jsonify
from admin import admin
import mysql.connector
from mysql.connector import pooling
import random
import json
import os
import requests
from threading import Thread

# Database Connection Pool
try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="admin_pool",
        pool_size=5,
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT", 3306)),
    )
    print("✅ Admin database pool created")
except Exception as e:
    print(f"❌ Admin database pool failed: {e}")
    db_pool = None

def get_db():
    """Get database connection from pool"""
    if db_pool is None:
        db = mysql.connector.connect(
            host=os.getenv("MYSQLHOST"),
            user=os.getenv("MYSQLUSER"),
            password=os.getenv("MYSQLPASSWORD"),
            database=os.getenv("MYSQLDATABASE"),
            port=int(os.getenv("MYSQLPORT", 3306)),
            autocommit=False
        )
    else:
        db = db_pool.get_connection()
    
    cursor = db.cursor(dictionary=True)
    return db, cursor

SUPER_ADMIN_EMAIL = "nagardivya73@gmail.com"


# ══════════════════════════════════════
#  EMAIL HELPERS
# ══════════════════════════════════════

def get_email_template(otp, title="OTP Verification"):
    return f"""
    <html>
    <body style="font-family:Arial;background:#f4f4f4;padding:30px;">
      <div style="max-width:500px;margin:auto;background:#fff;padding:30px;border-radius:12px;">
        <h2 style="text-align:center;color:#4f46e5;">Resume Studio Admin</h2>
        <h3 style="text-align:center;">{title}</h3>
        <div style="
            font-size:34px;
            font-weight:bold;
            text-align:center;
            background:#4f46e5;
            color:white;
            padding:15px;
            border-radius:10px;
            letter-spacing:8px;
            margin:25px 0;
        ">
            {otp}
        </div>
        <p style="text-align:center;">OTP valid for one time use.</p>
      </div>
    </body>
    </html>
    """

def send_otp_email_async(to_email, otp, subject="OTP Verification"):
    """Send email asynchronously using Brevo API"""
    api_key = os.getenv("BREVO_API_KEY")
    
    if not api_key:
        print("❌ BREVO_API_KEY not configured")
        print(f"🔐 OTP for {to_email}: {otp}")
        return

    payload = {
        "sender": {
            "name": "Resume Studio Admin",
            "email": "nagardivya73@gmail.com"
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": get_email_template(otp, subject)
    }

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }

    try:
        print(f"📧 Sending admin email to {to_email}...")
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=15
        )
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ Admin email sent to {to_email}")
        else:
            print(f"❌ Brevo error: {response.status_code} - {response.text}")
            print(f"🔐 OTP for {to_email}: {otp}")
            
    except Exception as e:
        print(f"❌ Email error: {e}")
        print(f"🔐 OTP for {to_email}: {otp}")

def send_otp_email(to_email, otp, subject="OTP Verification"):
    """Wrapper to send email in background"""
    thread = Thread(target=send_otp_email_async, args=(to_email, otp, subject))
    thread.daemon = True
    thread.start()


# ══════════════════════════════════════
#  ADMIN SIGNUP
# ══════════════════════════════════════

@admin.route("/admin_signup", methods=["GET", "POST"])
def admin_signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

        if not all([username, email, password, confirm]):
            return render_template("admin_signup.html", error="All fields are required")

        if password != confirm:
            return render_template("admin_signup.html", error="Passwords do not match")

        db, cursor = get_db()

        try:
            # Check if email OR username already exists
            cursor.execute(
                "SELECT id FROM admin_signup WHERE email=%s OR username=%s", 
                (email, username)
            )
            
            existing = cursor.fetchone()
            if existing:
                return render_template("admin_signup.html", error="Email or Username already registered")

            cursor.execute(
                """
                INSERT INTO admin_signup (username, email, password, is_verified)
                VALUES (%s, %s, %s, 0)
                """,
                (username, email, password)
            )

            otp = str(random.randint(100000, 999999))

            cursor.execute(
                """
                INSERT INTO admin_otp (email, otp, is_used)
                VALUES (%s, %s, 0)
                """,
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

        except Exception as e:
            db.rollback()
            print(f"❌ Admin signup error: {e}")
            return render_template("admin_signup.html", error="Signup failed. Try again.")

        finally:
            cursor.close()
            db.close()

    return render_template("admin_signup.html")


@admin.route("/admin_otp", methods=["GET", "POST"])
def admin_otp():
    email = session.get("otp_email")

    if not email:
        return redirect(url_for("admin.admin_signup"))

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()

        if not otp:
            return render_template("admin_otp.html", error="Please enter OTP")

        db, cursor = get_db()

        try:
            cursor.execute(
                """
                SELECT id FROM admin_otp
                WHERE email=%s AND otp=%s AND is_used=0
                ORDER BY id DESC LIMIT 1
                """,
                (email, otp)
            )

            row = cursor.fetchone()

            if not row:
                return render_template("admin_otp.html", error="Invalid or expired OTP")

            cursor.execute("UPDATE admin_otp SET is_used=1 WHERE id=%s", (row["id"],))
            cursor.execute("UPDATE admin_signup SET is_verified=1 WHERE email=%s", (email,))
            db.commit()
            
            return redirect(url_for("admin.admin_login"))

        except Exception as e:
            db.rollback()
            print(f"❌ Admin OTP error: {e}")
            return render_template("admin_otp.html", error="Verification failed")

        finally:
            cursor.close()
            db.close()

    return render_template("admin_otp.html")


# ══════════════════════════════════════
#  ADMIN LOGIN (STATUS REMOVED)
# ══════════════════════════════════════

@admin.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            return render_template(
                "admin_login.html",
                error="All fields are required"
            )

        db, cursor = get_db()

        try:
            db.ping(reconnect=True, attempts=3, delay=2)

            cursor.execute("""
                SELECT id, username, email
                FROM admin_signup
                WHERE LOWER(email)=%s
                AND password=%s
                AND is_verified=1
                LIMIT 1
            """, (email, password))

            row = cursor.fetchone()

            if row is None:
                # Log failed login attempt (without status column)
                try:
                    cursor.execute("""
                        INSERT INTO admin_login
                        (username, email)
                        VALUES (%s, %s)
                    """, ("FAILED", email))
                    db.commit()
                except:
                    pass  # Don't fail login if logging fails

                return render_template(
                    "admin_login.html",
                    error="Invalid email or password"
                )

            # Clear any existing session
            session.clear()
            session.permanent = True

            # Set session variables
            session["admin_id"] = row["id"]
            session["admin_name"] = row["username"]
            session["admin_email"] = row["email"]

            # Log successful login (without status column)
            try:
                cursor.execute("""
                    INSERT INTO admin_login
                    (username, email)
                    VALUES (%s, %s)
                """, (row["username"], row["email"]))
                db.commit()
            except Exception as log_error:
                print(f"⚠️ Could not log login: {log_error}")
                # Don't fail the login if logging fails

            return redirect(url_for("admin.admin_dashboard"))

        except Exception as e:
            db.rollback()
            print(f"❌ Admin login error: {e}")

            return render_template(
                "admin_login.html",
                error="Login failed"
            )

        finally:
            cursor.close()
            db.close()

    return render_template("admin_login.html")


# ══════════════════════════════════════
#  FORGOT PASSWORD
# ══════════════════════════════════════

@admin.route("/forgot_admin", methods=["GET", "POST"])
def forgot_admin():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            return render_template("forgot_admin.html", error="Email required")

        db, cursor = get_db()

        try:
            cursor.execute("SELECT id FROM admin_signup WHERE email=%s", (email,))

            if not cursor.fetchone():
                return render_template("forgot_admin.html", error="Email not registered")

            otp = str(random.randint(100000, 999999))

            cursor.execute(
                """
                INSERT INTO admin_otp (email, otp, is_used)
                VALUES (%s, %s, 0)
                """,
                (email, otp)
            )
            db.commit()

            send_otp_email(email, otp, "Admin Password Reset OTP")

            session["reset_email"] = email

            return redirect(url_for("admin.forgot_admin_otp"))

        except Exception as e:
            db.rollback()
            print(f"❌ Forgot admin error: {e}")
            return render_template("forgot_admin.html", error="Request failed")

        finally:
            cursor.close()
            db.close()

    return render_template("forgot_admin.html")


@admin.route("/forgot_admin_otp", methods=["GET", "POST"])
def forgot_admin_otp():
    email = session.get("reset_email")

    if not email:
        return redirect(url_for("admin.forgot_admin"))

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()

        if not otp:
            return render_template("forgot_admin_otp.html", error="OTP required")

        db, cursor = get_db()

        try:
            cursor.execute(
                """
                SELECT id
                FROM admin_otp
                WHERE email=%s AND otp=%s AND is_used=0
                ORDER BY id DESC LIMIT 1
                """, 
                (email, otp)
            )

            row = cursor.fetchone()

            if not row:
                return render_template("forgot_admin_otp.html", error="Invalid OTP")

            cursor.execute("UPDATE admin_otp SET is_used=1 WHERE id=%s", (row["id"],))
            db.commit()

            session.permanent = True
            session["reset_email"] = email
            session["otp_verified"] = True

            return redirect(url_for("admin.reset_password"))

        except Exception as e:
            db.rollback()
            print(f"❌ Forgot OTP Error: {e}")
            return render_template("forgot_admin_otp.html", error="OTP verification failed")

        finally:
            cursor.close()
            db.close()

    return render_template("forgot_admin_otp.html")


@admin.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    email = session.get("reset_email")
    otp_verified = session.get("otp_verified")

    if email is None or otp_verified is not True:
        return redirect(url_for("admin.forgot_admin"))

    if request.method == "POST":
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not new_password or not confirm_password:
            return render_template("reset_password.html", error="All fields are required")

        if len(new_password) < 6:
            return render_template("reset_password.html", error="Password must be at least 6 characters")

        if new_password != confirm_password:
            return render_template("reset_password.html", error="Passwords do not match")

        db, cursor = get_db()

        try:
            cursor.execute("SELECT id, email FROM admin_signup WHERE email=%s", (email,))
            
            user = cursor.fetchone()
            
            if not user:
                return render_template("reset_password.html", error="User not found")

            cursor.execute(
                """
                UPDATE admin_signup
                SET password=%s
                WHERE email=%s
                """,
                (new_password, email)
            )
            db.commit()

            print(f"✅ Password updated successfully for {email}")

            session.pop("reset_email", None)
            session.pop("otp_verified", None)

            return render_template(
                "reset_password.html",
                success="Password reset successful! Redirecting to login...",
                redirect_login=True
            )

        except Exception as e:
            db.rollback()
            print(f"❌ Reset Password Error: {e}")
            import traceback
            traceback.print_exc()

            return render_template("reset_password.html", error="Password reset failed. Please try again.")

        finally:
            if cursor:
                cursor.close()
            if db:
                db.close()

    return render_template("reset_password.html")


# ══════════════════════════════════════
#  DELETE ADMIN
# ══════════════════════════════════════

@admin.route("/delete_admin/<int:admin_id>", methods=["POST"])
def delete_admin(admin_id):
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    db, cursor = get_db()

    try:
        cursor.execute(
            "SELECT id, username, email FROM admin_signup WHERE id=%s",
            (admin_id,)
        )

        row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Admin not found"}), 404

        if row["email"] == SUPER_ADMIN_EMAIL:
            return jsonify({"success": False, "message": "Super Admin cannot be deleted"}), 403

        if row["id"] == session["admin_id"]:
            return jsonify({"success": False, "message": "You cannot delete yourself"}), 400

        cursor.execute("DELETE FROM admin_signup WHERE id=%s", (admin_id,))
        cursor.execute("DELETE FROM admin_otp WHERE email=%s", (row["email"],))
        db.commit()
        
        return jsonify({
            "success": True,
            "message": f"Admin '{row['username']}' deleted successfully"
        })

    except Exception as e:
        db.rollback()
        print(f"❌ Delete admin error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        db.close()


# ══════════════════════════════════════
#  ADMIN DASHBOARD
# ══════════════════════════════════════

@admin.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    db, cursor = get_db()

    try:
        # ===== IT RESUMES =====
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

            first_name = r.get("first_name", "") if r.get("first_name") else ""
            last_name = r.get("last_name", "") if r.get("last_name") else ""
            name = (first_name + " " + last_name).strip() or "No Name"

            users.append({
                "user_id": user_id,
                "name": name,
                "email": r.get("email") or "Not Provided",
                "mobile": r.get("mobile") or "Not Provided",
                "major": r.get("major") or "Not Provided",
                "status": 1,
                "raw": r
            })

            resumes.append({
                "user_id": user_id,
                "name": name,
                "email": r.get("email") or "Not Provided",
                "skills": ", ".join(r.get("skills", [])) if r.get("skills") else "",
                "experience": len(r.get("experience", [])) if r.get("experience") else 0,
                "projects": len(r.get("projects", [])) if r.get("projects") else 0,
                "raw": r
            })

        # ===== OTHER RESUMES =====
        cursor.execute("SELECT user_id, resume_data FROM other_resume")
        other_rows = cursor.fetchall()

        other_resumes = []

        for row in other_rows:
            try:
                r = json.loads(row["resume_data"]) if isinstance(row["resume_data"], str) else row["resume_data"]
            except:
                continue

            other_resumes.append({
                "user_id": row["user_id"],
                "name": r.get("name") or "No Name",
                "email": r.get("email") or "Not Provided",
                "career": r.get("career") or "",
                "skills": ", ".join(r.get("skills", [])) if r.get("skills") else "",
                "experience": len(r.get("experience", [])) if r.get("experience") else 0,
                "projects": len(r.get("projects", [])) if r.get("projects") else 0,
                "raw": r
            })

        # ===== ADMINS =====
        cursor.execute(
            """
            SELECT id, username, email, is_verified, created_at
            FROM admin_signup
            ORDER BY id DESC
            """
        )

        admin_rows = cursor.fetchall()
        admins = []

        for row in admin_rows:
            admins.append({
                "id": row["id"],
                "username": row["username"] or "",
                "email": row["email"] or "",
                "is_verified": bool(row["is_verified"]),
                "created_at": str(row["created_at"]) if row.get("created_at") else "",
                "is_self": row["id"] == session["admin_id"]
            })

        # ===== LOGIN ACTIVITY =====
        cursor.execute(
            """
            SELECT id, username, email, created_at
            FROM admin_login
            ORDER BY created_at DESC
            LIMIT 50
            """
        )

        login_rows = cursor.fetchall()
        login_activity = []

        for row in login_rows:
            login_activity.append({
                "id": row["id"],
                "username": row.get("username") or "",
                "email": row.get("email") or "",
                "login_time": str(row["created_at"]) if row.get("created_at") else ""
            })

        # ===== SUCCESS LOGIN COUNT (updated without status column) =====
        cursor.execute(
            """
            SELECT COUNT(DISTINCT email) AS total
            FROM admin_login
            WHERE username != 'FAILED'
            """
        )

        result = cursor.fetchone()
        successful_logins = result["total"] if result and result.get("total") else 0

        # ===== RENDER PAGE =====
        return render_template(
            "admin/dashbord_admin.html",
            users=users,
            resumes=resumes,
            other_resumes=other_resumes,
            admins=admins,
            login_activity=login_activity,
            total_users=len(users),
            total_resumes=len(resumes),
            total_other_resumes=len(other_resumes),
            verified_admins=sum(1 for a in admins if a["is_verified"]),
            successful_logins=successful_logins,
            admin_name=session.get("admin_name", "Admin"),
            admin_email=session.get("admin_email", ""),
            current_admin_id=session.get("admin_id")
        )

    except Exception as e:
        print(f"❌ ADMIN DASHBOARD ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        return f"""
        <html>
        <head><title>Error</title></head>
        <body style="font-family: Arial; padding: 50px; text-align: center;">
            <h1>⚠️ Dashboard Error</h1>
            <p>{str(e)}</p>
            <a href="/admin_login">Back to Login</a>
        </body>
        </html>
        """, 500

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db' in locals() and db:
            db.close()


@admin.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin.admin_login"))