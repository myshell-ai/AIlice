import os
from ailice.modules.AScrollablePage import AScrollablePage

class AFileBrowser(AScrollablePage):
    def __init__(self, functions: dict[str, str]):
        super(AFileBrowser, self).__init__(functions=functions)
        return

    def Browse(self, path: str) -> str:
        if not (os.path.exists(path) and os.path.isdir(path)):
            return f"Specified directory {path} does NOT exist."
        
        files = []
        dirs = []
        for filename in os.listdir(path):
            if os.path.isfile(os.path.join(path, filename)):
                files.append(filename)
            else:
                dirs.append(filename)
        self.LoadPage("Folders: " + " ".join(dirs) + "\n\nFiles: " + " ".join(files), "BOTTOM")
        return self()
    
    def Destroy(self):
        return