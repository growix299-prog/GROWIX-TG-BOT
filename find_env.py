import os
for root, dirs, files in os.walk("c:\\Users\\Hp\\Desktop\\TG BOT"):
    for file in files:
        if file.endswith(".env") or file == ".env":
            print(os.path.join(root, file))
