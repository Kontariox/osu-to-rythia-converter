import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from converter import convert_osz


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("osu! to Rythia Converter")
        self.minsize(520, 180)

        self.input_path_var = tk.StringVar(value="")
        self.output_dir_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Wybierz plik .osz i folder zapisu")

        root = tk.Frame(self, padx=12, pady=12)
        root.pack(fill="both", expand=True)

        # Plik wejściowy
        tk.Label(root, text="Plik .osz:").grid(row=0, column=0, sticky="w")
        tk.Entry(root, textvariable=self.input_path_var).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        tk.Button(root, text="Wybierz…", command=self.choose_input).grid(row=0, column=2, sticky="ew")

        # Folder wyjściowy
        tk.Label(root, text="Folder zapisu:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        tk.Entry(root, textvariable=self.output_dir_var).grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))
        tk.Button(root, text="Wybierz…", command=self.choose_output_dir).grid(row=1, column=2, sticky="ew", pady=(10, 0))

        # Akcje
        self.convert_btn = tk.Button(root, text="Konwertuj", command=self.on_convert)
        self.convert_btn.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(14, 0))

        tk.Label(root, textvariable=self.status_var, anchor="w", fg="#444").grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0)
        )

        root.columnconfigure(1, weight=1)

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

