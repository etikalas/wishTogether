from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import os

app = Flask(__name__)

# Use DATABASE_URL from environment (Render sets this for PostgreSQL),
# fall back to local SQLite for development.
database_url = os.environ.get('DATABASE_URL', 'sqlite:///cards.db')
# Render provides postgres:// but SQLAlchemy needs postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

db = SQLAlchemy(app)

# ─── Models ───────────────────────────────────────────────────────────────────

class Card(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contribute_slug = db.Column(db.String(12), unique=True, nullable=False)
    view_slug = db.Column(db.String(12), unique=True, nullable=False)
    birthday_person = db.Column(db.String(100), nullable=False)
    birthday_date = db.Column(db.String(20))
    organizer_name = db.Column(db.String(100), nullable=False)
    organizer_message = db.Column(db.Text)
    theme = db.Column(db.String(20), default='sunset')
    is_locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    wishes = db.relationship('Wish', backref='card', lazy=True, order_by='Wish.created_at')

class Wish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.String(36), db.ForeignKey('card.id'), nullable=False)
    contributor_name = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    emoji = db.Column(db.String(10), default='🎂')
    color = db.Column(db.String(20), default='purple')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    return render_template('index.html')

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        birthday_person = request.form.get('birthday_person', '').strip()
        organizer_name = request.form.get('organizer_name', '').strip()
        organizer_message = request.form.get('organizer_message', '').strip()
        birthday_date = request.form.get('birthday_date', '').strip()
        theme = request.form.get('theme', 'sunset')

        if not birthday_person or not organizer_name:
            return render_template('create.html', error="Please fill in all required fields.")

        card = Card(
            id=str(uuid.uuid4()),
            contribute_slug=generate_slug(),
            view_slug=generate_slug(),
            birthday_person=birthday_person,
            organizer_name=organizer_name,
            organizer_message=organizer_message,
            birthday_date=birthday_date,
            theme=theme,
        )
        db.session.add(card)
        db.session.commit()
        return redirect(url_for('manage', contribute_slug=card.contribute_slug))

    return render_template('create.html')

@app.route('/card/<contribute_slug>')
def contribute(contribute_slug):
    card = Card.query.filter_by(contribute_slug=contribute_slug).first_or_404()
    if card.is_locked:
        return render_template('locked.html', card=card)
    return render_template('contribute.html', card=card)

@app.route('/card/<contribute_slug>/add', methods=['POST'])
def add_wish(contribute_slug):
    card = Card.query.filter_by(contribute_slug=contribute_slug).first_or_404()
    if card.is_locked:
        return jsonify({'error': 'Card is locked'}), 403

    name = request.form.get('name', '').strip()
    message = request.form.get('message', '').strip()
    emoji = request.form.get('emoji', '🎂').strip()
    color = request.form.get('color', 'purple').strip()

    if not name or not message:
        return jsonify({'error': 'Name and message are required'}), 400

    wish = Wish(card_id=card.id, contributor_name=name, message=message, emoji=emoji, color=color)
    db.session.add(wish)
    db.session.commit()

    return jsonify({
        'success': True,
        'wish': {
            'id': wish.id,
            'name': wish.contributor_name,
            'message': wish.message,
            'emoji': wish.emoji,
            'color': wish.color,
        }
    })

@app.route('/manage/<contribute_slug>')
def manage(contribute_slug):
    card = Card.query.filter_by(contribute_slug=contribute_slug).first_or_404()
    return render_template('manage.html', card=card)

@app.route('/manage/<contribute_slug>/lock', methods=['POST'])
def lock_card(contribute_slug):
    card = Card.query.filter_by(contribute_slug=contribute_slug).first_or_404()
    card.is_locked = True
    db.session.commit()
    return jsonify({'success': True, 'view_url': url_for('view_card', view_slug=card.view_slug, _external=True)})

@app.route('/view/<view_slug>')
def view_card(view_slug):
    card = Card.query.filter_by(view_slug=view_slug).first_or_404()
    return render_template('view.html', card=card)

@app.route('/api/card/<contribute_slug>/wishes')
def get_wishes(contribute_slug):
    card = Card.query.filter_by(contribute_slug=contribute_slug).first_or_404()
    wishes = [
        {
            'id': w.id,
            'name': w.contributor_name,
            'message': w.message,
            'emoji': w.emoji,
            'color': w.color,
            'created_at': w.created_at.strftime('%b %d, %Y')
        }
        for w in card.wishes
    ]
    return jsonify({'wishes': wishes, 'count': len(wishes)})

# Create tables on startup — works for both gunicorn (Render) and local dev
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
