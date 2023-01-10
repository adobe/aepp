import aepp
from aepp import connector
from copy import deepcopy
import time,json
import logging
from dataclasses import dataclass

@dataclass
class _Data:
    def __init__(self):
        self.flowId = {}
        self.flowSpecId = {}


class FlowService:
    """
    The Flow Service manage the ingestion part of the data in AEP.
    For more information, relate to the API Documentation, you can directly refer to the official documentation:
        https://www.adobe.io/apis/experienceplatform/home/api-reference.html#!acpdr/swagger-specs/flow-service.yaml
        https://experienceleague.adobe.com/docs/experience-platform/sources/home.html
        https://experienceleague.adobe.com/docs/experience-platform/destinations/home.html
    """

    PATCH_REFERENCE = [
        {
            "op": "Add",
            "path": "/auth/params",
            "value": {
                "description": "A new description to provide further context on a specified connection or flow."
            },
        }
    ]

    ## logging capability
    loggingEnabled = False
    logger = None

    def __init__(
        self,
        config: dict = aepp.config.config_object,
        header=aepp.config.header,
        loggingObject: dict = None,
        **kwargs,
    ):
        """
        initialize the Flow Service instance.
        Arguments:
            config : OPTIONAL : config object in the config module.
            header : OPTIONAL : header object  in the config module.
            loggingObject : OPTIONAL : A dictionary presenting the configuration of the logging service.
        """
        if loggingObject is not None and sorted(
            ["level", "stream", "format", "filename", "file"]
        ) == sorted(list(loggingObject.keys())):
            self.loggingEnabled = True
            self.logger = logging.getLogger(f"{__name__}")
            self.logger.setLevel(loggingObject["level"])
            formatter = logging.Formatter(loggingObject["format"])
            if loggingObject["file"]:
                fileHandler = logging.FileHandler(loggingObject["filename"])
                fileHandler.setFormatter(formatter)
                self.logger.addHandler(fileHandler)
            if loggingObject["stream"]:
                streamHandler = logging.StreamHandler()
                streamHandler.setFormatter(formatter)
                self.logger.addHandler(streamHandler)
        self.connector = connector.AdobeRequest(
            config_object=config,
            header=header,
            loggingEnabled=self.loggingEnabled,
            logger=self.logger,
        )
        self.header = self.connector.header
        self.header.update(**kwargs)
        self.sandbox = self.connector.config["sandbox"]
        self.endpoint = aepp.config.endpoints["global"] + aepp.config.endpoints["flow"]
        self.data = _Data()

    def getResource(
        self,
        endpoint: str = None,
        params: dict = None,
        format: str = "json",
        save: bool = False,
        **kwargs,
    ) -> dict:
        """
        Template for requesting data with a GET method.
        Arguments:
            endpoint : REQUIRED : The URL to GET
            params: OPTIONAL : dictionary of the params to fetch
            format : OPTIONAL : Type of response returned. Possible values:
                json : default
                txt : text file
                raw : a response object from the requests module
        """
        if endpoint is None:
            raise ValueError("Require an endpoint")
        if self.loggingEnabled:
            self.logger.debug(f"Starting getResource")
        res = self.connector.getData(endpoint, params=params, format=format)
        if save:
            if format == "json":
                aepp.saveFile(
                    module="catalog",
                    file=res,
                    filename=f"resource_{int(time.time())}",
                    type_file="json",
                    encoding=kwargs.get("encoding", "utf-8"),
                )
            elif format == "txt":
                aepp.saveFile(
                    module="catalog",
                    file=res,
                    filename=f"resource_{int(time.time())}",
                    type_file="txt",
                    encoding=kwargs.get("encoding", "utf-8"),
                )
            else:
                print(
                    "element is an object. Output is unclear. No save made.\nPlease save this element manually"
                )
        return res

    def getConnections(
        self, limit: int = 20, n_results: int = 100, count: bool = False, **kwargs
    ) -> list:
        """
        Returns the list of connections available.
        Arguments:
            limit : OPTIONAL : number of result returned per request (default 20)
            n_results : OPTIONAL : number of total result returned (default 100, set to "inf" for retrieving everything)
            count : OPTIONAL : if set to True, just returns the number of connections
        kwargs will be added as query parameters
        """
        if self.loggingEnabled:
            self.logger.debug(f"Starting getConnections")
        params = {"limit": limit}
        if count:
            params["count"] = count
        for kwarg in kwargs:
            params[kwarg] = kwargs[kwarg]
        path = "/connections"
        res = self.connector.getData(self.endpoint + path, params=params)
        try:
            data = res["items"]
            continuationToken = res.get("_links", {}).get("next", {}).get("href", "")
            while continuationToken != "" and len(data) < float(n_results):
                res = self.connector.getData(
                    self.endpoint + continuationToken, params=params
                )
                data += res["items"]
                continuationToken = (
                    res.get("_links", {}).get("next", {}).get("href", "")
                )
            return data
        except:
            return res

    def createConnection(
        self,
        data: dict = None,
        name: str = None,
        auth: dict = None,
        connectionSpec: dict = None,
        **kwargs,
    ) -> dict:
        """
        Create a connection based on either the data being passed or the information passed.
        Arguments:
            data : REQUIRED : dictionary containing the different elements required for the creation of the connection.

            In case you didn't pass a data parameter, you can pass different information.
            name : REQUIRED : name of the connection.
            auth : REQUIRED : dictionary that contains "specName" and "params"
                specName : string that names of the the type of authentication to be used with the base connection.
                params : dict that contains credentials and values necessary to authenticate and create a connection.
            connectionSpec : REQUIRED : dictionary containing the "id" and "verison" key.
                id : The specific connection specification ID associated with source
                version : Specifies the version of the connection specification ID. Omitting this value will default to the most recent version
        Possible kwargs:
            responseType : by default json, but you can request 'raw' that return the requests response object.
        """
        if self.loggingEnabled:
            self.logger.debug(f"Starting createConnection")
        path = "/connections"
        if data is not None:
            if (
                "name" not in data.keys()
                or "auth" not in data.keys()
                or "connectionSpec" not in data.keys()
            ):
                raise Exception(
                    "Require some keys to be present : name, auth, connectionSpec"
                )
            obj = data
            res = self.connector.postData(self.endpoint + path, data=obj,format=kwargs.get('responseType','json'))
            return res
        elif data is None:
            if "specName" not in auth.keys() or "params" not in auth.keys():
                raise Exception(
                    "Require some keys to be present in auth dict : specName, params"
                )
            if "id" not in connectionSpec.keys():
                raise Exception(
                    "Require some keys to be present in connectionSpec dict : id"
                )
            if name is None:
                raise Exception("Require a name to be present")
            obj = {"name": name, "auth": auth, "connectionSpec": connectionSpec}
            res = self.connector.postData(self.endpoint + path, data=obj,format=kwargs.get('responseType','json'))
            return res

    def createStreamingConnection(
        self,
        name: str = None,
        sourceId: str = None,
        dataType: str = "xdm",
        paramName: str = None,
        description: str = "provided by aepp",
        **kwargs,
    ) -> dict:
        """
        Create a Streaming connection based on the following connectionSpec :
        "connectionSpec": {
                "id": "bc7b00d6-623a-4dfc-9fdb-f1240aeadaeb",
                "version": "1.0",
            },
            with provider ID : 521eee4d-8cbe-4906-bb48-fb6bd4450033
        Arguments:
            name : REQUIRED : Name of the Connection.
            sourceId : REQUIRED : The ID of the streaming connection you want to create (random string possible).
            dataType : REQUIRED : The type of data to ingest (default xdm)
            paramName : REQUIRED : The name of the streaming connection you want to create.
            description : OPTIONAL : if you want to add a description
        kwargs possibility:
            specName : if you want to modify the specification Name.(Default : "Streaming Connection")
            responseType : by default json, but you can request 'raw' that return the requests response object.
        """
        if name is None:
            raise ValueError("Require a name for the connection")
        if sourceId is None:
            raise Exception("Require an ID for the connection")
        if dataType is None:
            raise Exception("Require a dataType specified")
        if paramName is None:
            raise ValueError("Require a name for the Streaming Connection")
        if self.loggingEnabled:
            self.logger.debug(f"Starting createStreamingConnection")
        obj = {
            "name": name,
            "providerId": "521eee4d-8cbe-4906-bb48-fb6bd4450033",
            "description": description,
            "connectionSpec": {
                "id": "bc7b00d6-623a-4dfc-9fdb-f1240aeadaeb",
                "version": "1.0",
            },
            "auth": {
                "specName": kwargs.get("specName", "Streaming Connection"),
                "params": {
                    "sourceId": sourceId,
                    "dataType": dataType,
                    "name": paramName,
                },
            },
        }
        res = self.createConnection(data=obj,responseType=kwargs.get('responseType','json'))
        return res

    def getConnection(self, connectionId: str = None) -> dict:
        """
        Returns a specific connection object.
        Argument:
            connectionId : REQUIRED : The ID of the connection you wish to retrieve.
        """
        if connectionId is None:
            raise Exception("Require a connectionId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting getConnection")
        path = f"/connections/{connectionId}"
        res = self.connector.getData(self.endpoint + path)
        return res

    def connectionTest(self, connectionId: str = None) -> dict:
        """
        Test a specific connection ID.
        Argument:
            connectionId : REQUIRED : The ID of the connection you wish to test.
        """
        if connectionId is None:
            raise Exception("Require a connectionId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting connectionTest")
        path: str = f"/connections/{connectionId}/test"
        res: dict = self.connector.getData(self.endpoint + path)
        return res

    def deleteConnection(self, connectionId: str = None) -> dict:
        """
        Delete a specific connection ID.
        Argument:
            connectionId : REQUIRED : The ID of the connection you wish to delete.
        """
        if connectionId is None:
            raise Exception("Require a connectionId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting deleteConnection")
        path: str = f"/connections/{connectionId}"
        res: dict = self.connector.deleteData(self.endpoint + path)
        return res

    def getConnectionSpecs(self) -> list:
        """
        Returns the list of connectionSpecs in that instance.
        If that doesn't work, return the response.
        """
        path: str = "/connectionSpecs"
        if self.loggingEnabled:
            self.logger.debug(f"Starting getConnectionSpecs")
        res: dict = self.connector.getData(self.endpoint + path)
        try:
            data: list = res["items"]
            return data
        except:
            return res

    def getConnectionSpec(self, specId: str = None) -> dict:
        """
        Returns the detail for a specific connection.
        Arguments:
            specId : REQUIRED : The specification ID of a connection
        """
        if specId is None:
            raise Exception("Require a specId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting getConnectionSpec")
        path: str = f"/connectionSpecs/{specId}"
        res: dict = self.connector.getData(self.endpoint + path)
        return res.get('items',[{}])[0]

    def getFlows(
        self,
        limit: int = 10,
        n_results: int = 100,
        prop: str = None,
        filterMappingSetIds: list = None,
        filterSourceIds: list = None,
        filterTargetIds: list = None,
        **kwargs,
    ) -> list:
        """
        Returns the flows set between Source and Target connection.
        Arguments:
            limit : OPTIONAL : number of results returned
            n_results : OPTIONAL : total number of results returned (default 100, set to "inf" for retrieving everything)
            prop : OPTIONAL : comma separated list of top-level object properties to be returned in the response.
                Used to cut down the amount of data returned in the response body.
                For example, prop=id==3416976c-a9ca-4bba-901a-1f08f66978ff,6a8d82bc-1caf-45d1-908d-cadabc9d63a6,3c9b37f8-13a6-43d8-bad3-b863b941fedd.
            filterMappingSetId : OPTIONAL : returns only the flow that possess the mappingSetId passed in a list.
            filterSourceIds : OPTIONAL : returns only the flow that possess the sourceConnectionIds passed in a list.
            filterTargetIds : OPTIONAL : returns only the flow that possess the targetConnectionIds passed in a list.
        """
        if self.loggingEnabled:
            self.logger.debug(f"Starting getFlows")
        params: dict = {"limit": limit, "count": kwargs.get("count", False)}
        if property is not None:
            params["property"] = prop
        if kwargs.get("continuationToken", False) != False:
            params["continuationToken"] = kwargs.get("continuationToken")
        path: str = "/flows"
        res: dict = self.connector.getData(self.endpoint + path, params=params)
        token: str = res.get("_links", {}).get("next", {}).get("href", "")
        items = res["items"]
        while token != "" and len(items) < float(n_results):
            continuationToken = token.split("=")[1]
            params["continuationToken"] = continuationToken
            res = self.connector.getData(self.endpoint + path, params=params)
            token = res["_links"].get("next", {}).get("href", "")
            items += res["items"]
        self.data.flowId = {item["name"]: item["id"] for item in items}
        self.data.flowSpecId = {item["name"]: item.get("flowSpec",{}).get('id') for item in items}
        if filterMappingSetIds is not None:
            filteredItems = []
            for mappingsetId in filterMappingSetIds:
                for item in items:
                    if "transformations" in item.keys():
                        for element in item["transformations"]:
                            if element["params"].get("mappingId", "") == mappingsetId:
                                filteredItems.append(item)
            items = filteredItems
        if filterSourceIds is not None:
            filteredItems = []
            for sourceId in filterSourceIds:
                for item in items:
                    if sourceId in item["sourceConnectionIds"]:
                        filteredItems.append(item)
            items = filteredItems
        if filterTargetIds is not None:
            filteredItems = []
            for targetId in filterTargetIds:
                for item in items:
                    if targetId in item["targetConnectionIds"]:
                        filteredItems.append(item)
            items = filteredItems
        return items

    def getFlow(self, flowId: str = None) -> dict:
        """
        Returns the details of a specific flow.
        Arguments:
            flowId : REQUIRED : the flow ID to be returned
        """
        if flowId is None:
            raise Exception("Require a flowId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting getFlow")
        path: str = f"/flows/{flowId}"
        res: dict = self.connector.getData(self.endpoint + path)
        return res.get('items',[{}])[0]

    def deleteFlow(self, flowId: str = None) -> dict:
        """
        Delete a specific flow by its ID.
        Arguments:
            flowId : REQUIRED : the flow ID to be returned
        """
        if flowId is None:
            raise Exception("Require a flowId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting deleteFlow")
        path: str = f"/flows/{flowId}"
        res: dict = self.connector.deleteData(self.endpoint + path)
        return res

    def createFlow(self, obj: dict = None) -> dict:
        """
        Create a flow with the API.
        Arguments:
            obj : REQUIRED : body to create the flow service.
                Details can be seen at https://www.adobe.io/apis/experienceplatform/home/api-reference.html#/Flows/postFlow
                requires following keys : name, flowSpec, sourceConnectionIds, targetConnectionIds, transformations, scheduleParams.
        """
        if obj is None:
            raise Exception("Require a dictionary to create the flow")
        if "name" not in obj.keys():
            raise KeyError("missing 'name' parameter in the dictionary")
        if "flowSpec" not in obj.keys():
            raise KeyError("missing 'flowSpec' parameter in the dictionary")
        if "sourceConnectionIds" not in obj.keys():
            raise KeyError("missing 'sourceConnectionIds' parameter in the dictionary")
        if "targetConnectionIds" not in obj.keys():
            raise KeyError("missing 'targetConnectionIds' parameter in the dictionary")
        if self.loggingEnabled:
            self.logger.debug(f"Starting createFlow")
        path: str = "/flows"
        res: dict = self.connector.postData(self.endpoint + path, data=obj)
        return res

    def updateFlow(
        self, flowId: str = None, etag: str = None, updateObj: list = None
    ) -> dict:
        """
        update the flow based on the operation provided.
        Arguments:
            flowId : REQUIRED : the ID of the flow to Patch.
            etag : REQUIRED : ETAG value for patching the Flow.
            updateObj : REQUIRED : List of operation to realize on the flow.

            Follow the following structure:
            [
                {
                    "op": "Add",
                    "path": "/auth/params",
                    "value": {
                    "description": "A new description to provide further context on a specified connection or flow."
                    }
                }
            ]
        """
        if flowId is None:
            raise Exception("Require a flow ID to be present")
        if etag is None:
            raise Exception("Require etag to be present")
        if updateObj is None:
            raise Exception("Require a list with data to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting updateFlow")
        privateHeader = deepcopy(self.header)
        privateHeader["if-match"] = etag
        path: str = f"/flows/{flowId}"
        res: dict = self.connector.patchData(
            self.endpoint + path, headers=privateHeader, data=updateObj
        )
        return res

    def getFlowSpecs(self, prop: str = None) -> list:
        """
        Returns the flow specifications.
        Arguments:
            prop : OPTIONAL : A comma separated list of top-level object properties to be returned in the response.
                Used to cut down the amount of data returned in the response body.
                For example, prop=id==3416976c-a9ca-4bba-901a-1f08f66978ff,6a8d82bc-1caf-45d1-908d-cadabc9d63a6,3c9b37f8-13a6-43d8-bad3-b863b941fedd.
        """
        if self.loggingEnabled:
            self.logger.debug(f"Starting getFlowSpecs")
        path: str = "/flowSpecs"
        params = {}
        if prop is not None:
            params["property"] = prop
        res: dict = self.connector.getData(self.endpoint + path, params=params)
        items: list = res["items"]
        return items

    def getFlowSpec(self, flowSpecId) -> dict:
        """
        Return the detail of a specific flow ID Spec
        Arguments:
            flowSpecId : REQUIRED : The flow ID spec to be checked
        """
        if flowSpecId is None:
            raise Exception("Require a flowSpecId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting getFlowSpec")
        path: str = f"/flowSpecs/{flowSpecId}"
        res: dict = self.connector.getData(self.endpoint + path)
        return res.get('items',[{}])[0]

    def getRuns(
        self, limit: int = 10, n_results: int = 100, prop: str = None, **kwargs
    ) -> list:
        """
        Returns the list of runs. Runs are instances of a flow execution.
        Arguments:
            limit : OPTIONAL : number of results returned per request
            n_results : OPTIONAL : total number of results returned (default 100, set to "inf" for retrieving everything)
            prop : OPTIONAL : comma separated list of top-level object properties to be returned in the response.
                Used to cut down the amount of data returned in the response body.
                For example, prop=id==3416976c-a9ca-4bba-901a-1f08f66978ff,6a8d82bc-1caf-45d1-908d-cadabc9d63a6,3c9b37f8-13a6-43d8-bad3-b863b941fedd.
        """
        if self.loggingEnabled:
            self.logger.debug(f"Starting getRuns")
        path = "/runs"
        params = {"limit": limit, "count": kwargs.get("count", False)}
        if prop is not None:
            params["property"] = prop
        if kwargs.get("continuationToken", False):
            params["continuationToken"] = kwargs.get("continuationToken")
        res: dict = self.connector.getData(self.endpoint + path, params=params)
        items: list = res["items"]
        nextPage = res["_links"].get("next", {}).get("href", "")
        while nextPage != "" and len(items) < float(n_results):
            token: str = res["_links"]["next"].get("href", "")
            continuationToken: str = token.split("=")[1]
            params["continuationToken"] = continuationToken
            res = self.connector.getData(self.endpoint + path, params=params)
            items += res.get('items')
            nextPage = res["_links"].get("next", {}).get("href", "")
        return items

    def createRun(self, flowId: str = None, status: str = "active") -> dict:
        """
        Generate a run based on the flowId.
        Arguments:
            flowId : REQUIRED : the flow ID to run
            stats : OPTIONAL : Status of the flow
        """
        path = "/runs"
        if flowId is None:
            raise Exception("Require a flowId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting createRun")
        obj = {"flowId": flowId, "status": status}
        res: dict = self.connector.postData(self.endpoint + path, data=obj)
        return res

    def getRun(self, runId: str = None) -> dict:
        """
        Return a specific runId.
        Arguments:
            runId : REQUIRED : the run ID to return
        """
        if runId is None:
            raise Exception("Require a runId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting getRun")
        path: str = f"/runs/{runId}"
        res: dict = self.connector.getData(self.endpoint + path)
        return res

    def getSourceConnections(self, n_results: int = 100, **kwargs) -> list:
        """
        Return the list of source connections
        Arguments:
            n_results : OPTIONAL : total number of results returned (default 100, set to "inf" for retrieving everything)
        kwargs will be added as query parameterss
        """
        if self.loggingEnabled:
            self.logger.debug(f"Starting getSourceConnections")
        params = {**kwargs}
        path: str = f"/sourceConnections"
        res: dict = self.connector.getData(self.endpoint + path, params=params)
        data: list = res["items"]
        nextPage = res["_links"].get("next", {}).get("href", "")
        while nextPage != "" and len(data) < float(n_results):
            continuationToken = nextPage.split("=")[1]
            params["continuationToken"] = continuationToken
            res: dict = self.connector.getData(self.endpoint + path, params=params)
            data += res["items"]
            nextPage = res["_links"].get("next", {}).get("href", "")
        return data

    def getSourceConnection(self, sourceConnectionId: str = None) -> dict:
        """
        Return detail of the sourceConnection ID
        Arguments:
            sourceConnectionId : REQUIRED : The source connection ID to be retrieved
        """
        if sourceConnectionId is None:
            raise Exception("Require a sourceConnectionId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting getSourceConnection")
        path: str = f"/sourceConnections/{sourceConnectionId}"
        res: dict = self.connector.getData(self.endpoint + path)
        return res.get('items',[{}])[0]

    def deleteSourceConnection(self, sourceConnectionId: str = None) -> dict:
        """
        Delete a sourceConnection ID
        Arguments:
            sourceConnectionId : REQUIRED : The source connection ID to be deleted
        """
        if sourceConnectionId is None:
            raise Exception("Require a sourceConnectionId to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting deleteSourceConnection")
        path: str = f"/sourceConnections/{sourceConnectionId}"
        res: dict = self.connector.deleteData(self.endpoint + path)
        return res

    def createSourceConnection(self, data: dict = None) -> dict:
        """
        Create a sourceConnection based on the dictionary passed.
        Arguments:
            obj : REQUIRED : the data to be passed for creation of the Source Connection.
                Details can be seen at https://www.adobe.io/apis/experienceplatform/home/api-reference.html#/Source_connections/postSourceConnection
                requires following keys : name, baseConnectionId, data, params, connectionSpec.
        """
        if data is None:
            raise Exception("Require a dictionary with data to be present")
        if "name" not in data.keys():
            raise KeyError("Require a 'name' key in the dictionary passed")
        if "connectionSpec" not in data.keys():
            raise KeyError("Require a 'connectionSpec' key in the dictionary passed")
        if self.loggingEnabled:
            self.logger.debug(f"Starting createSourceConnection")
        path: str = f"/sourceConnections"
        res: dict = self.connector.postData(self.endpoint + path, data=data)
        return res

    def createSourceConnectionStreaming(
        self,
        connectionId: str = None,
        name: str = None,
        format: str = "delimited",
        description: str = "",
    ) -> dict:
        """
        Create a source connection based on streaming connection created.
        Arguments:
            connectionId : REQUIRED : The Streaming connection ID.
            name : REQUIRED : Name of the Connection.
            format : REQUIRED : format of the data sent (default : delimited)
            description : REQUIRED : Description of of the Connection Source.
        """
        if self.loggingEnabled:
            self.logger.debug(f"Starting createSourceConnectionStreaming")
        obj = {
            "name": name,
            "providerId": "521eee4d-8cbe-4906-bb48-fb6bd4450033",
            "description": description,
            "baseConnectionId": connectionId,
            "connectionSpec": {
                "id": "bc7b00d6-623a-4dfc-9fdb-f1240aeadaeb",
                "version": "1.0",
            },
            "data": {"format": format},
        }
        res = self.createSourceConnection(data=obj)
        return res

    def updateSourceConnection(
        self, sourceConnectionId: str = None, etag: str = None, updateObj: list = None
    ) -> dict:
        """
        Update a source connection based on the ID provided with the object provided.
        Arguments:
            sourceConnectionId : REQUIRED : The source connection ID to be updated
            etag: REQUIRED : A header containing the etag value of the connection or flow to be updated.
            updateObj : REQUIRED : The operation call used to define the action needed to update the connection. Operations include add, replace, and remove.
        """
        if sourceConnectionId is None:
            raise Exception("Require a sourceConnection to be present")
        if etag is None:
            raise Exception("Require etag to be present")
        if updateObj is None:
            raise Exception("Require a list with data to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting updateSourceConnection")
        privateHeader = deepcopy(self.header)
        privateHeader["if-match"] = etag
        path: str = f"/sourceConnections/{sourceConnectionId}"
        res: dict = self.connector.patchData(
            self.endpoint + path, headers=privateHeader, data=updateObj
        )
        return res

    def getTargetConnections(self, n_results: int = 100, **kwargs) -> dict:
        """
        Return the target connections
        Arguments:
            n_results : OPTIONAL : total number of results returned (default 100, set to "inf" for retrieving everything)
        kwargs will be added as query parameterss
        """
        params = {**kwargs}
        path: str = f"/targetConnections"
        res: dict = self.connector.getData(self.endpoint + path, params=params)
        data: list = res["items"]
        nextPage = res["_links"].get("next", {}).get("href", "")
        while nextPage != "" and len(data) < float(n_results):
            continuationToken = nextPage.split("=")[1]
            params["continuationToken"] = continuationToken
            res: dict = self.connector.getData(self.endpoint + path, params=params)
            data += res["items"]
            nextPage = res["_links"].get("next", {}).get("href", "")
        return data

    def getTargetConnection(self, targetConnectionId: str = None) -> dict:
        """
        Retrieve a specific Target connection detail.
        Arguments:
            targetConnectionId : REQUIRED : The target connection ID is a unique identifier used to create a flow.
        """
        if targetConnectionId is None:
            raise Exception("Require a target connection ID to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting getTargetConnection")
        path: str = f"/targetConnections/{targetConnectionId}"
        res: dict = self.connector.getData(self.endpoint + path)
        return res.get('items',[None])[0]

    def deleteTargetConnection(self, targetConnectionId: str = None) -> dict:
        """
        Delete a specific Target connection detail
        Arguments:
             targetConnectionId : REQUIRED : The target connection ID to be deleted
        """
        if targetConnectionId is None:
            raise Exception("Require a target connection ID to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting deleteTargetConnection")
        path: str = f"/targetConnections/{targetConnectionId}"
        res: dict = self.connector.deleteData(self.endpoint + path)
        return res

    def createTargetConnection(
        self,
        name: str = None,
        connectionSpecId: str = None,
        datasetId: str = None,
        format: str = "parquet_xdm",
        version: str = "1.0",
        description: str = "",
        data: dict = None,
    ) -> dict:
        """
        Create a new target connection
        Arguments:
                name : REQUIRED : The name of the target connection
                connectionSpecId : REQUIRED : The connectionSpecId to use.
                datasetId : REQUIRED : The dataset ID that is the target
                version : REQUIRED : version to be used (1.0 by default)
                format : REQUIRED : Data format to be used (parquet_xdm by default)
                description : OPTIONAL : description of your target connection
                data : OPTIONAL : If you pass the complete dictionary for creation
        Details can be seen at https://www.adobe.io/apis/experienceplatform/home/api-reference.html#/Target_connections/postTargetConnection
        requires following keys : name, data, params, connectionSpec.
        """
        if self.loggingEnabled:
            self.logger.debug(f"Starting createTargetConnection")
        path: str = f"/targetConnections"
        if data is not None and type(data) == dict:
            obj = data
            res: dict = self.connector.postData(self.endpoint + path, data=obj)
        else:
            if name is None:
                raise ValueError("Require a name to be passed")
            if connectionSpecId is None:
                raise ValueError("Require a connectionSpec Id to be passed")
            if datasetId is None:
                raise ValueError("Require a datasetId to be passed")
            obj = {
                "name": name,
                "description": description,
                "connectionSpec": {"id": connectionSpecId, "version": version},
                "data": {"format": format},
                "params": {"dataSetId": datasetId},
            }
            res: dict = self.connector.postData(self.endpoint + path, data=obj)
        return res

    def createTargetConnectionDataLake(
        self,
        name: str = None,
        datasetId: str = None,
        schemaId: str = None,
        format: str = "delimited",
        version: str = "1.0",
        description: str = "",
    ) -> dict:
        """
        Create a target connection to the AEP Data Lake.
        Arguments:
            name : REQUIRED : The name of your target Destination
            datasetId : REQUIRED : the dataset ID of your target destination.
            schemaId : REQUIRED : The schema ID of your dataSet. (NOT meta:altId)
            format : REQUIRED : format of your data inserted
            version : REQUIRED : version of your target destination
            description : OPTIONAL : description of your target destination.
        """
        targetObj = {
            "name": name,
            "description": description,
            "data": {
                "format": format,
                "schema": {
                    "id": schemaId,
                    "version": "application/vnd.adobe.xed-full+json;version=1.0",
                },
            },
            "params": {"dataSetId": datasetId},
            "connectionSpec": {
                "id": "c604ff05-7f1a-43c0-8e18-33bf874cb11c",
                "version": version,
            },
        }
        if self.loggingEnabled:
            self.logger.debug(f"Starting createTargetConnectionDataLake")
        res = self.createTargetConnection(data=targetObj)
        return res

    def updateTargetConnection(
        self, targetConnectionId: str = None, etag: str = None, updateObj: list = None
    ) -> dict:
        """
        Update a target connection based on the ID provided with the object provided.
        Arguments:
            targetConnectionId : REQUIRED : The target connection ID to be updated
            etag: REQUIRED : A header containing the etag value of the connection or flow to be updated.
            updateObj : REQUIRED : The operation call used to define the action needed to update the connection. Operations include add, replace, and remove.
        """
        if targetConnectionId is None:
            raise Exception("Require a sourceConnection to be present")
        if etag is None:
            raise Exception("Require etag to be present")
        if updateObj is None:
            raise Exception("Require a dictionary with data to be present")
        if self.loggingEnabled:
            self.logger.debug(f"Starting updateTargetConnection")
        privateHeader = deepcopy(self.header)
        privateHeader["if-match"] = etag
        path: str = f"/targetConnections/{targetConnectionId}"
        res: dict = self.connector.patchData(
            self.endpoint + path, headers=privateHeader, data=updateObj
        )
        return res


