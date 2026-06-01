import os
path = os.path.join("templates", "patient_dashboard.html")
html = ""
with open(path, "w", encoding="utf-8") as f:
    f.write(html)
print("written")
