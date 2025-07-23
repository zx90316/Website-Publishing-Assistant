import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
import json
import os
import shutil
import threading
import time
from datetime import datetime, timedelta
import paramiko
import logging


class WebsitePublisher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("網站發布助手")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # 設置LOG記錄
        self.setup_logging()
        
        # 設定數據
        self.config = {
            'source_files': [],
            'delete_files': [],
            'servers': [],
            'schedule_time': None
        }
        
        # 定時器變量
        self.publish_timer = None
        self.countdown_timer = None
        self.is_countdown_active = False
        
        # 創建GUI
        self.create_gui()
        
        # 載入配置
        self.load_config()
        
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
        
        # 發布頁面
        self.create_publish_tab(notebook)
        
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
        
        # 設定權重
        publish_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=1)
        
        # 更新伺服器顯示
        self.update_server_display()
        
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
        """在背景線程中測試連接"""
        self.status_var.set(f"正在測試連接到 {server['ip']}...")
        self.logger.info(f"開始測試連接: {server['ip']}")
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 設定連接超時
            ssh.connect(
                hostname=server['ip'],
                username=server['username'],
                password=server['password'],
                timeout=10
            )
            
            # 測試基本命令
            stdin, stdout, stderr = ssh.exec_command('echo "Connection test successful"')
            result = stdout.read().decode().strip()
            
            # 測試目標路徑是否存在
            if '\\' in server['path']:
                # Windows路徑 - 使用適當的編碼處理中文
                stdin, stdout, stderr = ssh.exec_command(f'dir "{server["path"]}" 2>nul || echo "PATH_NOT_EXISTS"')
            else:
                # Linux路徑
                stdin, stdout, stderr = ssh.exec_command(f'ls -la "{server["path"]}" 2>/dev/null || echo "PATH_NOT_EXISTS"')
            
            # 讀取輸出並處理編碼問題
            stdout_bytes = stdout.read()
            try:
                path_result = stdout_bytes.decode('utf-8').strip()
            except UnicodeDecodeError:
                # 如果UTF-8解碼失敗，嘗試其他編碼
                try:
                    path_result = stdout_bytes.decode('cp950').strip()  # 繁體中文Windows
                except UnicodeDecodeError:
                    try:
                        path_result = stdout_bytes.decode('gbk').strip()  # 簡體中文Windows
                    except UnicodeDecodeError:
                        path_result = stdout_bytes.decode('latin-1').strip()  # 最後備選
            
            ssh.close()
            
            if "PATH_NOT_EXISTS" in path_result:
                message = f"連接成功！\n但目標路徑不存在: {server['path']}\n建議檢查路徑設定"
                self.logger.warning(f"連接成功但路徑不存在: {server['ip']} - {server['path']}")
                self.root.after(0, lambda: messagebox.showwarning("連接測試", message))
            else:
                message = f"連接測試成功！\n伺服器: {server['ip']}\n目標路徑: {server['path']}\n狀態: 正常"
                self.logger.info(f"連接測試成功: {server['ip']}")
                self.root.after(0, lambda: messagebox.showinfo("連接測試", message))
                
            self.status_var.set("連接測試完成")
            
        except paramiko.AuthenticationException:
            error_msg = f"認證失敗: 使用者名稱或密碼錯誤\n伺服器: {server['ip']}"
            self.logger.error(f"認證失敗: {server['ip']}")
            self.root.after(0, lambda: messagebox.showerror("連接測試失敗", error_msg))
            self.status_var.set("連接測試失敗: 認證錯誤")
            
        except paramiko.SSHException as e:
            error_msg = f"SSH連接錯誤: {str(e)}\n伺服器: {server['ip']}"
            self.logger.error(f"SSH連接錯誤: {server['ip']} - {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("連接測試失敗", error_msg))
            self.status_var.set("連接測試失敗: SSH錯誤")
            
        except Exception as e:
            error_msg = f"連接失敗: {str(e)}\n伺服器: {server['ip']}\n\n可能原因:\n1. IP地址錯誤\n2. 網路不通\n3. SSH服務未啟動\n4. 防火牆阻擋"
            self.logger.error(f"連接測試失敗: {server['ip']} - {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("連接測試失敗", error_msg))
            self.status_var.set("連接測試失敗")
            
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
        
    def _publish_worker(self):
        start_time = datetime.now()
        self.logger.info("=== 開始發布作業 ===")
        self.logger.info(f"發布時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"源文件數量: {len(self.config['source_files'])}")
        self.logger.info(f"目標伺服器數量: {len(self.config['servers'])}")
        
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
            
            self.status_var.set("發布完成")
            self.logger.info(f"=== 發布作業完成 ===")
            self.logger.info(f"成功發布到 {success_count}/{len(self.config['servers'])} 個伺服器")
            self.logger.info(f"總耗時: {total_duration:.2f} 秒")
            self.root.after(0, self._show_success_message)
            
        except Exception as e:
            error_msg = str(e)
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            self.status_var.set(f"發布失敗: {error_msg}")
            self.logger.error(f"=== 發布作業失敗 ===")
            self.logger.error(f"錯誤訊息: {error_msg}")
            self.logger.error(f"失敗時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.error(f"已執行時間: {total_duration:.2f} 秒")
            self.root.after(0, lambda msg=error_msg: self._show_error_message(msg))
            
    def _show_success_message(self):
        messagebox.showinfo("成功", "所有伺服器發布完成")
        
    def _show_error_message(self, error_msg):
        messagebox.showerror("錯誤", f"發布失敗: {error_msg}")
            
    def _publish_to_server(self, server):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=server['ip'],
                username=server['username'],
                password=server['password']
            )
            
            sftp = ssh.open_sftp()
            
            # 首先確保目標目錄存在
            self.logger.info(f"確保目標目錄存在: {server['path']}")
            if '\\' in server['path']:
                # Windows命令 - 使用md來創建多層目錄
                stdin, stdout, stderr = ssh.exec_command(f'if not exist "{server["path"]}" md "{server["path"]}"')
                stdout.read()
            else:
                # Linux命令
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {server['path']}")
                stdout.read()
            
            # 創建臨時目錄
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_path = f"{server['path']}_TEMP_{timestamp}"
            
            # 創建遠程臨時目錄
            self.logger.info(f"創建臨時目錄: {temp_path}")
            if '\\' in server['path']:
                # Windows命令 - 使用md來創建多層目錄
                stdin, stdout, stderr = ssh.exec_command(f'md "{temp_path}" 2>nul')
                stdout.read()  # 等待命令完成
            else:
                # Linux命令
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {temp_path}")
                stdout.read()  # 等待命令完成
            
            # 處理每個源檔案/目錄作為獨立專案
            for source in self.config['source_files']:
                self.logger.info(f"處理源文件: {source}")
                
                if os.path.isfile(source):
                    # 單一檔案 - 直接放在父目錄下
                    project_name = os.path.splitext(os.path.basename(source))[0]
                    project_temp_path = f"{temp_path}\\{project_name}" if '\\' in server['path'] else f"{temp_path}/{project_name}"
                    project_temp_path_sftp = project_temp_path.replace('\\', '/')
                    
                    # 創建專案臨時目錄 (SSH命令)
                    if '\\' in server['path']:
                        stdin, stdout, stderr = ssh.exec_command(f'md "{project_temp_path}" 2>nul')
                        stdout.read()  # 等待命令完成
                    else:
                        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {project_temp_path}")
                        stdout.read()  # 等待命令完成
                    
                    # 同時通過SFTP創建目錄（確保SFTP能夠訪問）
                    try:
                        sftp.mkdir(project_temp_path_sftp)
                    except OSError:
                        pass  # 目錄可能已存在
                    
                    remote_file = f"{project_temp_path_sftp}/{os.path.basename(source)}"
                    self.logger.info(f"上傳單一檔案: {source} -> {remote_file}")
                    sftp.put(source, remote_file)
                    
                elif os.path.isdir(source):
                    # 目錄 - 以目錄名稱作為專案名稱
                    project_name = os.path.basename(source)
                    project_temp_path = f"{temp_path}\\{project_name}" if '\\' in server['path'] else f"{temp_path}/{project_name}"
                    project_temp_path_sftp = project_temp_path.replace('\\', '/')
                    
                    self.logger.info(f"處理專案目錄: {source} -> {project_name}")
                    
                    # 創建專案臨時目錄 (SSH命令)
                    if '\\' in server['path']:
                        stdin, stdout, stderr = ssh.exec_command(f'md "{project_temp_path}" 2>nul')
                        stdout.read()  # 等待命令完成
                    else:
                        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {project_temp_path}")
                        stdout.read()  # 等待命令完成
                    
                    # 同時通過SFTP創建目錄（確保SFTP能夠訪問）
                    try:
                        sftp.mkdir(project_temp_path_sftp)
                    except OSError:
                        pass  # 目錄可能已存在
                    
                    # 上傳目錄內容到專案目錄（跳過需要刪除的檔案）
                    for item in os.listdir(source):
                        local_item = os.path.join(source, item)
                        
                        # 檢查是否為需要刪除的檔案，如果是則跳過上傳
                        if item in self.config['delete_files']:
                            self.logger.info(f"跳過上傳需刪除的檔案: {item}")
                            continue
                        
                        remote_item = f"{project_temp_path_sftp}/{item}"
                        
                        if os.path.isfile(local_item):
                            self.logger.info(f"上傳檔案: {local_item} -> {remote_item}")
                            sftp.put(local_item, remote_item)
                        elif os.path.isdir(local_item):
                            self.logger.info(f"上傳子目錄: {local_item} -> {remote_item}")
                            self._upload_directory(sftp, ssh, local_item, remote_item)
                    
            # 合併式部署 - 將新檔案與伺服器既有檔案合併
            for source in self.config['source_files']:
                if os.path.isfile(source):
                    project_name = os.path.splitext(os.path.basename(source))[0]
                elif os.path.isdir(source):
                    project_name = os.path.basename(source)
                else:
                    continue
                    
                project_path = f"{server['path']}\\{project_name}" if '\\' in server['path'] else f"{server['path']}/{project_name}"
                project_temp_path = f"{temp_path}\\{project_name}" if '\\' in server['path'] else f"{temp_path}/{project_name}"
                
                self.logger.info(f"合併部署專案: {project_name}")
                
                # 確保目標專案目錄存在
                if '\\' in server['path']:
                    stdin, stdout, stderr = ssh.exec_command(f'if not exist "{project_path}" md "{project_path}"')
                    stdout.read()
                else:
                    stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {project_path}")
                    stdout.read()
                
                if '\\' in server['path']:
                    # Windows命令 - 使用xcopy進行合併複製（覆蓋既有檔案以更新功能）
                    # /E: 複製目錄和子目錄，包括空目錄
                    # /H: 複製隱藏和系統檔案
                    # /K: 複製屬性
                    # /Y: 自動覆蓋既有檔案（用於功能更新）
                    stdin, stdout, stderr = ssh.exec_command(f'xcopy "{project_temp_path}\\*" "{project_path}" /E /H /K /Y')
                    stdout.read()
                else:
                    # Linux命令 - 使用rsync覆蓋既有檔案
                    stdin, stdout, stderr = ssh.exec_command(f"rsync -av {project_temp_path}/ {project_path}/")
                    stdout.read()
                
                self.logger.info(f"專案 {project_name} 合併完成")
            
            # 清理臨時目錄
            if '\\' in server['path']:
                ssh.exec_command(f'rmdir /s /q "{temp_path}" 2>nul')
            else:
                ssh.exec_command(f"rm -rf {temp_path}")
                
            self.logger.info("合併式部署完成")
            
        finally:
            sftp.close()
            ssh.close()
            
    def _upload_directory(self, sftp, ssh, local_dir, remote_dir):
        # SFTP路徑統一使用正斜線
        remote_dir_sftp = remote_dir.replace('\\', '/')
        
        # 檢查是否為Windows系統來決定使用的SSH命令
        if '\\' in remote_dir:
            ssh.exec_command(f'md "{remote_dir}" 2>nul')
        else:
            ssh.exec_command(f"mkdir -p {remote_dir}")
        
        for root, dirs, files in os.walk(local_dir):
            # 創建遠程目錄結構
            relative_path = os.path.relpath(root, local_dir)
            if relative_path != '.':
                remote_path = f"{remote_dir}/{relative_path}".replace('\\', '/')
                remote_path_sftp = f"{remote_dir_sftp}/{relative_path}".replace('\\', '/')
            else:
                remote_path = remote_dir
                remote_path_sftp = remote_dir_sftp
                
            # 創建目錄
            if '\\' in remote_dir:
                ssh.exec_command(f'md "{remote_path}" 2>nul')
            else:
                ssh.exec_command(f"mkdir -p {remote_path}")
            
            # 上傳檔案
            for file in files:
                local_file = os.path.join(root, file)
                if relative_path != '.':
                    remote_file = f"{remote_dir_sftp}/{relative_path}/{file}".replace('\\', '/')
                else:
                    remote_file = f"{remote_dir_sftp}/{file}"
                sftp.put(local_file, remote_file)
                
    def load_config(self):
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                    
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
        finally:
            if self.publish_timer:
                self.publish_timer.cancel()


class ServerDialog:
    def __init__(self, parent, server_info=None):
        self.result = None
        self.server_info = server_info
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("編輯伺服器" if server_info else "新增伺服器")
        self.dialog.geometry("700x300")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()
        
        # 居中顯示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # IP地址
        ttk.Label(main_frame, text="IP地址:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.ip_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.ip_var, width=80).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 使用者名稱
        ttk.Label(main_frame, text="使用者名稱:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.username_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.username_var, width=80).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 密碼
        ttk.Label(main_frame, text="密碼:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.password_var = tk.StringVar()
        password_frame = ttk.Frame(main_frame)
        password_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.password_entry = ttk.Entry(password_frame, textvariable=self.password_var, width=25, show="*")
        self.password_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.show_password_var = tk.BooleanVar()
        ttk.Checkbutton(password_frame, text="顯示", variable=self.show_password_var, 
                       command=self.toggle_password).grid(row=0, column=1, padx=(5, 0))
        password_frame.columnconfigure(0, weight=1)
        
        # 目標路徑
        ttk.Label(main_frame, text="目標路徑:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.path_var, width=80).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 連接埠 (可選)
        ttk.Label(main_frame, text="SSH埠號:").grid(row=4, column=0, sticky=tk.W, pady=(0, 15))
        self.port_var = tk.StringVar(value="22")
        ttk.Entry(main_frame, textvariable=self.port_var, width=80).grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # 如果是編輯模式，填入現有資料
        if self.server_info:
            self.ip_var.set(self.server_info.get('ip', ''))
            self.username_var.set(self.server_info.get('username', ''))
            self.password_var.set(self.server_info.get('password', ''))
            self.path_var.set(self.server_info.get('path', ''))
            self.port_var.set(str(self.server_info.get('port', 22)))
        
        # 按鈕
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
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
        if not all([self.ip_var.get(), self.username_var.get(), self.password_var.get()]):
            messagebox.showerror("錯誤", "請填寫IP、使用者名稱和密碼")
            return
            
        server_info = {
            'ip': self.ip_var.get(),
            'username': self.username_var.get(),
            'password': self.password_var.get(),
            'path': self.path_var.get() or '/tmp',
            'port': int(self.port_var.get()) if self.port_var.get().isdigit() else 22
        }
        
        # 在新線程中測試連接
        test_thread = threading.Thread(target=self._test_connection, args=(server_info,))
        test_thread.daemon = True
        test_thread.start()
        
    def _test_connection(self, server_info):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                hostname=server_info['ip'],
                username=server_info['username'],
                password=server_info['password'],
                port=server_info['port'],
                timeout=10
            )
            
            stdin, stdout, stderr = ssh.exec_command('echo "Connection test successful"')
            result = stdout.read().decode().strip()
            ssh.close()
            
            self.dialog.after(0, lambda: messagebox.showinfo("連接測試", 
                f"連接測試成功！\n伺服器: {server_info['ip']}:{server_info['port']}"))
                
        except Exception as e:
            error_msg = f"連接失敗: {str(e)}\n\n可能原因:\n1. IP地址或埠號錯誤\n2. 使用者名稱或密碼錯誤\n3. SSH服務未啟動\n4. 網路不通或防火牆阻擋"
            self.dialog.after(0, lambda: messagebox.showerror("連接測試失敗", error_msg))
        
    def ok_clicked(self):
        if all([self.ip_var.get(), self.username_var.get(), self.password_var.get(), self.path_var.get()]):
            port = 22
            if self.port_var.get().isdigit():
                port = int(self.port_var.get())
            elif self.port_var.get():
                messagebox.showerror("錯誤", "SSH埠號必須是數字")
                return
                
            self.result = {
                'ip': self.ip_var.get(),
                'username': self.username_var.get(),
                'password': self.password_var.get(),
                'path': self.path_var.get(),
                'port': port
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
    app = WebsitePublisher()
    app.run()