from cloudscape.portal.ui.core.template import PortalTemplate

class AppController(PortalTemplate):
    """
    Portal administration application controller class.
    """
    def __init__(self, parent):
        super(AppController, self).__init__(parent)
        
        # Construct the request map
        self.map = self._construct_map()
        
    def _construct_map(self):
        """
        Construct the request map.
        """
        return {
            'panels': {
                'users': {
                    'data': self._users
                },
                'groups': {
                    'data': self._groups
                },
                'acls': {
                    'data': self._acls
                },
                'endpoints': {
                    'data': self._endpoints,
                },
                'objects': {
                    'data': self._objects
                },
                'datacenters': {
                    'data': self._datacenters
                }
            },
            'default': 'endpoints'
        }
        
    def _datacenters(self):
        """
        Helper method used to construct the template data needed to render the datacenters
        administration pages.
        """
        
        # Look for a target datacenter
        dc_target = self.get_query_key('datacenter')
        
        # API request parameters
        request   = {
            'datacenters': ('locations', 'get_datacenters')
        }
        
        # If loading details for a datacenter
        if dc_target:
            request['hosts'] = ('host', 'get', {'filter':{'datacenter':dc_target}})
        
        # Make all required API calls
        response = self.api_call_threaded(request)
        
        # Target details / datacenter hosts
        dc_detail = None if not dc_target else [x for x in response['datacenters'] if x['uuid'] == dc_target][0]
        dc_hosts  = None if not dc_target else response['hosts']
        
        def set_contents():
            """
            Set template data contents.
            """
            if dc_target:
                return ['app/admin/tables/datacenters/details.html']
            return ['app/admin/tables/datacenters/list.html']
        
        def set_popups():
            """
            Set template data popups.
            """
            if dc_target:
                return []
            return [
                'app/admin/popups/datacenters/create.html',
                'app/admin/popups/datacenters/delete.html'
            ]
        
        # Return the template data
        return {
            'datacenters': {
                'all':    response['datacenters'],
                'detail': dc_detail,
                'hosts':  response['hosts'],
                'target': dc_target
            },
            'page': {
                'title': 'CloudScape Administration - Datacenters',
                'css': ['admin.css'],
                'contents': set_contents(),
                'popups':  set_popups()
            }
        }
        
    def _users(self):
        """
        Helper method used to construct the template data needed to render the users
        administration page.
        """
        
        # Make all required API calls
        response = self.api_call_threaded({
            'users':  ('user', 'get'),
            'groups': ('group', 'get')
        })
        
        # Return the template data
        return {
            'users':  response['users'],
            'groups': response['groups'],
            'page': {
                'title': 'CloudScape Administration - Users',
                'css': ['admin.css'],
                'contents': [
                    'app/admin/tables/user/all.html',
                    'app/admin/tables/user/details.html'
                ],
                'popups': [
                    'app/admin/popups/user/create.html',
                    'app/admin/popups/user/reset.html',
                    'app/admin/popups/user/disable.html',
                    'app/admin/popups/user/enable.html'
                ]
            } 
        }
        
    def _groups(self):
        """
        Helper method used to construct the template data needed to render the groups
        administration page.
        """
               
        # Make all required API calls
        response = self.api_call_threaded({
            'groups':      ('group', 'get'),
            'users':       ('user', 'get'),
            'acls':        ('auth', 'get_acl'),
            'acl_objects': ('auth', 'get_acl_objects', {'detailed':True})  
        })
                
        # Target group / group details
        groups_tgt    = self.get_query_key('group')
        groups_detail = None if not groups_tgt else [x for x in response['groups'] if x['uuid'] == groups_tgt][0]
                
        def get_contents():
            """
            Retrieve page contents.
            """
            if groups_tgt:
                return [
                    'app/admin/tables/group/overview.html',
                    'app/admin/tables/group/permissions.html'
                ]
            return ['app/admin/tables/group/list.html']
                
        def get_popups():
            """
            Retrieve page popups.
            """
            if groups_tgt:
                return [
                    'app/admin/popups/group/permissions/endpoints.html'
                ]
            return [
                'app/admin/popups/group/create.html',
                'app/admin/popups/group/delete.html'
            ]
                
        # Return the template data 
        return {
            'groups': {
                'all':     response['groups'],
                'target':  groups_tgt,
                'detail':  groups_detail,
                'members': None if not groups_tgt else [x['username'] for x in groups_detail['members']],
                'permissions': {
                    'global': None if not groups_tgt else [x['uuid'] for x in groups_detail['permissions']['global']],
                    'object': None if not groups_tgt else groups_detail['permissions']['object']
                }
            },
            'acls': {
                'all': sorted(response['acls'], key=lambda k: k['name']),
                'objects': response['acl_objects']
            },
            'users': response['users'],
            'page': {
                'title': 'CloudScape Administration - Groups',
                'css': ['admin.css'],
                'contents': get_contents(),
                'popups': get_popups()
            }          
        }
        
    def _acls(self):
        """
        Helper method used to construct the template data needed to render the ACLs
        administration page.
        """
        
        # Make all required API calls
        response = self.api_call_threaded({
            'acls':      ('auth', 'get_acl'),
            'endpoints': ('auth', 'get_endpoints')
        })
        
        # All ACLS / target ACL / target object / target UUID / target endpoint list
        acl_all    = sorted(response['acls'], key=lambda k: k['name'])
        acl_target = self.get_query_key('acl')
        acl_obj    = None if not acl_target else [x for x in acl_all if x['uuid'] == acl_target][0]
        acl_eplist = {'global':[],'object':[],'host':[]}
        
        # If rendering a detailed view of a single ACL
        if acl_target:
            for ep_type, ep_obj in acl_obj['endpoints'].iteritems():
                for ep in ep_obj['list']:
                    acl_eplist[ep_type].append(ep['uuid'])
        
        def set_contents():
            """
            Set template data contents.
            """
            if acl_target:
                return ['app/admin/tables/acl/details.html']
            return ['app/admin/tables/acl/list.html']
        
        def set_popups():
            """
            Set template data popups.
            """
            if acl_target:
                return []
            return [
                'app/admin/popups/acl/create.html',
                'app/admin/popups/acl/delete.html'
            ]
        
        # Return the ACL object
        return {
            'acls': {
                'all':       acl_all,
                'target':    acl_target,
                'uuid':      acl_target,
                'detail':    acl_obj,
                'endpoints': acl_eplist
            },
            'endpoints':     sorted(response['endpoints'], key=lambda k: k['name']),
            'page': {
                'title': 'CloudScape Administration - ACLs',
                'css': ['admin.css'],
                'contents': set_contents(),
                'popups':  set_popups()
            }               
        }
        
    def _objects(self):
        """
        Helper method used to construct the template data needed to render the API objects
        administration page.
        """
        
        # Make all required API calls
        response = self.api_call_threaded({
            'acl_objects': ('auth', 'get_acl_objects', {'detailed':True}),
            'acls':        ('auth', 'get_acl')
        })
        
        # All ACL objects / target object / object details
        acl_objects_all    = sorted(response['acl_objects'], key=lambda k: k['name'])
        acl_objects_tgt    = self.get_query_key('object')
        acl_objects_detail = None if not acl_objects_tgt else [x for x in acl_objects_all if x['type'] == acl_objects_tgt][0]
        
        def get_content():
            """
            Get page contents.
            """
            if acl_objects_tgt:
                return [
                    'app/admin/tables/objects/overview.html',
                    'app/admin/tables/objects/objects.html'
                ]
            return ['app/admin/tables/objects/list.html']
        
        def get_popups():
            """
            Get page popups.
            """
            if acl_objects_tgt:
                return []
            return [
                'app/admin/popups/objects/create.html',
                'app/admin/popups/objects/delete.html'   
            ]
        
        # Return the template data
        return {
            'acls': {
                'objects': {
                    'all':    acl_objects_all,
                    'detail': acl_objects_detail,
                    'target': self.get_query_key('object')
                },
                'all':     sorted(response['acls'], key=lambda k: k['name'])
            },
            'page': {
                'title': 'CloudScape Administration - Objects',
                'css': ['admin.css'],
                'contents': get_content(),
                'popups': get_popups()
            } 
        }
        
    def _endpoints(self):
        """
        Helper method used to construct the template data needed to render the API endpoints
        administration page.
        """
        
        # Make all required API calls
        response = self.api_call_threaded({
            'endpoints':   ('auth', 'get_endpoints'),
            'acl_objects': ('auth', 'get_acl_objects')
        })
        
        # All endpoints / target endpoint / endpoint object
        endpoint_all  = sorted(response['endpoints'], key=lambda k: k['name'])
        endpoint_tgt  = self.get_query_key('endpoint')
        endpoint_obj  = None if not endpoint_tgt else [x for x in endpoint_all if x['uuid'] == endpoint_tgt][0]
        
        # Endpoint modules / utilities / ACL objects
        utils         = []
        modules       = []
        acl_objects   = response['acl_objects']
        
        # Construct modules and utilities
        for ep in endpoint_all:
            utils.append(['%s.%s' % (ep['mod'], ep['cls']), ep['cls']])
            if not ep['mod'] in modules:
                modules.append(ep['mod'])
        
        def set_contents():
            """
            Set template data contents.
            """
            if endpoint_tgt:
                return ['app/admin/tables/endpoints/details.html']
            return ['app/admin/tables/endpoints/list.html']
        
        def set_popups():
            """
            Set template data popups.
            """
            if endpoint_tgt:
                return ['app/admin/popups/endpoints/close.html']
            return [
                'app/admin/popups/endpoints/create.html',
                'app/admin/popups/endpoints/delete.html'
            ]
        
        # Return the template data
        return {
            'endpoints': {
                'all':    endpoint_all,
                'target': endpoint_tgt,
                'uuid':   endpoint_tgt,
                'detail': endpoint_obj,
                'edit':   None if not endpoint_tgt else ('yes' if endpoint_obj['locked'] else 'no'),
            },
            'modules': modules,
            'methods': ['GET', 'POST', 'PUT', 'DELETE'],
            'utils':   utils,
            'acl': {
                'objects': acl_objects
            },
            'page': {
                'title': 'CloudScape Administration - Endpoints',
                'css': ['admin.css'],
                'contents': set_contents(),
                'popups':  set_popups()
            }           
        }
        
    def construct(self):
        """
        Construct and return the template object.
        """
        
        # If the panel is not supported
        if not self.panel in self.map['panels']:
            return self.redirect('portal/admin?panel=%s' % self.map['default'])
        
        # Set the template file
        t_file = 'app/admin/%s.html' % self.panel
        
        # Set the template attributes
        self.set_template(self.map['panels'][self.panel]['data']())
        
        # Construct and return the template response
        return self.response()