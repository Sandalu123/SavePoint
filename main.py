#!/usr/bin/env python3

import os
import sys
import json
import logging
import argparse
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ftplib
import gzip
import shutil
import time
from urllib.parse import urlparse
import requests
import zipfile
import platform
import subprocess
import shutil
from tqdm import tqdm

# Add colored output support
try:
    from colorama import init, Fore, Style

    init()
except ImportError:
    # Create dummy color codes if colorama is not installed
    class DummyColors:
        def __getattr__(self, name):
            return ''


    Fore = Style = DummyColors()


class CLI:
    # [Previous CLI class code remains the same]
    @staticmethod
    def print_header(text):
        """Print a formatted header."""
        print(f"\n{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}  {text}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}\n")

    @staticmethod
    def print_step(text):
        """Print a step indicator."""
        print(f"\n{Fore.CYAN}▶ {text}{Style.RESET_ALL}")

    @staticmethod
    def print_success(text):
        """Print a success message."""
        print(f"{Fore.GREEN}✔ {text}{Style.RESET_ALL}")

    @staticmethod
    def print_error(text):
        """Print an error message."""
        print(f"{Fore.RED}✘ {text}{Style.RESET_ALL}")

    @staticmethod
    def prompt(text, default=None):
        """Prompt for input with optional default value."""
        if default:
            prompt_text = f"{Fore.YELLOW}{text} [{default}]: {Style.RESET_ALL}"
        else:
            prompt_text = f"{Fore.YELLOW}{text}: {Style.RESET_ALL}"

        value = input(prompt_text)
        return value if value else default


class MongoToolsManager:
    DOWNLOAD_URLS = {
        'windows': 'https://fastdl.mongodb.org/tools/db/mongodb-database-tools-windows-x86_64-100.10.0.zip',
        'linux': 'https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu-x86_64-100.10.0.tgz'
    }

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.tools_dir = config_dir / 'mongodb-tools'
        self.system = 'windows' if platform.system().lower() == 'windows' else 'linux'

    def get_mongodump_path(self) -> Optional[str]:
        """Get path to mongodump executable, returns None if not found."""
        # First check if mongodump is in PATH
        mongodump_command = 'mongodump.exe' if self.system == 'windows' else 'mongodump'
        if shutil.which(mongodump_command):
            return mongodump_command

        # Check in our tools directory
        mongodump_path = self.tools_dir / 'bin' / mongodump_command
        if mongodump_path.exists():
            return str(mongodump_path)

        return None

    def download_tools(self) -> None:
        """Download MongoDB tools with progress bar."""
        CLI.print_step("Downloading MongoDB Database Tools")

        url = self.DOWNLOAD_URLS[self.system]
        local_filename = self.config_dir / url.split('/')[-1]

        try:
            # Download with progress bar
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))

            with open(local_filename, 'wb') as f, tqdm(
                    desc="Downloading",
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
            ) as pbar:
                for data in response.iter_content(chunk_size=1024):
                    size = f.write(data)
                    pbar.update(size)

            CLI.print_success("Download completed")
            return local_filename

        except Exception as e:
            CLI.print_error(f"Failed to download MongoDB tools: {str(e)}")
            raise

    def extract_tools(self, filename: Path) -> None:
        """Extract downloaded tools archive."""
        CLI.print_step("Extracting MongoDB Database Tools")

        try:
            if self.system == 'windows':
                with zipfile.ZipFile(filename, 'r') as zip_ref:
                    zip_ref.extractall(self.config_dir)

                # Find the extracted directory
                extracted_dir = next(self.config_dir.glob('mongodb-database-tools-windows-*'))

                # Move to our tools directory
                if self.tools_dir.exists():
                    shutil.rmtree(self.tools_dir)
                extracted_dir.rename(self.tools_dir)

            else:
                # For Linux systems
                import tarfile
                with tarfile.open(filename, 'r:gz') as tar:
                    tar.extractall(self.config_dir)

                # Find the extracted directory
                extracted_dir = next(self.config_dir.glob('mongodb-database-tools-*'))
                extracted_dir.rename(self.tools_dir)

            CLI.print_success("Extraction completed")

        except Exception as e:
            CLI.print_error(f"Failed to extract MongoDB tools: {str(e)}")
            raise
        finally:
            # Clean up downloaded file
            filename.unlink(missing_ok=True)

    def ensure_tools_available(self) -> str:
        """Ensure MongoDB tools are available, downloading if necessary."""
        mongodump_path = self.get_mongodump_path()

        if not mongodump_path:
            CLI.print_step("MongoDB tools not found. Setting up MongoDB Database Tools...")
            try:
                downloaded_file = self.download_tools()
                self.extract_tools(downloaded_file)
                mongodump_path = self.get_mongodump_path()

                if not mongodump_path:
                    raise Exception("Failed to setup MongoDB tools")

                CLI.print_success("MongoDB tools setup completed")

            except Exception as e:
                CLI.print_error(f"Failed to setup MongoDB tools: {str(e)}")
                raise

        return mongodump_path

