from flask import Flask
from flask.ext.restful import reqparse, abort, Api, Resource, fields, marshal
from flask.ext.httpauth import HTTPBasicAuth

from ids.zones import get_zone_details, make_zone, modify_zone, remove_zone, check_zone_endpoint
from ids.users import auth_irods_user

service = Flask(__name__)
api = Api(service)
auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    if username == 'tester' and password == 'blah':
        return True
    else:
        return auth_irods_user(username, password, scheme='password')

@auth.error_handler
def unauthorized():
    return abort(401, message="Invalid authentication credentials")


zone_fields = {
    'zone_name': fields.String,
    'type': fields.String,
    'endpoint': fields.String(attribute='connection'),
    'uri': fields.Url('zone_resource', absolute=True),
    }


# list of zone resources
class ZoneListAPI(Resource):

    @auth.login_required
    def get(self):
        zone_list = get_zone_details()
        if zone_list is None:
            abort(500, message="Server failed to retrieve zone information")
        zones = []
        for zone in zone_list:
            zones.append(marshal(zone, zone_fields))
        return zones


# single zone resources

def lookup_zone(zone_name, abort_notfound=True):
    """
    Get the requested zone resource, or abort with
    an appropriate error code.
    """
    zone = get_zone_details(zone_name=zone_name)
    if zone is None:
        abort(500, message="Server failed to retrieve zone information from iRODS")
    if zone:
        return zone[0]
    if abort_notfound:
        abort(404, message="Zone %s does not exist" % zone_name)
    return None


class ZoneAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('endpoint', type=str, required=True,
                                   help="Must provide the new zone's endpoint (fqdn:port)")
        super(ZoneAPI, self).__init__()


    @auth.login_required
    def get(self, zone_name):
        zone = lookup_zone(zone_name)
        return marshal(zone, zone_fields)


    @auth.login_required
    def delete(self, zone_name):
        zone = lookup_zone(zone_name)

        # we don't allow deletion of the local zone
        if zone['type'] == 'local':
            abort(403, message="Zone %s is local, and cannot be deleted" % zone_name)
            
        # only allow the zone creator to make changes
        if zone['comment'] != 'creator=%s' % auth.username():
            abort(403, message="Zone can only be removed by the zone creator")

        if remove_zone(zone_name):
            abort(500, message="Server error when removing zone %s" % zone_name)
        else:
            return '', 204


    @auth.login_required
    def put(self, zone_name):
        zone = lookup_zone(zone_name, abort_notfound=False)

        # we don't allow changing the local zone
        if zone and zone['type'] == 'local':
            abort(403, message="Zone %s is local, and cannot be managed" % zone_name)

        args = self.reqparse.parse_args()
        (success, reason) = check_zone_endpoint(zone_name, args['endpoint'])
        if not success:
            abort(400, message='problem with endpoint: %s' % reason)

        if zone:
            # updating an existing zone
            # only allow the zone creator to make changes
            if zone['comment'] != 'creator=%s' % auth.username():
                abort(403, message="Zone can only be updated by the zone creator")
                
            newzone = modify_zone(zone_name, args['endpoint'])
            if newzone:
                return marshal(newzone, zone_fields), 200
            else:
                abort(500, message="Server error when modifying zone %s" % zone_name)
        else:
            # creating a new zone
            comment = 'creator=%s' % auth.username()
            newzone = make_zone(zone_name, args['endpoint'], comment)
            if newzone:
                return marshal(newzone, zone_fields), 201
            else:
                abort(500, message="Server error when creating zone %s" % zone_name)


# API routing
api.add_resource(ZoneListAPI,
                 '/api/v1.0/zones',
                 endpoint='zones_resource')
api.add_resource(ZoneAPI,
                 '/api/v1.0/zone/<string:zone_name>',
                 endpoint='zone_resource')
