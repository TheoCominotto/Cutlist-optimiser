from dataclasses import dataclass


@dataclass(frozen=True)
class Cut:
    length: float
    name: str | None = None
    width: float | None = None
    thickness: float | None = None


def load_cutlist(file_path):
    """Load named cut lengths from a text cutlist report."""
    cut_lengths = []
    current_group = None

    def add_current_group():
        if current_group is None:
            return

        for index in range(current_group["count"]):
            name = (
                current_group["names"][index]
                if index < len(current_group["names"])
                else None
            )
            cut_lengths.append(
                Cut(
                    current_group["length"],
                    name,
                    current_group["width"],
                    current_group["thickness"],
                )
            )

    with open(file_path, encoding="utf-8") as cutlist_file:
        for line_number, line in enumerate(cutlist_file, start=1):
            values = line.split()
            if len(values) >= 4:
                try:
                    count = int(values[0])
                    length = float(values[1])
                    float(values[2])
                    float(values[3])
                except ValueError:
                    continue

                add_current_group()
                if count < 0 or length <= 0:
                    raise ValueError(
                        f"Invalid count or length on line {line_number}: {line.strip()}"
                    )
                current_group = {
                    "count": count,
                    "length": length,
                    "width": float(values[2]),
                    "thickness": float(values[3]),
                    "names": [" ".join(values[4:])] if len(values) > 4 else [],
                }
            elif current_group is not None and values:
                current_group["names"].append(" ".join(values))

    add_current_group()
    return cut_lengths


def cutlist_optimizer(stock_length, cut_lengths, kerf=0):
    """Pack cuts into stock pieces while preserving each cut's name."""
    if stock_length <= 0:
        raise ValueError("stock length must be greater than zero")
    if kerf < 0:
        raise ValueError("kerf cannot be negative")

    for cut in cut_lengths:
        cut_length = cut.length if isinstance(cut, Cut) else cut
        if cut_length + kerf > stock_length:
            raise ValueError(
                f"Cut length {cut_length:g} plus kerf does not fit in stock length "
                f"{stock_length:g}"
            )

    cut_lengths.sort(
        key=lambda cut: cut.length if isinstance(cut, Cut) else cut,
        reverse=True,
    )

    optimized_cuts = []
    while cut_lengths:
        current_cut = []
        remaining_length = stock_length

        for cut in cut_lengths[:]:
            cut_length = cut.length if isinstance(cut, Cut) else cut
            if cut_length + kerf <= remaining_length:
                current_cut.append(cut)
                remaining_length -= cut_length + kerf
                cut_lengths.remove(cut)

        optimized_cuts.append(current_cut)

    return optimized_cuts
