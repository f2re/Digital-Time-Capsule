# 🕰 Digital Time Capsule - Telegram Bot

**Send messages to the future. Securely. Encrypted. Reliable.**

A Telegram bot that allows users to create time capsules containing text, photos, videos, documents, and voice messages, which are delivered at a specified future date. Built with military-grade encryption and cloud storage.

[![Python](https://img.shields.io/ot API](https://img.shields.io/badge/Telegram%20Bot%20API-Latest.shields.io/badge/License-MIT-green 📋 Table of Contents

- [Features](#-features)
- [Payment System](#-payment-system)
- [Subscription Plans](#-subscription-plans)
- [Technology Stack](#-technology-stack)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Database Setup](#-database-setup)
- [Running the Bot](#-running-the-bot)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Security](#-security)
- [Migration System](#-migration-system)
- [Commands](#-bot-commands)
- [Contributing](#-contributing)
- [License](#-license)

***

## ✨ Features

### Core Functionality
- 📝 **Multiple Content Types**: Text, photos, videos, documents, and voice messages
- ⏰ **Flexible Delivery Times**: From 1 hour to 25 years (premium)
- 🎯 **Delivery Options**: To yourself, specific users, or groups
- 🔐 **Military-Grade Encryption**: Fernet (symmetric encryption) for all media files
- ☁️ **Cloud Storage**: Yandex S3-compatible storage for media files
- 📱 **Bilingual Interface**: Russian and English support
- 🔄 **Automatic Delivery**: Background scheduler checks and delivers capsules on time

### Payment & Monetization
- 💎 **Telegram Stars Integration**: Native Telegram payment system
- 📦 **Capsule-Based System**: Pay-per-capsule model with progressive discounts
- 🎁 **Subscription Plans**: Monthly and yearly premium subscriptions with included capsules
- 💰 **Flexible Pricing**: From single capsules to bulk packs (up to 45% discount)

### Advanced Features
- 🗄️ **Automatic Database Migrations**: Version-controlled schema updates
- 📊 **Usage Statistics**: Track capsules, storage, and subscription status
- 🛡️ **Quota Management**: Storage and capsule limits based on tier
- 🔍 **Capsule Management**: View, delete, and track all your time capsules
- 📈 **Transaction History**: Complete payment and capsule purchase tracking

***

## 💰 Payment System

### **Capsule Balance Model**

The bot uses a **capsule balance system** where users purchase capsules that are deducted when creating time capsules. This replaces the old limit-based system.

#### **How It Works:**
1. Users start with **0 capsules** (new users may receive 3 starter capsules via migration)
2. Each capsule creation **deducts 1 capsule** from balance
3. Users can purchase:
   - **Single capsules** (4 stars each)
   - **Capsule packs** with discounts
   - **Premium subscriptions** with included capsules

### **Pricing Structure**

#### **💎 Single Capsule**
- **Price**: 4 Telegram Stars (≈₽6.8)
- **Content**: Any type (text, photo, video, document, voice)
- **Valid for**: One-time use

#### **📦 Capsule Packs** (Progressive Discounts)

| Pack | Capsules | Price (Stars) | Price (₽) | Discount |
|------|----------|---------------|-----------|----------|
| Pack 3 | 3 capsules | 10 ⭐ | ₽17 | **17%** |
| Pack 10 | 10 capsules | 30 ⭐ | ₽51 | **25%** |
| Pack 25 | 25 capsules | 65 ⭐ | ₽110.5 | **35%** |
| Pack 100 | 100 capsules | 220 ⭐ | ₽374 | **45%** |

### **Cost Analysis**

```
Single Capsule:     ₽6.8  per capsule (4 stars)
Pack 3 (17% off):   ₽5.67 per capsule (3.3 stars)
Pack 10 (25% off):  ₽5.1  per capsule (3 stars)
Pack 25 (35% off):  ₽4.42 per capsule (2.6 stars)
Pack 100 (45% off): ₽3.74 per capsule (2.2 stars)
```

**Best Value**: Pack 100 saves **45%** compared to single purchases!

***

## 📊 Subscription Plans

### **FREE Plan**
- ❌ **No included capsules** (must purchase separately)
- 💾 **Storage**: 100 MB
- ⏰ **Max delivery time**: 1 year
- 📦 **Capsule types**: All types supported

### **💎 PREMIUM Month**
- **Price**: 60 Stars (₽102)
- ✅ **20 included capsules** per month
- 💾 **Storage**: 500 MB
- ⏰ **Max delivery time**: 25 years
- 🎯 **Priority support**
- 📈 **Cost per capsule**: ₽5.1 (if all used)

### **💎 PREMIUM Year**
- **Price**: 600 Stars (₽1,020)
- ✅ **240 included capsules** per year (20/month)
- 💾 **Storage**: 500 MB
- ⏰ **Max delivery time**: 25 years
- 🎯 **Priority support**
- 💰 **Save 17%** vs monthly plan
- 📈 **Cost per capsule**: ₽4.25 (if all used)

### **Comparison Table**

| Feature | FREE | Premium Month | Premium Year |
|---------|------|---------------|--------------|
| **Price** | ₽0 | ₽102/month | ₽1,020/year |
| **Included Capsules** | 0 | 20/month | 240/year |
| **Storage** | 100 MB | 500 MB | 500 MB |
| **Max Delivery** | 1 year | 25 years | 25 years |
| **Cost per Capsule** | ₽6.8 | ₽5.1 | ₽4.25 |
| **Best For** | Trying out | Regular users | Power users |

***

## 🛠 Technology Stack

### **Backend**
- **Python 3.9+**: Core programming language
- **python-telegram-bot 20.x**: Telegram Bot API wrapper
- **SQLAlchemy 2.x**: ORM for database operations
- **APScheduler**: Background task scheduling for capsule delivery
- **Cryptography (Fernet)**: Symmetric encryption for file security

### **Storage & Database**
- **PostgreSQL / SQLite**: Relational database (configurable)
- **Yandex Object Storage (S3)**: Cloud storage for media files
- **Boto3**: S3-compatible API client

### **Additional Libraries**
- **python-dateutil**: Date/time parsing
- **python-dotenv**: Environment variable management

***

## 📥 Installation

### **Prerequisites**
- Python 3.9 or higher
- PostgreSQL or SQLite
- Yandex Object Storage account (S3-compatible)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### **Step 1: Clone Repository**

```bash
git clone https://github.com/f2re/Digital-Time-Capsule.git
cd Digital-Time-Capsule
```

### **Step 2: Create Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### **Step 3: Install Dependencies**

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```txt
python-telegram-bot[job-queue]==20.7
sqlalchemy==2.0.23
cryptography==41.0.7
boto3==1.29.7
apscheduler==3.10.4
python-dateutil==2.8.2
python-dotenv==1.0.0
psycopg2-binary==2.9.9  # For PostgreSQL
```

***

## ⚙️ Configuration

### **Step 1: Create `.env` File**

Create a `.env` file in the project root:

```bash
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token_here

# Database (choose one)
DATABASE_URL=sqlite:///time_capsule.db
# DATABASE_URL=postgresql://user:password@localhost:5432/time_capsule

# Encryption
MASTER_KEY=your_generated_master_key_here

# Yandex Object Storage (S3-compatible)
YANDEX_ACCESS_KEY=your_yandex_access_key
YANDEX_SECRET_KEY=your_yandex_secret_key
YANDEX_BUCKET_NAME=your_bucket_name
YANDEX_REGION=ru-central1

# Payment (optional - for traditional payments)
PAYMENT_PROVIDER_TOKEN=your_payment_provider_token
```

### **Step 2: Generate Master Key**

Run the bot once to auto-generate a master key, or generate manually:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Add the generated key to `.env`:
```
MASTER_KEY=your_generated_key_here
```

### **Step 3: Yandex Object Storage Setup**

1. Create a Yandex Cloud account
2. Create an S3-compatible bucket
3. Generate access keys
4. Add credentials to `.env`

**Bucket Configuration:**
- **Name**: Choose unique name
- **Region**: `ru-central1`
- **Access**: Private
- **Versioning**: Disabled
- **Encryption**: Optional (bot uses Fernet encryption)

***

## 🗄️ Database Setup

### **Option 1: SQLite (Development)**

```bash
python init_db_sqlite.py
```

**Advantages:**
- ✅ No installation required
- ✅ Single file database
- ✅ Perfect for testing

**Disadvantages:**
- ⚠️ Not recommended for production
- ⚠️ Limited concurrent writes

### **Option 2: PostgreSQL (Production)**

#### **Install PostgreSQL**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql
brew services start postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/
```

#### **Update `.env`**

```bash
DATABASE_URL=postgresql://timecapsule_user:your_secure_password@localhost:5432/time_capsule
```

#### **Initialize Database**

```bash
python init_db_postgresql.py
```

### **Database Schema**

The bot automatically creates these tables:

| Table | Description |
|-------|-------------|
| **users** | User profiles, subscription status, capsule balance |
| **capsules** | Time capsule data and metadata |
| **payments** | Traditional payment records (legacy) |
| **transactions** | Capsule purchase transactions (Stars) |
| **migration_history** | Database migration tracking |

**Key Fields:**
- `users.capsule_balance`: Current available capsules (NEW)
- `users.subscription_status`: 'free' or 'premium'
- `users.subscription_expires`: Premium expiration date
- `users.total_storage_used`: Storage usage in bytes
- `transactions.transaction_type`: 'single', 'pack_3', 'premium_month', etc.

***

## 🚀 Running the Bot

### **Development Mode**

```bash
python main.py
```

### **Production Mode (with systemd)**

Create `/etc/systemd/system/timecapsule-bot.service`:

```ini
[Unit]
Description=Digital Time Capsule Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/Digital-Time-Capsule
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start Service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable timecapsule-bot
sudo systemctl start timecapsule-bot
sudo systemctl status timecapsule-bot
```

### **View Logs**

```bash
# Real-time logs
sudo journalctl -u timecapsule-bot -f

# Last 100 lines
sudo journalctl -u timecapsule-bot -n 100
```

***

## 📁 Project Structure

```
Digital-Time-Capsule/
├── main.py                      # Bot entry point
├── requirements.txt             # Python dependencies
├── init_db_sqlite.py           # SQLite database initialization
├── init_db_postgresql.py       # PostgreSQL database initialization
├── migrate.py                  # Manual migration CLI tool
├── .env                        # Environment variables (create this)
├── assets/
│   └── welcome.png             # Welcome screen image
├── src/
│   ├── config.py               # Configuration and pricing constants
│   ├── database.py             # Database models and functions
│   ├── scheduler.py            # Capsule delivery scheduler
│   ├── s3_utils.py             # S3 storage utilities
│   ├── translations.py         # Multilingual support (RU/EN)
│   ├── handlers/
│   │   ├── start.py            # /start command and language selection
│   │   ├── main_menu.py        # Main menu navigation
│   │   ├── create_capsule.py   # Capsule creation flow
│   │   ├── view_capsules.py    # View user capsules
│   │   ├── delete_capsule.py   # Delete capsules
│   │   ├── subscription.py     # Payment and subscription handling
│   │   ├── settings.py         # User settings
│   │   └── help.py             # Help command
│   └── migrations/
│       ├── __init__.py
│       ├── migration_manager.py           # Automatic migration system
│       └── versions/
│           ├── 001_add_capsule_balance.py    # Add capsule balance field
│           └── 002_add_transactions_table.py # Add transactions table
└── time_capsule.db             # SQLite database (auto-generated)
```

***

## 🔄 How It Works

### **1. User Registration**
```
User → /start → Select Language → Show Main Menu
                     ↓
              Create User Record (capsule_balance = 0)
```

### **2. Capsule Purchase Flow**
```
User → Subscription Menu → Select Pack → Telegram Invoice
                                             ↓
                                    Pay with Stars
                                             ↓
                              Pre-checkout Validation
                                             ↓
                                Payment Successful
                                             ↓
                          Add Capsules to Balance
                                             ↓
                          Record Transaction
```

### **3. Capsule Creation Flow**
```
User → Create Capsule → Check Balance (>0?)
                              ↓ YES
                    Select Content Type
                              ↓
                      Upload Content
                              ↓
                      Select Delivery Time
                              ↓
                    Select Recipient
                              ↓
                      Confirm Capsule
                              ↓
                    Encrypt File (if media)
                              ↓
                    Upload to S3
                              ↓
                Store in Database
                              ↓
        Deduct 1 from Capsule Balance
                              ↓
            Schedule Delivery Job
```

### **4. Capsule Delivery**
```
Scheduler (every 60s) → Check Pending Capsules
                              ↓
                   Find capsules where:
              delivery_time <= now AND delivered = false
                              ↓
                      For each capsule:
                              ↓
                  Download from S3
                              ↓
                    Decrypt File
                              ↓
              Send to Recipient (user/group)
                              ↓
            Mark as delivered in DB
                              ↓
            Delete from S3 (optional)
```

***

## 🔐 Security

### **Encryption Strategy**

#### **File Encryption (Fernet)**
- **Algorithm**: AES-128-CBC with HMAC-SHA256
- **Key Management**: Master key encrypts individual file keys
- **Process**:
  1. Generate unique encryption key per file
  2. Encrypt file with Fernet
  3. Encrypt file key with master key
  4. Store encrypted key in database
  5. Store encrypted file in S3

#### **Database Security**
- **Encrypted Fields**: `file_key` (binary encrypted)
- **Access Control**: Row-level user_id validation
- **SQL Injection**: Protected by SQLAlchemy ORM

#### **S3 Security**
- **Private Bucket**: No public access
- **Unique Keys**: UUID-based file naming
- **Access Control**: IAM-based credentials
- **HTTPS**: Encrypted transit

### **Best Practices**

```python
# config.py - Security constants
MASTER_KEY = os.getenv('MASTER_KEY')  # Never hardcode!
master_cipher = Fernet(MASTER_KEY.encode())

# s3_utils.py - Encryption example
def encrypt_and_upload_file(file_bytes, file_id):
    # Generate unique key
    file_key = Fernet.generate_key()
    cipher = Fernet(file_key)

    # Encrypt file
    encrypted_data = cipher.encrypt(file_bytes)

    # Encrypt key with master key
    encrypted_key = master_cipher.encrypt(file_key)

    # Upload to S3
    s3_key = f"capsules/{uuid.uuid4()}.enc"
    upload_to_s3(encrypted_data, s3_key)

    return encrypted_key, s3_key
```

***

## 🔄 Migration System

### **Automatic Migrations**

The bot includes an automatic database migration system that runs on startup:

```python
# main.py
async def main():
    init_db()  # Create tables

    from src.migrations import run_migrations
    migration_success = run_migrations()  # Apply pending migrations

    if not migration_success:
        logger.error("Migrations failed!")
        return
```

### **Migration Versions**

#### **001_add_capsule_balance.py**
- Adds `capsule_balance` field to users table
- Grants 3 starter capsules to existing free users
- Required for new payment system

#### **002_add_transactions_table.py**
- Creates `transactions` table for Stars payments
- Tracks all capsule purchases
- Stores transaction history

### **Manual Migration Commands**

```bash
# Check migration status
python migrate.py status

# Run pending migrations
python migrate.py migrate

# Rollback specific migration
python migrate.py rollback --version 001
```

### **Migration Output Example**

```
🔄 Starting database migration check...
✅ Migration history table created
📦 Found 2 pending migration(s)
📦 Applying migration 001: 001_add_capsule_balance
  ✓ Added capsule_balance column (SQLite)
  ✓ Granted 3 starter capsules to existing free users
✅ Migration 001 applied successfully
📦 Applying migration 002: 002_add_transactions_table
  ✓ Created transactions table (SQLite)
  ✓ Created index on transactions.user_id
✅ Migration 002 applied successfully
🎉 Successfully applied 2 migration(s)
✅ Database is up to date
```

***

## 🤖 Bot Commands

### **User Commands**

| Command | Description |
|---------|-------------|
| `/start` | Start bot and show main menu |
| `/create` | Create new time capsule |
| `/capsules` | View your capsules |
| `/subscription` | Manage subscription and buy capsules |
| `/settings` | Change language and preferences |
| `/help` | Show help information |
| `/paysupport` | Payment support and refund policy |

### **Main Menu Options**

📝 **Create Capsule**: Start capsule creation wizard
📦 **My Capsules**: View, manage, and delete capsules
💎 **Subscription**: Buy capsules or upgrade to premium
⚙️ **Settings**: Change language
❓ **Help**: Get assistance

***

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork** the repository
2. Create a **feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. Open a **Pull Request**

### **Code Style**
- Follow PEP 8
- Use type hints
- Add docstrings for functions
- Write meaningful commit messages

***

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

***

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [Cryptography](https://cryptography.io/) - Encryption library
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [APScheduler](https://apscheduler.readthedocs.io/) - Task scheduling

***

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/f2re/Digital-Time-Capsule/issues)

***

## 🚀 Roadmap

- [ ] **Web Dashboard**: View capsules via web interface
- [ ] **Mobile App**: Native iOS/Android apps
- [ ] **Group Features**: Group time capsules with shared access
- [ ] **Advanced Scheduling**: Recurring capsules
- [ ] **Analytics**: Detailed usage statistics for users
- [ ] **Multi-language**: Add more languages (German, Spanish, French)
- [ ] **API**: Public API for third-party integrations

***

**Made with ❤️ by the Digital Time Capsule Team**

**⭐ Star this repo if you find it useful!**