class BackupConfig:
    def __init__(self):
        """Initialize configuration with proper path handling."""
        # Get the directory where the script is located
        self.script_dir = Path(__file__).resolve().parent

        # Create a .config directory in the script directory
        self.config_dir = self.script_dir / '.config'
        self.config_dir.mkdir(exist_ok=True)

        # Set the config file path
        self.config_file = self.config_dir / 'backup_config.json'
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from JSON file or return default config."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)

        return {
            "database": {
                "type": None,
                "name": None,
                "connection_string": None,  # for MongoDB
                "host": "localhost",  # for MySQL
                "port": None,  # for MySQL
                "username": None,  # for MySQL
                "password": None  # for MySQL
            },
            "backup": {
                "local_path": str(self.script_dir / "backups"),
                "retention_days": 7
            },
            "email": {
                "smtp_server": None,
                "smtp_port": 587,
                "username": None,
                "password": None,
                "recipients": []
            },
            "ftp": {
                "enabled": False,
                "host": None,
                "port": 21,
                "username": None,
                "password": None,
                "directory": "/backups"
            },
            "schedule": {
                "frequency": "daily",
                "times": ["00:00"]
            }
        }

    def save(self):
        """Save current configuration to file."""
        try:
            # Ensure the config directory exists
            self.config_dir.mkdir(exist_ok=True)

            # Save the configuration
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)

        except Exception as e:
            CLI.print_error(f"Failed to save configuration: {str(e)}")
            raise


