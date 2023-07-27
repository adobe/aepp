# Connect Object class

This documentation is aiming at providing detail overview of the `ConnectInstance` parameter that is available from the `importConfigFile` method or the `configure` method.\
This parameter leverage the `ConnectObject` class that is available in the configs module of `aepp`. 


## Connect Object origin

The `ConnectObject` class origin comes from the possibility to handle multiple sandboxes within AEP via different connections.\
The previous capability of aepp requires you to always load the latest configuration of your sandbox when you wanted to create an instance for that different sandbox, even though the API credentials were the same and only the sandbox name setup was different.\
In order to simplify the move between sandboxes with the `aepp` wrapper, the idea was to keep the configuration parameter for each sandbox in its own class, that is independent from any other submodule of `aepp`, such as `schema`, `queryservice`, etc...\
This submodule can be used in the same manner for all submodule so you can better control which sandbox you are connecting to, even with the same config file.

## Connect Object creation

### Via importConfigFile

You can create a new instance of the ConnectObject class by passing `True` to the `ConnectInstance` parameter during the `importConfigFile` method. 
The sandbox selection can be done in 2 different places:

* You have different config file per sandbox
* You overwrite the sandbox in the config file during the import via the `sandbox` parameter.

Examples:

```python
import aepp

aepp.importConfigFile('myconfig.json') ## do NOT create an instance
mySandbox1 = aepp.importConfigFile('myconfig.sandbox1.json',connectInstance=True) ## create an instance for sandbox 1
mySandbox2 = aepp.importConfigFile('myconfig.sandbox2.json',connectInstance=True) ## create an instance for sandbox 2
mySandbox3 = aepp.importConfigFile('myconfig.sandbox1.json',connectInstance=True,sandbox='sandbox3') ## create an instance for sandbox 3
```

### Via configure method

The `configure` method also provides a parameter to create an instance.\
The main difference is that you need to pass all of the information for your connection directly as parameters.\

Examples:

```python
import aepp

aepp.configure(org_id=XXX,tech_id=YYYY,....) ## do NOT create an instance
mySandbox1 = aepp.configure(org_id=XXX,tech_id=YYYY,sandbox='sandbox1',...,connectInstance=True) ## create an instance for sandbox 1
```

### Via ConnectObject class

You can also create an instance directly from the `ConnectObject` class.\
In that case, you would also need to pass all the different information requires for that instantiation.\
The different parameter required for generating a `ConnectObject` class are: 

* org_id : REQUIRED : The organization IMS ID
* tech_id : REQUIRED : The Tech ID is available on the developer project.
* secret : REQUIRED : The secret that is available on the developer project.
* client_id : REQUIRED : The client ID is related to your developer project.
* path_to_key : OPTIONAL : In case you are doing JWT authentication, you would need to pass the path to the file containing the private.key.
* private_key : OPTIONAL : In case you are doing JWT authentication, you can pass the private.key content directly as a string here.
* scopes : OPTIONAL : In case you are doing Oauth V2, you would need to pass the scopes available on your developer project.
* sandbox : OPTIONAL : You can setup the sandbox name you want to use. Default with "prod"
* environment: OPTIONAL : Intended for adobe developer if they want to overwrite the endpoint to staging environment. Default 'prod'
* auth_code : OPTIONAL : Intended for internal Adobe service, in case they are using the Oauth V1 token.

## Using the instance of connectObject

Once you have an instance of the `connectObject`, you can use it in all of the different other sub modules and associated classes, by using `config` parameter.\
Example for the `schema` module with the `Schema` classes

```python
import aepp
mySandbox1 = aepp.importConfigFile('myconfig.sandbox1.json',connectInstance=True) ## create an instance for sandbox 1
mySandbox2 = aepp.importConfigFile('myconfig.sandbox2.json',connectInstance=True) ## create an instance for sandbox 2
mySandbox3 = aepp.importConfigFile('myconfig.sandbox1.json',connectInstance=True,sandbox='sandbox3') ## create an instance for sandbox 3

from aepp import schema

schemaSandbox1 = schema.Schema(config=mySandbox1)
schemaSandbox2 = schema.Schema(config=mySandbox2)
schemaSandbox3 = schema.Schema(config=mySandbox3)

```

## ConnectObject methods

Once you have created a `connectObject` instance, you can then use some of the methods described below:

### Connect

The `connect` method generates a token and provide a connector instance in that class.\
After that method is being used, there will be a `token`, `sandbox`, `connectionType` and `header` attributes available on the instance, such as (in the case `mySandbox1` is the instance):

* `mySandbox1.token` provides the token that can be used for requests
* `mySandbox1.header` provides the header that can be used for requests
* `mySandbox1.sandbox` provides the information about the connected sandbox
* `mysandbox1.connectionType` provides the type of connection used, either `OauthV2`, `OauthV1` or `jwt`

Example:

```python
import aepp
mySandbox1 = aepp.importConfigFile('myconfig.sandbox1.json',connectInstance=True) 

mySandbox1.connect()

mySandbox1.connectionType ## return the appropriate value, default `OauthV2`

```

