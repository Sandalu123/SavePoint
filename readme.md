# 💾 SavePoint

> Like a checkpoint in a game, but for your data!

SavePoint is your reliable companion for database backups, treating your data like a precious save file. Never lose progress on your MySQL or MongoDB databases with automated backups, notifications, and cloud saves.

## 🎮 Features

- 🎯 Quick-save your MySQL and MongoDB databases
- 📨 Get notified when your progress is saved (email notifications)
- ☁️ Cloud saves via FTP upload
- 🔄 Auto-installs required tools for MongoDB
- ⏰ Configure auto-save intervals
- 🎨 Gamer-friendly color terminal interface
- 📦 Auto-compression for save files
- ⚡ Quick setup wizard

## 🏁 Quick Start

### Installing the Game

1. Download the latest save point from the [releases page](https://github.com/yourusername/SavePoint/releases)

2. Load up your inventory (dependencies):
```bash
pip install -r requirements.txt
```

### Tutorial (First-Time Setup)

Run the setup wizard:
```bash
python savepoint.py --setup
```

The wizard will guide you through your initial setup:
- Database connection settings
- Save file location
- Notification preferences
- Cloud save settings

### Making a Save

Manual save:
```bash
python savepoint.py --run
```

### Auto-Save Settings

#### Linux Players (using cron)
Set up auto-save at midnight:
```bash
0 0 * * * /path/to/python /path/to/savepoint.py --run
```

#### Windows Players (using Task Scheduler)
Configure auto-save with:
```bash
"C:\Path\To\Python\python.exe" "C:\Path\To\savepoint.py" --run
```

## 📋 System Requirements

- Python 3.6+
- See `requirements.txt` for the full loadout
- MySQL: `mysqldump` tool for MySQL saves
- MongoDB: Don't worry, SavePoint auto-downloads what it needs!

## ⚙️ Save File Configuration

SavePoint keeps its settings in `.config/savepoint_config.json`:

```json
{
    "database": {
        "type": "mysql|mongodb",
        "name": "your_database",
        "connection_string": "mongodb://..." // for MongoDB
    },
    "backup": {
        "local_path": "/path/to/saves",
        "retention_days": 7
    },
    "email": {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "username": "your@email.com",
        "recipients": ["teammate@email.com"]
    },
    "ftp": {
        "enabled": false,
        "host": "ftp.example.com",
        "directory": "/saves"
    }
}
```

## 📜 Save Logs

- All saves are logged in `savepoint.log`
- Real-time status updates with RPG-style color coding

## 🆘 Need Help?

Having trouble with your saves?
1. Check the existing issues for similar quests
2. Open a new issue with details about your mission

## 🏆 Contributing

Want to join the party? We welcome:
- Bug reports
- Feature suggestions
- Pull requests
- Documentation improvements

## 📜 License

SavePoint is free loot! Licensed under MIT - see the LICENSE file for details.

---
*Remember: Saving your progress is just as important in real life as it is in games!* 🎮