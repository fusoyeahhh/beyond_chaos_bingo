import csv

def parse(fname):
    with open(fname) as fin:
        lines = fin.readlines()

    state = "header"
    row_tmplt = {
        "index": 0,
        "square": None,
        "segment": None,
        "segment_index": None,
        "choices": None,
        "type": None,
    }
    row = row_tmplt.copy()
    squares = []
    free = True
    while True:
        if row["segment"] is None:
            row["segment"] = lines.pop(0).strip()
            row["segment_index"] = int(row["segment"].split(" ")[1])
            lines.pop(0)
            continue

        if free:
            lines.pop(0)
            lines.pop(0)
            squares.append({
                **row,
                "square": lines.pop(0).strip(),
                "type": "free",
            })
            row["index"] += 1
            lines.pop(0)
            free = False
            continue

        if row["type"] is None:
            #print("no type --- ", lines[0].strip())
            #print(row)
            type_, choices = lines.pop(0).strip().split(":")
            row["type"], row["choices"] = type_.strip(), int(choices[1:-1].split(" ")[-1])
            #print(row)
            lines.pop(0)
            continue
        
        line = lines.pop(0).strip()
        if len(lines) == 0:
            break

        if line != "":
            #print("with type --- ", lines[0].strip())
            squares.append({
                **row,
                "square": line.strip(),
            })
            row["index"] += 1
            #print(squares[-1])
        else:
            row["type"] = None

    return squares

if __name__ == "__main__":
    import sys
    from csv import DictWriter

    squares = parse(sys.argv[-1])

    writer = DictWriter(sys.stdout, list(squares[0]))
    writer.writeheader()
    for entry in squares:
        writer.writerow(entry)
