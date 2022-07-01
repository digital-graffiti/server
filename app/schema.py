import re
import json
import jsonschema
from jsonschema.exceptions import ValidationError

# Mongo Operators
ALLOWED_QUERY_OPERATORS = ['eq', 'gt', 'gte', 'in', 'lt', 'lte', 'ne', 'nin', 'and', 'not', 'nor', 'or', 'exists', 'type', 'all', 'elemMatch', 'size', '', 'slice']

UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

UUID_SCHEMA = {
    "type": "string",
    "pattern": f"^{UUID_PATTERN}$"
}

# Hex representation of sha256
SHA256_SCHEMA = {
    "type": "string",
    "pattern": "^[0-9a-f]{64}$"
}

# Random user input - any reasonably sized string
RANDOM_SCHEMA = {
    "type": "string",
    "pattern": "^.{1,64}$"
}

OBJECT_OWNER_PATTERN = re.compile(f'"_by": "({UUID_PATTERN})"')
QUERY_OWNER_PATTERN  = re.compile(f'"_to": "({UUID_PATTERN})"')

def allowed_query_properties():
    allowed_properties = { '$' + o: { "$ref": "#/definitions/queryProp" } for o in ALLOWED_QUERY_OPERATORS }
    allowed_properties['_to'] = UUID_SCHEMA
    return allowed_properties

def socket_schema():
    return {
    "type": "object",
    "properties": {
        "messageID": RANDOM_SCHEMA
    },
    "required": ["messageID", "type"],
    "anyOf": [{
        # UPDATE
        "properties": {
            "type": { "const": "update" },
            "object": { "$ref": "#/definitions/object" },
            "idProof": { "oneOf": [
                { "type": "null" },
                RANDOM_SCHEMA
            ]}
        },
        "required": ["object", "idProof"],
    }, {
        # DELETE
        "properties": {
            "type": { "const": "delete" },
            "objectID": SHA256_SCHEMA
        },
        "required": ["objectID"],
    }, {
        # SUBSCRIBE
        "properties": {
            "type": { "const": "subscribe" },
            "query": { "$ref": "#/definitions/query" },
            "since": { "oneOf": [{
                    "type": "string",
                    # A mongo object ID
                    "pattern": "^([a-f\d]{24})$"
                }, { "type": "null" }]
            },
            "queryID": RANDOM_SCHEMA
        },
        "required": ["query", "since", "queryID"],
    }, {
        # UNSUBSCRIBE
        "properties": {
            "type": { "const": "unsubscribe" },
            "queryID": RANDOM_SCHEMA
        },
        "required": ["queryID"],
    }],
    "definitions": {
        "object": {
            "type": "object",
            "additionalProperties": False,
            "patternProperties": {
                # Anything not starting with a "_"
                "^(?!_).*$": True
            },
            "required": ["_id", "_to", "_by", "_contexts"],
            "properties": {
                "_by": UUID_SCHEMA,
                "_to": {
                    "type": "array",
                    "items": UUID_SCHEMA
                },
                "_id": SHA256_SCHEMA,
                "_contexts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "_nearMisses": {
                                "type": "array",
                                "items": { "type": "object" }
                            },
                            "_neighbors": {
                                "type": "array",
                                "items": { "type": "object" }
                            },
                        }
                    }
                }
            }
        },
        "query": {
            "type": "object",
            "additionalProperties": False,
            "patternProperties": {
                # Anything not starting with a "$"
                "^(?!\$).*$": { "$ref": "#/definitions/queryProp" }
            },
            "properties": allowed_query_properties()
        },
        "queryProp": { "oneOf": [
            # Either a root object type
            { "$ref": "#/definitions/query" },
            # A recursive array
            { "type": "array",
                "items": { "$ref": "#/definitions/queryProp" }
            },
            # Or something a constant
            { "type": "string" },
            { "type": "number" },
            { "type": "boolean" },
            { "type": "null" }
        ]}
    }
}

# Initialize the schema validator
VALIDATOR = jsonschema.Draft7Validator(socket_schema())

def validate(msg, owner_id):
    VALIDATOR.validate(msg)

    if msg['type'] == 'update':
        if msg['object']['_by'] != owner_id:
            raise ValidationError("you can only create objects _by yourself")
        if owner_id not in msg['object']['_to']:
            raise ValidationError("you must make all objects _to yourself")
    elif msg['type'] == 'subscribe':
        matches = QUERY_OWNER_PATTERN.findall(json.dumps(msg))
        for match in matches:
            if match != owner_id:
                raise ValidationError("you can only query for objects _to yourself")
