# 🎂 WishTogether — Group Birthday Card App

A beautiful web app to collect heartfelt birthday wishes from everyone and present them as a single, permanent group card that the birthday person can keep forever.

## Features

- 🎨 **5 beautiful themes** — Sunset, Ocean, Forest, Golden, Midnight
- 💌 **Group card** — everyone adds their own message with emoji and color
- 🔗 **Shareable link** — send one link to all contributors
- 🔒 **Card lock** — when ready, lock and send the view link to the birthday person
- 📥 **Download card** — save as a PNG image to keep forever
- 🎉 **Confetti** — animated confetti celebration when the card is opened
- ♾️ **Permanent** — cards live in a local SQLite database forever

## How to Run

```bash
cd birthday-card-app

# Install dependencies (only needed once)
pip3 install -r requirements.txt

# Start the app
python3 app.py
```

Then open **http://localhost:5001** in your browser.

## App Flow

| Role | Action | URL |
|------|---------|-----|
| Organizer | Create the card | `/create` |
| Organizer | Manage & share link | `/manage/<slug>` |
| Contributors | Add their wish | `/card/<slug>` |
| Birthday Person | View the card 🎉 | `/view/<slug>` |

## Tech Stack

- **Backend:** Python 3 + Flask + SQLite (via SQLAlchemy)
- **Frontend:** Tailwind CSS (CDN), vanilla JS
- **Extras:** canvas-confetti, html2canvas (card download)
