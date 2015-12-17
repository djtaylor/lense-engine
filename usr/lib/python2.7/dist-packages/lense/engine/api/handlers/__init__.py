class RequestHandler(object):
    def get_data(self, key, default=None):
        return LENSE.REQUEST.data.get(key, default)
    
    def ensure(self, *args, **kwargs):
        return LENSE.REQUEST.ensure(*args, **kwargs)