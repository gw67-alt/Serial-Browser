import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import threading
import time
import re
import html

class ESP32WebBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32-S3 Web Browser")
        self.root.geometry("800x600")
        
        self.serial_connection = None
        self.read_thread = None
        self.collecting_data = False
        self.data_buffer = ""
        
        # For file downloads
        self.downloading_file = False
        self.file_name = ""
        self.file_size = 0
        self.file_type = ""
        self.file_handle = None
        self.bytes_received = 0
        self.expecting_chunk_size = False
        self.current_chunk_size = 0
        
        self.create_ui()
        self.update_port_list()
    
    def create_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Serial connection frame
        conn_frame = ttk.LabelFrame(main_frame, text="Serial Connection", padding="5")
        conn_frame.pack(fill=tk.X, pady=5)
        
        # Port selection
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_combo = ttk.Combobox(conn_frame, width=30)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        refresh_btn = ttk.Button(conn_frame, text="Refresh", command=self.update_port_list)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Baud rate selection
        ttk.Label(conn_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.baud_combo = ttk.Combobox(conn_frame, width=10, values=["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.current(4)  # Default to 115200
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Connect button
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=1, column=2, padx=5, pady=5)
        
        # URL frame
        url_frame = ttk.LabelFrame(main_frame, text="URL Control", padding="5")
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.url_entry = ttk.Entry(url_frame, width=70)
        self.url_entry.insert(0, "https://example.com")
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        btn_frame = ttk.Frame(url_frame)
        btn_frame.grid(row=0, column=2, padx=5, pady=5)
        
        self.fetch_btn = ttk.Button(btn_frame, text="Fetch", command=self.fetch_url, state=tk.DISABLED)
        self.fetch_btn.pack(side=tk.LEFT, padx=2)
        
        self.download_btn = ttk.Button(btn_frame, text="Download", command=self.download_file, state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=2)
        
        # Browser view
        browser_frame = ttk.LabelFrame(main_frame, text="Web Content", padding="5")
        browser_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tabs for different views
        self.tab_control = ttk.Notebook(browser_frame)
        
        # Raw HTML tab
        self.raw_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.raw_frame, text="Raw HTML")
        
        self.raw_text = scrolledtext.ScrolledText(self.raw_frame, wrap=tk.WORD)
        self.raw_text.pack(fill=tk.BOTH, expand=True)
        
        # Rendered view tab
        self.rendered_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.rendered_frame, text="Rendered View")
        
        self.rendered_text = scrolledtext.ScrolledText(self.rendered_frame, wrap=tk.WORD)
        self.rendered_text.pack(fill=tk.BOTH, expand=True)
        
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Not Connected")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=5)
    
    def update_port_list(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)
    
    def toggle_connection(self):
        if self.serial_connection is None:
            self.connect_serial()
        else:
            self.disconnect_serial()
    
    def connect_serial(self):
        port = self.port_combo.get()
        baud_rate = int(self.baud_combo.get())
        
        try:
            self.serial_connection = serial.Serial(port, baud_rate, timeout=1)
            self.status_var.set(f"Connected to {port} at {baud_rate} baud")
            self.connect_btn.config(text="Disconnect")
            self.fetch_btn.config(state=tk.NORMAL)
            self.download_btn.config(state=tk.NORMAL)
            
            # Start the thread to read from serial
            self.read_thread = threading.Thread(target=self.read_serial_data)
            self.read_thread.daemon = True
            self.read_thread.start()
        
        except (serial.SerialException, ValueError) as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.status_var.set("Connection failed")
    
    def disconnect_serial(self):
        if self.serial_connection:
            self.serial_connection.close()
            self.serial_connection = None
            self.status_var.set("Disconnected")
            self.connect_btn.config(text="Connect")
            self.fetch_btn.config(state=tk.DISABLED)
            self.download_btn.config(state=tk.DISABLED)
    
    def fetch_url(self):
        if not self.serial_connection:
            return
        
        url = self.url_entry.get()
        if url:
            # Update URL on ESP32
            self.serial_connection.write(f"url:{url}\n".encode())
            time.sleep(0.5)  # Give ESP32 time to process the URL change
            
            # Trigger fetch command
            self.serial_connection.write(b"fetch\n")
            self.status_var.set(f"Fetching: {url}")
            
            # Clear previous content
            self.raw_text.delete(1.0, tk.END)
            self.rendered_text.delete(1.0, tk.END)
    
    def read_serial_data(self):
        while self.serial_connection and self.serial_connection.is_open:
            try:
                if self.serial_connection.in_waiting:
                    # Handle binary data for file downloads
                    if self.downloading_file and self.expecting_chunk_size and self.current_chunk_size > 0:
                        # Read binary chunk
                        chunk = self.serial_connection.read(self.current_chunk_size)
                        if chunk:
                            # Write to file
                            if self.file_handle:
                                self.file_handle.write(chunk)
                                self.bytes_received += len(chunk)
                                
                                # Update status (not too often to avoid UI freezing)
                                if self.bytes_received % 10240 == 0:  # Update every ~10KB
                                    self.status_var.set(f"Downloading: {self.bytes_received}/{self.file_size} bytes ({int(self.bytes_received*100/self.file_size)}%)")
                            
                            # Reset for next chunk size
                            self.expecting_chunk_size = True
                            self.current_chunk_size = 0
                            continue
                    
                    # Regular text line reading
                    line = self.serial_connection.readline().decode('utf-8', errors='replace').strip()
                    
                    # Process the received data
                    self.process_line(line)
                
                time.sleep(0.01)
            except Exception as e:
                print(f"Serial read error: {e}")
                if self.file_handle:
                    self.file_handle.close()
                    self.file_handle = None
                break
    
    def download_file(self):
        """Trigger file download from the ESP32"""
        if not self.serial_connection:
            return
            
        from tkinter import filedialog
        
        url = self.url_entry.get()
        if url:
            # First, get the expected filename from the URL
            import os
            from urllib.parse import urlparse
            
            parsed_url = urlparse(url)
            path = parsed_url.path
            filename = os.path.basename(path)
            
            if not filename:
                filename = "download.bin"
                
            # Ask user where to save the file
            save_path = filedialog.asksaveasfilename(
                initialfile=filename,
                defaultextension=".*",
                title="Save File As"
            )
            
            if not save_path:  # User cancelled
                return
                
            try:
                # Open file for writing
                self.file_handle = open(save_path, 'wb')
                
                # Update URL on ESP32
                self.serial_connection.write(f"url:{url}\n".encode())
                time.sleep(0.5)  # Give ESP32 time to process
                
                # Start download
                self.serial_connection.write(b"download\n")
                self.status_var.set(f"Starting download from: {url}")
                
                # Reset download state
                self.downloading_file = False
                self.file_name = os.path.basename(save_path)
                self.file_size = 0
                self.file_type = ""
                self.bytes_received = 0
                self.expecting_chunk_size = False
                
                # Clear text areas
                self.raw_text.delete(1.0, tk.END)
                self.rendered_text.delete(1.0, tk.END)
                self.raw_text.insert(tk.END, f"Downloading to: {save_path}\n")
                
            except Exception as e:
                messagebox.showerror("Download Error", f"Error preparing download: {str(e)}")
                if self.file_handle:
                    self.file_handle.close()
                    self.file_handle = None
    
    def process_line(self, line):
        # Update UI from the main thread
        def update_ui():
            # Don't log binary data chunks to the text area
            if not self.downloading_file or not self.expecting_chunk_size:
                self.raw_text.insert(tk.END, line + "\n")
                self.raw_text.see(tk.END)
            
            # Handle text data collection
            if line == "===DATA_BEGIN===":
                self.collecting_data = True
                self.data_buffer = ""
                self.status_var.set("Receiving data...")
            elif line == "===DATA_END===":
                self.collecting_data = False
                self.status_var.set("Data received")
                self.render_html_content(self.data_buffer)
            elif self.collecting_data:
                self.data_buffer += line + "\n"
                
            # Handle file download
            elif line == "===FILE_BEGIN===":
                self.downloading_file = True
                self.status_var.set("File download started")
                self.raw_text.insert(tk.END, "Download started\n")
                # Next lines will be filename, content-type, and size
            elif line == "===FILE_END===":
                self.downloading_file = False
                self.expecting_chunk_size = False
                if self.file_handle:
                    self.file_handle.close()
                    self.file_handle = None
                self.status_var.set(f"Download complete: {self.file_name} ({self.bytes_received}/{self.file_size} bytes)")
                self.raw_text.insert(tk.END, f"Download complete: {self.bytes_received} bytes\n")
            elif self.downloading_file:
                if self.file_name == "":
                    # First line is the filename
                    self.file_name = line
                    self.raw_text.insert(tk.END, f"Filename: {self.file_name}\n")
                elif self.file_type == "":
                    # Second line is content type
                    self.file_type = line
                    self.raw_text.insert(tk.END, f"Content type: {self.file_type}\n")
                elif self.file_size == 0:
                    # Third line is file size
                    try:
                        self.file_size = int(line)
                        self.raw_text.insert(tk.END, f"File size: {self.file_size} bytes\n")
                        self.expecting_chunk_size = True
                    except ValueError:
                        self.raw_text.insert(tk.END, f"Invalid file size: {line}\n")
                elif self.expecting_chunk_size:
                    # This line is the chunk size
                    try:
                        self.current_chunk_size = int(line)
                        if self.current_chunk_size == 0:
                            # End of file
                            self.expecting_chunk_size = False
                        else:
                            # We now expect binary data, this will be handled in read_serial_data
                            pass
                    except ValueError:
                        self.raw_text.insert(tk.END, f"Invalid chunk size: {line}\n")
                        self.expecting_chunk_size = False
        
        self.root.after(0, update_ui)
    
    def render_html_content(self, html_content):
        # Very basic HTML rendering - just strips tags and displays text
        # For a more advanced rendering, you would need to use a proper HTML parser
        
        # Convert some basic HTML entities
        text_content = html_content
        text_content = re.sub(r'<script.*?</script>', '', text_content, flags=re.DOTALL)
        text_content = re.sub(r'<style.*?</style>', '', text_content, flags=re.DOTALL)
        text_content = re.sub(r'<[^>]*>', ' ', text_content)
        text_content = html.unescape(text_content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Display in the rendered view
        self.rendered_text.delete(1.0, tk.END)
        self.rendered_text.insert(tk.END, text_content)

if __name__ == "__main__":
    root = tk.Tk()
    app = ESP32WebBrowser(root)
    root.mainloop()