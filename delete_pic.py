import os

folder_path = r"C:\Users\user\Desktop\Big_Folder\Programs\Graduation_project\Project\dest\assets" 

for filename in os.listdir(folder_path):
    if filename.lower().endswith(".png"):
        file_path = os.path.join(folder_path, filename)
        os.remove(file_path)