class FlowManager:
    """
    A class that abstract the different information retrieved by the Flow ID in order to provide all relationships inside that Flow.
    It takes a flow id and dig to all relationship inside that flow.
    """

    def __init__(self,
                flowId:str=None,
                config: dict = aepp.config.config_object,
                header=aepp.config.header)->None:
        """
        Instantiate a Flow Manager Instance based on the flow ID.
        Arguments:
            flowId : REQUIRED : A flow ID
        """
        from aepp import schema, catalog,dataprep,flowservice
        self.schemaAPI = schema.Schema()
        self.catalogAPI = catalog.Catalog()
        self.mapperAPI = dataprep.DataPrep()
        self.flowAPI = flowservice.FlowService()
        self.flowData = self.flowAPI.getFlow(flowId)
        self.id = flowId
        self.flowMapping = None
        self.sandbox = self.flowData.get('sandboxName')
        self.name = self.flowData.get('name')
        self.version = self.flowData.get('version')
        self.flowSpec = {'id' : self.flowData.get('flowSpec',{}).get('id')}
        self.flowSourceConnection = {'id' : self.flowData.get('sourceConnectionIds',[None])[0]}
        self.flowTargetConnection = {'id' : self.flowData.get('targetConnectionIds',[None])[0]}
        for trans in self.flowData.get('transformations',[{}]):
            if trans.get('name') == 'Mapping':
                self.flowMapping = {'id':trans.get('params',{}).get('mappingId')}
        ## Flow Spec part
        if self.flowSpec['id'] is not None:
            flowSpecData = self.flowAPI.getFlowSpec(self.flowSpec['id'])
            self.flowSpec['name'] = flowSpecData['name']
            self.flowSpec['frequency'] = flowSpecData.get('attributes',{}).get('frequency')
        ## Source Connection part
        if self.flowSourceConnection['id'] is not None:
            sourceConnData = self.flowAPI.getSourceConnection(self.flowSourceConnection['id'])
            self.flowSourceConnection['data'] = sourceConnData.get('data')
            self.flowSourceConnection['params'] = sourceConnData.get('params')
            self.flowSourceConnection['connectionSpec'] = sourceConnData.get('connectionSpec')
            if self.flowSourceConnection['connectionSpec'].get('id') is not None:
                connSpec = self.flowAPI.getConnectionSpec(self.flowSourceConnection['connectionSpec'].get('id'))
                self.flowSourceConnection['connectionSpec']['name'] = connSpec.get('name')
        ## Target Connection part
        if self.flowTargetConnection['id'] is not None:
            targetConnData = self.flowAPI.getTargetConnection(self.flowTargetConnection['id'])
            self.flowTargetConnection['name'] = targetConnData.get('name')
            self.flowTargetConnection['data'] = targetConnData.get('data')
            self.flowTargetConnection['params'] = targetConnData.get('params')
            self.flowTargetConnection['connectionSpec'] = targetConnData.get('connectionSpec')
            if self.flowTargetConnection['connectionSpec'].get('id') is not None:
                connSpec = self.flowAPI.getConnectionSpec(self.flowSourceConnection['connectionSpec'].get('id'))
                self.flowTargetConnection['connectionSpec']['name'] = connSpec.get('name')
        ## Catalog part
        if 'dataSetId' in self.flowTargetConnection['params'].keys():
            datasetInfo = self.catalogAPI.getDataSet(self.flowTargetConnection['params']['dataSetId'])
            self.flowTargetConnection['params']['datasetName'] = datasetInfo[list(datasetInfo.keys())[0]].get('name')
        ## Schema part
        if 'schema' in self.flowTargetConnection['data'].keys():
            schemaInfo = self.schemaAPI.getSchema(self.flowTargetConnection['data']['schema']['id'],full=False)
            self.flowTargetConnection['data']['schema']['name'] = schemaInfo.get('title')
        ## Mapping
        if self.flowMapping is not None:
            mappingInfo = self.mapperAPI.getMappingSet(self.flowMapping['id'])
            self.flowMapping['createdDate'] = time.ctime(mappingInfo.get('createdDate')/1000)

    def __repr__(self)->str:
        data = {
                "id" : self.id,
                "name": self.name,
                "version":self.version,
                "flowSpecs": self.flowSpec,
                "sourceConnection": self.flowSourceConnection,
                "targetConnection": self.flowTargetConnection,
            }
        if self.flowMapping is not None:
            data['mapping'] = self.flowMapping
        return json.dumps(data,indent=2)
    
    def __str__(self)->str:
        data = {
                "id" : self.id,
                "name": self.name,
                "version":self.version,
                "flowSpecs": self.flowSpec,
                "sourceConnection": self.flowSourceConnection,
                "targetConnection": self.flowTargetConnection,
            }
        if self.flowMapping is not None:
            data['mapping'] = self.flowMapping
        return json.dumps(data,indent=2)

    def getFlowSpec(self)->dict:
        """
        Return a dictionary of the flow Spec.
        """
        if self.flowSpec['id'] is not None:
            flowSpecData = self.flowAPI.getFlowSpec(self.flowSpec['id'])
            return flowSpecData

    def getSourceConnection(self)->dict:
        """
        Return a dictionary of the connection information
        """
        if self.flowSourceConnection['id'] is not None:
            sourceConnData = self.flowAPI.getSourceConnection(self.flowSourceConnection['id'])
            return sourceConnData
    
    def getConnectionSpec(self)->dict:
        """
        return a dictionary of the source connection spec information
        """
        if self.flowSourceConnection['connectionSpec'].get('id') is not None:
            connSpec = self.flowAPI.getConnectionSpec(self.flowSourceConnection['connectionSpec'].get('id'))
            return connSpec
    
    def getTargetConnection(self)->dict:
        """
        return a dictionary of the target connection
        """
        if self.flowTargetConnection['id'] is not None:
            targetConnData = self.flowAPI.getTargetConnection(self.flowTargetConnection['id'])
            return targetConnData
    
    def getTargetConnectionSpec(self)->dict:
        """
        return a dictionary of the target connection spec
        """
        if self.flowTargetConnection['connectionSpec'].get('id') is not None:
            connSpec = self.flowAPI.getConnectionSpec(self.flowSourceConnection['connectionSpec'].get('id'))
            return connSpec
    
    def getRuns(self,limit:int=10,n_results=100)->list:
        """
        Returns the last run of the flow.
        Arguments:
            limit : OPTIONAL : Amount of item per requests
            n_results : OPTIONAL : Total amount of item to return
        """
        runs = self.flowAPI.getRuns(limit,n_results,prop=f"flowId=={self.id}")
        return runs