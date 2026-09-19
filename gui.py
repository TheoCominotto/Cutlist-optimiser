import tkinter as tk
import webbrowser
import math
from tkinter import filedialog, messagebox, ttk

from optimizer import cutlist_optimizer, load_cutlist
from stock_db import add_stock, get_stock, update_stock


class CutlistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cutlist Optimizer")
        self.root.minsize(760, 520)

        self.file_path = tk.StringVar()
        self.kerf = tk.StringVar(value="3")
        self.stock_selection = tk.StringVar()
        self.summary = tk.StringVar(value="Select a cutlist and stock timber.")
        self.stock_items = {}
        self.optimized_cuts = []
        self.layout_stock_length = 0
        self.layout_kerf = 0
        self.cut_count = tk.StringVar(value="-")
        self.beam_count = tk.StringVar(value="-")
        self.total_price = tk.StringVar(value="€-")
        self.usage_percentage = tk.StringVar(value="-")
        self.usage_bar_style = "Usage.Bad.Horizontal.TProgressbar"

        style = ttk.Style(self.root)
        style.configure(
            "Usage.Bad.Horizontal.TProgressbar",
            background="#d95c5c",
            troughcolor="#f1dada",
        )
        style.configure(
            "Usage.Medium.Horizontal.TProgressbar",
            background="#e0a43a",
            troughcolor="#f4ead3",
        )
        style.configure(
            "Usage.Good.Horizontal.TProgressbar",
            background="#4fa66a",
            troughcolor="#dcefe2",
        )

        self._build_form()
        self._build_results()

    def _build_form(self):
        form = ttk.Frame(self.root, padding=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Cutlist file").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(form, textvariable=self.file_path).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(form, text="Browse...", command=self._choose_file).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(form, text="Stock timber").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.stock_combo = ttk.Combobox(
            form, textvariable=self.stock_selection, state="readonly", width=46
        )
        self.stock_combo.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(form, text="Auto pick stock", command=self._auto_pick_stock).grid(
            row=1, column=2, padx=(8, 0), pady=4
        )
        ttk.Separator(form, orient="vertical").grid(
            row=1, column=3, sticky="ns", padx=(12, 4), pady=2
        )
        ttk.Button(form, text="Add stock...", command=self._add_stock).grid(
            row=1, column=4, padx=(8, 0), pady=4
        )
        ttk.Button(form, text="Edit stock...", command=self._edit_stock).grid(
            row=1, column=5, padx=(8, 0), pady=4
        )
        self.open_link_button = ttk.Button(
            form, text="Open product page", command=self._open_stock_link
        )
        self.open_link_button.grid(row=1, column=6, padx=(8, 0), pady=4)
        self.stock_combo.bind("<<ComboboxSelected>>", self._update_link_button)

        ttk.Label(form, text="Kerf").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(form, textvariable=self.kerf, width=14).grid(row=2, column=1, sticky="w", pady=4)

        ttk.Button(form, text="Optimize", command=self._optimize).grid(row=3, column=1, sticky="w", pady=(10, 0))
        ttk.Label(form, textvariable=self.summary).grid(row=3, column=2, columnspan=3, sticky="e", pady=(10, 0))

        summary_frame = ttk.LabelFrame(form, text="Optimization summary", padding=8)
        summary_frame.grid(row=4, column=0, columnspan=5, sticky="ew", pady=(12, 0))
        for column in range(4):
            summary_frame.columnconfigure(column, weight=1)

        self._add_summary_card(summary_frame, 0, "Stock pieces", self.beam_count)
        self._add_summary_card(summary_frame, 1, "Total price", self.total_price)

        usage_frame = ttk.Frame(summary_frame)
        usage_frame.grid(row=0, column=2, padx=8, sticky="ew")
        ttk.Label(usage_frame, text="Usage", foreground="#666666").pack(anchor="w")
        ttk.Label(
            usage_frame, textvariable=self.usage_percentage, font=("Segoe UI", 16, "bold")
        ).pack(anchor="w")
        self.usage_bar = ttk.Progressbar(
            usage_frame,
            maximum=100,
            value=0,
            style=self.usage_bar_style,
        )
        self.usage_bar.pack(fill="x", pady=(4, 0))

        self._add_summary_card(summary_frame, 3, "Cuts", self.cut_count)

        self._refresh_stock()

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

    @staticmethod
    def _add_summary_card(parent, column, label, variable):
        card = ttk.Frame(parent)
        card.grid(row=0, column=column, padx=8, sticky="ew")
        ttk.Label(card, text=label, foreground="#666666").pack(anchor="w")
        ttk.Label(card, textvariable=variable, font=("Segoe UI", 16, "bold")).pack(
            anchor="w"
        )

    def _refresh_stock(self):
        self.stock_items.clear()
        labels = []
        for row in get_stock():
            stock_id, name, length, width, thickness, price, link = row
            label = (
                f"{name} — {length:g} mm, {width:g} x {thickness:g} mm — "
                f"€{price:.2f}"
            )
            labels.append(label)
            self.stock_items[label] = row

        self.stock_combo["values"] = labels
        if labels and self.stock_selection.get() not in self.stock_items:
            self.stock_selection.set(labels[0])
        elif not labels:
            self.stock_selection.set("")
        self._update_link_button()

    def _update_link_button(self, _event=None):
        selected = self.stock_items.get(self.stock_selection.get())
        has_link = selected is not None and bool(selected[6])
        self.open_link_button.configure(state="normal" if has_link else "disabled")

    def _open_stock_link(self):
        selected = self.stock_items.get(self.stock_selection.get())
        link = selected[6] if selected else None
        if not link:
            return
        if not link.lower().startswith(("http://", "https://")):
            messagebox.showerror(
                "Invalid product link",
                "Product links must begin with http:// or https://.",
            )
            return
        webbrowser.open(link)

    def _add_stock(self):
        self._stock_dialog()

    def _edit_stock(self):
        selected = self.stock_items.get(self.stock_selection.get())
        if selected is None:
            messagebox.showinfo("Edit stock", "Select a stock timber first.")
            return
        self._stock_dialog(selected)

    def _auto_pick_stock(self):
        try:
            cuts = load_cutlist(self.file_path.get())
            if not cuts:
                raise ValueError("The cutlist contains no cuts.")

            candidates = [
                row for row in self.stock_items.values() if self._stock_matches_cuts(row, cuts)
            ]
            if not candidates:
                raise ValueError("No stock timber matches the cutlist width and thickness.")

            ranked_candidates = []
            kerf = float(self.kerf.get())
            if kerf < 0:
                raise ValueError("kerf cannot be negative")

            for candidate in candidates:
                optimized_cuts = cutlist_optimizer(candidate[2], list(cuts), kerf=kerf)
                total_used = sum(
                    cut.length + kerf for stock_cuts in optimized_cuts for cut in stock_cuts
                )
                total_waste = len(optimized_cuts) * candidate[2] - total_used
                total_price = len(optimized_cuts) * candidate[5]
                ranked_candidates.append(
                    (len(optimized_cuts), total_price, total_waste, candidate)
                )

            selected = min(ranked_candidates, key=lambda item: item[:3])[3]
            label = next(label for label, row in self.stock_items.items() if row == selected)
            self.stock_selection.set(label)
            self._update_link_button()
            self._show_optimization(selected, cuts, kerf)
        except (OSError, ValueError) as error:
            messagebox.showerror("Unable to choose stock", str(error))

    @staticmethod
    def _stock_matches_cuts(stock, cuts):
        stock_width, stock_thickness = stock[3], stock[4]
        for cut in cuts:
            if cut.width is None or cut.thickness is None:
                return False
            direct_match = math.isclose(cut.width, stock_width) and math.isclose(
                cut.thickness, stock_thickness
            )
            rotated_match = math.isclose(cut.width, stock_thickness) and math.isclose(
                cut.thickness, stock_width
            )
            if not (direct_match or rotated_match):
                return False
        return True

    def _stock_dialog(self, selected=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit stock timber" if selected else "Add stock timber")
        dialog.transient(self.root)
        dialog.grab_set()

        fields = (
            "Name",
            "Length (mm)",
            "Width (mm)",
            "Thickness (mm)",
            "Price (€)",
            "Product page URL (optional)",
        )
        initial_values = (
            (selected[1], selected[2], selected[3], selected[4], selected[5], selected[6])
            if selected
            else ("", "", "", "", "", "")
        )
        variables = []
        for row, label in enumerate(fields):
            ttk.Label(dialog, text=label).grid(
                row=row, column=0, padx=10, pady=5, sticky="w"
            )
            variable = tk.StringVar(value=str(initial_values[row] or ""))
            variables.append(variable)
            ttk.Entry(dialog, textvariable=variable, width=24).grid(
                row=row, column=1, padx=10, pady=5
            )

        def save():
            try:
                name = variables[0].get().strip()
                length, width, thickness, price = (
                    float(variable.get()) for variable in variables[1:5]
                )
                if not name or min(length, width, thickness) <= 0 or price < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Invalid stock",
                    "Enter a name, positive dimensions, and a non-negative price.",
                    parent=dialog,
                )
                return

            link = variables[5].get().strip()
            if selected:
                update_stock(
                    selected[0], name, length, width, thickness, price, link
                )
            else:
                add_stock(name, length, width, thickness, price, link)
            dialog.destroy()
            self._refresh_stock()

        ttk.Button(dialog, text="Save", command=save).grid(
            row=len(fields), column=1, padx=10, pady=10, sticky="e"
        )

    def _optimize(self):
        try:
            selected = self.stock_items.get(self.stock_selection.get())
            if selected is None:
                raise ValueError("Add and select a stock timber first.")

            _, _, stock_length, _, _, stock_price, _ = selected
            kerf = float(self.kerf.get())
            if stock_price < 0:
                raise ValueError("price cannot be negative")

            cuts = load_cutlist(self.file_path.get())
            cut_count = len(cuts)
            self._show_optimization(selected, cuts, kerf, cut_count)
        except (OSError, ValueError) as error:
            messagebox.showerror("Unable to optimize", str(error))
            return

    def _show_optimization(self, selected, cuts, kerf, cut_count=None):
        _, _, stock_length, _, _, stock_price, _ = selected
        optimized_cuts = cutlist_optimizer(stock_length, list(cuts), kerf=kerf)
        if cut_count is None:
            cut_count = len(cuts)

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
        self.cut_count.set(str(cut_count))
        self.beam_count.set(str(len(optimized_cuts)))
        self.total_price.set(f"€{total_price:.2f}")
        self.usage_percentage.set(f"{total_usage:.1%}")
        usage_value = min(max(total_usage * 100, 0), 100)
        self.usage_bar.configure(
            value=usage_value,
            style=self._usage_style(total_usage),
        )
        self.summary.set("Optimization complete")
        self.optimized_cuts = optimized_cuts
        self.layout_stock_length = stock_length
        self.layout_kerf = kerf
        self._draw_layout()

    @staticmethod
    def _usage_style(usage):
        if usage < 0.5:
            return "Usage.Bad.Horizontal.TProgressbar"
        if usage < 0.8:
            return "Usage.Medium.Horizontal.TProgressbar"
        return "Usage.Good.Horizontal.TProgressbar"

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
