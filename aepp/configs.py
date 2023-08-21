#  Copyright 2023 Adobe. All rights reserved.
#  This file is licensed to you under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License. You may obtain a copy
#  of the License at http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software distributed under
#  the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#  OF ANY KIND, either express or implied. See the License for the specific language
#  governing permissions and limitations under the License.

import json
import os
from pathlib import Path
from typing import Optional
import json, time

# Non standard libraries
from .config import config_object, header, endpoints
from aepp import connector

def find_path(path: str) -> Optional[Path]:
    """Checks if the file denoted by the specified `path` exists and returns the Path object
    for the file.

    If the file under the `path` does not exist and the path denotes an absolute path, tries
    to find the file by converting the absolute path to a relative path.

    If the file does not exist with either the absolute and the relative path, returns `None`.
    """
    if Path(path).exists():
        return Path(path)
    elif path.startswith("/") and Path("." + path).exists():
        return Path("." + path)
    elif path.startswith("\\") and Path("." + path).exists():
        return Path("." + path)
    else:
        return None


def createConfigFile(
    destination: str = "config_aep_template.json",
    sandbox: str = "prod",
    environment: str = "prod",
    verbose: object = False,
    auth_type: str = "oauthV2",
    **kwargs,
) -> None:
    """
    This function will create a 'config_admin.json' file where you can store your access data.
    Arguments:
        destination : OPTIONAL : if you wish to save the file at a specific location.
        sandbox : OPTIONAL : You can directly set your sandbox name in this parameter.
        verbose : OPTIONAL : set to true, gives you a print stateent where is the location.
        auth_type : OPTIONAL : type of authentication, either "jwt" or "oauthV2" or "oauthV1". Default is oauthV2
    """
    json_data: dict = {
        "org_id": "<orgID>",
        "client_id": "<client_id>",
        "secret": "<YourSecret>",
        "sandbox-name": sandbox,
        "environment": environment
    }
    if auth_type == "jwt":
        json_data["tech_id"] = "<something>@techacct.adobe.com"
        json_data["pathToKey"] = "<path/to/your/privatekey.key>"
    elif auth_type == "oauthV2":
        json_data["scopes"] = "<scopes>"
    elif auth_type == "oauthV1":
        json_data["auth_code"] = "<auth_code>"
    else:
        raise ValueError("unsupported authentication type, currently only jwt, oauthV1 and oauthV2 are supported")
    if ".json" not in destination:
        destination: str = f"{destination}.json"
    with open(destination, "w") as cf:
        cf.write(json.dumps(json_data, indent=4))
    if verbose:
        print(
            f" file created at this location : {os.getcwd()}{os.sep}{destination}.json"
        )


def importConfigFile(
    path: str = None,
    connectInstance: bool = False,
    auth_type: str = None,
    sandbox:str = None,
):
    """Reads the file denoted by the supplied `path` and retrieves the configuration information
    from it.

    Arguments:
        path: REQUIRED : path to the configuration file. Can be either a fully-qualified or relative.
        connectInstance : OPTIONAL : If you want to return an instance of the ConnectObject class
        auth_type : OPTIONAL : type of authentication, either "jwt" or "oauthV1" or "oauthV2". Detected based on keys present in config file.
        sandbox : OPTIONAL : The sandbox to connect it.

    Example of path value.
    "config.json"
    "./config.json"
    "/my-folder/config.json"
    """
    if path is None:
        raise ValueError("require a path to a configuration file to be provided")
     
    config_file_path: Optional[Path] = find_path(path)
    if config_file_path is None:
        raise FileNotFoundError(
            f"Unable to find the configuration file under path `{path}`."
        )
    with open(config_file_path, "r") as file:
        provided_config = json.load(file)
        provided_keys = list(provided_config.keys())
        if "api_key" in provided_keys:
            ## old naming for client_id
            client_id = provided_config["api_key"]
        elif "client_id" in provided_keys:
            client_id = provided_config["client_id"]
        else:
            raise RuntimeError(
                f"Either an `api_key` or a `client_id` should be provided."
            )
        if auth_type is None:
            if 'scopes' in provided_keys:
                auth_type = 'oauthV2'
            elif 'tech_id' in provided_keys and "pathToKey" in provided_keys:
                auth_type = 'jwt'
            elif 'auth_code' in provided_keys:
                auth_type = 'oauthV1'
        args = {
            "org_id": provided_config["org_id"],
            "client_id": client_id,
            "secret": provided_config["secret"],
            "sandbox": provided_config.get("sandbox-name", "prod"),
            "environment": provided_config.get("environment", "prod"),
            "connectInstance": connectInstance
        }
        if sandbox is not None: ## overriding sandbox from parameter
            args["sandbox"] = sandbox
        if auth_type == "jwt":
            args["tech_id"] = provided_config["tech_id"]
            args["path_to_key"] = provided_config["pathToKey"]
        elif auth_type == "oauthV2":
            args["scopes"] = provided_config["scopes"].replace(' ','')
        elif auth_type == "oauthV1":
            args["auth_code"] = provided_config["auth_code"]
        else:
            raise ValueError("unsupported authentication type, currently only jwt and oauth are supported")
        myInstance = configure(**args)

    if connectInstance:
        return myInstance


