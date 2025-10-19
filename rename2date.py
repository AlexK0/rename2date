import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from typing import Iterable, Tuple


APP_TITLE = "Rename Files by Date Prefix"
DEFAULT_PATTERN = "%Y-%m-%d-%H-%M-%S"


def normalize_ext(ext: str) -> str:
    ext = ext.strip()
    if not ext:
        return ""
    if not ext.startswith('.'):
        ext = '.' + ext
    return ext.lower()


def iter_files(base_dir: str, recursive: bool) -> Iterable[str]:
    if recursive:
        for root, dirs, files in os.walk(base_dir):
            for name in files:
                yield os.path.join(root, name)
    else:
        with os.scandir(base_dir) as it:
            for entry in it:
                if entry.is_file():
                    yield entry.path


def build_prefixed_name(path: str, prefix: str) -> str:
    directory, filename = os.path.split(path)
    new_name = f"{prefix}_{filename}"
    return os.path.join(directory, new_name)


def ensure_unique_path(target_path: str) -> str:
    if not os.path.exists(target_path):
        return target_path
    directory, filename = os.path.split(target_path)
    stem, ext = os.path.splitext(filename)
    i = 1
    while True:
        candidate = os.path.join(directory, f"{stem}-{i}{ext}")
        if not os.path.exists(candidate):
            return candidate
        i += 1


def get_modification_prefix(path: str, pattern: str) -> str:
    try:
        ts = os.path.getmtime(path)
    except OSError:
        # If we cannot get mtime, fallback to current time
        ts = datetime.now().timestamp()
    dt = datetime.fromtimestamp(ts)
    return dt.strftime(pattern)


def should_skip_already_prefixed(filename: str, prefix: str) -> bool:
    return filename.startswith(prefix + "_")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("800x520")
        self.minsize(700, 480)
        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Directory row
        row1 = ttk.Frame(container)
        row1.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row1, text="Directory:").pack(side=tk.LEFT)
        self.dir_var = tk.StringVar()
        self.dir_entry = ttk.Entry(row1, textvariable=self.dir_var)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ttk.Button(row1, text="Browse...", command=self._browse_dir).pack(side=tk.LEFT)

        # Extension row
        row2 = ttk.Frame(container)
        row2.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row2, text="File extension:").pack(side=tk.LEFT)
        self.ext_var = tk.StringVar(value="jpg")
        self.ext_entry = ttk.Entry(row2, textvariable=self.ext_var, width=20)
        self.ext_entry.pack(side=tk.LEFT, padx=8)
        ttk.Label(row2, text="Example: jpg or .jpg").pack(side=tk.LEFT)

        # Pattern row
        row3 = ttk.Frame(container)
        row3.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row3, text="strftime pattern:").pack(side=tk.LEFT)
        self.pattern_var = tk.StringVar(value=DEFAULT_PATTERN)
        self.pattern_entry = ttk.Entry(row3, textvariable=self.pattern_var)
        self.pattern_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ttk.Label(row3, text="Default: %Y-%m-%d-%H-%M-%S").pack(side=tk.LEFT)

        # Options row
        row4 = ttk.Frame(container)
        row4.pack(fill=tk.X, pady=(0, 8))
        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row4, text="Scan subdirectories (recursive)", variable=self.recursive_var).pack(side=tk.LEFT)
        self.skip_already_prefixed_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row4, text="Skip files already prefixed", variable=self.skip_already_prefixed_var).pack(side=tk.LEFT, padx=(16, 0))

        # Action buttons
        row5 = ttk.Frame(container)
        row5.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(row5, text="Rename Files", command=self._on_rename).pack(side=tk.LEFT)
        ttk.Button(row5, text="Preview First 10", command=self._on_preview).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(row5, text="Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=(8, 0))

        # Log area
        self.log = tk.Text(container, height=18, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)
        self._log("Ready. Select a directory, extension, and pattern, then click 'Rename Files'.")

    def _browse_dir(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self.dir_var.set(d)

    def _clear_log(self) -> None:
        self.log.delete("1.0", tk.END)

    def _log(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _validate_inputs(self) -> Tuple[bool, str, str, str]:
        directory = self.dir_var.get().strip()
        if not directory:
            return False, "", "", "Select a directory."
        if not os.path.isdir(directory):
            return False, "", "", f"Directory does not exist: {directory}"
        ext = normalize_ext(self.ext_var.get())
        if not ext:
            return False, "", "", "Enter a file extension (e.g., jpg or .jpg)."
        pattern = self.pattern_var.get().strip() or DEFAULT_PATTERN
        # Basic validation: try formatting current time
        try:
            _ = datetime.now().strftime(pattern)
        except Exception as e:
            return False, "", "", f"Invalid strftime pattern: {e}"
        return True, directory, ext, pattern

    def _collect_targets(self, directory: str, ext: str, recursive: bool) -> Iterable[str]:
        for path in iter_files(directory, recursive):
            if not os.path.isfile(path):
                continue
            if os.path.splitext(path)[1].lower() == ext:
                yield path

    def _on_preview(self) -> None:
        ok, directory, ext, pattern = self._validate_inputs()
        if not ok:
            self._log(pattern)  # pattern holds the error message here
            messagebox.showerror(APP_TITLE, pattern)
            return
        recursive = self.recursive_var.get()
        preview_count = 0
        self._log(f"Preview (first 10) for directory={directory}, ext={ext}, pattern='{pattern}', recursive={recursive}")
        for path in self._collect_targets(directory, ext, recursive):
            directory_name, filename = os.path.split(path)
            prefix = get_modification_prefix(path, pattern)
            if self.skip_already_prefixed_var.get() and should_skip_already_prefixed(filename, prefix):
                continue
            new_path = build_prefixed_name(path, prefix)
            unique_path = ensure_unique_path(new_path)
            if unique_path != new_path:
                note = " (collision -> will use unique name)"
            else:
                note = ""
            self._log(f"{filename} -> {os.path.basename(unique_path)}{note}")
            preview_count += 1
            if preview_count >= 10:
                break
        if preview_count == 0:
            self._log("No matching files found for preview.")

    def _on_rename(self) -> None:
        ok, directory, ext, pattern = self._validate_inputs()
        if not ok:
            self._log(pattern)  # pattern holds the error message here
            messagebox.showerror(APP_TITLE, pattern)
            return
        recursive = self.recursive_var.get()
        self._log(f"Starting rename in {directory} (recursive={recursive}) for extension {ext} with pattern '{pattern}'")
        count = 0
        skipped = 0
        errors = 0
        for path in self._collect_targets(directory, ext, recursive):
            try:
                dir_name, filename = os.path.split(path)
                prefix = get_modification_prefix(path, pattern)
                if self.skip_already_prefixed_var.get() and should_skip_already_prefixed(filename, prefix):
                    skipped += 1
                    continue
                target = ensure_unique_path(build_prefixed_name(path, prefix))
                if os.path.abspath(path) == os.path.abspath(target):
                    skipped += 1
                    continue
                os.rename(path, target)
                self._log(f"RENAMED: {filename} -> {os.path.basename(target)}")
                count += 1
            except Exception as e:
                self._log(f"ERROR: {path}: {e}")
                errors += 1
        self._log(f"Done. Renamed: {count}, Skipped: {skipped}, Errors: {errors}")


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
