import argparse

from optimizer import cutlist_optimizer, load_cutlist


def main():
    parser = argparse.ArgumentParser(description="Optimize a text cutlist.")
    parser.add_argument("file_path", help="Path to the text cutlist report")
    parser.add_argument(
        "--stock-length",
        type=float,
        required=True,
        help="Length of each stock piece, in the same units as the cutlist",
    )
    parser.add_argument(
        "--kerf",
        type=float,
        default=0,
        help="Material lost by the blade for each cut (default: 0)",
    )
    parser.add_argument(
        "--stock-price",
        type=float,
        required=True,
        help="Price of one stock piece",
    )
    args = parser.parse_args()

    if args.stock_price < 0:
        parser.error("stock price cannot be negative")

    try:
        cuts = load_cutlist(args.file_path)
        imported_count = len(cuts)
        optimized_cuts = cutlist_optimizer(
            args.stock_length,
            cuts,
            kerf=args.kerf,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Imported cuts: {imported_count}")
    print(f"Stock length: {args.stock_length:g}")
    print(f"Kerf: {args.kerf:g}")
    print(f"Stock pieces needed: {len(optimized_cuts)}\n")
    print(f"Total price: {len(optimized_cuts) * args.stock_price:.2f}")

    total_used_length = 0
    for stock_number, stock_cuts in enumerate(optimized_cuts, start=1):
        used_length = sum(cut.length + args.kerf for cut in stock_cuts)
        waste = args.stock_length - used_length
        usage_percentage = used_length / args.stock_length * 100
        total_used_length += used_length
        print(
            f"Stock piece {stock_number}: used {used_length:g}, "
            f"waste {waste:g}, usage {usage_percentage:.1f}%"
        )
        for cut in stock_cuts:
            name = cut.name or "Unnamed cut"
            print(f"  {name}: {cut.length:g}")
        print()

    if optimized_cuts:
        total_stock_length = len(optimized_cuts) * args.stock_length
        total_usage_percentage = total_used_length / total_stock_length * 100
        print(f"Overall usage: {total_usage_percentage:.1f}%")


if __name__ == "__main__":
    main()