def configure(
    org_id: str = None,
    tech_id: str = None,
    secret: str = None,
    client_id: str = None,
    path_to_key: str = None,
    private_key: str = None,
    sandbox: str = "prod",
    connectInstance: bool = False,
    environment: str = "prod",
    scopes: str = None,
    auth_code:str=None
):
    """Performs programmatic configuration of the API using provided values.
    Arguments:
        org_id : REQUIRED : Organization ID
        tech_id : OPTIONAL : Technical Account ID
        secret : REQUIRED : secret generated for your connection
        client_id : REQUIRED : The client_id (old api_key) provided by the JWT connection.
        path_to_key : REQUIRED : If you have a file containing your private key value.
        private_key : REQUIRED : If you do not use a file but pass a variable directly.
        sandbox : OPTIONAL : If not provided, default to prod
        connectInstance : OPTIONAL : If you want to return an instance of the ConnectObject class
        environment : OPTIONAL : If not provided, default to prod
        scopes : OPTIONAL : The scope define in your project for your API connection. Oauth V2, for clients and customers.
        auth_code : OPTIONAL : If an authorization code is used directly instead of generating via JWT. Oauth V1 only, for adobe internal services.
    """
    if not org_id:
        raise ValueError("`org_id` must be specified in the configuration.")
    if not client_id:
        raise ValueError("`client_id` must be specified in the configuration.")
    if not secret:
        raise ValueError("`secret` must be specified in the configuration.")
    if (scopes is not None and (path_to_key is not None or private_key is not None) and auth_code is not None) \
            or (scopes is None and path_to_key is None and private_key is None and auth_code is None):
        raise ValueError("either `scopes` needs to be specified or one of `private_key` or `path_to_key` or an `auth_code`")
    config_object["org_id"] = org_id
    header["x-gw-ims-org-id"] = org_id
    config_object["client_id"] = client_id
    header["x-api-key"] = client_id
    config_object["tech_id"] = tech_id
    config_object["secret"] = secret
    config_object["pathToKey"] = path_to_key
    config_object["private_key"] = private_key
    config_object["scopes"] = scopes
    config_object["auth_code"] = auth_code
    config_object["sandbox"] = sandbox
    header["x-sandbox-name"] = sandbox

    # ensure we refer to the right environment endpoints
    config_object["environment"] = environment
    if environment == "prod":
        endpoints["global"] = "https://platform.adobe.io"
        config_object["imsEndpoint"] = "https://ims-na1.adobelogin.com"
    else:
        endpoints["global"] = f"https://platform-{environment}.adobe.io"
        config_object["imsEndpoint"] = "https://ims-na1-stg1.adobelogin.com"
    endpoints["streaming"]["inlet"] = f"{endpoints['global']}/data/core/edge"
    config_object["jwtTokenEndpoint"] = f"{config_object['imsEndpoint']}/ims/exchange/jwt"
    config_object["oauthTokenEndpointV1"] = f"{config_object['imsEndpoint']}/ims/token/v1"
    config_object["oauthTokenEndpointV2"] = f"{config_object['imsEndpoint']}/ims/token/v2"
    # ensure the reset of the state by overwriting possible values from previous import.
    config_object["date_limit"] = 0
    config_object["token"] = ""
    if connectInstance:
        myInstance = ConnectObject(
            org_id=org_id,
            tech_id=tech_id,
            secret=secret,
            client_id=client_id,
            path_to_key = path_to_key,
            private_key = private_key,
            sandbox=sandbox,
            scopes=scopes,
            auth_code=auth_code
        )
        return myInstance


