# Synchronizer (BETA)

The `synchronizer` is a sub module that lives on top of several sub modules of aepp (schema, schemamanger,fieldgroupmanager, datatypemanager, classmanager, catalog, identity).\
**NOTE** : The synchronizer module is currently a **work in progress** and is expected to support more capabilities in the future. Some elements could change in the future and the module is not stable since stated otherwise here. 

The module is intended to create or update elements between sandboxes within an organization.
The current supported artefacts for the synchronization job are: 
* data type
* field group
* schema
* class
* descriptors
* identity
* datasets
* mergepolicy
* audience


## Synchronizer class

The `Synchronizer` class is part of the `synchronizer` module and it takes the following elements as a parameter: 
* baseSandbox : REQUIRED : name of the base sandbox
* targets : REQUIRED : list of target sandboxes name as strings
* config : REQUIRED : ConnectObject with the configuration. Make sure that the configuration of your API allows connection to all targeted sandboxes.
* region : OPTIONAL : region of the sandboxes. default is 'nld2', possible values are: "va7" or "aus5 or "can2" or "ind2"
* localFolder : OPTIONAL : if provided, it will use the local environment as the base. Default is False.
                If localFolder is provided, the baseSandbox and targets are not used, and the configuration is used to connect to the local environment.
                configuration to use local environment is a folder with the name of your sandbox, inside that folder there must a folder for each base component:
                - class
                - schema
                - fieldgroup
                - datatype
                - identity
                - dataset
                - descriptor
                - mergepolicy
                - audience

For more details on localFolder, see [local files usage](./localfilesusage.md)

### Synchronizer attributes

Once instantiated the synchronizer object will contains certain attributes: 
* baseConfig : the config object with the base sandbox configuration to connect to the base sandbox (a `ConnectInstance` [instance](/getting-started.md#the-connectInstance-parameter))
* dict_targetsConfig : A dictionary of the different target sandbox configuration object (children of `ConnectInstance` class)
* region : The region used for the Identity Management for the Target and base Sandbox
* dict_targetComponents : A dictionary of the target components that has been created. A cache mechanisme to optimize the future usage of these components in the future. 


### Synchronizer methods: 

The following methods are available once you have instantianted the `Synchronizer` class.

#### syncComponent
Synchronize a component to the target sandbox(es).\
The component could be a string (name or id of the component in the base sandbox) or a dictionary with the definition of the component.\
If the component is a string, you have to have provided a base sandbox in the constructor.\
Arguments:
* component : REQUIRED : name or id of the component or a dictionary with the component definition
* componentType : OPTIONAL : type of the component (e.g. "schema", "fieldgroup", "datatypes", "class", "identity", "dataset", "mergepolicy", "audience"). Required if a string is passed.\
It is not required but if the type cannot be inferred from the component, it will raise an error. 
* verbose : OPTIONAL : if True, it will print the details of the synchronization process

#### getSyncFieldGroupManager
Helper method to get the FieldGroupManager for a target sandbox.\
It searches through the component cache to see if the FieldGroupManager for the target sandbox is already instantiated.\
If not, it generate an error.
Arguments:
* fieldgroup : REQUIRED : Either $id, or name or alt:Id of the field group to get
* sandbox : REQUIRED : name of the sandbox to get the field group from

#### getDatasetName
Helper method to get the name of a dataset from its id in a specific sandbox.\
Arguments:
* datasetId : REQUIRED : id of the dataset to get
* sandbox : REQUIRED : name of the sandbox to get the dataset from

## Notes on Synchronization capabilities

The synchronization capabilities are very similar to the sandbox tooling.

Due to the potential issue with ID management, the synchronizer bases its capabilities on name of the artefact.\
It means that the **name** of the schema, class, field group, data type, dataset, identity namespace are used. 

As of today, the synchronization will realize the following operation for the different artefacts: 

Operation |Schema | Class | Field Groups | Data Type | Descriptors | Dataset | Identity | Merge Policy | Audiences
--| -- | -- | -- | -- | -- | -- | -- | -- | -- |
Create | Supported | Supported | Supported | Supported | Supported | Supported | Supported | Supported | Supported |
Update | Supported | Supported | Supported | Supported | Suppported | - | - | - | - |
Delete | Not supported | Not supported | Not supported | Not supported | Not supported | Not supported | Not supported | Not supported | Not supported |

It is not supported to delete an artefact or delete a field in an Field Group or Data Type via the Synchronizer.\
The synchronizer only supports additive operations 

The synchronizer will automatically resolve the dependency to create the elements require for the artefact used.\
Example:\
Synchronizing a dataset will automatically synchronize the underlying schema and the different field groups.\
If the schema is in a relationship with another schema (lookup), the associated lookup schema will also be created and the associated created. (note: The dataset associated with the lookup schema won't be created)

### Create 

For all artefacts, if the element does not exist in the target sandbox, it will automatically create it.\
The synchronizer automatically resolves all dependencies, which mean that the associated elements Schema associated to a dataset, or field group associated to a schema or a data type associated to a field groups are automatically created as well.

As of today, the schema and datasets are not enabled for profile per default during creation.


### Update

The **Update** operation is provided the capacity to add new fields to `field groups` or `data type` in the base and replicate that change to the target change.\
The removal of fields are not supported as it could be a breaking change in the target sandboxes.

It also supports the addition of a field group to a `schema` and replicate that change to all target sandboxes.

### Notes on Merge Policies synchronization

When creating a merge policy, if the merge policy is of type `dataSetPrecedence`, the synchronizer will automatically map the dataset IDs from the base sandbox to the target sandbox.\
This means that the datasets used in the merge policy in the base sandbox will be created in the target sandbox for the merge policy creation to succeed.
Additionally, if the dataset reference a schema that does not exist in the target sandbox, the synchronizer will also create the schema and its associated field groups and data types. 

### Notes on Audience synchronization

When creating an audience, the synchronizer will simply copy the audience definition from the base sandbox to the target sandbox.\
For the audience to be created properly, the fields used in the audience definition must exist in the target sandbox and the schema should have been enabled for Profile.\
If the fields or schema do not exist in the target sandbox, the audience creation will fail.


## Incoming features

* Tags (dataset)
* Profile enabling capabilities
* Data Prep Mappings


