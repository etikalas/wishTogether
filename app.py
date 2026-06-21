from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime, date
import uuid
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)

database_url = os.environ.get('DATABASE_URL', 'sqlite:///cards.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

db = SQLAlchemy(app)

# ─── Occasion catalogue ───────────────────────────────────────────────────────

OCCASIONS = {
    'birthday': {
        'label': 'Birthday',
        'emoji': '🎂',
        'hero': 'A Celebration for',
        'subtext': 'people love you',
        'prompt': 'Write a birthday wish',
        'emojis': ['🎂','🎉','🌟','🎈','❤️','🌸','🥂','🎊','✨','🦋','🌻','🎁'],
    },
    'anniversary': {
        'label': 'Anniversary',
        'emoji': '💍',
        'hero': 'Celebrating',
        'subtext': 'people are celebrating with you',
        'prompt': 'Write an anniversary wish',
        'emojis': ['💍','❤️','💕','🥂','🌹','✨','💑','🎊','🌸','💐','🕊️','💫'],
    },
    'graduation': {
        'label': 'Graduation',
        'emoji': '🎓',
        'hero': 'Congratulations to',
        'subtext': 'people are proud of you',
        'prompt': 'Write a congratulations message',
        'emojis': ['🎓','🏆','🌟','📚','✨','🎉','💪','🚀','🌈','🥂','🎊','👏'],
    },
    'farewell': {
        'label': 'Farewell',
        'emoji': '👋',
        'hero': 'Farewell & Best Wishes to',
        'subtext': 'people will miss you',
        'prompt': 'Write a farewell message',
        'emojis': ['👋','❤️','✈️','🌟','🤗','💙','🎉','🌈','🚀','🌸','💫','🎁'],
    },
    'retirement': {
        'label': 'Retirement',
        'emoji': '🏆',
        'hero': 'Celebrating the Retirement of',
        'subtext': 'people are celebrating with you',
        'prompt': 'Write a retirement message',
        'emojis': ['🏆','🥂','🌟','⭐','🎉','❤️','🌻','✨','🎊','🏖️','👏','💛'],
    },
    'get_well': {
        'label': 'Get Well Soon',
        'emoji': '💪',
        'hero': 'Sending Love to',
        'subtext': 'people are thinking of you',
        'prompt': 'Write a get well message',
        'emojis': ['💪','❤️','🌸','🌻','✨','💙','🤗','🌈','🍀','💐','🌟','🕊️'],
    },
    'congratulations': {
        'label': 'Congratulations',
        'emoji': '🎊',
        'hero': 'Congratulations to',
        'subtext': 'people are cheering for you',
        'prompt': 'Write a congratulations message',
        'emojis': ['🎊','🏆','🌟','🥂','🎉','💪','✨','👏','🚀','💫','🌈','❤️'],
    },
    'custom': {
        'label': 'Other',
        'emoji': '🎉',
        'hero': 'A Special Message for',
        'subtext': 'people sent their love',
        'prompt': 'Write your message',
        'emojis': ['🎉','❤️','🌟','✨','🥂','🎊','💫','🌸','🎁','🌻','💐','👏'],
    },
}

def get_occasion(card):
    """Return occasion dict for a card, defaulting to birthday."""
    return OCCASIONS.get(getattr(card, 'occasion_type', None) or 'birthday', OCCASIONS['birthday'])

# ─── Models ───────────────────────────────────────────────────────────────────

class Card(db.Model):
    id               = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contribute_slug  = db.Column(db.String(12), unique=True, nullable=False)
    view_slug        = db.Column(db.String(12), unique=True, nullable=False)
    honoree_name     = db.Column(db.String(100), nullable=False)   # "who is this for"
    occasion_type    = db.Column(db.String(30), default='birthday')
    occasion_date    = db.Column(db.String(20))
    organizer_name   = db.Column(db.String(100), nullable=False)
    organizer_message= db.Column(db.Text)
    theme            = db.Column(db.String(20), default='sunset')
    is_locked        = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    wishes           = db.relationship('Wish', backref='card', lazy=True, order_by='Wish.created_at')

class Wish(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    card_id          = db.Column(db.String(36), db.ForeignKey('card.id'), nullable=False)
    contributor_name = db.Column(db.String(100), nullable=False)
    message          = db.Column(db.Text, nullable=False)
    emoji            = db.Column(db.String(10), default='🎉')
    color            = db.Column(db.String(20), default='purple')
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

class Birthday(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    person_name     = db.Column(db.String(100), nullable=False)
    birth_date      = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD or MM-DD
    reminder_email  = db.Column(db.String(200), nullable=False)
    your_name       = db.Column(db.String(100), nullable=False)
    notes           = db.Column(db.Text)                          # optional notes / relationship
    reminded_7      = db.Column(db.Integer, default=0)            # year last reminded at 7 days
    reminded_2      = db.Column(db.Integer, default=0)
    reminded_1      = db.Column(db.Integer, default=0)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

def generate_slug(length=8):
    import random, string
    chars = string.ascii_letters + string.digits
    while True:
        slug = ''.join(random.choices(chars, k=length))
        if not Card.query.filter(
            (Card.contribute_slug == slug) | (Card.view_slug == slug)
        ).first():
            return slug

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html', occasions=OCCASIONS)

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        honoree_name      = request.form.get('honoree_name', '').strip()
        organizer_name    = request.form.get('organizer_name', '').strip()
        organizer_message = request.form.get('organizer_message', '').strip()
        occasion_date     = request.form.get('occasion_date', '').strip()
        occasion_type     = request.form.get('occasion_type', 'birthday')
        theme             = request.form.get('theme', 'sunset')

        if not honoree_name or not organizer_name:
            return render_template('create.html', error="Please fill in all required fields.",
                                   occasions=OCCASIONS)

        card = Card(
            id=str(uuid.uuid4()),
            contribute_slug=generate_slug(),
            view_slug=generate_slug(),
            honoree_name=honoree_name,
            occasion_type=occasion_type,
            organizer_name=organizer_name,
            organizer_message=organizer_message,
            occasion_date=occasion_date,
            theme=theme,
        )
        db.session.add(card)
        db.session.commit()
        return redirect(url_for('manage', contribute_slug=card.contribute_slug))

    return render_template('create.html', occasions=OCCASIONS)

@app.route('/card/<contribute_slug>')
def contribute(contribute_slug):
    card = Card.query.filter_by(contribute_slug=contribute_slug).first_or_404()
    if card.is_locked:
        return render_template('locked.html', card=card, occasion=get_occasion(card))
    return render_template('contribute.html', card=card, occasion=get_occasion(card))

@app.route('/card/<contribute_slug>/add', methods=['POST'])
def add_wish(contribute_slug):
    card = Card.query.filter_by(contribute_slug=contribute_slug).first_or_404()
    if card.is_locked:
        return jsonify({'error': 'Card is locked'}), 403

    name    = request.form.get('name', '').strip()
    message = request.form.get('message', '').strip()
    emoji   = request.form.get('emoji', '🎉').strip()
    color   = request.form.get('color', 'purple').strip()

    if not name or not message:
        return jsonify({'error': 'Name and message are required'}), 400

    wish = Wish(card_id=card.id, contributor_name=name,
                message=message, emoji=emoji, color=color)
    db.session.add(wish)
    db.session.commit()

    return jsonify({'success': True, 'wish': {
        'id': wish.id, 'name': wish.contributor_name,
        'message': wish.message, 'emoji': wish.emoji, 'color': wish.color,
    }})

@app.route('/manage/<contribute_slug>')
def manage(contribute_slug):
    card = Card.query.filter_by(contribute_slug=contribute_slug).first_or_404()
    return render_template('manage.html', card=card, occasion=get_occasion(card))

@app.route('/manage/<contribute_slug>/lock', methods=['POST'])
def lock_card(contribute_slug):
    card = Card.query.filter_by(contribute_slug=contribute_slug).first_or_404()
    card.is_locked = True
    db.session.commit()
    return jsonify({'success': True,
                    'view_url': url_for('view_card', view_slug=card.view_slug, _external=True)})

@app.route('/view/<view_slug>')
def view_card(view_slug):
    card = Card.query.filter_by(view_slug=view_slug).first_or_404()
    return render_template('view.html', card=card, occasion=get_occasion(card))

@app.route('/api/card/<contribute_slug>/wishes')
def get_wishes(contribute_slug):
    card = Card.query.filter_by(contribute_slug=contribute_slug).first_or_404()
    wishes = [{
        'id': w.id, 'name': w.contributor_name,
        'message': w.message, 'emoji': w.emoji, 'color': w.color,
        'created_at': w.created_at.strftime('%b %d, %Y')
    } for w in card.wishes]
    return jsonify({'wishes': wishes, 'count': len(wishes)})

# ─── Birthday registry ────────────────────────────────────────────────────────

def days_until_birthday(birth_date_str):
    """Return (days_until, next_birthday_date) for a birthday string YYYY-MM-DD or MM-DD."""
    today = date.today()
    try:
        parts = birth_date_str.split('-')
        if len(parts) == 3:
            month, day = int(parts[1]), int(parts[2])
        else:
            month, day = int(parts[0]), int(parts[1])
        next_bday = date(today.year, month, day)
        if next_bday < today:
            next_bday = date(today.year + 1, month, day)
        return (next_bday - today).days, next_bday
    except Exception:
        return None, None

def send_reminder_email(to_email, your_name, person_name, days_away, create_url):
    smtp_user     = os.environ.get('SMTP_EMAIL', '')
    smtp_password = os.environ.get('SMTP_APP_PASSWORD', '')
    if not smtp_user or not smtp_password:
        return False

    if days_away == 7:
        subject = f"🎂 {person_name}'s birthday is in 1 week!"
        urgency = "You have a full week — perfect time to start collecting wishes from everyone."
        action  = "Start collecting wishes now"
    elif days_away == 2:
        subject = f"⏰ {person_name}'s birthday is in 2 days!"
        urgency = "2 days left! Start the card now so friends can add their wishes in time."
        action  = "Create the card — 2 days left!"
    else:
        subject = f"🚨 {person_name}'s birthday is TOMORROW!"
        urgency = "Last chance! Create the card today and share it with close friends."
        action  = "Create today's card"

    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
      <div style="background:linear-gradient(135deg,#f093fb,#f5576c,#fda085);padding:2.5rem;text-align:center;">
        <div style="font-size:3.5rem;margin-bottom:0.5rem;">🎂</div>
        <h1 style="color:white;font-size:1.6rem;margin:0;font-weight:800;">{person_name}'s Birthday</h1>
        <p style="color:rgba(255,255,255,0.9);margin:0.5rem 0 0;font-size:1rem;">in <strong>{days_away} day{'s' if days_away > 1 else ''}</strong></p>
      </div>
      <div style="padding:2rem;">
        <p style="color:#374151;font-size:1rem;line-height:1.6;">Hi <strong>{your_name}</strong>,</p>
        <p style="color:#374151;font-size:1rem;line-height:1.6;">{urgency}</p>
        <p style="color:#374151;font-size:1rem;line-height:1.6;">
          Create a group card on <strong>WishTogether</strong> and share the link — 
          friends and family can each add their own personal message. 
          <strong>{person_name}</strong> gets a beautiful card they can keep forever. 💌
        </p>
        <div style="text-align:center;margin:2rem 0;">
          <a href="{create_url}"
             style="background:linear-gradient(135deg,#f093fb,#7c3aed);color:white;text-decoration:none;
                    padding:14px 32px;border-radius:12px;font-weight:700;font-size:1rem;display:inline-block;">
            {action} →
          </a>
        </div>
        <p style="color:#9ca3af;font-size:0.8rem;text-align:center;">
          This reminder was set up on WishTogether · 
          <a href="{request.host_url}birthdays" style="color:#7c3aed;">Manage birthdays</a>
        </p>
      </div>
    </div>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = f"WishTogether 🎂 <{smtp_user}>"
    msg['To']      = to_email
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

@app.route('/birthdays')
def birthdays():
    all_bdays = Birthday.query.order_by(Birthday.person_name).all()
    upcoming  = []
    for b in all_bdays:
        days, next_date = days_until_birthday(b.birth_date)
        if days is not None:
            upcoming.append({'birthday': b, 'days': days, 'next_date': next_date})
    upcoming.sort(key=lambda x: x['days'])
    return render_template('birthdays.html', upcoming=upcoming)

@app.route('/birthdays/add', methods=['GET', 'POST'])
def add_birthday():
    if request.method == 'POST':
        person_name    = request.form.get('person_name', '').strip()
        birth_date     = request.form.get('birth_date', '').strip()
        reminder_email = request.form.get('reminder_email', '').strip()
        your_name      = request.form.get('your_name', '').strip()
        notes          = request.form.get('notes', '').strip()

        if not person_name or not birth_date or not reminder_email or not your_name:
            return render_template('birthday_add.html',
                                   error="Please fill in all required fields.")

        b = Birthday(person_name=person_name, birth_date=birth_date,
                     reminder_email=reminder_email, your_name=your_name, notes=notes)
        db.session.add(b)
        db.session.commit()
        return redirect(url_for('birthdays'))

    return render_template('birthday_add.html')

@app.route('/birthdays/<int:bid>/delete', methods=['POST'])
def delete_birthday(bid):
    b = Birthday.query.get_or_404(bid)
    db.session.delete(b)
    db.session.commit()
    return redirect(url_for('birthdays'))

@app.route('/api/send-reminders')
def send_reminders():
    """Called daily by cron-job.org. Protected by CRON_SECRET env var."""
    secret = os.environ.get('CRON_SECRET', 'wishtogether-cron')
    if request.args.get('key') != secret:
        return jsonify({'error': 'Unauthorized'}), 401

    today     = date.today()
    sent      = []
    skipped   = []

    for b in Birthday.query.all():
        days, _ = days_until_birthday(b.birth_date)
        if days is None:
            continue

        year = today.year
        create_url = request.host_url + 'create'

        if days == 7 and b.reminded_7 != year:
            ok = send_reminder_email(b.reminder_email, b.your_name, b.person_name, 7, create_url)
            if ok:
                b.reminded_7 = year
                sent.append(f"{b.person_name} (7 days) → {b.reminder_email}")
        elif days == 2 and b.reminded_2 != year:
            ok = send_reminder_email(b.reminder_email, b.your_name, b.person_name, 2, create_url)
            if ok:
                b.reminded_2 = year
                sent.append(f"{b.person_name} (2 days) → {b.reminder_email}")
        elif days == 1 and b.reminded_1 != year:
            ok = send_reminder_email(b.reminder_email, b.your_name, b.person_name, 1, create_url)
            if ok:
                b.reminded_1 = year
                sent.append(f"{b.person_name} (1 day) → {b.reminder_email}")
        else:
            skipped.append(f"{b.person_name} ({days} days away)")

    db.session.commit()
    return jsonify({'sent': sent, 'skipped': skipped, 'date': str(today)})

# ─── Startup ──────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    # Migrate old cards: add new columns if they don't exist yet
    is_pg = database_url.startswith('postgresql')
    with db.engine.connect() as conn:
        for col, typedef in [
            ('occasion_type', "VARCHAR(30) DEFAULT 'birthday'"),
            ('occasion_date', 'VARCHAR(20)'),
            ('honoree_name',  "VARCHAR(100) DEFAULT ''"),
        ]:
            try:
                if is_pg:
                    conn.execute(text(f"ALTER TABLE card ADD COLUMN IF NOT EXISTS {col} {typedef}"))
                else:
                    conn.execute(text(f"ALTER TABLE card ADD COLUMN {col} {typedef}"))
                conn.commit()
            except Exception:
                conn.rollback()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