def get_private_key_from_config(config: dict) -> str:
    """
    Returns the private key directly or read a file to return the private key.
    """
    private_key = config.get("private_key")
    if private_key is not None:
        return private_key
    private_key_path = find_path(config["pathToKey"])
    if private_key_path is None:
        raise FileNotFoundError(
            f'Unable to find the private key under path `{config["pathToKey"]}`.'
        )
    with open(Path(private_key_path), "r") as f:
        private_key = f.read()
    return private_key


def generateLoggingObject(level:str="WARNING",filename:str="aepp.log") -> dict:
    """
    Generates a dictionary for the logging object with basic configuration.
    You can find the information for the different possible values on the logging documentation.
        https://docs.python.org/3/library/logging.html
    Arguments:
        level : OPTIONAL : Level of the logger to display information (NOTSET, DEBUG,INFO,WARNING,EROR,CRITICAL)
            default WARNING
        filename : OPTIONAL : name of the file for debugging. default aepp.log
    Output:
        level : Level of the logger to display information (NOTSET, DEBUG,INFO,WARNING,EROR,CRITICAL)
        stream : If the logger should display print statements
        file : If the logger should write the messages to a file
        filename : name of the file where log are written
        format : format of the logs
    """
    myObject = {
        "level": level,
        "stream": True,
        "file": False,
        "format": "%(asctime)s::%(name)s::%(funcName)s::%(levelname)s::%(message)s::%(lineno)d",
        "filename": filename,
    }
    return myObject

