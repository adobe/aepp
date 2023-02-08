import aepp

config_object = {
    "org_id": "",
    "client_id": "",
    "tech_id": "",
    "pathToKey": "",
    "secret": "",
    "date_limit": 0,
    "sandbox": "",
    "environment": "",
    "token": "",
    "tokenEndpoint": "",
    "imsEndpoint": ""
}

header = {"Accept": "application/json",
          "Content-Type": "application/json",
          "Authorization": "",
          "x-api-key": config_object["client_id"],
          "x-gw-ims-org-id": config_object["org_id"],
          "x-sandbox-name": "prod"
          }

# endpoints
endpoints = {
    # global endpoint is https://platform.adobe.io in prod, otherwise https://platform-$ENV.adobe.io
    "global": "",
    "schemas": "/data/foundation/schemaregistry",
    "query": "/data/foundation/query",
    "catalog": "/data/foundation/catalog",
    "policy": "/data/foundation/dulepolicy",
    "segmentation": "/data/core/ups",
    "export": "/data/foundation/export",
    "identity": "/data/core/",
    "sandboxes": "/data/foundation/sandbox-management",
    "sensei": "/data/sensei",
    "access": "/data/foundation/access-control",
    "flow": "/data/foundation/flowservice",
    "privacy": "/data/core/privacy",
    "dataaccess": "/data/foundation/export",
    "mapping": "/data/foundation/conversion",
    "policy": "/data/foundation/dulepolicy",
    "dataset": "/data/foundation/dataset",
    "ingestion": "/data/foundation/import",
    "observability": "/data/infrastructure/observability/insights",
    "destinationAuthoring": "/data/core/activation/authoring",
    "streaming": {
        "inlet": "",
        "collection": "https://dcs.adobedc.net"
    },
    "audit": "/data/foundation"
}