class DatabaseBackup:
    def __init__(self, config: BackupConfig):
        self.config = config
        self.setup_logging()

    def setup_logging(self):
        """Configure logging for the backup process."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backup.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def backup_mysql(self) -> Optional[str]:
        """Perform MySQL backup using mysqldump."""
        try:
            db_config = self.config.config["database"]
            backup_dir = Path(self.config.config["backup"]["local_path"])
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"mysql_{db_config['name']}_{timestamp}.sql"

            cmd = [
                'mysqldump',
                f'-h{db_config["host"]}',
                f'-u{db_config["username"]}',
                f'-p{db_config["password"]}',
                db_config['name']
            ]

            with open(backup_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)

            # Compress the backup
            with open(backup_file, 'rb') as f_in:
                with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove the uncompressed file
            backup_file.unlink()

            self.logger.info(f"MySQL backup completed: {backup_file}.gz")
            return f"{backup_file}.gz"

        except subprocess.CalledProcessError as e:
            self.logger.error(f"MySQL backup failed: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during MySQL backup: {str(e)}")
            return None

    def backup_mongodb(self) -> Optional[str]:
        """Perform MongoDB backup using mongodump."""
        try:
            db_config = self.config.config["database"]
            backup_dir = Path(self.config.config["backup"]["local_path"])
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f"mongodb_{db_config['name']}_{timestamp}"

            # Ensure MongoDB tools are available
            tools_manager = MongoToolsManager(self.config.config_dir)
            mongodump_path = tools_manager.ensure_tools_available()

            if "connection_string" in db_config and db_config["connection_string"]:
                # Use connection string if available
                cmd = [
                    mongodump_path,
                    f'--uri={db_config["connection_string"]}',
                    f'--out={backup_path}'
                ]
            else:
                # Use individual parameters
                cmd = [
                    mongodump_path,
                    f'--host={db_config["host"]}',
                    f'--port={db_config["port"]}',
                    f'--db={db_config["name"]}',
                    f'--username={db_config["username"]}',
                    f'--password={db_config["password"]}',
                    f'--out={backup_path}'
                ]

            # Run mongodump
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"mongodump failed: {result.stderr}")

            # Create archive
            archive_path = f"{backup_path}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_path, arcname=os.path.basename(backup_path))

            # Clean up the temporary directory
            shutil.rmtree(backup_path)

            self.logger.info(f"MongoDB backup completed: {archive_path}")
            return archive_path

        except Exception as e:
            self.logger.error(f"MongoDB backup failed: {str(e)}")
            return None

    def send_email_notification(self, backup_file: str, success: bool):
        """Send email notification about backup status."""
        try:
            email_config = self.config.config["email"]
            msg = MIMEMultipart()
            msg['From'] = email_config["username"]
            msg['To'] = ", ".join(email_config["recipients"])
            msg['Subject'] = f"Database Backup {'Success' if success else 'Failure'}"

            body = f"""
            Backup Status: {'Success' if success else 'Failure'}
            Database: {self.config.config['database']['name']}
            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """

            if success:
                body += f"\nBackup File: {backup_file}"
                body += f"\nFile Size: {os.path.getsize(backup_file) / (1024 * 1024):.2f} MB"

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"]) as server:
                server.starttls()
                server.login(email_config["username"], email_config["password"])
                server.send_message(msg)

            self.logger.info("Email notification sent successfully")

        except Exception as e:
            self.logger.error(f"Failed to send email notification: {str(e)}")

    def upload_to_ftp(self, backup_file: str):
        """Upload backup file to FTP server."""
        try:
            ftp_config = self.config.config["ftp"]
            if not ftp_config["enabled"]:
                return

            with ftplib.FTP() as ftp:
                ftp.connect(ftp_config["host"], ftp_config["port"])
                ftp.login(ftp_config["username"], ftp_config["password"])

                # Create remote directory if it doesn't exist
                try:
                    ftp.mkd(ftp_config["directory"])
                except:
                    pass

                ftp.cwd(ftp_config["directory"])

                with open(backup_file, 'rb') as f:
                    ftp.storbinary(f'STOR {os.path.basename(backup_file)}', f)

            self.logger.info(f"Backup file uploaded to FTP: {backup_file}")

        except Exception as e:
            self.logger.error(f"Failed to upload to FTP: {str(e)}")

    def run_backup(self):
        """Run the backup process."""
        try:
            db_type = self.config.config["database"]["type"]

            if db_type == "mysql":
                backup_file = self.backup_mysql()
            elif db_type == "mongodb":
                backup_file = self.backup_mongodb()
            else:
                raise ValueError(f"Unsupported database type: {db_type}")

            if backup_file:
                self.upload_to_ftp(backup_file)
                self.send_email_notification(backup_file, True)
            else:
                self.send_email_notification(None, False)

        except Exception as e:
            self.logger.error(f"Backup process failed: {str(e)}")
            self.send_email_notification(None, False)



def validate_and_create_path(path_str: str) -> str:
    """Validate and create a directory path, returning the absolute path."""
    try:
        # Convert to Path object and resolve to absolute path
        path = Path(path_str).resolve()

        # Create the directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)

        return str(path)
    except Exception as e:
        CLI.print_error(f"Invalid path: {str(e)}")
        return None


def validate_mongodb_connection_string(connection_string: str) -> bool:
    """Validate MongoDB connection string format."""
    try:
        if not connection_string.startswith(('mongodb://', 'mongodb+srv://')):
            return False

        parsed = urlparse(connection_string)
        return bool(parsed.hostname)
    except Exception:
        return False


def setup_interactive():
    """Run interactive setup to configure the backup tool."""
    try:
        config = BackupConfig()

        CLI.print_header("Database Backup Tool - Configuration Setup")

        # Database configuration
        CLI.print_step("Database Configuration")

        db_type = CLI.prompt("Select database type (1 for MySQL, 2 for MongoDB)")
        while db_type not in ('1', '2'):
            CLI.print_error("Invalid selection. Please enter 1 for MySQL or 2 for MongoDB")
            db_type = CLI.prompt("Select database type (1 for MySQL, 2 for MongoDB)")

        if db_type == '1':
            config.config["database"]["type"] = "mysql"
            config.config["database"]["name"] = CLI.prompt("Database name")
            config.config["database"]["host"] = CLI.prompt("Database host", "localhost")
            config.config["database"]["port"] = CLI.prompt("Database port", "3306")
            config.config["database"]["username"] = CLI.prompt("Database username")
            config.config["database"]["password"] = CLI.prompt("Database password")
        else:
            config.config["database"]["type"] = "mongodb"
            while True:
                connection_string = CLI.prompt("MongoDB connection string (mongodb://...)")
                if validate_mongodb_connection_string(connection_string):
                    config.config["database"]["connection_string"] = connection_string
                    # Extract database name from connection string if present
                    try:
                        parsed = urlparse(connection_string)
                        db_name = parsed.path.strip('/') if parsed.path else None
                        if not db_name:
                            db_name = CLI.prompt("Database name")
                        config.config["database"]["name"] = db_name
                    except Exception:
                        config.config["database"]["name"] = CLI.prompt("Database name")
                    break
                CLI.print_error("Invalid MongoDB connection string format")

        # Backup configuration
        CLI.print_step("Backup Configuration")
        while True:
            backup_path = CLI.prompt("Local backup path", str(config.script_dir / "backups"))
            validated_path = validate_and_create_path(backup_path)
            if validated_path:
                config.config["backup"]["local_path"] = validated_path
                break
            CLI.print_error("Please enter a valid path")

        config.config["backup"]["retention_days"] = int(CLI.prompt("Backup retention days", "7"))

        # Email configuration
        CLI.print_step("Email Notification Configuration")
        setup_email = CLI.prompt("Do you want to setup email notifications? (y/n)", "n").lower() == 'y'
        if setup_email:
            config.config["email"]["smtp_server"] = CLI.prompt("SMTP server")
            config.config["email"]["smtp_port"] = int(CLI.prompt("SMTP port", "587"))
            config.config["email"]["username"] = CLI.prompt("Email username")
            config.config["email"]["password"] = CLI.prompt("Email password")
            recipients = CLI.prompt("Recipient email(s) (comma-separated)")
            config.config["email"]["recipients"] = [r.strip() for r in recipients.split(",")]

        # FTP configuration
        CLI.print_step("FTP Configuration")
        setup_ftp = CLI.prompt("Do you want to setup FTP upload? (y/n)", "n").lower() == 'y'
        if setup_ftp:
            config.config["ftp"]["enabled"] = True
            config.config["ftp"]["host"] = CLI.prompt("FTP host")
            config.config["ftp"]["port"] = int(CLI.prompt("FTP port", "21"))
            config.config["ftp"]["username"] = CLI.prompt("FTP username")
            config.config["ftp"]["password"] = CLI.prompt("FTP password")
            config.config["ftp"]["directory"] = CLI.prompt("FTP directory", "/backups")

        # Save configuration
        config.save()
        CLI.print_success("Configuration saved successfully!")

        # Display next steps
        CLI.print_header("Next Steps")
        print(f"""
{Fore.CYAN}To run a backup:{Style.RESET_ALL}
    python {Path(__file__).name} --run

{Fore.CYAN}To schedule backups on Linux:{Style.RESET_ALL}
    Add to crontab:
    0 0 * * * {sys.executable} {Path(__file__).resolve()} --run

{Fore.CYAN}To schedule backups on Windows:{Style.RESET_ALL}
    Create a scheduled task with the command:
    {sys.executable} {Path(__file__).resolve()} --run
    """)

    except Exception as e:
        CLI.print_error(f"Setup failed: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Database Backup Tool")
    parser.add_argument("--setup", action="store_true", help="Run interactive setup")
    parser.add_argument("--run", action="store_true", help="Run backup now")
    args = parser.parse_args()

    if args.setup:
        setup_interactive()
    elif args.run:
        CLI.print_header("Running Database Backup")
        config = BackupConfig()
        backup = DatabaseBackup(config)
        backup.run_backup()
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        CLI.print_error("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        CLI.print_error(f"An error occurred: {str(e)}")
        sys.exit(1)