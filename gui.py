import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from optimizer import cutlist_optimizer, load_cutlist


class CutlistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cutlist Optimizer")
        self.root.minsize(760, 520)

        self.file_path = tk.StringVar()
        self.stock_length = tk.StringVar(value="3000")
        self.kerf = tk.StringVar(value="3")
        self.stock_price = tk.StringVar(value="0")
        self.summary = tk.StringVar(value="Select a cutlist and enter its settings.")
        self.optimized_cuts = []
        self.layout_stock_length = 0
        self.layout_kerf = 0

        self._build_form()
        self._build_results()

    def _build_form(self):
        form = ttk.Frame(self.root, padding=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Cutlist file").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(form, textvariable=self.file_path).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(form, text="Browse...", command=self._choose_file).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(form, text="Stock length").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(form, textvariable=self.stock_length, width=14).grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Kerf").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(form, textvariable=self.kerf, width=14).grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Price per stock piece").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(form, textvariable=self.stock_price, width=14).grid(row=3, column=1, sticky="w", pady=4)

        ttk.Button(form, text="Optimize", command=self._optimize).grid(row=4, column=1, sticky="w", pady=(10, 0))
        ttk.Label(form, textvariable=self.summary).grid(row=4, column=2, sticky="e", pady=(10, 0))

    def _build_results(self):
        container = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)
        container.columnconfigure(0, weight=1)

        columns = ("stock", "used", "waste", "usage", "cuts")
        self.results = ttk.Treeview(container, columns=columns, show="headings")
        headings = {
            "stock": "Stock piece",
            "used": "Used",
            "waste": "Waste",
            "usage": "Usage",
            "cuts": "Cuts",
        }
        widths = {"stock": 90, "used": 90, "waste": 90, "usage": 80, "cuts": 420}
        for column in columns:
            self.results.heading(column, text=headings[column])
            self.results.column(column, width=widths[column], anchor="w")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.results.yview)
        self.results.configure(yscrollcommand=scrollbar.set)
        self.results.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        layout_frame = ttk.LabelFrame(container, text="Visual layout", padding=6)
        layout_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        layout_frame.rowconfigure(0, weight=1)
        layout_frame.columnconfigure(0, weight=1)

        self.layout_canvas = tk.Canvas(
            layout_frame,
            background="white",
            highlightthickness=1,
            highlightbackground="#c8c8c8",
        )
        layout_scrollbar = ttk.Scrollbar(
            layout_frame,
            orient="vertical",
            command=self.layout_canvas.yview,
        )
        self.layout_canvas.configure(yscrollcommand=layout_scrollbar.set)
        self.layout_canvas.grid(row=0, column=0, sticky="nsew")
        layout_scrollbar.grid(row=0, column=1, sticky="ns")
        self.layout_canvas.bind("<Configure>", lambda _event: self._draw_layout())

    def _choose_file(self):
        file_path = filedialog.askopenfilename(
            title="Select cutlist",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
        )
        if file_path:
            self.file_path.set(file_path)

    def _optimize(self):
        try:
            stock_length = float(self.stock_length.get())
            kerf = float(self.kerf.get())
            stock_price = float(self.stock_price.get())
            if stock_price < 0:
                raise ValueError("price cannot be negative")

            cuts = load_cutlist(self.file_path.get())
            optimized_cuts = cutlist_optimizer(stock_length, cuts, kerf=kerf)
        except (OSError, ValueError) as error:
            messagebox.showerror("Unable to optimize", str(error))
            return

        for item in self.results.get_children():
            self.results.delete(item)

        total_used = 0
        for stock_number, stock_cuts in enumerate(optimized_cuts, start=1):
            used = sum(cut.length + kerf for cut in stock_cuts)
            waste = stock_length - used
            total_used += used
            cut_text = ", ".join(
                f"{cut.name or 'Unnamed cut'} ({cut.length:g})" for cut in stock_cuts
            )
            self.results.insert(
                "",
                "end",
                values=(stock_number, f"{used:g}", f"{waste:g}", f"{used / stock_length:.1%}", cut_text),
            )

        total_price = len(optimized_cuts) * stock_price
        total_usage = total_used / (len(optimized_cuts) * stock_length) if optimized_cuts else 0
        self.summary.set(
            f"{len(cuts)} cuts | {len(optimized_cuts)} stock pieces | "
            f"Total: {total_price:.2f} | Usage: {total_usage:.1%}"
        )
        self.optimized_cuts = optimized_cuts
        self.layout_stock_length = stock_length
        self.layout_kerf = kerf
        self._draw_layout()

    def _draw_layout(self):
        if not hasattr(self, "layout_canvas"):
            return

        canvas = self.layout_canvas
        canvas.delete("all")
        if not self.optimized_cuts or self.layout_stock_length <= 0:
            canvas.configure(scrollregion=(0, 0, 0, 0))
            return

        canvas_width = max(canvas.winfo_width(), 760)
        left_margin = 115
        right_margin = 24
        available_width = canvas_width - left_margin - right_margin
        scale = available_width / self.layout_stock_length
        beam_height = 42
        row_gap = 28
        top_margin = 30
        cut_colors = ("#83b8d8", "#e5b567", "#9ac6a2", "#c69bd1")

        canvas.create_text(
            left_margin,
            12,
            anchor="w",
            text=f"0    {self.layout_stock_length:g}",
            fill="#555555",
            font=("Segoe UI", 9),
        )

        for stock_number, stock_cuts in enumerate(self.optimized_cuts, start=1):
            y = top_margin + (stock_number - 1) * (beam_height + row_gap)
            x = left_margin
            canvas.create_text(
                8,
                y + beam_height / 2,
                anchor="w",
                text=f"Beam {stock_number}",
                fill="#333333",
                font=("Segoe UI", 9, "bold"),
            )

            for cut_index, cut in enumerate(stock_cuts):
                cut_width = cut.length * scale
                cut_end = x + cut_width
                canvas.create_rectangle(
                    x,
                    y,
                    cut_end,
                    y + beam_height,
                    fill=cut_colors[cut_index % len(cut_colors)],
                    outline="#555555",
                )
                canvas.create_line(x, y - 5, x, y + beam_height + 5, fill="#333333")
                canvas.create_text(
                    (x + cut_end) / 2,
                    y + beam_height / 2,
                    text=f"{cut.name or 'Unnamed'}\n{cut.length:g}",
                    width=max(cut_width - 6, 30),
                    justify="center",
                    fill="#202020",
                    font=("Segoe UI", 8),
                )
                x = cut_end

                kerf_width = self.layout_kerf * scale
                if kerf_width > 0:
                    canvas.create_rectangle(
                        x,
                        y,
                        x + kerf_width,
                        y + beam_height,
                        fill="#eeeeee",
                        outline="",
                    )
                    x += kerf_width

            canvas.create_line(x, y - 5, x, y + beam_height + 5, fill="#333333")
            waste_width = max(self.layout_stock_length * scale - x + left_margin, 0)
            if waste_width > 0:
                canvas.create_rectangle(
                    x,
                    y,
                    left_margin + self.layout_stock_length * scale,
                    y + beam_height,
                    fill="#f1f1f1",
                    outline="#aaaaaa",
                    dash=(3, 3),
                )
                canvas.create_text(
                    (x + left_margin + self.layout_stock_length * scale) / 2,
                    y + beam_height / 2,
                    text=f"waste\n{waste_width / scale:g}",
                    fill="#666666",
                    font=("Segoe UI", 8),
                )

        canvas_height = top_margin + len(self.optimized_cuts) * (beam_height + row_gap)
        canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))


def main():
    root = tk.Tk()
    CutlistApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
