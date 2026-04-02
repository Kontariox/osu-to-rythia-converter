import os
import sys
import threading
import json
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox

from converter import convert_osz

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".osu-to-rythia-cfg.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.title("osu! to Rythia Converter")
        self.minsize(520, 400)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        tab1 = tk.Frame(notebook, padx=12, pady=12)
        notebook.add(tab1, text="osz -> sspm")

        self.input_path_var = tk.StringVar(value="")
        self.output_dir_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Wybierz plik .osz i folder zapisu")

        # Plik wejściowy
        tk.Label(tab1, text="Plik .osz:").grid(row=0, column=0, sticky="w")
        tk.Entry(tab1, textvariable=self.input_path_var).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        tk.Button(tab1, text="Wybierz…", command=self.choose_input).grid(row=0, column=2, sticky="ew")

        # Folder wyjściowy
        tk.Label(tab1, text="Folder zapisu:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        tk.Entry(tab1, textvariable=self.output_dir_var).grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))
        tk.Button(tab1, text="Wybierz…", command=self.choose_output_dir).grid(row=1, column=2, sticky="ew", pady=(10, 0))

        # Akcje
        self.convert_btn = tk.Button(tab1, text="Konwertuj", command=self.on_convert)
        self.convert_btn.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(14, 0))

        tk.Label(tab1, textvariable=self.status_var, anchor="w", fg="#444").grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0)
        )

        tab1.columnconfigure(1, weight=1)

        self.init_tab2(notebook)

    def init_tab2(self, notebook):
        tab2 = tk.Frame(notebook, padx=12, pady=12)
        notebook.add(tab2, text="osu Songs -> Rhythia")

        self.songs_dir_var = tk.StringVar(value=self.config.get("songs_dir", ""))
        self.rhythia_dir_var = tk.StringVar(value=self.config.get("rhythia_dir", ""))
        self.tab2_status = tk.StringVar(value="Wybierz foldery")

        # When paths change, save them and refresh list
        self.songs_dir_var.trace_add("write", self.on_paths_changed)
        self.rhythia_dir_var.trace_add("write", self.on_paths_changed)

        tk.Label(tab2, text="Folder Songs:").grid(row=0, column=0, sticky="w")
        tk.Entry(tab2, textvariable=self.songs_dir_var).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        tk.Button(tab2, text="Wybierz…", command=self.choose_songs_dir).grid(row=0, column=2, sticky="ew")

        tk.Label(tab2, text="Folder Rhythia:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        tk.Entry(tab2, textvariable=self.rhythia_dir_var).grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(5, 0))
        tk.Button(tab2, text="Wybierz…", command=lambda: self.rhythia_dir_var.set(filedialog.askdirectory())).grid(row=1, column=2, sticky="ew", pady=(5, 0))

        self.songs_listbox = tk.Listbox(tab2, selectmode=tk.MULTIPLE, height=10)
        self.songs_listbox.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(10, 0))

        # Akcje
        self.convert2_btn = tk.Button(tab2, text="Konwertuj wybrane", command=self.on_convert2)
        self.convert2_btn.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        tk.Label(tab2, textvariable=self.tab2_status, anchor="w", fg="#444").grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=(5, 0)
        )

        tab2.columnconfigure(1, weight=1)
        tab2.rowconfigure(2, weight=1)

        # Populate list initially if paths exist
        if self.songs_dir_var.get():
            self.refresh_songs_list(self.songs_dir_var.get())

    def on_paths_changed(self, *args):
        self.config["songs_dir"] = self.songs_dir_var.get()
        self.config["rhythia_dir"] = self.rhythia_dir_var.get()
        save_config(self.config)

    def choose_songs_dir(self):
        path = filedialog.askdirectory(title="Wybierz folder Songs z osu!")
        if path:
            self.songs_dir_var.set(path)
            self.refresh_songs_list(path)

    def refresh_songs_list(self, path):
        self.songs_listbox.delete(0, tk.END)
        self.tab2_status.set("Wczytywanie listy piosenek...")

        def worker():
            items = []
            try:
                if os.path.exists(path):
                    items = sorted([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Błąd", f"Nie można odczytać folderu: {e}"))
                self.after(0, lambda: self.tab2_status.set("Błąd wczytywania"))
                return

            imported_legacy_ids = set()
            rhythia_dir = self.rhythia_dir_var.get()
            if rhythia_dir:
                db_path = os.path.join(rhythia_dir, "rhythia.db")
                if os.path.exists(db_path):
                    try:
                        import sqlite3
                        conn = sqlite3.connect(db_path)
                        cur = conn.cursor()
                        cur.execute("SELECT LegacyId FROM Maps")
                        imported_legacy_ids = {row[0] for row in cur.fetchall()}
                        conn.close()
                    except Exception:
                        pass

            import re

            listbox_items = []
            for item in items:
                item_path = os.path.join(path, item)
                is_imported = False

                if imported_legacy_ids:
                    try:
                        for f in os.listdir(item_path):
                            if f.endswith(".osu"):
                                with open(os.path.join(item_path, f), "r", encoding="utf-8", errors="ignore") as osu_f:
                                    content = osu_f.read()
                                    creator_match = re.search(r'Creator:(.*?)\n', content)
                                    title_match = re.search(r'Title:(.*?)\n', content)
                                    if creator_match and title_match:
                                        c = creator_match.group(1).strip().lower()
                                        t = title_match.group(1).strip().lower()
                                        l_id = f"{c} - {t} - rhythia"
                                        if l_id in imported_legacy_ids:
                                            is_imported = True
                                            break
                    except Exception:
                        pass

                display_text = f"[✓] {item}" if is_imported else item
                listbox_items.append(display_text)

            def finalize():
                self.songs_listbox.delete(0, tk.END)
                for i in listbox_items:
                    self.songs_listbox.insert(tk.END, i)
                self.tab2_status.set("Gotowe do konwersji")

            self.after(0, finalize)

        threading.Thread(target=worker, daemon=True).start()

    def on_convert2(self):
        from converter import convert_songs_to_json
        songs = [self.songs_listbox.get(i) for i in self.songs_listbox.curselection()]
        if not songs:
            messagebox.showwarning("Uwaga", "Nie wybrano żadnych piosenek z listy.")
            return

        # usuń prefix [✓]
        songs = [s[4:] if s.startswith("[✓] ") else s for s in songs]

        songs_dir = self.songs_dir_var.get()
        rhythia_dir = self.rhythia_dir_var.get()

        if not all((songs_dir, rhythia_dir)):
            messagebox.showerror("Błąd", "Wybierz oba foldery.")
            return

        self.convert2_btn.configure(state="disabled")
        self.tab2_status.set("Konwertuję…")

        def worker():
            try:
                for song in songs:
                    song_path = os.path.join(songs_dir, song)
                    convert_songs_to_json(song_path, rhythia_dir)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Błąd konwersji", str(e)))
                self.after(0, lambda: self.tab2_status.set("Błąd konwersji"))
            else:
                self.after(0, lambda: self.tab2_status.set("Gotowe"))
                self.after(0, lambda: self.refresh_songs_list(songs_dir)) # odśwież listę
            finally:
                self.after(0, lambda: self.convert2_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def choose_input(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik .osz",
            filetypes=[("osu! beatmap archive", "*.osz"), ("Wszystkie pliki", "*")],
        )
        if path:
            self.input_path_var.set(path)
            # delikatna wygoda: ustaw domyślny folder zapisu na folder pliku, jeśli pusty
            if not self.output_dir_var.get():
                self.output_dir_var.set(os.path.dirname(path))

    def choose_output_dir(self):
        path = filedialog.askdirectory(title="Wybierz folder zapisu")
        if path:
            self.output_dir_var.set(path)

    def _validate(self) -> tuple[str, str] | None:
        in_path = self.input_path_var.get().strip()
        out_dir = self.output_dir_var.get().strip()

        if not in_path:
            messagebox.showerror("Błąd", "Nie wybrano pliku .osz.")
            return None
        if not in_path.lower().endswith(".osz"):
            messagebox.showerror("Błąd", "Plik wejściowy musi mieć rozszerzenie .osz.")
            return None
        if not os.path.isfile(in_path):
            messagebox.showerror("Błąd", "Wybrany plik nie istnieje.")
            return None

        if not out_dir:
            messagebox.showerror("Błąd", "Nie wybrano folderu zapisu.")
            return None
        if os.path.exists(out_dir) and not os.path.isdir(out_dir):
            messagebox.showerror("Błąd", "Ścieżka zapisu nie jest folderem.")
            return None

        return in_path, out_dir

    def on_convert(self):
        validated = self._validate()
        if not validated:
            return
        in_path, out_dir = validated

        self.convert_btn.configure(state="disabled")
        self.status_var.set("Konwertuję…")

        def worker():
            try:
                convert_osz(in_path, out_dir)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Błąd konwersji", str(e)))
                self.after(0, lambda: self.status_var.set("Błąd konwersji"))
            else:
                self.after(0, lambda: self.status_var.set("Gotowe"))
            finally:
                self.after(0, lambda: self.convert_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()


def main_gui():
    app = App()
    app.mainloop()

