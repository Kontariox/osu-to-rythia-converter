import os
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox

from converter import convert_osz


class App(tk.Tk):
    def __init__(self):
        super().__init__()
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
        notebook.add(tab2, text="osu Songs -> JSON/Audio/Covers")

        self.songs_dir_var = tk.StringVar(value="")
        self.audio_dir_var = tk.StringVar(value="")
        self.covers_dir_var = tk.StringVar(value="")
        self.maps_dir_var = tk.StringVar(value="")
        self.db_path_var = tk.StringVar(value="")
        self.tab2_status = tk.StringVar(value="Wybierz foldery i plik bazy danych")

        tk.Label(tab2, text="Folder Songs:").grid(row=0, column=0, sticky="w")
        tk.Entry(tab2, textvariable=self.songs_dir_var).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        tk.Button(tab2, text="Wybierz…", command=self.choose_songs_dir).grid(row=0, column=2, sticky="ew")

        tk.Label(tab2, text="Folder Audio:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        tk.Entry(tab2, textvariable=self.audio_dir_var).grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(5, 0))
        tk.Button(tab2, text="Wybierz…", command=lambda: self.audio_dir_var.set(filedialog.askdirectory())).grid(row=1, column=2, sticky="ew", pady=(5, 0))

        tk.Label(tab2, text="Folder Covers:").grid(row=2, column=0, sticky="w", pady=(5, 0))
        tk.Entry(tab2, textvariable=self.covers_dir_var).grid(row=2, column=1, sticky="ew", padx=(8, 8), pady=(5, 0))
        tk.Button(tab2, text="Wybierz…", command=lambda: self.covers_dir_var.set(filedialog.askdirectory())).grid(row=2, column=2, sticky="ew", pady=(5, 0))

        tk.Label(tab2, text="Folder Maps:").grid(row=3, column=0, sticky="w", pady=(5, 0))
        tk.Entry(tab2, textvariable=self.maps_dir_var).grid(row=3, column=1, sticky="ew", padx=(8, 8), pady=(5, 0))
        tk.Button(tab2, text="Wybierz…", command=lambda: self.maps_dir_var.set(filedialog.askdirectory())).grid(row=3, column=2, sticky="ew", pady=(5, 0))

        tk.Label(tab2, text="Baza rhythia.db:").grid(row=4, column=0, sticky="w", pady=(5, 0))
        tk.Entry(tab2, textvariable=self.db_path_var).grid(row=4, column=1, sticky="ew", padx=(8, 8), pady=(5, 0))
        tk.Button(tab2, text="Wybierz…", command=self.choose_db).grid(row=4, column=2, sticky="ew", pady=(5, 0))

        self.songs_listbox = tk.Listbox(tab2, selectmode=tk.MULTIPLE, height=10)
        self.songs_listbox.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(10, 0))

        # Akcje
        self.convert2_btn = tk.Button(tab2, text="Konwertuj wybrane", command=self.on_convert2)
        self.convert2_btn.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        tk.Label(tab2, textvariable=self.tab2_status, anchor="w", fg="#444").grid(
            row=7, column=0, columnspan=3, sticky="ew", pady=(5, 0)
        )

        tab2.columnconfigure(1, weight=1)
        tab2.rowconfigure(5, weight=1)

    def choose_songs_dir(self):
        path = filedialog.askdirectory(title="Wybierz folder Songs z osu!")
        if path:
            self.songs_dir_var.set(path)
            self.refresh_songs_list(path)

    def refresh_songs_list(self, path):
        self.songs_listbox.delete(0, tk.END)
        try:
            for item in sorted(os.listdir(path)):
                if os.path.isdir(os.path.join(path, item)):
                    self.songs_listbox.insert(tk.END, item)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie można odczytać folderu: {e}")

    def choose_db(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik z bazą (rythia.db)",
            filetypes=[("SQLite DB", "*.db"), ("Wszystkie pliki", "*")]
        )
        if path:
            self.db_path_var.set(path)

    def on_convert2(self):
        from converter import convert_songs_to_json
        songs = [self.songs_listbox.get(i) for i in self.songs_listbox.curselection()]
        if not songs:
            messagebox.showwarning("Uwaga", "Nie wybrano żadnych piosenek z listy.")
            return

        songs_dir = self.songs_dir_var.get()
        audio_dir = self.audio_dir_var.get()
        covers_dir = self.covers_dir_var.get()
        maps_dir = self.maps_dir_var.get()
        db_path = self.db_path_var.get()

        if not all((songs_dir, audio_dir, covers_dir, maps_dir)):
            messagebox.showerror("Błąd", "Wybierz wszystkie 4 foldery.")
            return

        self.convert2_btn.configure(state="disabled")
        self.tab2_status.set("Konwertuję…")

        def worker():
            try:
                for song in songs:
                    song_path = os.path.join(songs_dir, song)
                    convert_songs_to_json(song_path, audio_dir, covers_dir, maps_dir, db_path)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Błąd konwersji", str(e)))
                self.after(0, lambda: self.tab2_status.set("Błąd konwersji"))
            else:
                self.after(0, lambda: self.tab2_status.set("Gotowe"))
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

