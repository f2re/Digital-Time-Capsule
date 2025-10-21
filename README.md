# 🕰️ Digital Time Capsule Bot

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21.0+-blue.svg)](https://python-telegram-bot.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg?logo=telegram)](https://t.me/your_bot_username)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg?logo=docker)](Dockerfile)
[![Stars](https://img.shields.io/badge/Telegram-Stars-yellow.svg)](https://core.telegram.org/bots/payments-stars)

A powerful Telegram bot that allows users to create encrypted time capsules and send messages to the future! Features include multi-language support (Russian/English), Telegram Stars payment integration, S3 cloud storage, and scheduled delivery.

## ✨ Features

### Core Functionality
- 📅 **Time Capsule Creation** - Send messages to your future self, friends, or groups
- 🔐 **End-to-End Encryption** - All content is encrypted using Fernet (symmetric encryption)
- ☁️ **Cloud Storage** - Secure file storage in Yandex Object Storage (S3-compatible)
- ⏰ **Scheduled Delivery** - Automatic delivery at specified date/time using APScheduler
- 🌍 **Multi-language** - Full support for Russian and English

### Content Types
- 📝 Text messages
- 🖼️ Photos
- 🎥 Videos
- 📎 Documents
- 🎤 Voice messages
- 🎵 Audio files

### Payment & Subscriptions
- ⭐ **Telegram Stars Integration** - Native in-app payments
- 💳 **Flexible Plans**:
  - **Free Tier**: 3 capsules, 10 MB storage, up to 1 year delivery
  - **Premium Single**: 20 Stars for one premium capsule
  - **Premium Yearly**: 40 Stars for unlimited capsules, 1 GB storage, up to 25 years delivery
- 💰 **Payment Support** - Built-in `/paysupport` command with refund policy

### Technical Features
- 🗄️ **Dual Database Support** - SQLite (dev) and PostgreSQL (production)
- 🐳 **Docker Ready** - Containerized deployment with docker-compose
- 📊 **Conversation Management** - State-based conversation flow
- 🔄 **Auto-scheduling** - Background task scheduler for capsule delivery
- 📈 **Usage Tracking** - Storage and capsule count monitoring

## 📋 Table of Contents

- [Installation](#-installation)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [Usage](#-usage)
- [Payment Setup](#-payment-setup)
- [Deployment](#-deployment)
- [Commands](#-commands)
- [Development](#-development)
- [License](#-license)

## 🚀 Installation

### Prerequisites

- Python 3.11 or higher
- PostgreSQL (for production) or SQLite (for development)
- Yandex Cloud account (for S3 storage)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/time-capsule-bot.git
cd time-capsule-bot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
# For SQLite (development)
python init_db_sqlite.py

# For PostgreSQL (production)
python init_db_postgresql.py
```

6. **Run the bot**
```bash
python main.py
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here

# Database
DATABASE_URL=sqlite:///time_capsule.db  # or postgresql://user:pass@host:port/dbname

# Encryption
MASTER_KEY=your_fernet_key_here  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Yandex Object Storage (S3)
YANDEX_ACCESS_KEY=your_yandex_access_key
YANDEX_SECRET_KEY=your_yandex_secret_key
YANDEX_BUCKET_NAME=your_bucket_name
YANDEX_REGION=ru-central1

# Payment (Optional - for traditional payment providers)
PAYMENT_PROVIDER_TOKEN=  # Leave empty for Telegram Stars
```

### Yandex Cloud Setup

1. **Create S3 Bucket**:
   - Go to [Yandex Cloud Console](https://console.cloud.yandex.com/)
   - Create a new Object Storage bucket
   - Set bucket permissions appropriately

2. **Generate Access Keys**:
   - Go to "Service Accounts"
   - Create a service account with `storage.editor` role
   - Generate static access keys
   - Add keys to `.env` file

### Database Configuration

**SQLite** (Development):
```python
DATABASE_URL=sqlite:///time_capsule.db
```

**PostgreSQL** (Production):
```python
DATABASE_URL=postgresql://username:password@localhost:5432/timecapsule
```

## 📁 Project Structure

```
time-capsule-bot/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration and constants
│   ├── database.py            # Database models and operations
│   ├── translations.py        # Multi-language support
│   ├── s3_utils.py           # S3 storage utilities
│   ├── scheduler.py          # Task scheduling for delivery
│   └── handlers/
│       ├── __init__.py
│       ├── start.py          # Start command and language selection
│       ├── main_menu.py      # Main menu navigation
│       ├── create_capsule.py # Capsule creation flow
│       ├── view_capsules.py  # View and manage capsules
│       ├── subscription.py   # Payment and subscription management
│       ├── settings.py       # User settings
│       └── help.py           # Help command
├── main.py                    # Application entry point
├── init_db_sqlite.py         # SQLite database initialization
├── init_db_postgresql.py     # PostgreSQL database initialization
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker container configuration
├── docker-compose.yml       # Docker Compose setup
├── .env.example            # Environment variables template
├── .gitignore
└── README.md

```

## 🎯 Usage

### Creating a Time Capsule

1. Start the bot: `/start`
2. Select your language (first time only)
3. Click "✨ Create Capsule"
4. Choose content type (text, photo, video, etc.)
5. Send your content
6. Select delivery time (1 hour to 1 year, or custom date)
7. Choose recipient (yourself, another user, or group)
8. Confirm creation

### Managing Capsules

- **View Capsules**: `/capsules` or "📦 My Capsules"
- **Delete Capsule**: Select capsule → "🗑 Delete"
- **Check Storage**: `/subscription`

### Subscription Management

- **View Plan**: `/subscription`
- **Upgrade**: Select premium option and pay with Telegram Stars
- **Support**: `/paysupport` for payment issues

## 💳 Payment Setup

### Telegram Stars Integration

The bot uses **Telegram Stars** for in-app payments. No external payment provider needed!

**Key Implementation Details**:

```python
# Sending invoice
await context.bot.send_invoice(
    chat_id=chat_id,
    title="Premium Subscription",
    description="1 year of unlimited capsules",
    payload=f"user_{user_id}_{uuid}",
    provider_token="",  # Empty string for Stars!
    currency="XTR",     # Telegram Stars currency
    prices=[LabeledPrice(label="XTR", amount=40)],  # 40 Stars
)
```

**Important Notes**:
- `provider_token` must be an empty string `""`
- `currency` must be `"XTR"`
- `prices` must be a list with exactly one `LabeledPrice`
- Maximum amount: 2500 Stars per transaction
- Bot owner cannot test purchases (use secondary account)

### Testing Payments

1. **Buy Test Stars**:
   - Open Telegram → Settings → Telegram Stars
   - Purchase minimum amount (50-100 Stars)

2. **Test Flow**:
   ```bash
   /start → Subscription → Buy Premium → Pay with Stars
   ```

3. **Verify**:
   - Check payment confirmation message
   - Run `/subscription` to verify premium status
   - Check logs for transaction ID

### Withdrawal

Stars can be withdrawn after 21 days:
1. Convert to Toncoin (TON cryptocurrency)
2. Sell on exchange for fiat currency
3. Or use for Telegram Ads
4. Telegram takes ~30% commission

## 🐳 Deployment

### Docker Deployment

1. **Build and run**:
```bash
docker-compose up -d
```

2. **View logs**:
```bash
docker-compose logs -f bot
```

3. **Stop bot**:
```bash
docker-compose down
```

### Production Deployment

**Using systemd** (Linux):

1. Create service file: `/etc/systemd/system/timecapsule.service`
```ini
[Unit]
Description=Time Capsule Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/opt/timecapsule-bot
Environment=PATH=/opt/timecapsule-bot/venv/bin
ExecStart=/opt/timecapsule-bot/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Enable and start:
```bash
sudo systemctl enable timecapsule
sudo systemctl start timecapsule
sudo systemctl status timecapsule
```

### Environment-Specific Settings

**Development**:
```env
DATABASE_URL=sqlite:///time_capsule.db
LOG_LEVEL=DEBUG
```

**Production**:
```env
DATABASE_URL=postgresql://...
LOG_LEVEL=INFO
```

## 📝 Commands

| Command | Description |
|---------|-------------|
| `/start` | Start bot and show main menu |
| `/create` | Create a new time capsule |
| `/capsules` | View all your capsules |
| `/subscription` | Check subscription status and upgrade |
| `/settings` | Change language and preferences |
| `/help` | Show help information |
| `/paysupport` | Payment support and refund policy |

## 🔧 Development

### Adding New Features

1. **New Handler**:
```python
# src/handlers/my_feature.py
from telegram import Update
from telegram.ext import ContextTypes

async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your code here
    pass
```

2. **Register in main.py**:
```python
from src.handlers.my_feature import my_handler
application.add_handler(CommandHandler('mycommand', my_handler))
```

### Adding Translations

Edit `src/translations.py`:
```python
TRANSLATIONS = {
    'ru': {
        'new_key': 'Русский текст',
    },
    'en': {
        'new_key': 'English text',
    }
}
```

### Database Migrations

**Adding a column**:
```python
from sqlalchemy import Column, String
from src.database import metadata, engine

# Add column to table definition
my_table = Table('my_table', metadata,
    Column('new_column', String(255)),
    extend_existing=True
)

# Apply migration
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE my_table ADD COLUMN new_column VARCHAR(255)"))
    conn.commit()
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# With coverage
pytest --cov=src tests/
```

## 📊 Database Schema

### Users Table
- `id` - Primary key
- `telegram_id` - Unique Telegram user ID
- `username` - Telegram username
- `first_name` - User's first name
- `language_code` - Preferred language (ru/en)
- `subscription_status` - free/premium
- `subscription_expires` - Premium expiration date
- `total_storage_used` - Total bytes used
- `capsule_count` - Number of capsules created

### Capsules Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `capsule_uuid` - Unique capsule identifier
- `content_type` - text/photo/video/etc
- `content_text` - Text content (if applicable)
- `file_key` - Encrypted S3 file key
- `s3_key` - S3 object key
- `file_size` - File size in bytes
- `recipient_type` - self/user/group
- `recipient_id` - Target Telegram ID
- `delivery_time` - Scheduled delivery datetime
- `delivered` - Boolean delivery status
- `message` - Optional message with capsule

### Payments Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `payment_type` - stars/provider
- `amount` - Payment amount
- `currency` - XTR for Stars
- `subscription_type` - single/yearly
- `payment_id` - Transaction ID (for refunds)
- `successful` - Boolean payment status
- `created_at` - Payment timestamp

## 🔒 Security Features

- **Encryption**: All file keys encrypted with Fernet
- **Input Validation**: Strict validation of dates, file sizes, formats
- **Rate Limiting**: Quota checks prevent abuse
- **Secure Storage**: Files stored in private S3 bucket
- **No Data Leakage**: Capsules only deliverable to intended recipients
- **SQL Injection Protection**: SQLAlchemy ORM prevents injection attacks

## 🐛 Troubleshooting

### Common Issues

**1. "Bad Request: currency XTR is invalid"**
```bash
# Solution: Update python-telegram-bot
pip install --upgrade python-telegram-bot
```

**2. Payment not working**
```python
# Check these:
provider_token="" # Must be empty string!
currency="XTR"    # Must be XTR
prices=[LabeledPrice(label="XTR", amount=N)]  # Exactly one item
```

**3. Bot owner can't buy**
```text
This is normal! Telegram prevents bot owners from purchasing.
Test with a second account.
```

**4. Database connection error**
```bash
# Check DATABASE_URL format
# PostgreSQL: postgresql://user:pass@host:port/dbname
# SQLite: sqlite:///path/to/db.db
```

**5. S3 upload fails**
```bash
# Verify credentials and bucket permissions
# Ensure YANDEX_BUCKET_NAME is correct
# Check service account has storage.editor role
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Support

For support, contact:
- Telegram: [@your_support_username](https://t.me/your_support_username)
- Email: support@example.com
- Issues: [GitHub Issues](https://github.com/yourusername/time-capsule-bot/issues)

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [APScheduler](https://apscheduler.readthedocs.io/) - Task scheduling
- [Cryptography](https://cryptography.io/) - Encryption library
- [Yandex Cloud](https://cloud.yandex.com/) - Object Storage

## 📈 Roadmap

- [ ] Group time capsules with multiple recipients
- [ ] Video/audio preview before delivery
- [ ] Recurring capsules (daily/weekly/monthly)
- [ ] Capsule templates
- [ ] Statistics dashboard
- [ ] Web interface for management
- [ ] Export capsule history
- [ ] Multi-file capsules

---

Made with ❤️ by [Your Name](https://github.com/f2re)

⭐ Star this repo if you find it useful!
