import sys

data = sys.stdin.read()

hist = {}
total = 0
maxim = 0
for val in data.split("\n"):
    try:
        no = int(val)
        if no not in hist:
            hist[no] = 0
        hist[no] += 1
        total += 1
        if hist[no] > maxim:
            maxim = hist[no]
    except:
        pass
scale = 80 / maxim

print("total:", total)
for key in sorted(hist.keys()):
    print(key, "=" * int(hist[key] * scale))
    # print(key+": "+ ("="*(hist[key]*scale) ))