### Connector methods

Once you have use the `connect` method, you can use the follwing methods: 

### getConfigObject

The method will return the config object expected.\
The config object will return the following information, if available:

* "org_id"
* "client_id"
* "tech_id"
* "pathToKey"
* "private_key"
* "secret"
* "date_limit" 
* "sandbox"
* "token"
* "imsEndpoint"
* "jwtTokenEndpoint"
* "oauthTokenEndpointV1"
* "oauthTokenEndpointV2"
* "scopes"
* "auth_code"

### getConfigHeader

It will return the header that can be used for the requests, such as:

```JSON
{"Accept": "application/json",
"Content-Type": "application/json",
"Authorization": "....",
"x-api-key": "client_id",
"x-gw-ims-org-id": "org_id",
"x-sandbox-name": "sandbox"
}
```

### setSandbox

This can take an argument that would change the sandbox associated with the instance.\
You need to pass a sandbox name as a parameter.\
This will replace the sandbox setup in the header and for the attribute provided.

Example: 

```python
import aepp
mySandbox1 = aepp.importConfigFile('myconfig.sandbox1.json',connectInstance=True) 

mySandbox1.setSandbox('sandbox2') ## Now the mySandbox1 instance will be connected to sandbox 2

```

## Using the instance after the connection

Once you have connected your instance with the Adobe API, you can use the `connector` object with the following methods:

* `getData`
* `postData`
* `putData`
* `patchData`
* `deleteData`

Example:

```python
mySandbox1 = aepp.importConfigFile('myconfig.sandbox1.json',connectInstance=True) 

mySandbox1.connect()

mySandbox1.connector.getData('endpoint',params={'key':'value'}) ## return the json response.

```


## Rotating Client Secret Programatically

If you have used the `Oauth Server to Server` type of connection, you can also add the `I/O Management API` to your project in the project to manage the token you have on your Oauth setup.

Only the `Oauth Server to Server` configuration type and adding the API mention above will make the following method working.

**tip**: If you add the `I/O Management API` afterward, you would need to adjust the scopes.

### setOauthV2setup

This method is the recommended approach before using the other methods described below.\
It will save the credentialId and the orgDevId into attribute of your instance.
It takes these 2 values as parameter.

You can find both information, on your project page, when looking at the Oauth Server to Server page, on the developer.adobe.com website.\
Such as : <https://developer.adobe.com/console/projects/{orgId}/{projectId}/credentials/{credentialId}/details/oauthservertoserver>

Example: 

```python 
import aepp
mySandbox1 = aepp.importConfigFile('myconfig.sandbox1.json',connectInstance=True) 

mySandbox1.setOauthV2setup('credentialIdValue','orgDevIdValue')

mySandbox1.credentialId ## returns credentialIdValue
mySandbox1.orgDevId ## returns orgDevIdValue
```

### getSecrets

Access the different available token from your client ID.
It takes 2 optional parameters, in case you did not use the `setOauthV2setup` method: in case you did not use the `setOauthV2setup` method:

* credentialId : OPTIONAL : The ID of your Project.(if you did not use the `setOauthV2setup` method)
* orgDevId : OPTIONAL : The Organzation ID from the developer console. It is NOT the same Id than the IMS org Id. (if you did not use the `setOauthV2setup` method)


### createSecret

This method allows you to generate a secret token directly from the API.\
It takes 2 optional paremeters, in case you did not use the `setOauthV2setup` method:

* credentialId : OPTIONAL : The ID of your Project.(if you did not use the `setOauthV2setup` method)
* orgDevId : OPTIONAL : The Organzation ID from the developer console. It is NOT the same Id than the IMS org Id. (if you did not use the `setOauthV2setup` method)

You can find both information, on your project page, when looking at the Oauth Server to Server page, on the developer.adobe.com website.\
Such as : <https://developer.adobe.com/console/projects/{orgId}/{projectId}/credentials/{credentialId}/details/oauthservertoserver>

**Important**
The instance will automatically switch its setting to use the latest client secret for generating a new token.
**You will need to update the config file if you are using one. You can use the `updateConfigFile` method**

### updateConfigFile

After creating a new secret, the connection will automatically switch to the latest secret created.\
However, your config file, if you have used one, is still having the old secret written.  
If you wish to uupdate your config file, you can use that method, that will save the config file with the existing configuration options.
Arguments:

 * destination : REQUIRED : The path (optional) with the filename to be created.

### deleteSecrete

This will delete a token from the existing tokens available for this Oauth Server to Server setup.\
It takes 1 required parameter and 2 optional parameters. 
Arguments:

* tokenUID : REQUIRED : The secret uuid to deleted
* credentialId : OPTIONAL : The ID of your Project.(if you did not use the `setOauthV2setup` method)
* orgDevId : OPTIONAL : The Organzation ID from the developer console. It is NOT the same Id than the IMS org Id. (if you did not use the `setOauthV2setup` method)