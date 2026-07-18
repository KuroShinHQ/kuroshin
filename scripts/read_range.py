file_path = "kuroshin-downloads/datalar2.md"
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

start = 3900
end = len(lines)
for i in range(start, end):
    print(f"{i+1}: {lines[i]}", end="")
