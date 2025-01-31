import asyncio
import os
from PyQt6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox, QInputDialog, QFileDialog
from PyQt6.QtGui import QFont
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded

from parse_window import ParserWindow


class AuthWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Авторизация в Telegram (Pyrogram)")
        self.setGeometry(100, 100, 350, 300)

        font = QFont("Arial", 10)

        # Поля для ввода API ID, API HASH, телефона
        self.label_api_id = QLabel("API ID:", self)
        self.label_api_id.setFont(font)
        self.input_api_id = QLineEdit(self)
        self.input_api_id.setFont(font)

        self.label_api_hash = QLabel("API Hash:", self)
        self.label_api_hash.setFont(font)
        self.input_api_hash = QLineEdit(self)
        self.input_api_hash.setFont(font)

        self.label_phone = QLabel("Телефон:", self)
        self.label_phone.setFont(font)
        self.input_phone = QLineEdit(self)
        self.input_phone.setFont(font)

        # Кнопки
        self.btn_login = QPushButton("Создать сессию", self)
        self.btn_login.setFont(font)
        self.btn_login.clicked.connect(self.start_auth)

        self.btn_import = QPushButton("Импортировать сессию", self)
        self.btn_import.setFont(font)
        self.btn_import.clicked.connect(self.import_session)

        # Размещение элементов
        layout = QVBoxLayout()
        layout.addWidget(self.label_api_id)
        layout.addWidget(self.input_api_id)
        layout.addWidget(self.label_api_hash)
        layout.addWidget(self.input_api_hash)
        layout.addWidget(self.label_phone)
        layout.addWidget(self.input_phone)
        layout.addWidget(self.btn_login)
        layout.addWidget(self.btn_import)
        self.setLayout(layout)

    def start_auth(self):
        """Запуск авторизации в асинхронном режиме"""
        api_id = self.input_api_id.text()
        api_hash = self.input_api_hash.text()
        phone = self.input_phone.text()

        if not api_id or not api_hash or not phone:
            QMessageBox.warning(self, "Ошибка", "Все поля должны быть заполнены!")
            return

        try:
            api_id = int(api_id)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.create_session(api_id, api_hash, phone))
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "API ID должен быть числом!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка авторизации: {e}")

    async def create_session(self, api_id, api_hash, phone):
        session_name = "my_session"
        app = Client(session_name, api_id, api_hash)

        await app.connect()

        try:
            sent_code = await app.send_code(phone)
            code = self.ask_for_code()
            if not code:
                return

            await app.sign_in(phone, sent_code.phone_code_hash, code)

            if await app.get_me():
                QMessageBox.information(self, "Успех", "Сессия создана и сохранена!")
                self.open_parser_window(session_name)
                return

            if isinstance(await app.get_me(), SessionPasswordNeeded):
                password = self.ask_for_password()
                if not password:
                    return
                await app.check_password(password)

            QMessageBox.information(self, "Успех", "Сессия создана и сохранена!")
            self.open_parser_window(session_name)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка авторизации: {e}")
        finally:
            await app.disconnect()

    def import_session(self):
        """Выбор и импорт существующего файла сессии"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл сессии", "", "Session Files (*.session)")

        if not file_path:
            return

        session_name = os.path.splitext(os.path.basename(file_path))[0]
        self.open_parser_window(session_name)

    def open_parser_window(self, session_name):
        """Открытие окна парсинга после успешной авторизации"""
        self.close()
        self.parser_window = ParserWindow(session_name)
        self.parser_window.show()

    def ask_for_code(self):
        code, ok = QInputDialog.getText(self, "Код подтверждения", "Введите код из Telegram:")
        return code if ok else None

    def ask_for_password(self):
        password, ok = QInputDialog.getText(self, "Двухфакторная аутентификация", "Введите пароль:")
        return password if ok else None
