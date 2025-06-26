import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QCheckBox, QMessageBox, QListWidget,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QFileDialog
)
from pymongo import MongoClient
import qdarkstyle
import csv
import json


class MongoGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MongoDB Modern GUI - Gelişmiş Veri Yönetimi")
        self.setGeometry(500, 100, 1000, 750)

        self.client = None
        self.current_db = None
        self.current_collection = None

        # --- Giriş Alanları ---
        self.host_input = QLineEdit("127.0.0.1")
        self.port_input = QLineEdit("27017")
        self.user_input = QLineEdit()
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.auth_checkbox = QCheckBox("Şifreli Bağlantı (Auth)")

        self.connect_btn = QPushButton("Bağlan")

        # --- Listeleme Alanları ---
        self.db_list = QListWidget()
        self.collection_list = QListWidget()

        self.data_table = QTableWidget()

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)

        self.add_btn = QPushButton("Yeni Belge Ekle")
        self.delete_btn = QPushButton("Seçili Belgeyi Sil")
        self.export_json_btn = QPushButton("JSON Dışa Aktar")
        self.export_csv_btn = QPushButton("CSV Dışa Aktar")
        self.refresh_btn = QPushButton("Verileri Yenile")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filtre (örn: name:Ali)")

        # --- Layout ---
        self.build_ui()

        self.connect_btn.clicked.connect(self.connect_mongo)
        self.auth_checkbox.stateChanged.connect(self.toggle_auth_fields)
        self.db_list.itemClicked.connect(self.load_collections)
        self.collection_list.itemClicked.connect(self.load_collection_data)
        self.add_btn.clicked.connect(self.add_document)
        self.delete_btn.clicked.connect(self.delete_document)
        self.export_json_btn.clicked.connect(self.export_json)
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.filter_input.returnPressed.connect(self.refresh_data)

        self.toggle_auth_fields()

    def build_ui(self):
        main_layout = QVBoxLayout()

        connection_layout = QVBoxLayout()
        connection_layout.addWidget(QLabel("Host:"))
        connection_layout.addWidget(self.host_input)
        connection_layout.addWidget(QLabel("Port:"))
        connection_layout.addWidget(self.port_input)
        connection_layout.addWidget(self.auth_checkbox)
        connection_layout.addWidget(QLabel("Kullanıcı Adı:"))
        connection_layout.addWidget(self.user_input)
        connection_layout.addWidget(QLabel("Şifre:"))
        connection_layout.addWidget(self.pass_input)
        connection_layout.addWidget(self.connect_btn)

        list_layout = QHBoxLayout()
        list_layout.addWidget(self.db_list)
        list_layout.addWidget(self.collection_list)

        data_btn_layout = QHBoxLayout()
        data_btn_layout.addWidget(self.add_btn)
        data_btn_layout.addWidget(self.delete_btn)
        data_btn_layout.addWidget(self.export_json_btn)
        data_btn_layout.addWidget(self.export_csv_btn)
        data_btn_layout.addWidget(self.refresh_btn)
        data_btn_layout.addWidget(self.filter_input)

        main_layout.addLayout(connection_layout)
        main_layout.addLayout(list_layout)
        main_layout.addLayout(data_btn_layout)
        main_layout.addWidget(self.data_table)
        main_layout.addWidget(self.result_area)

        self.setLayout(main_layout)

    def toggle_auth_fields(self):
        auth_required = self.auth_checkbox.isChecked()
        self.user_input.setEnabled(auth_required)
        self.pass_input.setEnabled(auth_required)

    def connect_mongo(self):
        host = self.host_input.text()
        port = self.port_input.text()

        try:
            port = int(port)
        except ValueError:
            QMessageBox.critical(self, "Hata", "Port sayısal olmalı!")
            return

        uri = f"mongodb://{host}:{port}/"
        if self.auth_checkbox.isChecked():
            username = self.user_input.text()
            password = self.pass_input.text()
            uri = f"mongodb://{username}:{password}@{host}:{port}/"

        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            dbs = self.client.list_database_names()
            self.db_list.clear()
            self.collection_list.clear()
            self.data_table.clear()
            self.result_area.setPlainText("Veritabanları Yüklendi:\n" + "\n".join(dbs))
            for db in dbs:
                self.db_list.addItem(db)
        except Exception as e:
            QMessageBox.critical(self, "Bağlantı Hatası", str(e))

    def load_collections(self, item):
        db_name = item.text()
        self.current_db = self.client[db_name]
        collections = self.current_db.list_collection_names()
        self.collection_list.clear()
        self.data_table.clear()
        self.result_area.setPlainText(f"{db_name} veritabanındaki koleksiyonlar yüklendi.")
        for col in collections:
            self.collection_list.addItem(col)

    def load_collection_data(self, item):
        self.refresh_data()

    def refresh_data(self):
        if not self.current_collection and self.collection_list.currentItem():
            self.current_collection = self.current_db[self.collection_list.currentItem().text()]

        if not self.current_collection:
            return

        filter_text = self.filter_input.text().strip()
        query = {}
        if ":" in filter_text:
            try:
                key, val = filter_text.split(":", 1)
                query[key.strip()] = val.strip()
            except Exception:
                QMessageBox.warning(self, "Uyarı", "Filtre formatı hatalı. Örnek: alan:deger")

        try:
            documents = list(self.current_collection.find(query).limit(500))

            if not documents:
                self.result_area.setPlainText("Koleksiyon boş veya filtre sonucu bulunamadı.")
                self.data_table.setRowCount(0)
                self.data_table.setColumnCount(0)
                return

            headers = list(documents[0].keys())
            self.data_table.setColumnCount(len(headers))
            self.data_table.setHorizontalHeaderLabels(headers)
            self.data_table.setRowCount(len(documents))

            for row_idx, doc in enumerate(documents):
                for col_idx, header in enumerate(headers):
                    value = str(doc.get(header, ""))
                    self.data_table.setItem(row_idx, col_idx, QTableWidgetItem(value))

            self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.result_area.setPlainText(f"{len(documents)} belge yüklendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def add_document(self):
        if not self.current_collection:
            QMessageBox.warning(self, "Uyarı", "Önce bir koleksiyon seçmelisiniz.")
            return

        text, ok = QInputDialog.getText(self, "Yeni Belge", "JSON formatında belge girin:")
        if ok and text:
            try:
                doc = json.loads(text)
                self.current_collection.insert_one(doc)
                self.refresh_data()
                QMessageBox.information(self, "Başarılı", "Yeni belge eklendi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", str(e))

    def delete_document(self):
        if not self.current_collection:
            QMessageBox.warning(self, "Uyarı", "Önce bir koleksiyon seçmelisiniz.")
            return

        selected_row = self.data_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Uyarı", "Silmek için bir belge seçmelisiniz.")
            return

        _id = self.data_table.item(selected_row, 0).text()
        try:
            from bson import ObjectId
            self.current_collection.delete_one({"_id": ObjectId(_id)})
            self.refresh_data()
            QMessageBox.information(self, "Başarılı", "Belge silindi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def export_json(self):
        if not self.current_collection:
            QMessageBox.warning(self, "Uyarı", "Önce bir koleksiyon seçmelisiniz.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "JSON Dışa Aktar", "data.json", "JSON Files (*.json)")
        if file_path:
            try:
                documents = list(self.current_collection.find())
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(documents, f, indent=4, default=str)
                QMessageBox.information(self, "Başarılı", "JSON dosyası kaydedildi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", str(e))

    def export_csv(self):
        if not self.current_collection:
            QMessageBox.warning(self, "Uyarı", "Önce bir koleksiyon seçmelisiniz.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "CSV Dışa Aktar", "data.csv", "CSV Files (*.csv)")
        if file_path:
            try:
                documents = list(self.current_collection.find())
                if not documents:
                    QMessageBox.warning(self, "Uyarı", "Koleksiyon boş, dışa aktarılacak veri yok.")
                    return

                headers = list(documents[0].keys())
                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    for doc in documents:
                        writer.writerow({k: str(v) for k, v in doc.items()})
                QMessageBox.information(self, "Başarılı", "CSV dosyası kaydedildi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))

    window = MongoGUI()
    window.show()

    sys.exit(app.exec())