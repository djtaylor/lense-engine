from lense.engine.api.handlers import RequestHandler
from lense.common.manifest.interface import ManifestInterface

class Manifest_Compile(RequestHandler):
    """
    Compile a request handler manifest.
    """
    def launch(self):
        return self.ok(data=ManifestInterface(self.get_data('manifest')).compile(dump=True))
    
class Manifest_Execute(RequestHandler):
    """
    Execute a request handler manifest.
    """
    def launch(self):
        return self.ok(data=ManifestInterface(self.get_data('manifest')).execute())