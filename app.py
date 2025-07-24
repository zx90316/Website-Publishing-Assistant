import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
import json
import os
import shutil
import threading
import time
import subprocess
import sys
from datetime import datetime, timedelta
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


class WebsitePublisher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("網站發布助手")
        self.root.geometry("900x800")
        self.root.configure(bg='#f0f0f0')
        
        # 設置LOG記錄
        self.setup_logging()
        
        # 設定數據
        self.config = {
            'source_files': [],
            'delete_files': [],
            'servers': [],
            'schedule_time': None,
            'smtp_config': {
                'smtp_server': '',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'use_tls': True
            },
            'notification_emails': []
        }
        
        # 定時器變量
        self.publish_timer = None
        self.countdown_timer = None
        self.is_countdown_active = False
        
        # 創建GUI
        self.create_gui()
        
        # 載入配置
        self.load_config()
        
        # 設置GUI日誌處理器
        self.setup_gui_logging()
        
        # 初始化進度相關變數
        self.total_files = 0
        self.processed_files = 0
        
        # 初始化發布報告變數
        self.publish_report = {
            'servers': {},
            'start_time': None,
            'end_time': None,
            'total_stats': {
                'new_files': 0,
                'updated_files': 0,
                'skipped_files': 0,
                'deleted_files': 0
            }
        }
        
    def setup_logging(self):
        """設置LOG記錄"""
        # 創建logs目錄
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # 設置日誌格式
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # 配置日誌
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(f'logs/publish_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
        # 添加GUI日誌處理器（稍後在create_gui後設置）
        self.gui_log_handler = None
        
        self.logger.info("網站發布助手啟動")
        
    def create_gui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 標題
        title_label = ttk.Label(main_frame, text="網站發布助手", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 創建筆記本控件（分頁）
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 設定頁面
        self.create_settings_tab(notebook)
        
        # SMTP設定頁面
        self.create_smtp_tab(notebook)
        
        # 發布頁面
        self.create_publish_tab(notebook)
        
        # 發布歷史頁面
        self.create_history_tab(notebook)
        
        # 狀態欄
        self.status_var = tk.StringVar(value="就緒")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # 配置權重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
    def create_settings_tab(self, notebook):
        settings_frame = ttk.Frame(notebook, padding="10")
        notebook.add(settings_frame, text="設定")
        
        # 源檔案設定
        source_label = ttk.Label(settings_frame, text="目標發行檔案:", font=('Arial', 10, 'bold'))
        source_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        source_frame = ttk.Frame(settings_frame)
        source_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.source_listbox = tk.Listbox(source_frame, height=4)
        self.source_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        source_scroll = ttk.Scrollbar(source_frame, orient=tk.VERTICAL, command=self.source_listbox.yview)
        source_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.source_listbox.configure(yscrollcommand=source_scroll.set)
        
        source_btn_frame = ttk.Frame(source_frame)
        source_btn_frame.grid(row=0, column=2, padx=(10, 0), sticky=tk.N)
        
        ttk.Button(source_btn_frame, text="新增檔案", command=self.add_source_file).grid(row=0, column=0, pady=(0, 5))
        ttk.Button(source_btn_frame, text="新增資料夾", command=self.add_source_folder).grid(row=1, column=0, pady=(0, 5))
        ttk.Button(source_btn_frame, text="移除", command=self.remove_source).grid(row=2, column=0)
        
        # 刪除檔案設定
        delete_label = ttk.Label(settings_frame, text="發布前需刪除的檔案:", font=('Arial', 10, 'bold'))
        delete_label.grid(row=2, column=0, sticky=tk.W, pady=(20, 5))
        
        delete_frame = ttk.Frame(settings_frame)
        delete_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.delete_listbox = tk.Listbox(delete_frame, height=3)
        self.delete_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        delete_scroll = ttk.Scrollbar(delete_frame, orient=tk.VERTICAL, command=self.delete_listbox.yview)
        delete_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.delete_listbox.configure(yscrollcommand=delete_scroll.set)
        
        delete_btn_frame = ttk.Frame(delete_frame)
        delete_btn_frame.grid(row=0, column=2, padx=(10, 0), sticky=tk.N)
        
        self.delete_entry = ttk.Entry(delete_btn_frame, width=15)
        self.delete_entry.grid(row=0, column=0, pady=(0, 5))
        
        ttk.Button(delete_btn_frame, text="新增", command=self.add_delete_file).grid(row=1, column=0, pady=(0, 5))
        ttk.Button(delete_btn_frame, text="測試檔案", command=self.test_delete_files).grid(row=2, column=0, pady=(0, 5))
        ttk.Button(delete_btn_frame, text="移除", command=self.remove_delete_file).grid(row=3, column=0)
        
        # 伺服器設定
        server_label = ttk.Label(settings_frame, text="目標伺服器:", font=('Arial', 10, 'bold'))
        server_label.grid(row=4, column=0, sticky=tk.W, pady=(20, 5))
        
        server_frame = ttk.Frame(settings_frame)
        server_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.server_listbox = tk.Listbox(server_frame, height=4)
        self.server_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        server_scroll = ttk.Scrollbar(server_frame, orient=tk.VERTICAL, command=self.server_listbox.yview)
        server_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.server_listbox.configure(yscrollcommand=server_scroll.set)
        
        server_btn_frame = ttk.Frame(server_frame)
        server_btn_frame.grid(row=0, column=2, padx=(10, 0), sticky=tk.N)
        
        ttk.Button(server_btn_frame, text="新增伺服器", command=self.add_server).grid(row=0, column=0, pady=(0, 5))
        ttk.Button(server_btn_frame, text="編輯", command=self.edit_server).grid(row=1, column=0, pady=(0, 5))
        ttk.Button(server_btn_frame, text="測試連接", command=self.test_server_connection).grid(row=2, column=0, pady=(0, 5))
        ttk.Button(server_btn_frame, text="移除", command=self.remove_server).grid(row=3, column=0)
        
        # 設定權重
        source_frame.columnconfigure(0, weight=1)
        delete_frame.columnconfigure(0, weight=1)
        server_frame.columnconfigure(0, weight=1)
        settings_frame.columnconfigure(0, weight=1)
        
    def create_smtp_tab(self, notebook):
        smtp_frame = ttk.Frame(notebook, padding="10")
        notebook.add(smtp_frame, text="郵件通知")
        
        # SMTP設定區域
        smtp_label = ttk.Label(smtp_frame, text="SMTP伺服器設定:", font=('Arial', 10, 'bold'))
        smtp_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        smtp_config_frame = ttk.LabelFrame(smtp_frame, text="SMTP設定", padding="10")
        smtp_config_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # SMTP伺服器
        ttk.Label(smtp_config_frame, text="SMTP伺服器:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.smtp_server_var = tk.StringVar()
        ttk.Entry(smtp_config_frame, textvariable=self.smtp_server_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5), padx=(10, 0))
        
        # SMTP埠號
        ttk.Label(smtp_config_frame, text="埠號:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.smtp_port_var = tk.StringVar(value="587")
        ttk.Entry(smtp_config_frame, textvariable=self.smtp_port_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=(0, 5), padx=(10, 0))
        
        # 使用者名稱
        ttk.Label(smtp_config_frame, text="使用者名稱:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.smtp_username_var = tk.StringVar()
        ttk.Entry(smtp_config_frame, textvariable=self.smtp_username_var, width=50).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 5), padx=(10, 0))
        
        # 密碼
        ttk.Label(smtp_config_frame, text="密碼:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        password_frame = ttk.Frame(smtp_config_frame)
        password_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 5), padx=(10, 0))
        
        self.smtp_password_var = tk.StringVar()
        self.smtp_password_entry = ttk.Entry(password_frame, textvariable=self.smtp_password_var, width=35, show="*")
        self.smtp_password_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.show_smtp_password_var = tk.BooleanVar()
        ttk.Checkbutton(password_frame, text="顯示", variable=self.show_smtp_password_var, 
                       command=self.toggle_smtp_password).grid(row=0, column=1, padx=(5, 0))
        password_frame.columnconfigure(0, weight=1)
        
        # TLS設定
        ttk.Label(smtp_config_frame, text="使用TLS:").grid(row=4, column=0, sticky=tk.W, pady=(0, 10))
        self.use_tls_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(smtp_config_frame, variable=self.use_tls_var).grid(row=4, column=1, sticky=tk.W, pady=(0, 10), padx=(10, 0))
        
        # SMTP測試按鈕
        smtp_test_frame = ttk.Frame(smtp_config_frame)
        smtp_test_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(smtp_test_frame, text="儲存SMTP設定", command=self.save_smtp_config).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(smtp_test_frame, text="測試SMTP連接", command=self.test_smtp_connection).grid(row=0, column=1)
        
        # 通知人員名單
        notify_label = ttk.Label(smtp_frame, text="通知人員名單:", font=('Arial', 10, 'bold'))
        notify_label.grid(row=2, column=0, sticky=tk.W, pady=(20, 5))
        
        notify_frame = ttk.Frame(smtp_frame)
        notify_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.notify_listbox = tk.Listbox(notify_frame, height=4)
        self.notify_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        notify_scroll = ttk.Scrollbar(notify_frame, orient=tk.VERTICAL, command=self.notify_listbox.yview)
        notify_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.notify_listbox.configure(yscrollcommand=notify_scroll.set)
        
        notify_btn_frame = ttk.Frame(notify_frame)
        notify_btn_frame.grid(row=0, column=2, padx=(10, 0), sticky=tk.N)
        
        self.email_entry = ttk.Entry(notify_btn_frame, width=25)
        self.email_entry.grid(row=0, column=0, pady=(0, 5))
        
        ttk.Button(notify_btn_frame, text="新增", command=self.add_notification_email).grid(row=1, column=0, pady=(0, 5))
        ttk.Button(notify_btn_frame, text="測試郵件", command=self.test_email_to_selected).grid(row=2, column=0, pady=(0, 5))
        ttk.Button(notify_btn_frame, text="移除", command=self.remove_notification_email).grid(row=3, column=0)
        
        # 設定權重
        smtp_config_frame.columnconfigure(1, weight=1)
        notify_frame.columnconfigure(0, weight=1)
        smtp_frame.columnconfigure(0, weight=1)
        
    def create_publish_tab(self, notebook):
        publish_frame = ttk.Frame(notebook, padding="10")
        notebook.add(publish_frame, text="發布")
        
        # 定時設定
        schedule_label = ttk.Label(publish_frame, text="定時發布設定:", font=('Arial', 12, 'bold'))
        schedule_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        time_frame = ttk.Frame(publish_frame)
        time_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 20))
        
        # 日期選擇
        ttk.Label(time_frame, text="發布日期:").grid(row=0, column=0, padx=(0, 5))
        
        self.date_var = tk.StringVar()
        try:
            self.date_entry = DateEntry(time_frame, textvariable=self.date_var, 
                                       date_pattern='yyyy-mm-dd', width=12,
                                       mindate=datetime.now().date())
            self.date_entry.grid(row=0, column=1, padx=(0, 10))
        except ImportError:
            # 如果沒有tkcalendar，使用簡單的Entry
            self.date_entry = ttk.Entry(time_frame, textvariable=self.date_var, width=12)
            self.date_entry.grid(row=0, column=1, padx=(0, 10))
            self.date_var.set(datetime.now().strftime("%Y-%m-%d"))
        
        # 時間選擇
        ttk.Label(time_frame, text="時間:").grid(row=0, column=2, padx=(0, 5))
        
        self.hour_var = tk.StringVar(value="21")
        self.minute_var = tk.StringVar(value="00")
        
        hour_spin = ttk.Spinbox(time_frame, from_=0, to=23, textvariable=self.hour_var, width=3, format="%02.0f")
        hour_spin.grid(row=0, column=3)
        
        ttk.Label(time_frame, text=":").grid(row=0, column=4)
        
        minute_spin = ttk.Spinbox(time_frame, from_=0, to=59, textvariable=self.minute_var, width=3, format="%02.0f")
        minute_spin.grid(row=0, column=5)
        
        ttk.Button(time_frame, text="設定定時發布", command=self.schedule_publish).grid(row=0, column=6, padx=(10, 0))
        ttk.Button(time_frame, text="取消定時", command=self.cancel_schedule).grid(row=0, column=7, padx=(5, 0))
        
        # 狀態顯示
        status_frame = ttk.LabelFrame(publish_frame, text="發布狀態", padding="10")
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.next_publish_var = tk.StringVar(value="無排程")
        ttk.Label(status_frame, text="下次發布時間:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.next_publish_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        self.countdown_var = tk.StringVar(value="")
        ttk.Label(status_frame, text="倒數計時:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.countdown_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        self.target_servers_var = tk.StringVar(value="")
        ttk.Label(status_frame, text="目標伺服器:").grid(row=2, column=0, sticky=tk.W)
        target_label = ttk.Label(status_frame, textvariable=self.target_servers_var, wraplength=400)
        target_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # 手動發布按鈕
        ttk.Button(publish_frame, text="立即發布", command=self.publish_now, style='Accent.TButton').grid(row=3, column=0, columnspan=2, pady=20)
        
        # 進度和控制台顯示
        progress_frame = ttk.LabelFrame(publish_frame, text="發布進度與狀態", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 進度條
        progress_label_frame = ttk.Frame(progress_frame)
        progress_label_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(progress_label_frame, text="總體進度:").grid(row=0, column=0, sticky=tk.W)
        self.progress_label = ttk.Label(progress_label_frame, text="0 / 0 (0%)")
        self.progress_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 控制台輸出
        ttk.Label(progress_frame, text="發布日誌:").grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        console_frame = ttk.Frame(progress_frame)
        console_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.console_text = tk.Text(console_frame, height=15, wrap=tk.WORD, state='disabled',
                                   bg='#1e1e1e', fg='#ffffff', font=('Consolas', 9))
        self.console_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        console_scroll = ttk.Scrollbar(console_frame, orient=tk.VERTICAL, command=self.console_text.yview)
        console_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.console_text.configure(yscrollcommand=console_scroll.set)
        
        # 清除日誌按鈕
        ttk.Button(progress_frame, text="清除日誌", command=self.clear_console).grid(row=4, column=0, columnspan=2, pady=(5, 0))
        
        # 設定權重
        publish_frame.columnconfigure(0, weight=1)
        publish_frame.rowconfigure(4, weight=1)
        status_frame.columnconfigure(1, weight=1)
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(3, weight=1)
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        
        # 更新伺服器顯示
        self.update_server_display()
    
    def create_history_tab(self, notebook):
        """創建發布歷史頁面"""
        history_frame = ttk.Frame(notebook, padding="10")
        notebook.add(history_frame, text="發布歷史")
        
        # 標題
        title_label = ttk.Label(history_frame, text="發布歷史記錄", font=('Arial', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # 控制按鈕區域
        control_frame = ttk.Frame(history_frame)
        control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(control_frame, text="刷新記錄", command=self.refresh_history).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(control_frame, text="清除所有記錄", command=self.clear_all_history).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(control_frame, text="刪除選中記錄", command=self.delete_selected_history).grid(row=0, column=2)
        
        # 歷史記錄列表
        list_frame = ttk.LabelFrame(history_frame, text="歷史記錄", padding="10")
        list_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 創建Treeview顯示歷史記錄
        columns = ('發布時間', '耗時', '伺服器數量', '總檔案操作', '狀態')
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 設置列標題
        self.history_tree.heading('發布時間', text='發布時間')
        self.history_tree.heading('耗時', text='耗時(秒)')
        self.history_tree.heading('伺服器數量', text='伺服器數量')
        self.history_tree.heading('總檔案操作', text='總檔案操作')
        self.history_tree.heading('狀態', text='狀態')
        
        # 設置列寬
        self.history_tree.column('發布時間', width=150)
        self.history_tree.column('耗時', width=80)
        self.history_tree.column('伺服器數量', width=100)
        self.history_tree.column('總檔案操作', width=120)
        self.history_tree.column('狀態', width=80)
        
        # 添加滾動條
        history_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        history_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        
        # 綁定雙擊事件查看詳細報告
        self.history_tree.bind('<Double-1>', self.view_history_detail)
        
        # 詳細信息區域
        detail_frame = ttk.LabelFrame(history_frame, text="發布詳情 (雙擊上方記錄查看詳細資訊)", padding="10")
        detail_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 詳細信息顯示區域
        self.history_detail_text = tk.Text(detail_frame, height=10, wrap=tk.WORD, state='disabled',
                                          bg='#f8f9fa', font=('Consolas', 9))
        self.history_detail_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.history_detail_text.yview)
        detail_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.history_detail_text.configure(yscrollcommand=detail_scroll.set)
        
        # 設定權重
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(2, weight=1)
        history_frame.rowconfigure(3, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)
        
        # 初始化載入歷史記錄
        self.load_history_records()
    
    def setup_gui_logging(self):
        """設置GUI日誌處理器"""
        class GUILogHandler(logging.Handler):
            def __init__(self, console_widget, root):
                super().__init__()
                self.console_widget = console_widget
                self.root = root
            
            def emit(self, record):
                # 在主線程中更新GUI
                self.root.after(0, self._update_console, self.format(record))
            
            def _update_console(self, message):
                # 啟用文字框編輯
                self.console_widget.config(state='normal')
                
                # 添加時間戳和訊息
                timestamp = datetime.now().strftime('%H:%M:%S')
                formatted_message = f"[{timestamp}] {message}\n"
                
                # 插入訊息
                self.console_widget.insert(tk.END, formatted_message)
                
                # 自動滾動到底部
                self.console_widget.see(tk.END)
                
                # 禁用文字框編輯
                self.console_widget.config(state='disabled')
                
                # 限制最大行數（保留最後1000行）
                lines = int(self.console_widget.index('end-1c').split('.')[0])
                if lines > 1000:
                    self.console_widget.config(state='normal')
                    self.console_widget.delete('1.0', f'{lines-1000}.0')
                    self.console_widget.config(state='disabled')
        
        # 創建並添加GUI日誌處理器
        if hasattr(self, 'console_text') and self.console_text is not None:
            self.gui_log_handler = GUILogHandler(self.console_text, self.root)
            self.gui_log_handler.setLevel(logging.INFO)
            self.gui_log_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
            self.logger.addHandler(self.gui_log_handler)
            self.logger.info("GUI日誌處理器已啟用")
    
    def clear_console(self):
        """清除控制台輸出"""
        self.console_text.config(state='normal')
        self.console_text.delete('1.0', tk.END)
        self.console_text.config(state='disabled')
        self.logger.info("控制台日誌已清除")
    
    def init_progress(self, total_files):
        """初始化進度條"""
        self.total_files = total_files
        self.processed_files = 0
        self.progress_bar['maximum'] = total_files
        self.progress_bar['value'] = 0
        self.update_progress_label()
    
    def update_progress(self, increment=1):
        """更新進度"""
        self.processed_files += increment
        if hasattr(self, 'progress_bar'):
            self.root.after(0, self._update_progress_gui)
    
    def _update_progress_gui(self):
        """在主線程中更新進度GUI"""
        self.progress_bar['value'] = self.processed_files
        self.update_progress_label()
        
    def update_progress_label(self):
        """更新進度標籤"""
        if self.total_files > 0:
            percentage = (self.processed_files / self.total_files) * 100
            self.progress_label.config(text=f"{self.processed_files} / {self.total_files} ({percentage:.1f}%)")
        else:
            self.progress_label.config(text="0 / 0 (0%)")

    def add_source_file(self):
        filename = filedialog.askopenfilename(title="選擇發行檔案")
        if filename:
            self.config['source_files'].append(filename)
            self.source_listbox.insert(tk.END, filename)
            self.save_config()
            
    def add_source_folder(self):
        folder_name = filedialog.askdirectory(title="選擇發行資料夾")
        if folder_name:
            self.config['source_files'].append(folder_name)
            self.source_listbox.insert(tk.END, folder_name)
            self.save_config()
            
    def remove_source(self):
        selection = self.source_listbox.curselection()
        if selection:
            index = selection[0]
            self.source_listbox.delete(index)
            del self.config['source_files'][index]
            self.save_config()
            
    def add_delete_file(self):
        filename = self.delete_entry.get().strip()
        if filename:
            self.config['delete_files'].append(filename)
            self.delete_listbox.insert(tk.END, filename)
            self.delete_entry.delete(0, tk.END)
            self.save_config()
            
    def test_delete_files(self):
        if not self.config['delete_files']:
            messagebox.showwarning("警告", "請先新增要測試的檔案")
            return
            
        if not self.config['servers']:
            messagebox.showwarning("警告", "請先設定目標伺服器")
            return
            
        # 在新線程中執行測試
        test_thread = threading.Thread(target=self._test_delete_files_worker)
        test_thread.daemon = True
        test_thread.start()
        
    def _test_delete_files_worker(self):
        """在背景線程中測試刪除檔案"""
        self.status_var.set("正在檢查刪除檔案...")
        self.logger.info("開始檢查刪除檔案")
        
        results = []
        
        # 首先檢查本地發行檔案中是否包含要刪除的檔案
        local_conflicts = []
        self.logger.info("檢查本地發行檔案中的衝突")
        
        for delete_file in self.config['delete_files']:
            found_in_local = []
            
            for source in self.config['source_files']:
                if os.path.isfile(source):
                    # 單個檔案
                    if os.path.basename(source) == delete_file:
                        size = os.path.getsize(source)
                        size_str = self._format_file_size(size)
                        found_in_local.append(f"檔案: {source} ({size_str})")
                        
                elif os.path.isdir(source):
                    # 搜尋目錄中的檔案
                    for root, dirs, files in os.walk(source):
                        if delete_file in files:
                            file_path = os.path.join(root, delete_file)
                            size = os.path.getsize(file_path)
                            size_str = self._format_file_size(size)
                            rel_path = os.path.relpath(file_path, source)
                            found_in_local.append(f"目錄 {source} 中的 {rel_path} ({size_str})")
                        
                        if delete_file in dirs:
                            dir_path = os.path.join(root, delete_file)
                            rel_path = os.path.relpath(dir_path, source)
                            found_in_local.append(f"目錄 {source} 中的資料夾 {rel_path}")
            
            if found_in_local:
                local_conflicts.append(f"⚠️ {delete_file}:")
                for item in found_in_local:
                    local_conflicts.append(f"   📤 本地包含: {item}")
                local_conflicts.append(f"   ⚠️ 警告: 此檔案會被本地版本覆蓋，無法保留伺服器版本!")
                self.logger.warning(f"本地檔案衝突: {delete_file} 存在於發行檔案中")
            else:
                local_conflicts.append(f"✅ {delete_file}: 本地不包含，可正確保留伺服器版本")
                self.logger.info(f"無衝突: {delete_file} 不在本地發行檔案中")
        
        if local_conflicts:
            results.append("📦 本地發行檔案衝突檢查:\n" + "\n".join(f"   {r}" for r in local_conflicts))
        
        # 顯示結果
        result_text = "\n\n".join(results)
        self.status_var.set("檢查完成")
        
        self.root.after(0, lambda: self._show_delete_test_results(result_text))
        
    def _format_file_size(self, size_bytes):
        """格式化檔案大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            
        
    def _show_delete_test_results(self, result_text):
        """顯示刪除檔案測試結果"""
        # 創建結果對話框
        result_dialog = tk.Toplevel(self.root)
        result_dialog.title("刪除檔案檢查結果")
        result_dialog.geometry("600x400")
        result_dialog.resizable(True, True)
        
        # 居中顯示
        result_dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 100, self.root.winfo_rooty() + 50))
        
        main_frame = ttk.Frame(result_dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 標題
        title_label = ttk.Label(main_frame, text="刪除檔案檢查結果", font=('Arial', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # 結果文字區域
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        result_text_widget = tk.Text(text_frame, wrap=tk.WORD, height=15, width=70)
        result_text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=result_text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        result_text_widget.configure(yscrollcommand=scrollbar.set)
        
        # 插入結果文字
        result_text_widget.insert(tk.END, result_text)
        result_text_widget.configure(state='disabled')
        
        # 關閉按鈕
        ttk.Button(main_frame, text="關閉", command=result_dialog.destroy).grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        # 設定權重
        result_dialog.columnconfigure(0, weight=1)
        result_dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
            
    def remove_delete_file(self):
        selection = self.delete_listbox.curselection()
        if selection:
            index = selection[0]
            self.delete_listbox.delete(index)
            del self.config['delete_files'][index]
            self.save_config()
    
    def toggle_smtp_password(self):
        if self.show_smtp_password_var.get():
            self.smtp_password_entry.configure(show="")
        else:
            self.smtp_password_entry.configure(show="*")
    
    def save_smtp_config(self):
        if not self.smtp_server_var.get():
            messagebox.showwarning("警告", "請填寫SMTP伺服器地址")
            return
        
        try:
            port = int(self.smtp_port_var.get())
        except ValueError:
            messagebox.showerror("錯誤", "埠號必須是數字")
            return
        
        self.config['smtp_config'] = {
            'smtp_server': self.smtp_server_var.get(),
            'smtp_port': port,
            'username': self.smtp_username_var.get(),
            'password': self.smtp_password_var.get(),
            'use_tls': self.use_tls_var.get()
        }
        self.save_config()
        messagebox.showinfo("成功", "SMTP設定已儲存")
    
    def test_smtp_connection(self):
        if not self.smtp_server_var.get():
            messagebox.showwarning("警告", "請先填寫SMTP伺服器地址")
            return
        
        test_thread = threading.Thread(target=self._test_smtp_worker)
        test_thread.daemon = True
        test_thread.start()
    
    def _test_smtp_worker(self):
        self.status_var.set("正在測試SMTP連接...")
        
        try:
            smtp_config = {
                'smtp_server': self.smtp_server_var.get(),
                'smtp_port': int(self.smtp_port_var.get()),
                'username': self.smtp_username_var.get(),
                'password': self.smtp_password_var.get(),
                'use_tls': self.use_tls_var.get()
            }
            
            # 檢查常見的設定問題
            email_domain = smtp_config['username'].split('@')[-1] if '@' in smtp_config['username'] else ''
            smtp_domain = smtp_config['smtp_server'].lower()
            
            self.logger.info(f"正在測試 SMTP 連接到 {smtp_config['smtp_server']}:{smtp_config['smtp_port']}")
            self.logger.info(f"用戶: {smtp_config['username']}")
            
            # 設定超時時間
            server = smtplib.SMTP(timeout=30)
            server.connect(smtp_config['smtp_server'], smtp_config['smtp_port'])
            
            if smtp_config['use_tls']:
                self.logger.info("啟用 TLS 加密...")
                # 檢查是否為 IP 地址
                import re
                is_ip = re.match(r'^\d+\.\d+\.\d+\.\d+$', smtp_config['smtp_server'])
                if is_ip:
                    self.logger.warning("檢測到使用 IP 地址進行 TLS 連接，將跳過證書驗證")
                    # 對於 IP 地址，跳過主機名驗證
                    import ssl
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    server.starttls(context=context)
                else:
                    server.starttls()
            
            # 只有在提供用戶名時才進行身份驗證
            if smtp_config['username'].strip():
                self.logger.info("正在進行身份驗證...")
                server.login(smtp_config['username'], smtp_config['password'])
            else:
                self.logger.info("無需身份驗證（開放式 SMTP 中繼）")
            server.quit()
            
            self.status_var.set("SMTP測試完成")
            self.root.after(0, lambda: messagebox.showinfo("SMTP測試", "SMTP連接測試成功！"))
            self.logger.info("SMTP連接測試成功")
            
        except smtplib.SMTPConnectError as e:
            error_msg = f"無法連接到SMTP伺服器: {str(e)}\n\n可能原因:\n1. 伺服器地址或端口錯誤\n2. 防火牆阻止連接\n3. 網絡問題"
            self._handle_smtp_error(error_msg, "連接錯誤")
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP身份驗證失敗: {str(e)}\n\n可能原因:\n1. 用戶名或密碼錯誤\n2. 需要使用應用程式密碼\n3. 帳戶被鎖定或禁用"
            self._handle_smtp_error(error_msg, "驗證錯誤")
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # 針對常見錯誤提供具體建議
            if "10060" in error_msg:
                suggestions = self._get_smtp_suggestions(smtp_config)
                error_msg = f"連接超時錯誤: {error_msg}\n\n{suggestions}"
            elif "10061" in error_msg:
                error_msg = f"連接被拒絕: {error_msg}\n\n可能原因:\n1. SMTP端口錯誤\n2. 伺服器不允許連接\n3. 防火牆阻止"
            
            self._handle_smtp_error(f"{error_type}: {error_msg}", "SMTP測試失敗")
    
    def _handle_smtp_error(self, error_msg, title):
        """處理SMTP錯誤"""
        self.status_var.set("SMTP測試失敗")
        self.root.after(0, lambda: messagebox.showerror(title, error_msg))
        self.logger.error(f"SMTP連接測試失敗: {error_msg}")
    
    def _get_smtp_suggestions(self, smtp_config):
        """根據配置提供SMTP設定建議"""
        email_domain = smtp_config['username'].split('@')[-1] if '@' in smtp_config['username'] else ''
        smtp_server = smtp_config['smtp_server'].lower()
        
        suggestions = "建議的解決方案:\n"
        
        # 檢查是否為 IP 地址
        import re
        is_ip = re.match(r'^\d+\.\d+\.\d+\.\d+$', smtp_server)
        
        # 檢查郵箱和SMTP伺服器是否匹配
        if email_domain == 'vscc.org.tw' and 'gmail' in smtp_server:
            suggestions += "1. ⚠️ 郵箱域名不匹配！您使用的是 @vscc.org.tw 郵箱，但配置的是 Gmail SMTP\n"
            suggestions += "   建議使用 VSCC 的 SMTP 伺服器:\n"
            suggestions += "   - SMTP伺服器: mail.vscc.org.tw 或 smtp.vscc.org.tw\n"
            suggestions += "   - 端口: 587 (TLS) 或 465 (SSL)\n\n"
        elif email_domain == 'gmail.com' and 'gmail' in smtp_server:
            suggestions += "1. Gmail 需要使用應用程式密碼，不能使用普通密碼\n"
            suggestions += "2. 啟用兩步驟驗證後生成應用程式密碼\n\n"
        elif is_ip and smtp_config['use_tls'] and smtp_config['smtp_port'] == 25:
            suggestions += "1. ⚠️ 配置問題！您使用 IP 地址 + 端口 25 + TLS，這通常不相容\n"
            suggestions += "   VSCC 內部 SMTP 伺服器建議配置:\n"
            suggestions += "   - SMTP伺服器: 192.168.80.60\n"
            suggestions += "   - 端口: 25\n"
            suggestions += "   - 用戶名: 空白\n"
            suggestions += "   - 密碼: 空白\n"
            suggestions += "   - TLS: 關閉\n\n"
        elif is_ip and smtp_config['use_tls']:
            suggestions += "1. ℹ️ 使用 IP 地址進行 TLS 連接已自動跳過證書驗證\n"
            suggestions += "   如果仍然失敗，建議:\n"
            suggestions += "   - 關閉 TLS（如果是內部伺服器）\n"
            suggestions += "   - 或使用伺服器的域名而非 IP\n\n"
        
        suggestions += "2. 檢查網絡連接:\n"
        suggestions += "   - 確認防火牆沒有阻止端口 " + str(smtp_config['smtp_port']) + "\n"
        suggestions += "   - 嘗試使用公司內部網絡\n\n"
        
        suggestions += "3. 常見 SMTP 設定:\n"
        suggestions += "   - Gmail: smtp.gmail.com:587 (TLS) 或 :465 (SSL)\n"
        suggestions += "   - Outlook: smtp-mail.outlook.com:587 (TLS)\n"
        suggestions += "   - VSCC: 請聯繫IT部門確認SMTP設定\n\n"
        
        suggestions += "4. 如果是公司郵箱，請聯繫IT部門獲取正確的SMTP設定"
        
        return suggestions
    
    def add_notification_email(self):
        email = self.email_entry.get().strip()
        if email:
            if '@' not in email:
                messagebox.showerror("錯誤", "請輸入正確的電子郵件地址")
                return
            
            if email not in self.config['notification_emails']:
                self.config['notification_emails'].append(email)
                self.notify_listbox.insert(tk.END, email)
                self.email_entry.delete(0, tk.END)
                self.save_config()
            else:
                messagebox.showwarning("警告", "此電子郵件地址已存在")
    
    def remove_notification_email(self):
        selection = self.notify_listbox.curselection()
        if selection:
            index = selection[0]
            self.notify_listbox.delete(index)
            del self.config['notification_emails'][index]
            self.save_config()
    
    def test_email_to_selected(self):
        selection = self.notify_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "請先選擇要測試的電子郵件地址")
            return
        
        index = selection[0]
        test_email = self.config['notification_emails'][index]
        
        test_thread = threading.Thread(target=self._test_email_worker, args=(test_email,))
        test_thread.daemon = True
        test_thread.start()
    
    def _test_email_worker(self, test_email):
        self.status_var.set(f"正在發送測試郵件到 {test_email}...")
        
        try:
            if not self.config['smtp_config']['smtp_server']:
                self.root.after(0, lambda: messagebox.showerror("錯誤", "請先設定並儲存SMTP設定"))
                return
            
            subject = f"網站發布助手測試郵件 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            content = f"""這是一封來自網站發布助手的測試郵件。

測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
收件者: {test_email}

如果您收到此郵件，表示SMTP設定正確，系統可以正常發送通知郵件。

系統資訊:
- 發送時間: {datetime.now()}
- SMTP伺服器: {self.config['smtp_config']['smtp_server']}
- 使用TLS: {'是' if self.config['smtp_config']['use_tls'] else '否'}

此為系統自動發送的測試郵件，請勿回覆。
"""
            
            self._send_email([test_email], subject, content)
            
            self.status_var.set("測試郵件發送完成")
            self.root.after(0, lambda: messagebox.showinfo("成功", f"測試郵件已發送到 {test_email}"))
            self.logger.info(f"測試郵件發送成功: {test_email}")
            
        except Exception as e:
            error_msg = f"測試郵件發送失敗: {str(e)}"
            self.status_var.set("測試郵件發送失敗")
            self.root.after(0, lambda: messagebox.showerror("發送失敗", error_msg))
            self.logger.error(f"測試郵件發送失敗: {str(e)}")
            
    def add_server(self):
        server_dialog = ServerDialog(self.root)
        server_info = server_dialog.get_server_info()
        if server_info:
            self.config['servers'].append(server_info)
            self.server_listbox.insert(tk.END, f"{server_info['ip']} - {server_info['path']}")
            self.save_config()
            self.update_server_display()
            self.logger.info(f"新增伺服器: {server_info['ip']} - {server_info['path']}")
            
    def edit_server(self):
        selection = self.server_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "請先選擇要編輯的伺服器")
            return
            
        index = selection[0]
        current_server = self.config['servers'][index]
        
        server_dialog = ServerDialog(self.root, current_server)
        server_info = server_dialog.get_server_info()
        if server_info:
            self.config['servers'][index] = server_info
            self.server_listbox.delete(index)
            self.server_listbox.insert(index, f"{server_info['ip']} - {server_info['path']}")
            self.server_listbox.selection_set(index)
            self.save_config()
            self.update_server_display()
            self.logger.info(f"編輯伺服器: {server_info['ip']} - {server_info['path']}")
            
    def test_server_connection(self):
        selection = self.server_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "請先選擇要測試的伺服器")
            return
            
        index = selection[0]
        server = self.config['servers'][index]
        
        # 在新線程中執行測試
        test_thread = threading.Thread(target=self._test_connection_worker, args=(server,))
        test_thread.daemon = True
        test_thread.start()
        
    def _test_connection_worker(self, server):
        """在背景線程中測試網路共享連接"""
        self.status_var.set(f"正在測試連接到 {server['ip']}...")
        self.logger.info(f"開始測試網路共享連接: {server['ip']}")
        
        try:
            # 解析遠端路徑
            remote_path = server['path']
            remote_ip = server['ip']
            remote_user = server['username']
            remote_pass = server['password']
            
            try:
                drive_letter = remote_path.split(':')[0]
                dir_path = remote_path.split(':')[1].lstrip('\\')
                
                # 完整的 UNC 目標路徑
                full_unc_path = f"\\\\{remote_ip}\\{drive_letter}$\\{dir_path}"
                share_to_map = f"\\\\{remote_ip}\\{drive_letter}$"
                
            except IndexError:
                error_msg = f"遠端路徑格式不正確: {remote_path}\n應為 'D:\\資料夾' 格式"
                self.logger.error(f"路徑格式錯誤: {remote_path}")
                self.root.after(0, lambda: messagebox.showerror("路徑錯誤", error_msg))
                self.status_var.set("路徑格式錯誤")
                return

            # 網路連接命令
            connection_command = [
                "net", "use", share_to_map, remote_pass, f"/user:{remote_user}", "/persistent:no"
            ]
            disconnection_command = [
                "net", "use", share_to_map, "/delete"
            ]

            # 1. 建立網路連接
            self.logger.info(f"正在連線至 {share_to_map}...")
            result = subprocess.run(connection_command, check=True, capture_output=True, text=True)
            self.logger.info("網路共享連線成功")

            # 2. 測試目標路徑是否存在
            if os.path.exists(full_unc_path):
                # 基本連接和路徑測試成功，進行資料夾結構檢查
                folder_check_result = self._check_target_folders_network(full_unc_path)
                
                if folder_check_result['success']:
                    message = f"連接測試成功！\n伺服器: {server['ip']}\n目標路徑: {server['path']}\n網路路徑: {full_unc_path}\n資料夾結構: 正確\n狀態: 正常"
                    self.logger.info(f"網路共享連接測試成功: {server['ip']}")
                    self.root.after(0, lambda: messagebox.showinfo("連接測試", message))
                else:
                    message = f"連接成功但資料夾結構不完整！\n伺服器: {server['ip']}\n目標路徑: {server['path']}\n\n缺少的資料夾:\n{folder_check_result['missing_folders']}\n\n建議先執行一次發布以建立正確的資料夾結構"
                    self.logger.warning(f"連接成功但資料夾結構不完整: {server['ip']} - 缺少: {folder_check_result['missing_folders']}")
                    self.root.after(0, lambda: messagebox.showwarning("資料夾結構檢查", message))
            else:
                message = f"連接成功！\n但目標路徑不存在: {full_unc_path}\n建議檢查路徑設定或手動建立資料夾"
                self.logger.warning(f"連接成功但路徑不存在: {server['ip']} - {full_unc_path}")
                self.root.after(0, lambda: messagebox.showwarning("連接測試", message))
                
            # 3. 中斷連接
            subprocess.run(disconnection_command, capture_output=True)
            self.status_var.set("連接測試完成")
            
        except subprocess.CalledProcessError as e:
            error_message = e.stderr if e.stderr else str(e)
            error_msg = f"網路共享連接失敗\n伺服器: {server['ip']}\n\n可能原因:\n1. 帳號密碼錯誤\n2. 網路不通\n3. 遠端主機未啟用系統管理分享(C$, D$)\n4. 防火牆阻擋\n\n詳細錯誤: {error_message}"
            self.logger.error(f"網路共享連接失敗: {server['ip']} - {error_message}")
            self.root.after(0, lambda: messagebox.showerror("連接測試失敗", error_msg))
            self.status_var.set("連接測試失敗")
            
        except Exception as e:
            error_msg = f"連接失敗: {str(e)}\n伺服器: {server['ip']}\n\n可能原因:\n1. IP地址錯誤\n2. 網路不通\n3. 遠端主機未開機\n4. 防火牆阻擋"
            self.logger.error(f"連接測試失敗: {server['ip']} - {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("連接測試失敗", error_msg))
            self.status_var.set("連接測試失敗")
    
    def _check_target_folders_network(self, full_unc_path):
        """檢查目標網路路徑上是否包含所有源檔案對應的資料夾"""
        result = {
            'success': True,
            'missing_folders': []
        }
        
        try:
            # 獲取所有源檔案的專案名稱
            expected_folders = []
            for source_path in self.config.get('source_files', []):
                if os.path.isdir(source_path):
                    folder_name = os.path.basename(source_path)
                    expected_folders.append(folder_name)
                elif os.path.isfile(source_path):
                    # 如果是檔案，使用其父目錄名稱
                    folder_name = os.path.basename(os.path.dirname(source_path))
                    if folder_name not in expected_folders:
                        expected_folders.append(folder_name)
            
            if not expected_folders:
                # 如果沒有源檔案設定，跳過檢查
                return result
            
            # 檢查目標路徑下的資料夾
            existing_folders = []
            if os.path.exists(full_unc_path):
                for item in os.listdir(full_unc_path):
                    item_path = os.path.join(full_unc_path, item)
                    if os.path.isdir(item_path):
                        existing_folders.append(item)
            
            # 檢查缺少的資料夾
            for expected_folder in expected_folders:
                if expected_folder not in existing_folders:
                    result['missing_folders'].append(expected_folder)
                    result['success'] = False
            
            # 格式化缺少的資料夾列表
            if result['missing_folders']:
                result['missing_folders'] = '\n'.join([f"• {folder}" for folder in result['missing_folders']])
            
        except Exception as e:
            self.logger.error(f"資料夾結構檢查失敗: {full_unc_path} - {str(e)}")
            result['success'] = False
            result['missing_folders'] = f"檢查過程發生錯誤: {str(e)}"
        
        return result
            
    def remove_server(self):
        selection = self.server_listbox.curselection()
        if selection:
            index = selection[0]
            server = self.config['servers'][index]
            self.server_listbox.delete(index)
            del self.config['servers'][index]
            self.save_config()
            self.update_server_display()
            self.logger.info(f"移除伺服器: {server['ip']} - {server['path']}")
            
    def update_server_display(self):
        servers = [server['ip'] for server in self.config['servers']]
        self.target_servers_var.set(", ".join(servers) if servers else "無")
        
    def schedule_publish(self):
        try:
            # 解析日期
            date_str = self.date_var.get()
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            
            # 組合日期和時間
            try:
                schedule_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("錯誤", "日期格式錯誤，請使用 YYYY-MM-DD 格式")
                return
                
            schedule_time = datetime.combine(schedule_date, datetime.min.time().replace(hour=hour, minute=minute))
            now = datetime.now()
            
            # 檢查時間不能早於當前時間
            if schedule_time <= now:
                messagebox.showerror("錯誤", "發布時間不能早於當前時間\n請選擇未來的日期和時間")
                return
                
            self.config['schedule_time'] = schedule_time.isoformat()
            self.save_config()
            
            self.next_publish_var.set(schedule_time.strftime("%Y-%m-%d %H:%M:%S"))
            
            if self.publish_timer:
                self.publish_timer.cancel()
                
            delay = (schedule_time - now).total_seconds()
            self.publish_timer = threading.Timer(delay, self.publish_now)
            self.publish_timer.start()
            
            self.start_countdown()
            
            messagebox.showinfo("成功", f"已設定定時發布：{schedule_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except ValueError as e:
            messagebox.showerror("錯誤", f"請輸入有效的日期和時間：{str(e)}")
            
    def cancel_schedule(self):
        if self.publish_timer:
            self.publish_timer.cancel()
            self.publish_timer = None
            
        self.is_countdown_active = False
        self.config['schedule_time'] = None
        self.save_config()
        
        self.next_publish_var.set("無排程")
        self.countdown_var.set("")
        
        messagebox.showinfo("成功", "已取消定時發布")
        
    def start_countdown(self):
        self.is_countdown_active = True
        self.update_countdown()
        
    def update_countdown(self):
        if not self.is_countdown_active or not self.config['schedule_time']:
            return
            
        schedule_time = datetime.fromisoformat(self.config['schedule_time'])
        now = datetime.now()
        
        if now >= schedule_time:
            self.countdown_var.set("發布中...")
            return
            
        remaining = schedule_time - now
        
        days = remaining.days
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            countdown_text = f"{days}天 {hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            countdown_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
        self.countdown_var.set(countdown_text)
        
        if self.is_countdown_active:
            self.root.after(1000, self.update_countdown)
            
    def publish_now(self):
        if not self.config['source_files']:
            messagebox.showerror("錯誤", "請先設定發行檔案")
            return
            
        if not self.config['servers']:
            messagebox.showerror("錯誤", "請先設定目標伺服器")
            return
            
        self.status_var.set("發布中...")
        
        # 在新線程中執行發布
        publish_thread = threading.Thread(target=self._publish_worker)
        publish_thread.daemon = True
        publish_thread.start()
        
    def _count_total_files(self):
        """計算總檔案數量"""
        total_files = 0
        
        for source in self.config['source_files']:
            if os.path.isfile(source):
                total_files += 1
            elif os.path.isdir(source):
                for root, dirs, files in os.walk(source):
                    for file in files:
                        # 跳過需要刪除的檔案
                        if file not in self.config['delete_files']:
                            total_files += 1
        
        # 乘以伺服器數量（每個伺服器都要複製一遍）
        return total_files * len(self.config['servers'])

    def _publish_worker(self):
        start_time = datetime.now()
        
        # 初始化發布報告
        self.publish_report = {
            'servers': {},
            'start_time': start_time,
            'end_time': None,
            'total_stats': {
                'new_files': 0,
                'updated_files': 0,
                'skipped_files': 0,
                'deleted_files': 0
            }
        }
        
        self.logger.info("=== 開始發布作業 ===")
        self.logger.info(f"發布時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"源文件數量: {len(self.config['source_files'])}")
        self.logger.info(f"目標伺服器數量: {len(self.config['servers'])}")
        
        # 計算總檔案數並初始化進度條
        total_files = self._count_total_files()
        self.logger.info(f"預計處理檔案總數: {total_files}")
        self.root.after(0, lambda: self.init_progress(total_files))
        
        try:
            success_count = 0
            for i, server in enumerate(self.config['servers'], 1):
                self.status_var.set(f"正在發布到 {server['ip']} ({i}/{len(self.config['servers'])})...")
                self.logger.info(f"開始發布到伺服器 {i}/{len(self.config['servers'])}: {server['ip']}")
                
                server_start = datetime.now()
                self._publish_to_server(server)
                server_end = datetime.now()
                server_duration = (server_end - server_start).total_seconds()
                
                self.logger.info(f"伺服器 {server['ip']} 發布完成，耗時 {server_duration:.2f} 秒")
                success_count += 1
                
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            # 更新報告結束時間
            self.publish_report['end_time'] = end_time
            
            self.status_var.set("發布完成")
            self.logger.info(f"=== 發布作業完成 ===")
            self.logger.info(f"成功發布到 {success_count}/{len(self.config['servers'])} 個伺服器")
            self.logger.info(f"總耗時: {total_duration:.2f} 秒")
            
            # 在主線程中處理發布完成的所有操作
            self.root.after(0, lambda: self._handle_publish_success(start_time, end_time))
            
        except Exception as e:
            error_msg = str(e)
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            self.status_var.set(f"發布失敗: {error_msg}")
            self.logger.error(f"=== 發布作業失敗 ===")
            self.logger.error(f"錯誤訊息: {error_msg}")
            self.logger.error(f"失敗時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.error(f"已執行時間: {total_duration:.2f} 秒")
            
            # 在主線程中處理發布失敗的所有操作
            self.root.after(0, lambda: self._handle_publish_failure(start_time, end_time, error_msg))
            
    def _handle_publish_success(self, start_time, end_time):
        """在主線程中處理發布成功的所有操作"""
        try:
            # 完成進度條
            self.init_progress(0)
            
            # 保存到發布歷史（不觸發GUI刷新）
            self.save_history_record(self.publish_report, is_success=True)
            
            # 刷新歷史記錄顯示
            if hasattr(self, 'history_tree'):
                self.refresh_history()
            
            # 發送成功通知郵件（在背景線程中執行）
            email_thread = threading.Thread(
                target=self._send_deployment_notification, 
                args=(True, start_time, end_time)
            )
            email_thread.daemon = True
            email_thread.start()
            
            # 顯示發布報告
            self._show_publish_report()
            
            # 顯示成功訊息
            self._show_success_message()
            
        except Exception as e:
            self.logger.error(f"處理發布成功時發生錯誤: {str(e)}")
    
    def _handle_publish_failure(self, start_time, end_time, error_msg):
        """在主線程中處理發布失敗的所有操作"""
        try:
            # 重置進度條
            self.init_progress(0)
            
            # 保存失敗記錄到歷史（不觸發GUI刷新）
            self.save_history_record(self.publish_report, is_success=False)
            
            # 刷新歷史記錄顯示
            if hasattr(self, 'history_tree'):
                self.refresh_history()
            
            # 發送失敗通知郵件（在背景線程中執行）
            email_thread = threading.Thread(
                target=self._send_deployment_notification, 
                args=(False, start_time, end_time, error_msg)
            )
            email_thread.daemon = True
            email_thread.start()
            
            # 顯示錯誤訊息
            self._show_error_message(error_msg)
            
        except Exception as e:
            self.logger.error(f"處理發布失敗時發生錯誤: {str(e)}")

    def _show_publish_report(self):
        """顯示發布報告對話框"""
        try:
            # 檢查發布報告是否存在
            if not hasattr(self, 'publish_report') or not self.publish_report:
                self.logger.warning("無法顯示發布報告：報告數據不存在")
                return
            
            report_dialog = tk.Toplevel(self.root)
            report_dialog.title("發布完成報告")
            report_dialog.geometry("1300x700")
            report_dialog.resizable(True, True)
            
            # 延遲設置 grab_set，避免干擾其他對話框
            self.root.after(100, lambda: report_dialog.grab_set() if report_dialog.winfo_exists() else None)
            
            # 居中顯示
            try:
                x = self.root.winfo_rootx() + 50
                y = self.root.winfo_rooty() + 50
                report_dialog.geometry("+%d+%d" % (x, y))
            except tk.TclError:
                # 如果無法獲取父窗口位置，使用默認位置
                pass
            
            main_frame = ttk.Frame(report_dialog, padding="15")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # 標題
            title_label = ttk.Label(main_frame, text="🎉 發布完成報告", font=('Arial', 16, 'bold'))
            title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
            
            # 總體資訊
            info_frame = ttk.LabelFrame(main_frame, text="總體資訊", padding="10")
            info_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
            
            # 計算總體統計
            total_stats = self.publish_report['total_stats']
            start_time = self.publish_report['start_time']
            end_time = self.publish_report['end_time']
            duration = (end_time - start_time).total_seconds() if end_time else 0
            
            info_text = f"""⏰ 發布時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
⏱️ 總耗時: {duration:.1f} 秒
🖥️ 伺服器數量: {len(self.publish_report['servers'])}
📁 新增檔案: {total_stats['new_files']}
🔄 更新檔案: {total_stats['updated_files']}
⏭️ 跳過檔案: {total_stats['skipped_files']}
🗑️ 刪除檔案: {total_stats['deleted_files']}
📊 總檔案操作: {sum(total_stats.values())}"""
            
            info_label = ttk.Label(info_frame, text=info_text, font=('Consolas', 10))
            info_label.grid(row=0, column=0, sticky=(tk.W, tk.N))
            
            # 詳細資訊
            detail_frame = ttk.LabelFrame(main_frame, text="詳細資訊", padding="10")
            detail_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
            
            # 創建Notebook來顯示各伺服器的詳細信息
            notebook = ttk.Notebook(detail_frame)
            notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # 為每個伺服器創建一個頁面
            for server_key, server_data in self.publish_report['servers'].items():
                server_frame = ttk.Frame(notebook)
                notebook.add(server_frame, text=f"伺服器: {server_key}")
                
                # 創建伺服器統計資訊
                server_stats = server_data['stats']
                stats_text = f"📁 新增: {server_stats['new_files']} | 🔄 更新: {server_stats['updated_files']} | ⏭️ 跳過: {server_stats['skipped_files']} | 🗑️ 刪除: {server_stats['deleted_files']}"
                stats_label = ttk.Label(server_frame, text=stats_text, font=('Arial', 9))
                stats_label.grid(row=0, column=0, sticky=(tk.W), pady=(0, 10))
                
                # 創建樹狀視圖顯示檔案操作詳情
                tree_frame = ttk.Frame(server_frame)
                tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
                
                columns = ('operation', 'path', 'detail', 'time')
                tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=15)
                
                # 設定列標題並綁定排序功能
                tree.heading('#0', text='檔案名稱 ↕️', command=lambda: self._sort_tree(tree, '#0'))
                tree.heading('operation', text='操作 ↕️', command=lambda: self._sort_tree(tree, 'operation'))
                tree.heading('path', text='路徑 ↕️', command=lambda: self._sort_tree(tree, 'path'))
                tree.heading('detail', text='詳細資訊 ↕️', command=lambda: self._sort_tree(tree, 'detail'))
                tree.heading('time', text='時間 ↕️', command=lambda: self._sort_tree(tree, 'time'))
                
                # 設定列寬
                tree.column('#0', width=200, minwidth=150)
                tree.column('operation', width=80, minwidth=60)
                tree.column('path', width=300, minwidth=200)
                tree.column('detail', width=250, minwidth=150)
                tree.column('time', width=150, minwidth=120)
                
                # 初始化排序狀態
                tree.sort_states = {col: 'none' for col in ['#0'] + list(columns)}
                
                tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
                
                # 添加垂直滾動條
                v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
                v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
                tree.configure(yscrollcommand=v_scrollbar.set)
                
                # 添加水平滾動條
                h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
                h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
                tree.configure(xscrollcommand=h_scrollbar.set)
                
                # 填充樹狀視圖數據
                for project_name, project_data in server_data['projects'].items():
                    # 創建專案節點
                    project_stats = project_data['stats']
                    project_text = f"[專案] {project_name} (新增:{project_stats['new_files']}, 更新:{project_stats['updated_files']}, 跳過:{project_stats['skipped_files']}, 刪除:{project_stats['deleted_files']})"
                    project_node = tree.insert('', 'end', text=project_text, values=('', '', '', ''))
                    
                    # 添加有實際操作的檔案記錄 (排除跳過的檔案)
                    actual_operations = [f for f in project_data['files'] if f['operation'] != 'skipped']
                    for file_info in actual_operations:
                        operation_icons = {
                            'new': '📄 新增',
                            'updated': '🔄 更新', 
                            'deleted': '🗑️ 刪除'
                        }
                        
                        operation_text = operation_icons.get(file_info['operation'], file_info['operation'])
                        # 從 path 中提取檔案名稱
                        filename = os.path.basename(file_info['path']) if file_info['path'] else ''
                        tree.insert(project_node, 'end', 
                                  text=filename,
                                  values=(operation_text, file_info['path'], 
                                         file_info['detail'], file_info['timestamp']))
                
                # 設定權重
                server_frame.columnconfigure(0, weight=1)
                server_frame.rowconfigure(1, weight=1)
                tree_frame.columnconfigure(0, weight=1)
                tree_frame.rowconfigure(0, weight=1)
            
            # 按鈕區域
            button_frame = ttk.Frame(main_frame)
            button_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
            
            ttk.Button(button_frame, text="關閉", command=report_dialog.destroy).grid(row=0, column=0)
            
            # 設定權重
            report_dialog.columnconfigure(0, weight=1)
            report_dialog.rowconfigure(0, weight=1)
            main_frame.columnconfigure(0, weight=1)
            main_frame.rowconfigure(3, weight=1)
            detail_frame.columnconfigure(0, weight=1)
            detail_frame.rowconfigure(0, weight=1)
            
        except Exception as e:
            self.logger.error(f"顯示發布報告時發生錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"無法顯示發布報告: {str(e)}")
    
    def _sort_tree(self, tree, column):
        """對樹狀視圖進行排序"""
        try:
            # 獲取當前排序狀態
            current_sort = tree.sort_states.get(column, 'none')
            
            # 切換排序方向
            if current_sort == 'none' or current_sort == 'desc':
                new_sort = 'asc'
                sort_icon = '↑'
            else:
                new_sort = 'desc'
                sort_icon = '↓'
            
            # 更新排序狀態
            tree.sort_states[column] = new_sort
            
            # 更新標題顯示
            column_titles = {
                '#0': '專案/檔案',
                'operation': '操作',
                'path': '路徑',
                'detail': '詳細資訊',
                'time': '時間'
            }
            
            # 重置所有標題
            for col, title in column_titles.items():
                if col == column:
                    tree.heading(col, text=f"{title} {sort_icon}")
                else:
                    tree.heading(col, text=f"{title} ↕️")
            
            # 對每個專案的檔案進行排序
            for project_item in tree.get_children():
                file_items = tree.get_children(project_item)
                if not file_items:
                    continue
                
                # 收集檔案數據
                file_data = []
                for file_item in file_items:
                    item_text = tree.item(file_item, 'text')
                    item_values = tree.item(file_item, 'values')
                    file_data.append({
                        'item_id': file_item,
                        'text': item_text,
                        'values': item_values
                    })
                
                # 排序檔案數據
                if column == '#0':
                    # 按專案/檔案名稱排序
                    file_data.sort(key=lambda x: x['text'].lower(), reverse=(new_sort == 'desc'))
                elif column == 'operation':
                    # 按操作類型排序
                    operation_order = {'📄 新增': 1, '🔄 更新': 2, '🗑️ 刪除': 3, '': 4}
                    file_data.sort(key=lambda x: operation_order.get(x['values'][0], 4), reverse=(new_sort == 'desc'))
                elif column == 'path':
                    # 按檔案路徑排序
                    file_data.sort(key=lambda x: x['values'][1].lower(), reverse=(new_sort == 'desc'))
                elif column == 'detail':
                    # 按詳細資訊排序
                    file_data.sort(key=lambda x: x['values'][2].lower(), reverse=(new_sort == 'desc'))
                elif column == 'time':
                    # 按時間排序
                    file_data.sort(key=lambda x: x['values'][3], reverse=(new_sort == 'desc'))
                
                # 重新排列項目
                for index, item_data in enumerate(file_data):
                    tree.move(item_data['item_id'], project_item, index)
            
        except Exception as e:
            # 排序出錯時不影響主要功能
            print(f"排序錯誤: {e}")
    
    def save_history_record(self, report, is_success=True):
        """保存發布記錄到歷史"""
        try:
            # 創建歷史記錄目錄
            if not os.path.exists('history'):
                os.makedirs('history')
            
            # 生成歷史記錄項目
            history_item = {
                'id': report['start_time'].strftime('%Y%m%d_%H%M%S'),
                'start_time': report['start_time'].isoformat(),
                'end_time': report['end_time'].isoformat() if report['end_time'] else None,
                'duration': (report['end_time'] - report['start_time']).total_seconds() if report['end_time'] else 0,
                'server_count': len(report['servers']),
                'total_stats': report['total_stats'].copy(),
                'servers': report['servers'].copy(),
                'status': '成功' if is_success else '失敗'
            }
            
            # 載入現有歷史記錄
            history_file = 'history/publish_history.json'
            history_records = []
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        history_records = json.load(f)
                except:
                    history_records = []
            
            # 添加新記錄到列表開頭（最新的在最上面）
            history_records.insert(0, history_item)
            
            # 保留最近100筆記錄
            if len(history_records) > 100:
                history_records = history_records[:100]
            
            # 保存歷史記錄
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_records, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"發布記錄已保存到歷史 ID: {history_item['id']}")
            
        except Exception as e:
            self.logger.error(f"保存歷史記錄失敗: {str(e)}")
    
    def load_history_records(self):
        """載入歷史記錄"""
        try:
            history_file = 'history/publish_history.json'
            if not os.path.exists(history_file):
                return []
            
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"載入歷史記錄失敗: {str(e)}")
            return []
    
    def refresh_history(self):
        """刷新歷史記錄顯示"""
        try:
            # 清空現有項目
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            
            # 載入歷史記錄
            history_records = self.load_history_records()
            
            # 填充到TreeView
            for record in history_records:
                start_time = datetime.fromisoformat(record['start_time']).strftime('%Y-%m-%d %H:%M:%S')
                duration = f"{record['duration']:.1f}"
                server_count = str(record['server_count'])
                
                # 計算總檔案操作數
                total_ops = (record['total_stats']['new_files'] + 
                           record['total_stats']['updated_files'] + 
                           record['total_stats']['skipped_files'] + 
                           record['total_stats']['deleted_files'])
                
                status = record['status']
                
                self.history_tree.insert('', 'end', iid=record['id'], values=(
                    start_time, duration, server_count, str(total_ops), status
                ))
            
            self.logger.info(f"已載入 {len(history_records)} 筆歷史記錄")
            
        except Exception as e:
            self.logger.error(f"刷新歷史記錄失敗: {str(e)}")
    
    def view_history_detail(self, event):
        """查看歷史記錄詳情"""
        try:
            # 獲取選中的項目
            selection = self.history_tree.selection()
            if not selection:
                return
            
            record_id = selection[0]
            
            # 載入歷史記錄
            history_records = self.load_history_records()
            target_record = None
            
            for record in history_records:
                if record['id'] == record_id:
                    target_record = record
                    break
            
            if not target_record:
                return
            
            # 生成詳細報告文字
            detail_text = self._generate_history_detail_text(target_record)
            
            # 顯示在詳細信息區域
            self.history_detail_text.config(state='normal')
            self.history_detail_text.delete('1.0', tk.END)
            self.history_detail_text.insert(tk.END, detail_text)
            self.history_detail_text.config(state='disabled')
            
        except Exception as e:
            self.logger.error(f"查看歷史詳情失敗: {str(e)}")
    
    def _generate_history_detail_text(self, record):
        """生成歷史記錄詳細文字"""
        lines = []
        
        # 基本資訊
        start_time = datetime.fromisoformat(record['start_time']).strftime('%Y-%m-%d %H:%M:%S')
        end_time = datetime.fromisoformat(record['end_time']).strftime('%Y-%m-%d %H:%M:%S') if record['end_time'] else '未知'
        
        lines.append(f"📋 發布資訊")
        lines.append(f"   記錄ID: {record['id']}")
        lines.append(f"   開始時間: {start_time}")
        lines.append(f"   結束時間: {end_time}")
        lines.append(f"   總耗時: {record['duration']:.2f} 秒")
        lines.append(f"   狀態: {record['status']}")
        lines.append("")
        
        # 總體統計
        stats = record['total_stats']
        lines.append(f"📊 總體統計")
        lines.append(f"   新增檔案: {stats['new_files']} 個")
        lines.append(f"   覆蓋檔案: {stats['updated_files']} 個")
        lines.append(f"   跳過檔案: {stats['skipped_files']} 個")
        lines.append(f"   刪除檔案: {stats['deleted_files']} 個")
        lines.append("")
        
        # 各伺服器詳情
        lines.append(f"🖥️ 伺服器詳情")
        for server_key, server_data in record['servers'].items():
            lines.append(f"   ── {server_key} ──")
            server_stats = server_data['stats']
            lines.append(f"   統計: 新增 {server_stats['new_files']}, 覆蓋 {server_stats['updated_files']}, 跳過 {server_stats['skipped_files']}, 刪除 {server_stats['deleted_files']}")
            
            for project_name, project_data in server_data['projects'].items():
                lines.append(f"   📁 {project_name}")
                project_stats = project_data['stats']
                lines.append(f"      統計: 新增 {project_stats['new_files']}, 覆蓋 {project_stats['updated_files']}, 跳過 {project_stats['skipped_files']}, 刪除 {project_stats['deleted_files']}")
                
                # 過濾並顯示有實際操作的檔案 (排除跳過的檔案)
                actual_operations = [f for f in project_data['files'] if f['operation'] != 'skipped']
                if actual_operations:
                    lines.append(f"      檔案操作 (顯示前10個實際操作):")
                    for i, file_info in enumerate(actual_operations[:10]):
                        operation_name = {
                            'new': '新增',
                            'updated': '覆蓋',
                            'deleted': '刪除'
                        }.get(file_info['operation'], '未知')
                        lines.append(f"        [{file_info['timestamp']}] {operation_name}: {file_info['path']}")
                    
                    if len(actual_operations) > 10:
                        lines.append(f"        ... 還有 {len(actual_operations) - 10} 個實際操作")
                lines.append("")
        
        return '\n'.join(lines)
    
    def delete_selected_history(self):
        """刪除選中的歷史記錄"""
        try:
            selection = self.history_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "請先選擇要刪除的記錄")
                return
            
            # 確認刪除
            if not messagebox.askyesno("確認刪除", "確定要刪除選中的發布記錄嗎？"):
                return
            
            # 載入歷史記錄
            history_records = self.load_history_records()
            
            # 刪除選中的記錄
            for record_id in selection:
                history_records = [r for r in history_records if r['id'] != record_id]
            
            # 保存更新後的歷史記錄
            history_file = 'history/publish_history.json'
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_records, f, ensure_ascii=False, indent=2)
            
            # 刷新顯示
            self.refresh_history()
            
            # 清空詳細信息區域
            self.history_detail_text.config(state='normal')
            self.history_detail_text.delete('1.0', tk.END)
            self.history_detail_text.config(state='disabled')
            
            messagebox.showinfo("成功", f"已刪除 {len(selection)} 筆記錄")
            
        except Exception as e:
            self.logger.error(f"刪除歷史記錄失敗: {str(e)}")
            messagebox.showerror("錯誤", f"刪除記錄失敗: {str(e)}")
    
    def clear_all_history(self):
        """清除所有歷史記錄"""
        try:
            # 確認清除
            if not messagebox.askyesno("確認清除", "確定要清除所有發布歷史記錄嗎？\n此操作無法復原！"):
                return
            
            # 清除歷史記錄檔案
            history_file = 'history/publish_history.json'
            if os.path.exists(history_file):
                os.remove(history_file)
            
            # 刷新顯示
            self.refresh_history()
            
            # 清空詳細信息區域
            self.history_detail_text.config(state='normal')
            self.history_detail_text.delete('1.0', tk.END)
            self.history_detail_text.config(state='disabled')
            
            messagebox.showinfo("成功", "所有歷史記錄已清除")
            
        except Exception as e:
            self.logger.error(f"清除歷史記錄失敗: {str(e)}")
            messagebox.showerror("錯誤", f"清除記錄失敗: {str(e)}")


    def _show_success_message(self):
        messagebox.showinfo("成功", "所有伺服器發布完成")
        
    def _show_error_message(self, error_msg):
        messagebox.showerror("錯誤", f"發布失敗: {error_msg}")
    
    def _send_email(self, recipients, subject, content):
        """發送電子郵件"""
        if not self.config['smtp_config']['smtp_server'] or not recipients:
            return
        
        try:
            smtp_config = self.config['smtp_config']
            
            # 創建郵件
            msg = MIMEMultipart()
            # 如果沒有配置用戶名，使用預設的 VSCC 發件人地址
            from_email = smtp_config['username'] if smtp_config['username'].strip() else 'noreply@vscc.org.tw'
            msg['From'] = from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = Header(subject, 'utf-8')
            
            # 添加郵件內容
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 發送郵件
            server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
            if smtp_config['use_tls']:
                # 檢查是否為 IP 地址
                import re
                is_ip = re.match(r'^\d+\.\d+\.\d+\.\d+$', smtp_config['smtp_server'])
                if is_ip:
                    # 對於 IP 地址，跳過主機名驗證
                    import ssl
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    server.starttls(context=context)
                else:
                    server.starttls()
            
            # 只有在提供用戶名時才進行身份驗證
            if smtp_config['username'].strip():
                server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"郵件發送成功，收件者: {', '.join(recipients)}")
            
        except Exception as e:
            self.logger.error(f"郵件發送失敗: {str(e)}")
    
    def _send_deployment_notification(self, is_success, start_time, end_time, error_msg=None):
        """發送部署結果通知郵件"""
        if not self.config['notification_emails'] or not self.config['smtp_config']['smtp_server']:
            return
        
        # 只對定時發布發送郵件通知
        if not self.config.get('schedule_time'):
            return
        
        try:
            date_str = datetime.now().strftime('%Y-%m-%d')
            status = "成功" if is_success else "失敗"
            subject = f"網站發布通知 - {date_str} - {status}"
            
            # 讀取日誌檔案內容
            log_content = ""
            try:
                log_file = f'logs/publish_{datetime.now().strftime("%Y%m%d")}.log'
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        # 獲取最近的發布日誌（從開始時間之後的日誌）
                        relevant_lines = []
                        for line in lines:
                            if start_time.strftime('%Y-%m-%d %H:%M') in line:
                                relevant_lines = lines[lines.index(line):]
                                break
                        log_content = ''.join(relevant_lines[-50:])  # 最後50行
            except Exception as e:
                log_content = f"無法讀取日誌檔案: {str(e)}"
            
            duration = (end_time - start_time).total_seconds()
            
            content = f"""網站發布助手自動部署通知

部署狀態: {status}
部署日期: {date_str}
開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
結束時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
執行時間: {duration:.2f} 秒
目標伺服器數量: {len(self.config['servers'])}

"""
            
            if error_msg:
                content += f"錯誤訊息: {error_msg}\n\n"
            
            content += f"""伺服器列表:
"""
            for i, server in enumerate(self.config['servers'], 1):
                content += f"{i}. {server['ip']} - {server['path']}\n"
            
            content += f"""

發布日誌:
==========================================
{log_content}
==========================================

此為系統自動發送的通知郵件。
網站發布助手 v2.0
"""
            
            # 發送郵件
            self._send_email(self.config['notification_emails'], subject, content)
            self.logger.info(f"部署通知郵件已發送給 {len(self.config['notification_emails'])} 位收件者")
            
        except Exception as e:
            self.logger.error(f"發送部署通知郵件失敗: {str(e)}")
    
    def _send_error_notification(self, error_type, error_msg):
        """發送程式異常通知郵件"""
        if not self.config['notification_emails'] or not self.config['smtp_config']['smtp_server']:
            return
        
        try:
            date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            subject = f"網站發布助手異常通知 - {error_type} - {date_str}"
            
            content = f"""網站發布助手程式異常通知

異常類型: {error_type}
發生時間: {date_str}
錯誤訊息: {error_msg}

程式狀態: 異常終止

請檢查系統狀態並重新啟動程式。

此為系統自動發送的異常通知郵件。
網站發布助手 v2.0
"""
            
            # 發送郵件
            self._send_email(self.config['notification_emails'], subject, content)
            self.logger.error(f"異常通知郵件已發送: {error_type}")
            
        except Exception as e:
            self.logger.error(f"發送異常通知郵件失敗: {str(e)}")
            
    def _publish_to_server(self, server):
        """使用Windows網路共享方式合併式發布到伺服器"""
        try:
            # 初始化伺服器報告
            server_key = f"{server['ip']} ({server['path']})"
            self.publish_report['servers'][server_key] = {
                'projects': {},
                'stats': {
                    'new_files': 0,
                    'updated_files': 0,
                    'skipped_files': 0,
                    'deleted_files': 0
                }
            }
            self.current_server_key = server_key
            
            # 解析遠端路徑設定
            remote_path = server['path']
            remote_ip = server['ip']
            remote_user = server['username']
            remote_pass = server['password']
            
            try:
                drive_letter = remote_path.split(':')[0]
                dir_path = remote_path.split(':')[1].lstrip('\\')
                
                # 完整的 UNC 目標路徑
                full_unc_path = f"\\\\{remote_ip}\\{drive_letter}$\\{dir_path}"
                share_to_map = f"\\\\{remote_ip}\\{drive_letter}$"
                
            except IndexError:
                raise Exception(f"遠端路徑格式不正確: {remote_path}，應為 'D:\\資料夾' 格式")

            # 網路連接命令
            connection_command = [
                "net", "use", share_to_map, remote_pass, f"/user:{remote_user}", "/persistent:no"
            ]
            disconnection_command = [
                "net", "use", share_to_map, "/delete"
            ]

            try:
                # 1. 建立網路連接
                self.logger.info(f"正在連線至 {share_to_map}...")
                subprocess.run(connection_command, check=True, capture_output=True)
                self.logger.info("✅ 遠端主機連線成功")

                # 2. 確保遠端目標目錄存在
                if not os.path.exists(full_unc_path):
                    self.logger.info(f"⚠️ 警告: 遠端目錄 '{full_unc_path}' 不存在，正在嘗試建立...")
                    os.makedirs(full_unc_path)
                
                # 3. 合併式部署 - 覆蓋衝突檔案，保留其餘檔案
                for source in self.config['source_files']:
                    if os.path.isfile(source):
                        project_name = os.path.splitext(os.path.basename(source))[0]
                    elif os.path.isdir(source):
                        project_name = os.path.basename(source)
                    else:
                        continue
                        
                    remote_target_dir = os.path.join(full_unc_path, project_name)
                    
                    # 初始化專案報告
                    self.publish_report['servers'][self.current_server_key]['projects'][project_name] = {
                        'files': [],
                        'stats': {
                            'new_files': 0,
                            'updated_files': 0,
                            'skipped_files': 0,
                            'deleted_files': 0
                        }
                    }
                    self.current_project = project_name
                    
                    self.logger.info(f"正在合併部署 '{source}' 至 '{remote_target_dir}'...")
                    
                    try:
                        # 確保目標專案目錄存在
                        if not os.path.exists(remote_target_dir):
                            self.logger.info(f"  建立目標專案目錄: {remote_target_dir}")
                            os.makedirs(remote_target_dir)
                        
                        if os.path.isfile(source):
                            # 單一檔案處理 - 直接複製覆蓋
                            target_file = os.path.join(remote_target_dir, os.path.basename(source))
                            filename = os.path.basename(source)
                            
                            # 檢查是否為覆蓋還是新增
                            if os.path.exists(target_file):
                                # 比較檔案
                                src_size = os.path.getsize(source)
                                dst_size = os.path.getsize(target_file)
                                src_mtime = os.path.getmtime(source)
                                dst_mtime = os.path.getmtime(target_file)
                                
                                if src_size == dst_size and abs(src_mtime - dst_mtime) < 2:
                                    operation_type = 'skipped'
                                    operation_detail = "檔案內容相同"
                                    self.logger.info(f"  ⏭️ 跳過相同檔案: {filename}")
                                else:
                                    operation_type = 'updated'
                                    operation_detail = f"大小: {src_size} bytes, 修改時間: {datetime.fromtimestamp(src_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
                                    self.logger.info(f"  🔄 覆蓋檔案: {filename}")
                                    shutil.copy2(source, target_file)
                            else:
                                operation_type = 'new'
                                src_size = os.path.getsize(source)
                                src_mtime = os.path.getmtime(source)
                                operation_detail = f"大小: {src_size} bytes, 修改時間: {datetime.fromtimestamp(src_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
                                self.logger.info(f"  ➕ 新增檔案: {filename}")
                                shutil.copy2(source, target_file)
                            
                            # 記錄檔案操作
                            self._record_file_operation(operation_type, "", filename, operation_detail)
                            
                            # 更新進度
                            if hasattr(self, 'update_progress'):
                                self.update_progress(1)
                            
                        elif os.path.isdir(source):
                            # 目錄處理 - 合併複製，保留不衝突的檔案
                            self.logger.info(f"  📁 開始合併目錄內容...")
                            self._merge_directory_to_target(source, remote_target_dir)
                        
                        self.logger.info(f"  ✅ 專案 '{project_name}' 合併部署成功！")
                        
                    except Exception as e:
                        self.logger.error(f"  ❌ 合併部署失敗: {e}")
                        raise  # 重新拋出異常以中止後續操作
                
                self.logger.info("✅ 所有專案合併式部署成功！")

            except subprocess.CalledProcessError as e:
                error_message = e.stderr.decode('cp950', errors='ignore') if e.stderr else str(e)
                self.logger.error("❌ 錯誤: 建立遠端連線失敗")
                self.logger.error("請確認：1.帳號密碼正確 2.防火牆設定 3.遠端主機已啟用系統管理分享(C$, D$)")
                self.logger.error(f"詳細錯誤: {error_message.strip()}")
                raise Exception(f"網路連線失敗: {error_message.strip()}")
            
            finally:
                # 4. 中斷連線
                self.logger.info("正在中斷遠端連線...")
                subprocess.run(disconnection_command, capture_output=True)
                self.logger.info("--- 遠端傳輸流程結束 ---")
                
        except Exception as e:
            self.logger.error(f"發布到伺服器失敗: {server['ip']} - {str(e)}")
            raise
    
    def _record_file_operation(self, operation_type, relative_path, filename, detail):
        """記錄檔案操作到報告中"""
        if not hasattr(self, 'current_server_key') or not hasattr(self, 'current_project'):
            return
            
        # 構建完整的檔案路徑
        if relative_path:
            full_path = f"{relative_path}/{filename}" if relative_path else filename
        else:
            full_path = filename
            
        # 記錄到專案報告
        project_report = self.publish_report['servers'][self.current_server_key]['projects'][self.current_project]
        project_report['files'].append({
            'path': full_path,
            'operation': operation_type,
            'detail': detail,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
        # 更新統計
        if operation_type == 'new':
            key = 'new_files'
        elif operation_type == 'updated':
            key = 'updated_files'
        elif operation_type == 'skipped':
            key = 'skipped_files'
        elif operation_type == 'deleted':
            key = 'deleted_files'
        else:
            return
            
        # 更新專案統計
        project_report['stats'][key] += 1
        
        # 更新伺服器統計
        self.publish_report['servers'][self.current_server_key]['stats'][key] += 1
        
        # 更新總體統計
        self.publish_report['total_stats'][key] += 1
    
    def _merge_directory_to_target(self, src_dir, dst_dir, relative_path=""):
        """合併式複製目錄到目標位置，覆蓋衝突檔案，保留不衝突檔案"""
        # 確保目標目錄存在
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        
        for item in os.listdir(src_dir):
            # 檢查是否為需要刪除的檔案，如果是則跳過
            if item in self.config['delete_files']:
                self.logger.info(f"    ⏭️ 跳過複製需刪除的檔案: {item}")
                self._record_file_operation('deleted', relative_path, item, "跳過複製需刪除的檔案")
                continue
                
            src_item = os.path.join(src_dir, item)
            dst_item = os.path.join(dst_dir, item)
            item_relative_path = os.path.join(relative_path, item) if relative_path else item
            
            if os.path.isfile(src_item):
                # 檔案處理：檢查是否需要複製
                should_copy = True
                operation_type = 'new'
                operation_detail = ""
                
                if os.path.exists(dst_item):
                    # 比較檔案大小和修改時間
                    src_size = os.path.getsize(src_item)
                    dst_size = os.path.getsize(dst_item)
                    src_mtime = os.path.getmtime(src_item)
                    dst_mtime = os.path.getmtime(dst_item)
                    
                    if src_size == dst_size and abs(src_mtime - dst_mtime) < 2:
                        # 檔案相同，跳過複製
                        self.logger.info(f"    ⏭️ 跳過相同檔案: {item}")
                        should_copy = False
                        operation_type = 'skipped'
                        operation_detail = "檔案內容相同"
                        # 更新進度
                        if hasattr(self, 'update_progress'):
                            self.update_progress(1)
                    else:
                        self.logger.info(f"    🔄 覆蓋檔案: {item} (大小或時間不同)")
                        operation_type = 'updated'
                        operation_detail = f"大小: {src_size} bytes, 修改時間: {datetime.fromtimestamp(src_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
                else:
                    self.logger.info(f"    ➕ 新增檔案: {item}")
                    operation_type = 'new'
                    src_size = os.path.getsize(src_item)
                    src_mtime = os.path.getmtime(src_item)
                    operation_detail = f"大小: {src_size} bytes, 修改時間: {datetime.fromtimestamp(src_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
                
                # 記錄檔案操作
                self._record_file_operation(operation_type, relative_path, item, operation_detail)
                
                if should_copy:
                    shutil.copy2(src_item, dst_item)
                    # 更新進度
                    if hasattr(self, 'update_progress'):
                        self.update_progress(1)
                
            elif os.path.isdir(src_item):
                # 目錄處理：遞迴合併
                if os.path.exists(dst_item):
                    self.logger.info(f"    📁 合併目錄: {item}")
                else:
                    self.logger.info(f"    📁 建立目錄: {item}")
                self._merge_directory_to_target(src_item, dst_item, item_relative_path)
            

                
    def load_config(self):
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合併配置，確保新鍵不會丟失
                    for key, value in loaded_config.items():
                        self.config[key] = value
                    
                    # 確保所有必要的鍵都存在
                    if 'notification_emails' not in self.config:
                        self.config['notification_emails'] = []
                    if 'smtp_config' not in self.config:
                        self.config['smtp_config'] = {
                            'smtp_server': '',
                            'smtp_port': 587,
                            'username': '',
                            'password': '',
                            'use_tls': True
                        }
                    
                # 清空現有GUI內容
                self.source_listbox.delete(0, tk.END)
                self.delete_listbox.delete(0, tk.END)
                self.server_listbox.delete(0, tk.END)
                
                # 載入GUI狀態
                for source in self.config.get('source_files', []):
                    self.source_listbox.insert(tk.END, source)
                    
                for delete_file in self.config.get('delete_files', []):
                    self.delete_listbox.insert(tk.END, delete_file)
                    
                for server in self.config.get('servers', []):
                    self.server_listbox.insert(tk.END, f"{server['ip']} - {server['path']}")
                    
                # 更新伺服器顯示
                self.update_server_display()
                
                # 載入SMTP設定
                smtp_config = self.config.get('smtp_config', {})
                if hasattr(self, 'smtp_server_var'):
                    self.smtp_server_var.set(smtp_config.get('smtp_server', ''))
                    self.smtp_port_var.set(str(smtp_config.get('smtp_port', 587)))
                    self.smtp_username_var.set(smtp_config.get('username', ''))
                    self.smtp_password_var.set(smtp_config.get('password', ''))
                    self.use_tls_var.set(smtp_config.get('use_tls', True))
                
                # 載入通知人員名單
                if hasattr(self, 'notify_listbox'):
                    for email in self.config.get('notification_emails', []):
                        self.notify_listbox.insert(tk.END, email)
                    
                # 恢復定時設定
                if self.config.get('schedule_time'):
                    schedule_time = datetime.fromisoformat(self.config['schedule_time'])
                    if schedule_time > datetime.now():
                        self.next_publish_var.set(schedule_time.strftime("%Y-%m-%d %H:%M:%S"))
                        delay = (schedule_time - datetime.now()).total_seconds()
                        self.publish_timer = threading.Timer(delay, self.publish_now)
                        self.publish_timer.start()
                        self.start_countdown()
                    else:
                        self.config['schedule_time'] = None
                        
        except Exception as e:
            print(f"載入配置失敗: {e}")
            
    def save_config(self):
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存配置失敗: {e}")
            
    def run(self):
        try:
            self.root.mainloop()
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"程式異常終止: {error_msg}")
            # 發送異常通知郵件
            self._send_error_notification("程式異常終止", error_msg)
            raise
        finally:
            if self.publish_timer:
                self.publish_timer.cancel()

    def get_directory_info(self, directory):
        """獲取資料夾的檔案數量和總大小"""
        total_files = 0
        total_size = 0
        
        for root, dirs, files in os.walk(directory):
            total_files += len(files)
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, IOError):
                    # 跳過無法存取的檔案
                    pass
        
        return total_files, total_size

    def format_size(self, size_bytes):
        """格式化檔案大小顯示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def show_progress(self, current, total, prefix="Progress", bar_length=50):
        """顯示進度條"""
        percent = (current / total) * 100
        filled_length = int(bar_length * current // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        sys.stdout.write(f'\r{prefix}: |{bar}| {current}/{total} ({percent:.1f}%)')
        sys.stdout.flush()
        
        if current == total:
            print()  # 完成後換行

    def copytree_with_progress(self, src, dst):
        """帶進度條的資料夾複製"""
        print(f"  正在分析資料夾結構...")
        total_files, total_size = self.get_directory_info(src)
        
        print(f"  檔案數量: {total_files}")
        print(f"  總大小: {self.format_size(total_size)}")
        
        copied_files = 0
        copied_size = 0
        
        def copy_function(src_file, dst_file):
            nonlocal copied_files, copied_size
            
            # 建立目標目錄
            dst_dir = os.path.dirname(dst_file)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            
            # 複製檔案
            shutil.copy2(src_file, dst_file)
            
            # 更新進度
            try:
                file_size = os.path.getsize(src_file)
                copied_size += file_size
            except (OSError, IOError):
                pass
            
            copied_files += 1
            self.show_progress(copied_files, total_files, "複製進度")
        
        # 遞迴複製所有檔案
        def copy_tree_recursive(src_path, dst_path):
            if not os.path.exists(dst_path):
                os.makedirs(dst_path)
            
            for item in os.listdir(src_path):
                src_item = os.path.join(src_path, item)
                dst_item = os.path.join(dst_path, item)
                
                if os.path.isdir(src_item):
                    copy_tree_recursive(src_item, dst_item)
                else:
                    copy_function(src_item, dst_item)
        
        copy_tree_recursive(src, dst)


class ServerDialog:
    def __init__(self, parent, server_info=None):
        self.result = None
        self.server_info = server_info
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("編輯伺服器" if server_info else "新增伺服器")
        self.dialog.geometry("700x350")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()
        
        # 居中顯示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 說明標題
        title_label = ttk.Label(main_frame, text="Windows網路共享設定", font=('Arial', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # 說明文字
        help_text = "此設定使用Windows網路共享方式(UNC路徑)連接到遠端伺服器，無需設定SSH。\n請確保遠端伺服器已啟用系統管理分享(如C$, D$)。"
        help_label = ttk.Label(main_frame, text=help_text, foreground="blue", wraplength=650)
        help_label.grid(row=1, column=0, columnspan=2, pady=(0, 15))
        
        # IP地址
        ttk.Label(main_frame, text="遠端主機IP:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.ip_var = tk.StringVar()
        ip_entry = ttk.Entry(main_frame, textvariable=self.ip_var, width=80)
        ip_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 使用者名稱
        ttk.Label(main_frame, text="管理員帳號:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(main_frame, textvariable=self.username_var, width=80)
        username_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 密碼
        ttk.Label(main_frame, text="管理員密碼:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.password_var = tk.StringVar()
        password_frame = ttk.Frame(main_frame)
        password_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.password_entry = ttk.Entry(password_frame, textvariable=self.password_var, width=25, show="*")
        self.password_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.show_password_var = tk.BooleanVar()
        ttk.Checkbutton(password_frame, text="顯示", variable=self.show_password_var, 
                       command=self.toggle_password).grid(row=0, column=1, padx=(5, 0))
        password_frame.columnconfigure(0, weight=1)
        
        # 目標路徑
        ttk.Label(main_frame, text="目標路徑:").grid(row=5, column=0, sticky=tk.W, pady=(0, 5))
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(main_frame, textvariable=self.path_var, width=80)
        path_entry.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 路徑說明
        path_help = "格式: D:\\VSCC_3G1 (必須包含磁碟機代號，系統會自動轉換為UNC路徑)"
        ttk.Label(main_frame, text=path_help, foreground="gray", font=('Arial', 8)).grid(row=6, column=1, sticky=tk.W, pady=(0, 15))
        
        # 如果是編輯模式，填入現有資料
        if self.server_info:
            self.ip_var.set(self.server_info.get('ip', ''))
            self.username_var.set(self.server_info.get('username', ''))
            self.password_var.set(self.server_info.get('password', ''))
            self.path_var.set(self.server_info.get('path', ''))
        
        # 設定預設值
        if not self.server_info:
            self.username_var.set("Administrator")
            self.path_var.set("D:\\VSCC_3G1")
        
        # 按鈕
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="測試連接", command=self.test_connection).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="確定", command=self.ok_clicked).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=self.cancel_clicked).grid(row=0, column=2)
        
        main_frame.columnconfigure(1, weight=1)
        
    def toggle_password(self):
        if self.show_password_var.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")
            
    def test_connection(self):
        if not all([self.ip_var.get(), self.username_var.get(), self.password_var.get(), self.path_var.get()]):
            messagebox.showerror("錯誤", "請填寫所有必要欄位")
            return
            
        server_info = {
            'ip': self.ip_var.get(),
            'username': self.username_var.get(),
            'password': self.password_var.get(),
            'path': self.path_var.get()
        }
        
        # 在新線程中測試連接
        test_thread = threading.Thread(target=self._test_connection, args=(server_info,))
        test_thread.daemon = True
        test_thread.start()
        
    def _test_connection(self, server_info):
        try:
            # 解析遠端路徑
            remote_path = server_info['path']
            remote_ip = server_info['ip']
            remote_user = server_info['username']
            remote_pass = server_info['password']
            
            try:
                drive_letter = remote_path.split(':')[0]
                dir_path = remote_path.split(':')[1].lstrip('\\')
                
                # 完整的 UNC 目標路徑
                full_unc_path = f"\\\\{remote_ip}\\{drive_letter}$\\{dir_path}"
                share_to_map = f"\\\\{remote_ip}\\{drive_letter}$"
                
            except IndexError:
                error_msg = f"遠端路徑格式不正確: {remote_path}\n應為 'D:\\資料夾' 格式"
                self.dialog.after(0, lambda: messagebox.showerror("路徑錯誤", error_msg))
                return

            # 網路連接命令
            connection_command = [
                "net", "use", share_to_map, remote_pass, f"/user:{remote_user}", "/persistent:no"
            ]
            disconnection_command = [
                "net", "use", share_to_map, "/delete"
            ]

            # 測試網路連接
            subprocess.run(connection_command, check=True, capture_output=True, text=True)
            
            # 測試目標路徑存取
            access_test = os.path.exists(full_unc_path)
            
            # 中斷連接
            subprocess.run(disconnection_command, capture_output=True)
            
            if access_test:
                success_msg = f"連接測試成功！\n伺服器: {server_info['ip']}\n網路路徑: {full_unc_path}\n狀態: 可正常存取"
                self.dialog.after(0, lambda: messagebox.showinfo("連接測試", success_msg))
            else:
                warning_msg = f"連接成功但路徑不存在！\n伺服器: {server_info['ip']}\n網路路徑: {full_unc_path}\n建議檢查路徑設定或手動建立資料夾"
                self.dialog.after(0, lambda: messagebox.showwarning("連接測試", warning_msg))
                
        except subprocess.CalledProcessError as e:
            error_message = e.stderr if e.stderr else str(e)
            error_msg = f"網路共享連接失敗\n伺服器: {server_info['ip']}\n\n可能原因:\n1. 帳號密碼錯誤\n2. 網路不通\n3. 遠端主機未啟用系統管理分享(C$, D$)\n4. 防火牆阻擋\n\n詳細錯誤: {error_message}"
            self.dialog.after(0, lambda: messagebox.showerror("連接測試失敗", error_msg))
            
        except Exception as e:
            error_msg = f"連接失敗: {str(e)}\n\n可能原因:\n1. IP地址錯誤\n2. 網路不通\n3. 遠端主機未開機\n4. 防火牆阻擋"
            self.dialog.after(0, lambda: messagebox.showerror("連接測試失敗", error_msg))
        
    def ok_clicked(self):
        if all([self.ip_var.get(), self.username_var.get(), self.password_var.get(), self.path_var.get()]):
            # 簡單驗證路徑格式
            if ':' not in self.path_var.get():
                messagebox.showerror("錯誤", "路徑格式不正確，應為 'D:\\資料夾' 格式")
                return
                
            self.result = {
                'ip': self.ip_var.get(),
                'username': self.username_var.get(),
                'password': self.password_var.get(),
                'path': self.path_var.get()
            }
            self.dialog.destroy()
        else:
            messagebox.showerror("錯誤", "請填寫所有必要欄位")
            
    def cancel_clicked(self):
        self.dialog.destroy()
        
    def get_server_info(self):
        self.dialog.wait_window()
        return self.result


if __name__ == "__main__":
    try:
        app = WebsitePublisher()
        app.run()
    except KeyboardInterrupt:
        print("程式被使用者中斷")
    except Exception as e:
        print(f"程式發生未預期的錯誤: {e}")
        if 'app' in locals():
            app._send_error_notification("未預期的錯誤", str(e))
        raise