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

def get_otp_email_template(otp, purpose="verification"):
    """Returns professional HTML email template"""
    
    if purpose == "verification":
        title = "Verify Your Account"
        message = "Thank you for signing up with Resume Studio! Please use the OTP below to verify your account."
    else:
        title = "Reset Your Password"
        message = "You requested to reset your password. Please use the OTP below to proceed."
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f4f4f4;
            }}
            .email-container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .email-header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px 20px;
                text-align: center;
            }}
            .logo {{
                font-size: 32px;
                font-weight: bold;
                color: #ffffff;
                margin: 0;
                letter-spacing: 1px;
            }}
            .tagline {{
                color: #e0e7ff;
                font-size: 14px;
                margin-top: 5px;
            }}
            .email-body {{
                padding: 40px 30px;
                color: #333333;
            }}
            .email-title {{
                font-size: 24px;
                font-weight: 600;
                color: #1a202c;
                margin-bottom: 20px;
                text-align: center;
            }}
            .email-message {{
                font-size: 16px;
                line-height: 1.6;
                color: #4a5568;
                margin-bottom: 30px;
                text-align: center;
            }}
            .otp-container {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 8px;
                padding: 25px;
                text-align: center;
                margin: 30px 0;
            }}
            .otp-label {{
                color: #e0e7ff;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 10px;
            }}
            .otp-code {{
                font-size: 36px;
                font-weight: bold;
                color: #ffffff;
                letter-spacing: 8px;
                margin: 10px 0;
                font-family: 'Courier New', monospace;
            }}
            .otp-validity {{
                color: #e0e7ff;
                font-size: 13px;
                margin-top: 10px;
            }}
            .warning-box {{
                background-color: #fff5f5;
                border-left: 4px solid #fc8181;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .warning-text {{
                color: #742a2a;
                font-size: 14px;
                margin: 0;
            }}
            .email-footer {{
                background-color: #f7fafc;
                padding: 30px;
                text-align: center;
                border-top: 1px solid #e2e8f0;
            }}
            .footer-text {{
                color: #718096;
                font-size: 13px;
                margin: 5px 0;
            }}
            .footer-link {{
                color: #667eea;
                text-decoration: none;
            }}
            .social-links {{
                margin: 20px 0;
            }}
            .social-links a {{
                display: inline-block;
                margin: 0 10px;
                color: #667eea;
                text-decoration: none;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="email-header">
                <h1 class="logo">📄 Resume Studio</h1>
                <p class="tagline">Build Your Perfect Resume</p>
            </div>
            
            <div class="email-body">
                <h2 class="email-title">{title}</h2>
                <p class="email-message">{message}</p>
                
                <div class="otp-container">
                    <div class="otp-label">Your One-Time Password</div>
                    <div class="otp-code">{otp}</div>
                    <div class="otp-validity">⏱ Valid for 10 minutes</div>
                </div>
                
                <div class="warning-box">
                    <p class="warning-text">
                        🔒 <strong>Security Note:</strong> Never share this OTP with anyone. 
                        Resume Studio will never ask for your OTP via phone or email.
                    </p>
                </div>
                
                <p class="email-message" style="font-size: 14px; margin-top: 30px;">
                    If you didn't request this code, please ignore this email or contact our support team.
                </p>
            </div>
            
            <div class="email-footer">
                <p class="footer-text"><strong>Resume Studio</strong></p>
                <p class="footer-text">Your Professional Resume Builder</p>
                
                <div class="social-links">
                    <a href="#">Help Center</a> • 
                    <a href="#">Contact Support</a> • 
                    <a href="#">Privacy Policy</a>
                </div>
                
                <p class="footer-text" style="margin-top: 20px;">
                    © 2026 Resume Studio. All rights reserved.
                </p>
                <p class="footer-text" style="font-size: 11px; color: #a0aec0;">
                    This is an automated message, please do not reply to this email.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


# ---------------- ASYNC EMAIL SENDING ----------------

def send_email_async(to_email, otp, purpose="verification"):
    """Send email in background thread to avoid timeout"""
    sender_email = os.getenv("nagardivya73@gmail.com")
    sender_password = os.getenv("ahxd cufn tmwc yfxu")
    
    if not sender_email or not sender_password:
        print("❌ ERROR: Email credentials not configured in environment variables")
        print("Please set SENDER_EMAIL and SENDER_APP_PASSWORD in Render")
        return
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg["Subject"] = f"Resume Studio - {'Account Verification' if purpose == 'verification' else 'Password Reset'} OTP"
    msg["From"] = f"Resume Studio <{sender_email}>"
    msg["To"] = to_email
    
    # Plain text version (fallback)
    text_content = f"""
    Resume Studio - {'Account Verification' if purpose == 'verification' else 'Password Reset'}
    
    Your OTP is: {otp}
    
    This code is valid for 10 minutes.
    
    If you didn't request this, please ignore this email.
    
    © 2026 Resume Studio
    """
    
    # HTML version
    html_content = get_otp_email_template(otp, purpose)
    
    # Attach both versions
    part1 = MIMEText(text_content, 'plain')
    part2 = MIMEText(html_content, 'html')
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        print(f"📧 Attempting to send email to {to_email}...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"✅ Email sent successfully to {to_email}")
    except smtplib.SMTPAuthenticationError:
        print(f"❌ Email authentication failed. Check SENDER_EMAIL and SENDER_APP_PASSWORD")
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")
    except Exception as e:
        print(f"❌ Email send failed: {e}")


def send_email(to_email, otp, purpose="verification"):
    """Wrapper to send email in background thread"""
    thread = Thread(target=send_email_async, args=(to_email, otp, purpose))
    thread.daemon = True
    thread.start()
    print(f"🚀 Email queued for {to_email}")


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

            # Set session
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