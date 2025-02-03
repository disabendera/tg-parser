import asyncio
import csv
from PyQt6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox, QFileDialog, QSpinBox, QRadioButton, QHBoxLayout
from PyQt6.QtGui import QFont
from pyrogram import Client


class ParserWindow(QWidget):
    def __init__(self, session_name):
        super().__init__()
        self.session_name = session_name
        self.chat_list = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Парсинг сообщений")
        self.setGeometry(100, 100, 400, 300)

        font = QFont("Arial", 10)

        self.btn_load_chats = QPushButton("Импортировать список чатов", self)
        self.btn_load_chats.setFont(font)
        self.btn_load_chats.clicked.connect(self.load_chats)

        self.label_count = QLabel("Количество сообщений:", self)
        self.label_count.setFont(font)
        self.input_count = QSpinBox(self)
        self.input_count.setFont(font)
        self.input_count.setRange(1, 10000)

        self.label_filename = QLabel("Имя выходного файла:", self)
        self.label_filename.setFont(font)
        self.input_filename = QLineEdit(self)
        self.input_filename.setFont(font)

        self.radio_all = QRadioButton("Парсить все сообщения", self)
        self.radio_all.setChecked(True)

        self.radio_filter = QRadioButton("Парсить по слову", self)
        self.radio_filter.toggled.connect(self.toggle_word_filter)

        self.radio_function = QRadioButton("Парсить с поиском сообщений", self)
        self.radio_function.toggled.connect(self.toggle_word_filter)

        self.word_filter_input = QLineEdit(self)
        self.word_filter_input.setPlaceholderText("Введите текст для фильтрации")
        self.word_filter_input.setDisabled(True)

        self.exclude_filter_input = QLineEdit(self)
        self.exclude_filter_input.setPlaceholderText("Введите текст для исключения")

        layout = QVBoxLayout()
        layout.addWidget(self.btn_load_chats)
        layout.addWidget(self.label_count)
        layout.addWidget(self.input_count)
        layout.addWidget(self.label_filename)
        layout.addWidget(self.input_filename)

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.radio_all)
        radio_layout.addWidget(self.radio_filter)
        radio_layout.addWidget(self.radio_function)

        layout.addLayout(radio_layout)
        layout.addWidget(self.word_filter_input)
        layout.addWidget(self.exclude_filter_input)

        self.btn_parse = QPushButton("Собрать датасет", self)
        self.btn_parse.setFont(font)
        self.btn_parse.clicked.connect(self.start_parsing)

        layout.addWidget(self.btn_parse)
        self.setLayout(layout)

    def toggle_word_filter(self):
        if self.radio_filter.isChecked() or self.radio_function.isChecked():
            self.word_filter_input.setEnabled(True)
        else:
            self.word_filter_input.setEnabled(False)

    def load_chats(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите текстовый файл", "", "Text Files (*.txt)")
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.chat_list = [line.strip() for line in f if line.strip()]
            QMessageBox.information(self, "Успех", f"Загружено {len(self.chat_list)} чатов.")

    def start_parsing(self):
        filename = self.input_filename.text().strip()
        if not filename or not self.chat_list:
            QMessageBox.warning(self, "Ошибка", "Введите имя файла и загрузите список чатов!")
            return

        filename += ".csv"
        count = self.input_count.value()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.parse_messages(filename, count))

        self.input_filename.clear()
        self.input_count.setValue(1)

    async def parse_messages(self, filename, count):
        try:
            app = Client(self.session_name)
            await app.start()

            seen_messages = set()
            exclude_phrases = [phrase.strip().lower() for phrase in self.exclude_filter_input.text().split(',') if phrase.strip()]

            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["text", "mark"])
                if self.radio_all.isChecked():
                    """Парсинг всех сообщений"""
                    counter = 0
                    while counter < count:
                        for chat in self.chat_list:
                            messages_found = True
                            offset = 0
                            while messages_found:
                                messages_found = False
                                async for message in app.get_chat_history(chat, limit=100, offset=offset):
                                    messages_found = True
                                    text = message.text or ""
                                    if text and text not in seen_messages and not any(phrase in text.lower() for phrase in exclude_phrases):
                                        writer.writerow([text, ""])
                                        seen_messages.add(text)
                                        counter += 1
                                    if counter >= count:
                                        await app.stop()
                                        QMessageBox.information(self, "Готово", f"Датасет сохранён в {filename}!")
                                        return
                                offset += 100
                        if not messages_found:
                            break

                elif self.radio_filter.isChecked():
                    """Парсинг через сканирование сообщений на наличие заданной фразы"""
                    word = self.word_filter_input.text().strip()
                    if word:
                        counter = 0
                        while counter < count:
                            for chat in self.chat_list:
                                messages_found = True
                                offset = 0
                                while messages_found:
                                    messages_found = False
                                    async for message in app.get_chat_history(chat, limit=100, offset=offset):
                                        messages_found = True
                                        if message.text:
                                            if word.lower() in message.text.lower() and message.text not in seen_messages and not any(phrase in text.lower() for phrase in exclude_phrases):
                                                writer.writerow([message.text, ""])
                                                seen_messages.add(message.text)
                                                counter += 1
                                        if counter >= count:
                                            await app.stop()
                                            QMessageBox.information(self, "Готово", f"Датасет сохранён в {filename}!")
                                            return
                                    offset += 100
                            if not messages_found:
                                break

                elif self.radio_function.isChecked():
                    """Парсинг через поиск сообщений"""
                    word = self.word_filter_input.text().strip()
                    if word:
                        counter = 0
                        while counter < count:
                            for chat in self.chat_list:
                                messages_found = True
                                offset = 0
                                while messages_found:
                                    messages_found = False
                                    async for message in app.search_messages(chat, query=word, limit=100, offset=offset):
                                        messages_found = True
                                        text = message.text
                                        if text and text not in seen_messages and not any(phrase in text.lower() for phrase in exclude_phrases):
                                            writer.writerow([text, ""])
                                            seen_messages.add(text)
                                            counter += 1
                                        if counter >= count:
                                            await app.stop()
                                            QMessageBox.information(self, "Готово", f"Датасет сохранён в {filename}!")
                                            return
                                    offset += 100
                            if not messages_found:
                                break

            await app.stop()
            QMessageBox.information(self, "Готово", f"Датасет сохранён в {filename}!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка парсинга: {e}")