class ConnectObject:
    """
    A connect Object class that keep tracks of the configuration loaded during the importConfigFile operation or during configure operation.
    
    """

    def __init__(self,
            org_id: str = None,
            tech_id: str = None,
            secret: str = None,
            client_id: str = None,
            path_to_key: str = None,
            private_key: str = None,
            scopes:str=None,
            sandbox: str = "prod",
            environment: str = "prod",
            auth_code:str=None,
            **kwargs)->None:
        """
        Take a config object and save the configuration directly in the instance of the class.
        """
        self.header = {"Accept": "application/json",
          "Content-Type": "application/json",
          "Authorization": "",
          "x-api-key": client_id,
          "x-gw-ims-org-id": org_id,
          "x-sandbox-name": sandbox
          }
        ## setting environment prod vs non-prod for token generation
        if environment == "prod":
            self.globalEndpoint = "https://platform.adobe.io"
            self.imsEndpoint = "https://ims-na1.adobelogin.com"
        else:
            self.globalEndpoint = f"https://platform-{environment}.adobe.io"
            self.imsEndpoint = "https://ims-na1-stg1.adobelogin.com"
        self.streamInletEndpoint = f"{self.globalEndpoint}/data/core/edge"
        self.jwtEndpoint = f"{self.imsEndpoint}/ims/exchange/jwt"
        self.oauthEndpointV1 = f"{self.imsEndpoint}/ims/token/v1"
        self.oauthEndpointV2 = f"{self.imsEndpoint}/ims/token/v2"
        self.org_id = org_id
        self.tech_id = tech_id
        self.client_id = client_id
        self.secret = secret
        self.pathToKey = path_to_key
        self.privateKey = private_key
        self.sandbox = sandbox
        self.scopes = scopes
        self.token = ""
        self.auth_code = auth_code
        self.__configObject__ = {
            "org_id": self.org_id,
            "client_id": self.client_id,
            "tech_id": self.tech_id,
            "pathToKey": self.pathToKey,
            "private_key": self.privateKey,
            "secret": self.secret,
            "date_limit" : 0,
            "sandbox": self.sandbox,
            "token": "",
            "imsEndpoint" : self.imsEndpoint,
            "jwtTokenEndpoint" : self.jwtEndpoint,
            "oauthTokenEndpointV1" : self.oauthEndpointV1,
            "oauthTokenEndpointV2" : self.oauthEndpointV2,
            "scopes": self.scopes,
            "auth_code": self.auth_code
        }
    
    def connect(self)->None:
        """
        Generate a token and provide a connector instance in that class.
        """
        self.connector = connector.AdobeRequest(self.__configObject__,self.header)
        self.token = self.connector.token
        self.header['Authorization'] = 'bearer '+self.token
        self.connectionType = self.connector.connectionType
    
    def getConfigObject(self)->dict:
        """
        Return the config object expected.
        """
        return self.__configObject__
    
    def getConfigHeader(self)->dict:
        """
        Return the default header
        """
        return self.header

    def setSandbox(self,sandbox:str=None)->dict:
        """
        Update the sandbox used
        """
        if sandbox is None:
            return None
        self.sandbox = sandbox
        self.header["x-sandbox-name"] = sandbox
        self.__configObject__["sandbox"] = sandbox
        return self.getConfigObject()

    def setOauthV2setup(self,credentialId:str=None,orgDevId:str=None)->bool:
        """
        set the credential ID and the OrgIdDev as attributes of the instance.
        * credentialId
        * orgDevId
        Argument:
            credentialId : OPTIONAL : The credential id that can be found on your Project page.
            orgDevId : OPTIONAL : the org Id but NOT the IMS string. It is defined on your project page.
                Example : https://developer.adobe.com/console/projects/<orgId>/<projectId>/credentials/<credentialId>/details/oauthservertoserver
        """
        if self.connectionType != "oauthV2":
            raise Exception("You are trying to set credential ID or orgDevId for auth that is not OauthV2. We do not support these auth type.")
        if credentialId is None:
            raise ValueError("credentialId is None")
        if orgDevId is None:
            raise ValueError("orgDevId is None")
        self.credentialId = credentialId
        self.orgDevId = orgDevId
    
    def getSecrets(self,credentialId:str=None,orgDevId:str=None)->dict:
        """
        Access the different token available for your client ID.
        If you did not use the setOauthV2setup, you can pass the required information as parameters.
        Arguments:
            credentialId : OPTIONAL : The credential id that can be found on your Project page.
            orgDevId : OPTIONAL : the org Id but NOT the IMS string. It is defined on your project page.
                Example : https://developer.adobe.com/console/projects/<orgId>/<projectId>/credentials/<credentialId>/details/oauthservertoserver
        """
        if self.connectionType != "oauthV2":
            raise Exception("You are trying to use a service that is only supportede for OauthV2 authen. We do not support the other auth types.")
        if credentialId is None and self.credentialId is None:
            raise ValueError("You are not providing the credential ID and did not use the setOauthV2setup method.\n Use it to prepare this method")
        if orgDevId is None and self.orgDevId is None:
            raise ValueError("You are not providing the orgDevId and did not use the setOauthV2setup method.\n Use it to prepare this method")
        if credentialId is None and self.credentialId is not None:
            credentialId = self.credentialId
        if orgDevId is None and self.orgDevId is not None:
            orgDevId = self.orgDevId
        if self.token is None:
            raise Exception("You need to generate a token by using the connect method first")
        myheader = {
            'Authorization' : 'Bearer '+self.token,
            'x-api-key' : self.client_id
        }
        endpoint = f"https://api.adobe.io/console/organizations/{orgDevId}/credentials/{credentialId}/secrets"
        res = self.connector.getData(endpoint,headers=myheader)
        return res
    
    def createSecret(self,credentialId:str=None,orgDevId:str=None)->dict:
        """
        Create a new secret with a new token for Oauth V2 credentials.
        If you did not use the setOauthV2setup, you can pass the required information as parameters.
        ATTENTION : In order to use it, you will need to have added the I/O Management API to your project.
        Returns the new token and new secret that is automatically being used for that connection.
        Arguments
            credentialId : OPTIONAL : The credential id that can be found on your Project page.
            orgDevId : OPTIONAL : the org Id but NOT the IMS string. It is defined on your project page.
                Example : https://developer.adobe.com/console/projects/<orgId>/<projectId>/credentials/<credentialId>/details/oauthservertoserver
        """
        if self.connectionType != "oauthV2":
            raise Exception("You are trying to use a service that is only supportede for OauthV2 authen. We do not support the other auth types.")
        if credentialId is None and self.credentialId is None:
            raise ValueError("You are not providing the credential ID and did not use the setOauthV2setup method.\n Use it to prepare this method")
        if orgDevId is None and self.orgDevId is None:
            raise ValueError("You are not providing the orgDevId and did not use the setOauthV2setup method.\n Use it to prepare this method")
        if credentialId is None and self.credentialId is not None:
            credentialId = self.credentialId
        if orgDevId is None and self.orgDevId is not None:
            orgDevId = self.orgDevId
        if self.token is None:
            raise Exception("You need to generate a token by using the connect method first")
        myheader = {
            'Authorization' : 'Bearer '+self.token,
            'x-api-key' : self.client_id
        }
        endpoint = f"https://api.adobe.io/console/organizations/{orgDevId}/credentials/{credentialId}/secrets"
        res = self.connector.postData(endpoint,headers=myheader)
        if 'client_secret' not in res.keys():
            raise Exception("Could not find a client_secret in the key")
        self.secret = res['client_secret']
        self.__configObject__['secret'] = res['client_secret']
        self.connector.config['secret'] = res['client_secret']
        return res
    
    def updateConfigFile(self,destination:str=None)->None:
        """
        Once creating a client secret, you would need to update your config file with your new secret.
        Arguments:
            destination : REQUIRED : Destination path of the file name to updated.
        """
        if self.connectionType != 'OauthV2':
            raise Exception('Do not support update for non Oauth Server to Server type')
        json_data: dict = {
            "org_id": self.org_id,
            "client_id": self.client_id,
            "secret": self.secret,
            "sandbox-name": self.sandbox,
            "scopes": self.scopes,
            "environment": "prod"
        }
        with open(destination, "w") as cf:
            cf.write(json.dumps(json_data, indent=4))
    
    def deleteSecrete(self,secretUID:str=None,credentialId:str=None,orgDevId:str=None,)->None:
        """
        Delete an old token from your different token accessed
        Arguments:
            secretUID : REQUIRED : The token to delete
            credentialId : OPTIONAL : The credential id that can be found on your Project page.
            orgDevId : OPTIONAL : the org Id but NOT the IMS string. It is defined on your project page.
                Example : https://developer.adobe.com/console/projects/<orgId>/<projectId>/credentials/<credentialId>/details/oauthservertoserver
        """
        if self.connectionType != "oauthV2":
            raise Exception("You are trying to use a service that is only supportede for OauthV2 authen. We do not support the other auth types.")
        if credentialId is None and self.credentialId is None:
            raise ValueError("You are not providing the credential ID and did not use the setOauthV2setup method.\n Use it to prepare this method")
        if orgDevId is None and self.orgDevId is None:
            raise ValueError("You are not providing the orgDevId and did not use the setOauthV2setup method.\n Use it to prepare this method")
        if credentialId is None and self.credentialId is not None:
            credentialId = self.credentialId
        if orgDevId is None and self.orgDevId is not None:
            orgDevId = self.orgDevId
        if self.token is None:
            raise Exception("You need to generate a token by using the connect method first")
        if secretUID is None:
            raise ValueError("You need to pass a correct value for the tokenUID")
        endpoint = f"https://api.adobe.io/console/organizations/{orgDevId}/credentials/{credentialId}/secrets/{secretUID}/"
        myheader = {
            'Authorization' : 'Bearer '+self.token,
            'x-api-key' : self.client_id
        }
        res = self.connector.deleteData(endpoint,headers=myheader)
        return res