# 🕰 Digital Time Capsule - Telegram Bot

A fully-featured Telegram bot that allows users to create "time capsules" - messages, photos, videos, or documents that will be delivered in the future to themselves, friends, or groups.

## 🌟 Features

### Core Functionality
- **Multiple Content Types**: Text, photos, videos, documents, voice messages
- **Flexible Scheduling**: From 1 hour to 25 years in the future
- **Multiple Recipients**: Send to yourself, other users, or groups
- **Secure Storage**: End-to-end encryption with Yandex S3 cloud storage
- **Bilingual**: Full Russian and English support

### Subscription Tiers

#### Free Tier
- ✅ Up to 3 capsules
- ✅ 10 MB total storage
- ✅ Maximum 1 year delivery time
- ✅ All content types supported

#### Premium Tier
- ⭐ Unlimited capsules
- ⭐ 1 GB total storage
- ⭐ Up to 25 years delivery time
- ⭐ Priority support
- ⭐ Pricing: 200₽ single / 400₽ yearly

## 📋 Requirements

- Python 3.11+
- PostgreSQL 16+ (or SQLite for development)
- Yandex Object Storage account
- Telegram Bot Token

## 🚀 Quick Start

### 1. Clone the Repository

```
git clone <repository-url>
cd digital-time-capsule
```

### 2. Set Up Environment

```
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 3. Install Dependencies

```
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 4. Initialize Database

For SQLite (development):
```
python init_db_sqlite.py
```

For PostgreSQL (production):
```
python init_db_postgresql.py
```

### 5. Run the Bot

```
python bot.py
```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### Manual Docker Build

```
# Build image
docker build -t timecapsule-bot .

# Run container
docker run -d \
  --name timecapsule-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  timecapsule-bot
```

## ⚙️ Configuration

### Generate Master Encryption Key

```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Yandex S3 Setup

1. Create a Yandex Cloud account
2. Create an Object Storage bucket
3. Generate service account keys
4. Add credentials to `.env`

### Telegram Bot Setup

1. Talk to [@BotFather](https://t.me/botfather)
2. Create new bot with `/newbot`
3. Copy token to `.env`
4. Enable inline mode (optional)
5. Set bot commands:

```
start - Start the bot
create - Create a new time capsule
capsules - View my capsules
subscription - Manage subscription
help - Get help
```

## 🗄️ Database Schema

### Users Table
- `id`: Primary key
- `telegram_id`: Telegram user ID (unique)
- `username`: Telegram username
- `subscription_status`: 'free' or 'premium'
- `subscription_expires`: Premium expiration date
- `total_storage_used`: Bytes used
- `capsule_count`: Number of capsules

### Capsules Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `capsule_uuid`: Unique identifier
- `content_type`: Type of content
- `content_text`: Text content (if applicable)
- `file_key`: Encrypted file encryption key
- `s3_key`: S3 object key
- `file_size`: Size in bytes
- `recipient_type`: 'self', 'user', or 'group'
- `recipient_id`: Telegram ID of recipient
- `delivery_time`: When to deliver
- `delivered`: Delivery status

### Payments Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `payment_type`: 'stars' or 'provider'
- `amount`: Payment amount
- `subscription_type`: 'single' or 'yearly'
- `successful`: Payment status

## 🔒 Security Features

1. **Encryption**: All files encrypted with Fernet (symmetric encryption)
2. **Key Management**: File keys encrypted with master key
3. **Secure Storage**: Files stored in encrypted form on S3
4. **No Plain Text**: Content never stored unencrypted
5. **Automatic Cleanup**: Delivered capsules can be auto-deleted

## 📱 Bot Commands

- `/start` - Start the bot and show main menu
- `/create` - Create a new time capsule
- `/capsules` - View your pending capsules
- `/subscription` - View and upgrade subscription
- `/help` - Show help information

## 🛠️ Development

### Project Structure

```
digital-time-capsule/
├── bot.py                    # Main bot application
├── init_db_sqlite.py         # SQLite initialization
├── init_db_postgresql.py     # PostgreSQL initialization
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Docker Compose configuration
├── README.md                 # This file
└── data/                     # Local data directory
```

### Adding New Features

1. Add handler function in `bot.py`
2. Register handler in `main()`
3. Update translations in `TRANSLATIONS` dict
4. Test with both languages

## 🔧 Maintenance

### Database Backup (PostgreSQL)

```
# Backup
docker exec timecapsule_postgres pg_dump -U timecapsule_user time_capsule > backup.sql

# Restore
docker exec -i timecapsule_postgres psql -U timecapsule_user time_capsule < backup.sql
```

### View Logs

```
# Docker Compose
docker-compose logs -f bot

# Docker
docker logs -f timecapsule-bot
```

### Update Bot

```
git pull
docker-compose down
docker-compose up -d --build
```

## 📊 Monitoring

The bot logs all important events:
- User registrations
- Capsule creations
- Delivery attempts
- Errors and exceptions

Monitor logs for issues and performance.

## 🐛 Troubleshooting

### Bot Not Starting
- Check `.env` file has all required variables
- Verify BOT_TOKEN is correct
- Ensure database is accessible

### Capsules Not Delivering
- Check scheduler is running
- Verify system time is correct
- Check bot has permission to message recipient

### S3 Upload Errors
- Verify Yandex credentials
- Check bucket permissions
- Ensure bucket exists

## 📄 License

This project is provided as-is for educational and commercial use.

## 🤝 Support

For issues and feature requests, please contact the developer or open an issue.

## 🎯 Roadmap

- [ ] Group capsules (collaborative)
- [ ] Recurring capsules
- [ ] Capsule reactions
- [ ] Statistics dashboard
- [ ] Mobile app integration
- [ ] More payment methods
- [ ] Capsule templates

## 📞 Contact

- Telegram: @your_username
- Email: your_email@example.com

---

Made with ❤️ for preserving memories across time