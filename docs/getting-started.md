# Getting started with aepp

## Menu

-   [Installing the module](#installing-the-module)
-   [Create a Developer Project ](#create-a-developer-project)
    - [Oauth Server-to-Server](#oauth-server-to-server)
    - [Oauth V1](#oauth-v1)
-   [Using the module](#using-the-module)
    - [Create a Config file](#create-a-config-file)
    - [Environments](#environments)
    - [Importing the config file](#importing-the-config-file)
    - [Alternative method for cloud configuration](#alternative-method-for-cloud-configuration)
    - [The ConnectInstance parameter](#the-connectinstance-parameter)
-   [Importing a sub module to work with](#importing-a-sub-module-to-work-with)
-   [Help](#help)

## Installing the module

You would need to install the module in your environment.\
You can use the pip command to do so.

```shell
pip install aepp --upgrade
```

You can use the upgrade argument when a release has been made.

## Create a Developer Project

You will need to have a developer project that has access to the Adobe Experience Platform API.\
When creating a project you have the possibility to use 2 authentication methods.

* OAuth-based authentication

### Oauth Server-to-Server

In 2023, the Oauth Server-to-Server token has been introduced in the API environment of Adobe.\
`aepp` is now supporting this capabiliy and you can create an `Oauth Server-to-Server` integration.\
In the config file, it is named `oauthV2`.

in developer.adobe.com, make sure you have developer rights and attaching the correct product profile to your integration.\
You will need to have the following information saved to be used later:
- Client ID
- Client secret
- Technical Account ID
- Scopes
- IMS Org

### Oauth V1

For internal usage of the aepp module, for Adobe teams, you can also use the oauth v1 to interact with other services.
You will need to have the following information saved to be used later:
- Client ID
- Client secret
- auth_code : note that this can be either a permanent or temporary code
- IMS Org

## Using the module

Once you have created the developer project in developer.adobe.com, you can start using the module.\
In order to start using the module, you will need to import it on your environment.\
This is where the `import` keyword is used for that module.


```python
import aepp
```

### Create a config file

Once you have imported the module in your environment, you probably want to create a config file for authentication.\
The `createConfigFile` is the method directly available out of aepp module to help you create the configuration file needed.\

As explained above, there are 2 options:

* Oauth V2 config file
* Oauth V1 config (internal Adobe engineering)


If you want to use OAuth-V2-based authentication, use the following code:

```python
import aepp
aepp.createConfigFile(destination='template_config.json', auth_type="oauthV2")
```

The resulting file will have different fields:

```JSON
{
    "org_id": "<orgID>",
    "client_id": "<client_id>",
    "secret": "<YourSecret>",
    "sandbox-name": "prod",
    "environment": "prod",
    "scopes": "<scopes>"
}
```

If you want to use OAuth-V1-based authentication, use the following code:

```python
import aepp
aepp.createConfigFile(destination='template_config.json', auth_type="oauthV1")
```
The resulting file will have different fields:

```JSON
{
    "org_id": "<orgID>",
    "client_id": "<client_id>",
    "secret": "<YourSecret>",
    "sandbox-name": "prod",
    "environment": "prod",
    "auth_code": "<auth_code>"
}
```

In both cases, remove the `<placeholder>` and replace them with your information.\
All information are available on your project page on developer.adobe.com

**Note** By default, we are setting the sandbox name to "prod". If you don't know what that value, you can override it via a parameter.

**Note** The default behavior has been changed starting June 2023, where oauthV2 is the default type of configuration file created in case you omit the parameter.

Parameter for `createConfigFile` method:

* destination : OPTIONAL : The name of the file to be created (with a dedicated path if needed)
* sandbox : OPTIONAL : You can directly set your sandbox name in this parameter.
* auth_type : OPTIONAL : type of authentication, either "jwt" or "oauthV2" or "oauthV1" (default oauthV2)
* verbose : OPTIONAL : set to true, gives you a print stateent where is the location.


### Environments

By default, the environment is set to `prod`. This is different from the sandbox, as it refers to the physical environment where the organization was setup.

For all AEP customers "prod" is what should be used, but for internal accounts it can be set to "stage" or "int".

### Importing the config file

Once your config file has been generated, you can import it in your script by using the `importConfigFile` method.

```python
import aepp
aepp.importConfigFile('myConfig_file.json')
```

The type of authentication will be automatically determined based on the keys provided by the JSON config file. Be careful to not mix JWT and Oauth on the same config file.\

Parameter for `importConfigFile` method:
* path: REQUIRED : path to the configuration file. Can be either a fully-qualified or relative.
* connectInstance : OPTIONAL : If you want to return an instance of the ConnectObject class
* auth_type : OPTIONAL : type of authentication, either "jwt" or "oauth". Detected based on keys present in config file.
* sandbox : OPTIONAL : The sandbox to connect it.

The `connectInstance` parameter is described below. see [Tip for multi sandbox work](#tip-for-multi-sandbox-work)\
The `sandbox` paramter is to facilitate your life, in case you want to use the same config file for multiple sandboxes.

### Alternative method for cloud configuration

You can also use the configure method to setup the connection directly on the aepp setup.\
This approach is better if you don't want to use a file in your system.\
In that case, you can directly pass the elements in the configure method.

If you want to use OAuth-V2-based authentication, simply use different parameters when calling `configure`:

```python
import aepp
aepp.configure(
    org_id=my_org_id,
    secret=my_secret,
    client_id=my_client_id,
    scopes=my_scopes,
    environment="prod"
)
```

If you instead want to use OAuth-V1-based authentication, simply use different parameters when calling `configure`:

```python
import aepp
aepp.configure(
    org_id=my_org_id,
    secret=my_secret,
    client_id=my_client_id,
    auth_code=my_auth_code,
    environment="prod"
)
```

**NOTE** : In both case, I didn't provide a `sandbox` parameter but this parameter does exist and can be used to setup a specific sandbox.\
By default, the `prod` sandbox will be used. To use that, use the code below (for JWT):

```python
import aepp
aepp.configure(
    org_id=my_org_id,
    tech_id=my_tech_id, 
    secret=my_secret,
    private_key=my_key_as_string,
    client_id=my_client_id,
    environment="prod",
    sandbox=my_sandbox
)
```

**NOTE** The `environment` parameter is optional and defaults to "prod".

### The ConnectInstance parameter

The `aepp` module contains a parameter named `connectInstance` for `importConfig` and `configure` methods that provide a way to store the configuration setup.\
As you import the config file, you will default any instantiation of the sub module to the latest loaded configuration.\
Using this parameter will make the methods returning an instance of the `ConnectObject` class.\
That will store the information required to connect to your IMS or sandbox setup (secret, client_id, tech_id, IMSorg, etc...)

You can use that instance then in any of the sub module that is provided with the aepp package and that are related to the AEP API.\
You will be able to pass that instance to the `config` parameter of any submodule (see next section)

Example:

```python
import aepp
myOrg1 = aepp.importConfigFile('org1_config.json',connectInstance=True)
```

## Importing a sub module to work with

You can then import the sub module and you will require to instantiate the class inside that module.\
The class has usually the same name than the sub module but with a capital letter.

Example with schema sub module and Schema class.

```python
import aepp
aepp.importConfigFile('myConfig_file.json')
## using the connectInstance parameter
config1 = aepp.importConfigFile('myConfig_file.json',connectInstance=True)

from aepp import schema

mySchemaInstance = schema.Schema()
## using the instance of config use 
mySchemaInstance = schema.Schema(config=config1)
```

This works exactly the same for all of the sub modules mentioned in the [README page](../README.md).
Note the queryservice and privacyservice have exceptions mentioned on the README.

The idea to have a class instantiated for each submodule has been made in order to allow to work with several sandboxes (or organization) in the same environment.\
You can always access the sandbox used by using the instance `sandbox` attribute.\
Following the previous example:

```python
mySchemaInstance.sandbox ## will return which sandbox is configured in that environment.
```

## Help

You can always use the docstring definition to help you using the functions.\
I tried to give a clear documentation of what each function is capable of.

```python
help(mySchemaInstance.getSchemas)
## returns

#getSchemas(**kwargs) -> list method of aepp.schema.Schema instance
#    Returns the list of schemas retrieved for that instances in a "results" list.
#    Kwargs:
#        debug : if set to true, will print the result when error happens
```
