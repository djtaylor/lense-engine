from lense.engine.api.core.manifest import LenseManifest
from lense.engine.api.handlers import RequestHandler

class Tools_Manifest(RequestHandler):
    """
    Tools for debugging request handler manifests.
    """
    def launch(self):
        """
        Worker method for retrieving group details.
        """
        action = self.get_data('action')
        
        # Compile
        if action == 'compile':
            contents = self.get_data('manifest')
            
            # Run the manifest
            return LenseManifest(contents).launch()