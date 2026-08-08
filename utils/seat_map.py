from models.seat_layout import Seat


def structured_seat_layout(layout, provider):
    is_shaw = provider.casefold() == "shaw"
    max_seat_number = max((max(numbers) for numbers in layout.rows.values() if numbers), default=0)
    rows = []
    for row in sorted(layout.rows, reverse=is_shaw):
        numbers = sorted(set(layout.rows[row]))
        if not numbers:
            continue
        seats = []
        seat_numbers = range(1, max_seat_number + 1)
        if is_shaw:
            seat_numbers = reversed(list(seat_numbers))
        for number in seat_numbers:
            seat = Seat(row, number)
            if seat in layout.available:
                status = "AVAILABLE"
            elif seat in layout.occupied:
                status = "OCCUPIED"
            elif seat not in layout.valid:
                status = "NOT_A_SEAT"
            else:
                status = "UNKNOWN"
            seats.append({"number": number, "status": status})
        rows.append({"row": row, "seats": seats})
    return rows
