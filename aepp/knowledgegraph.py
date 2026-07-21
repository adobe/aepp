#  Copyright 2024 Adobe. All rights reserved.
#  This file is licensed to you under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License. You may obtain a copy
#  of the License at http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software distributed under
#  the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#  OF ANY KIND, either express or implied. See the License for the specific language
#  governing permissions and limitations under the License.

# Internal Library
import aepp
from aepp import schema, catalog, customerprofile, identity, segmentation, flowservice
from aepp.schemamanager import SchemaManager
from copy import deepcopy
from typing import Union
from pathlib import Path
import logging
import concurrent.futures
from .configs import ConnectObject
import pandas as pd
from rdflib.namespace import RDF, RDFS, XSD, DCAT, DCTERMS
from rdflib import Graph, Namespace, Literal,URIRef


class KnowledgeGraph:
    """
    Build a knowledge graph of the artefacts of a single AEP sandbox.

    The class crawls the other aepp modules (schema, catalog, customerprofile,
    identity, segmentation, ...) and turns the discovered artefacts and the
    relationships between them into a set of RDF triples.

    The triple store is provider-agnostic (a plain list of (subject, predicate,
    object) tuples) so that serialization to Turtle / Mermaid / SVG does not
    require any heavy dependency to be installed unless that specific export is
    requested.
    """

    ## logging capability
    loggingEnabled = False
    logger = None


    ## The artefact types that buildFromSandbox knows how to crawl.
    ARTEFACT_TYPES = ["schema", "class", "fieldgroup", "datatype",
                      "dataset", "identity", "audience", "mergePolicy"]

    def __init__(
        self,
        config: Union[dict, ConnectObject] = aepp.config.config_object,
        header: dict = aepp.config.header,
        loggingObject: dict = None,
        **kwargs,
    ):
        """
        Instantiate the KnowledgeGraph for one sandbox.

        Arguments:
            config : REQUIRED : ConnectObject (or config dict) pointing at the
                sandbox you want to graph.
            header : OPTIONAL : header object from the config module.
            loggingObject : OPTIONAL : logging object to log messages.
        """
        if loggingObject is not None and sorted(
            ["level", "stream", "format", "filename", "file"]
        ) == sorted(list(loggingObject.keys())):
            self.loggingEnabled = True
            self.logger = logging.getLogger(f"{__name__}")
            self.logger.setLevel(loggingObject["level"])
            if type(loggingObject["format"]) == str:
                formatter = logging.Formatter(loggingObject["format"])
            elif type(loggingObject["format"]) == logging.Formatter:
                formatter = loggingObject["format"]
            if loggingObject["file"]:
                fileHandler = logging.FileHandler(loggingObject["filename"])
                fileHandler.setFormatter(formatter)
                self.logger.addHandler(fileHandler)
            if loggingObject["stream"]:
                streamHandler = logging.StreamHandler()
                streamHandler.setFormatter(formatter)
                self.logger.addHandler(streamHandler)
        self.sandbox = config.sandbox if isinstance(config, ConnectObject) else config.get("sandbox")
        self.config = config
        self.header = header
        self.loggingObject = loggingObject
        ## the source of truth: a list of (subject, predicate, object) triples
        self.triples = []
        self.schemaAPI = schema.Schema(config=self.config, loggingObject=self.loggingObject)
        self.catalogAPI = catalog.Catalog(config=self.config, loggingObject=self.loggingObject)
        self.customerProfileAPI = customerprofile.Profile(config=self.config, loggingObject=self.loggingObject)
        self.flowServiceAPI = flowservice.FlowService(config=self.config, loggingObject=self.loggingObject)
        self.identityAPI = identity.Identity(config=self.config, loggingObject=self.loggingObject)
        self.segmentationAPI = segmentation.Segmentation(config=self.config, loggingObject=self.loggingObject)
        self.tenant = self.schemaAPI.getTenantId()
        self.tenantNamespace = Namespace(self.tenant)
        self.tenantGlobal = Namespace("Adobe")
        self.SANDBOX = Namespace(f"https://sandbox/{self.sandbox}")
        self.SCHEMA = Namespace(f"https://sandbox/{self.sandbox}/xdm/")
        self.CATALOG = Namespace(f"https://sandbox/{self.sandbox}/catalog/")
        self.IDENTITY = Namespace(f"https://sandbox/{self.sandbox}/identity/")
        self.PROFILE = Namespace(f"https://sandbox/{self.sandbox}/profile/")
        self.FLOWS = Namespace(f"https://sandbox/{self.sandbox}/flows/")
        self.AUDIENCES = Namespace(f"https://sandbox/{self.sandbox}/audiences/")
        namespace_preview = self.customerProfileAPI.getPreviewNamespace()
        self.__list_graph_identities_namespaces__ = []
        for element in namespace_preview:
            self.__list_graph_identities_namespaces__.append(element['code'])
        self.global_graph = None
        self.schema_graph = None

    
    ## ------------------------------------------------------------------ ##
    ## graph construction                                                  ##
    ## ------------------------------------------------------------------ ##

    def buildGraph(self,hasdata:bool=True,detail:bool=True,enabled:bool=False,**kwargs) -> Graph:
        """
        Crawl the sandbox and populate the triple store.
        Arguments:
            hasdata : OPTIONAL : Filters to dataset with ingested data. Default True.
            detail : OPTIONAL : Provide additional information on row level for schema (default True)
            enabled : OPTIONAL : Filters to dataset enabled for Profile (Profile or Identity). Default False.
        """
        s_classes:list = self.schemaAPI.getClasses()
        s_classesglobal:list = self.schemaAPI.getClassesGlobal()
        full_list_classes:list = s_classes + s_classesglobal
        dict_id_title = {el['$id']:el['title'] for el in full_list_classes}
        descriptors:list = self.schemaAPI.getDescriptors()
        datasets:list = self.catalogAPI.getDataSets(output="list")
        if hasdata:
            df_datasets:pd.DataFrame = self.catalogAPI.data.infos[self.catalogAPI.data.infos.datalake_storageSize>0].copy()
        else: 
            df_datasets:pd.DataFrame = self.catalogAPI.data.infos.copy()
        ingestion_flows = self.flowServiceAPI.getFlows(onlySources=True)
        if enabled:
            df_datasets = df_datasets[df_datasets.profileEnabled |df_datasets.identityEnabled ].copy()
        list_obs_schemas = self._build_observable_schema_(df_datasets["id"].tolist())
        dict_schemaId_obs = {el['observableSchema'].get('$id'):el for el in list_obs_schemas if el['observableSchema'].get('$id') is not None}
        if hasdata:
            list_of_schema = df_datasets[(~df_datasets.schemaId.str.contains('__union',na=False)) & (df_datasets.schemaId.str.contains(self.tenant,na=False))]["schemaId"].unique().tolist()## removing Snapshots and OOTB
        else:
            list_of_schema = [el['$id'] for el in self.schemaAPI.getSchemas() if '__union' not in el['$id'] and self.tenant in el['$id']]
        ## Schema Managers 
        schema_managers: list[SchemaManager] = self._build_schema_managers_(list_of_schema)
        ## Flow Managers
        flow_managers: list[flowservice.FlowManager] = self._build_flow_managers_([flow['id'] for flow in ingestion_flows])
        ## Audiences 
        audiences = self.segmentationAPI.getAudiences()
        ## building graph
        graph = Graph()
        SANDBOX_NODE = URIRef(str(self.SANDBOX))
        SCHEMA_NODE = URIRef(str(self.SCHEMA))
        CATALOG_NODE = URIRef(str(self.CATALOG))
        PROFILE_NODE = URIRef(str(self.PROFILE))
        IDENTITY_NODE = URIRef(str(self.IDENTITY))
        FLOWS_NODE = URIRef(str(self.FLOWS))
        AUDIENCES_NODE = URIRef(str(self.AUDIENCES))
        graph.bind(self.sandbox, SANDBOX_NODE)
        graph.bind("XDM", self.SCHEMA)
        if kwargs.get('only_schema',False) == False: 
            graph.bind("Catalog", CATALOG_NODE)
            graph.bind("Identity", IDENTITY_NODE)
            graph.bind("Profile", PROFILE_NODE)
            graph.bind("Flows", FLOWS_NODE)
            graph.bind("Audience", AUDIENCES_NODE)
        graph.add((SANDBOX_NODE, self.SANDBOX.contains, SCHEMA_NODE))
        graph.add((SANDBOX_NODE, self.SANDBOX.contains, FLOWS_NODE))
        graph.add((SANDBOX_NODE, self.SANDBOX.contains, CATALOG_NODE))
        graph.add((SANDBOX_NODE, self.SANDBOX.contains, AUDIENCES_NODE))
        graph.add((SANDBOX_NODE, self.SANDBOX.contains, PROFILE_NODE))
        graph.add((PROFILE_NODE, self.PROFILE.contains, self.PROFILE.UPS))
        graph.add((PROFILE_NODE, self.PROFILE.contains, self.PROFILE.IdentityGraph))
        graph.add((SANDBOX_NODE, self.SANDBOX.contains, IDENTITY_NODE))
        graph.add((SANDBOX_NODE, RDFS.label, Literal(self.sandbox)))
        for namespace_code in self.__list_graph_identities_namespaces__:
            graph.add((IDENTITY_NODE,self.IDENTITY.contains,self.IDENTITY[namespace_code]))
            graph.add((self.IDENTITY[namespace_code],RDFS.label,Literal(namespace_code)))
            graph.add((self.IDENTITY[namespace_code],RDF.type,self.IDENTITY.namespace))
        classes = set([sc.classId for sc in schema_managers if sc.classId is not None])
        for clas in classes:
            graph.add((SCHEMA_NODE, self.SCHEMA.contains, URIRef(clas)))
            graph.add((URIRef(clas), RDF.type, self.SCHEMA["class"]))
            graph.add((URIRef(clas), RDFS.label, Literal(dict_id_title.get(clas,clas))))
        dict_field_group_managers = {}
        for sch in schema_managers:
            if '__union' not in sch.classId:
                graph.add((URIRef(sch.id), RDF.type, self.SCHEMA.schema))
                graph.add((URIRef(sch.id), RDFS.label, Literal(sch.title)))
                graph.add((URIRef(sch.id), self.SCHEMA.implements, URIRef(sch.classId)))
                if detail == True:
                    obs_instance = dict_schemaId_obs.get(sch.id)
                    if obs_instance is not None:
                        obs_manager = catalog.ObservableSchemaManager(obs_instance)
                        df:pd.DataFrame = obs_manager.to_dataframe()
                        def assign_path_schema(row):
                            graph.add((URIRef(sch.id), self.SCHEMA.contains, self.SCHEMA[row['path'].replace('{}', '').replace('[]', '')]))
                            graph.add((self.SCHEMA[row['path'].replace('{}', '').replace('[]', '')], self.SCHEMA.usedIn,URIRef(sch.id)))
                            graph.add((self.SCHEMA[row['path'].replace('{}', '').replace('[]', '')], RDFS.label, Literal(row['title'])))
                            graph.add((self.SCHEMA[row['path'].replace('{}', '').replace('[]', '')], RDF.type, self.SCHEMA.path))
                            graph.add((self.SCHEMA[row['path'].replace('{}', '').replace('[]', '')],self.SCHEMA.xdmType , Literal(row['xdmType'])))
                            graph.add((self.SCHEMA[row['path'].replace('{}', '').replace('[]', '')],self.CATALOG.hasData , Literal(True)))
                        df.apply(assign_path_schema, axis=1)
                for fg in sch.fieldGroups:
                    if fg not in dict_field_group_managers.keys():
                        myFG = sch.getFieldGroupManager(fg)
                        dict_field_group_managers[myFG.id] = myFG
                        graph.add((URIRef(sch.id), self.SCHEMA.implements, URIRef(myFG.id)))
                        graph.add((URIRef(myFG.id), RDF.type, self.SCHEMA.fieldgroup))
                        graph.add((URIRef(myFG.id), RDFS.label, Literal(myFG.title)))
                        for dt in myFG.dataTypes:
                            myDT = myFG.getDataTypeManager(dt)
                            graph.add((URIRef(myFG.id), self.SCHEMA.contains, URIRef(myDT.id)))
                            graph.add((URIRef(myDT.id), RDF.type, self.SCHEMA.datatype))
                            graph.add((URIRef(myDT.id), RDFS.label, Literal(myDT.title)))
        if detail:
            for fgId, fgManager in dict_field_group_managers.items():
                df:pd.DataFrame = fgManager.to_dataframe()
                def assign_path_fg(row):
                    node = self.SCHEMA[row['path'].replace('{}', '').replace('[]', '')]
                    graph.add((URIRef(fgId), self.SCHEMA.defines, node))
                    graph.add((node, self.SCHEMA.defines_on, URIRef(fgId)))
                    graph.add((node, self.SCHEMA.description, Literal(row.get('description'),'')))
                    if row.get('origin') == 'dataType':
                        graph.add((node, self.SCHEMA.origin, Literal('dataType')))
                    else:
                        graph.add((node, self.SCHEMA.origin, Literal('fieldGroup')))
                df.apply(assign_path_fg, axis=1)
        supported_descriptors = ['xdm:descriptorIdentity', 'xdm:descriptorOneToOne','xdm:descriptorReferenceIdentity','xdm:descriptorRelationship'] 
        for desc in descriptors:
            if desc.get('@type','') in supported_descriptors and desc.get('xdm:sourceSchema','') in list_of_schema:
                if desc.get('@type') == 'xdm:descriptorIdentity': ## linked identities to schemas
                    graph.add((URIRef(desc['xdm:sourceSchema']), self.IDENTITY.linked, self.IDENTITY[desc['xdm:namespace']]))
                    if detail == True:
                        graph.add((self.SCHEMA[desc['xdm:sourceProperty'].replace('/','.',)[1:]],self.SCHEMA.identityField,URIRef(desc['xdm:sourceSchema'])))
                        if desc.get('xdm:isPrimary',False) == True:
                            graph.add((self.SCHEMA[desc['xdm:sourceProperty'].replace('/','.',)[1:]],self.SCHEMA.isPrimary, Literal(True, datatype=XSD.boolean)))
                        else:
                            graph.add((self.SCHEMA[desc['xdm:sourceProperty'].replace('/','.',)[1:]],self.SCHEMA.isPrimary, Literal(False, datatype=XSD.boolean)))
                if desc.get('@type') in ['xdm:descriptorOneToOne','xdm:descriptorRelationship']:
                    graph.add((URIRef(desc['xdm:sourceSchema']), self.SCHEMA.relationship, URIRef(desc['xdm:destinationSchema'])))
                    if detail == True:
                        graph.add((self.SCHEMA[desc.get('xdm:sourceProperty','').replace('/','.').replace('[*]','')[1:]],self.SCHEMA.relationship, self.SCHEMA.implementation))
                if desc.get('@type') == 'xdm:descriptorReferenceIdentity':
                    graph.add((URIRef(desc['xdm:sourceSchema']),self.SCHEMA.relationship,Literal(desc['xdm:identityNamespace'])))
                    graph.add((URIRef(desc['xdm:sourceSchema']), self.IDENTITY.linked, self.IDENTITY[desc['xdm:identityNamespace']]))
                    if detail == True:
                        graph.add((self.SCHEMA[desc.get('xdm:sourceProperty','').replace('/','.').replace('[*]','')[1:]],self.SCHEMA.relationship, self.SCHEMA.implementation))
                if desc.get('@type') == 'xdm:descriptorPrimaryKey':
                    graph.add((URIRef(desc['xdm:sourceSchema']), self.SCHEMA.relationship, URIRef(desc['xdm:destinationSchema'])))
                    if detail == True:
                        sourceProperty = desc.get('xdm:sourceProperty','')
                        if type(sourceProperty) == list:
                            for sourceProperty in sourceProperty:
                                graph.add((self.SCHEMA[sourceProperty.replace('/','.').replace('[*]','')[1:]],self.SCHEMA.relationship, self.SCHEMA.implementation))
                            sourceProperty = sourceProperty[0]
                            graph.add((self.SCHEMA[sourceProperty],self.SCHEMA.relationship, Literal("descriptorPrimaryKey")))
        if kwargs.get('only_schema',False) == False:
            for index, row in df_datasets.iterrows():
                graph.add((SANDBOX_NODE, self.SANDBOX.contains, self.CATALOG[row['id']]))
                graph.add((CATALOG_NODE, self.CATALOG.contains, self.CATALOG[row['id']]))
                graph.add((self.CATALOG[row['id']], RDF.type, DCAT.Dataset))
                graph.add((self.CATALOG[row['id']], self.SCHEMA.implements, URIRef(row['schemaId'])))
                graph.add((self.CATALOG[row['id']], DCTERMS.title, Literal((row.get('name')))))
                if row['profileEnabled']:
                    graph.add((PROFILE_NODE,self.PROFILE.contains,self.CATALOG[row['id']]))
                    graph.add((self.CATALOG[row['id']],self.PROFILE.linked, PROFILE_NODE))
                    graph.add((self.CATALOG[row['id']],self.PROFILE.participates,self.PROFILE.UPS))
                if row['identityEnabled']:
                    graph.add((self.CATALOG[row['id']],self.PROFILE.linked, PROFILE_NODE))
                    graph.add((self.CATALOG[row['id']],self.PROFILE.participates,self.PROFILE.IdentityGraph))
            for flow in flow_managers:
                if hasattr(flow, 'datasetId'):
                    if flow.datasetId is not None and flow.datasetId in df_datasets['id'].tolist():
                        graph.add((FLOWS_NODE, self.SANDBOX.contains, self.FLOWS[flow.id]))
                        graph.add((self.FLOWS[flow.id], RDFS.label, Literal(flow.name)))
                        graph.add((self.FLOWS[flow.id], RDF.type, Literal('Ingestion Flow')))
                        graph.add((self.FLOWS[flow.id], self.FLOWS.loads, self.CATALOG[flow.datasetId]))
                        if flow.frequency is not None:
                            graph.add((self.FLOWS[flow.id], self.FLOWS.frequency, Literal(flow.frequency)))
            for audience in audiences:
                graph.add((AUDIENCES_NODE, self.AUDIENCES.contains, self.AUDIENCES[audience['id']]))
                graph.add((self.AUDIENCES[audience['id']], RDFS.label, Literal(audience.get('name'))))
                graph.add((self.AUDIENCES[audience['id']], RDF.type, self.AUDIENCES.audience))
                evaluationInfo = audience.get('evaluationInfo',{})
                if evaluationInfo.get('batch',{}).get('enabled',False):
                    graph.add((self.AUDIENCES[audience['id']], self.AUDIENCES.evaluation, Literal("BATCH")))
                if evaluationInfo.get('continuous',{}).get('enabled',False):
                    graph.add((self.AUDIENCES[audience['id']], self.AUDIENCES.evaluation, Literal("STREAMING")))
                if evaluationInfo.get('synchronous',{}).get('enabled',False):
                    graph.add((self.AUDIENCES[audience['id']], self.AUDIENCES.evaluation, Literal("EDGE")))
                paths = self.segmentationAPI.extractPaths(audience)
                if paths is not None:
                    for path in paths:
                        if '@' not in path and path != 'xEvent':
                            if path.startswith('xEvent.'):
                                path = path.replace('xEvent.','')
                            else:
                                if (self.AUDIENCES[audience['id']], self.AUDIENCES.behavior, Literal("Profile-based")) not in graph:
                                    graph.add((self.AUDIENCES[audience['id']], self.AUDIENCES.behavior, Literal("Profile-based")))
                            node = self.SCHEMA[path.replace('{}', '').replace('[]', '')]
                            if (node, RDF.type, self.SCHEMA.path) in graph:
                                graph.add((node, self.AUDIENCES.usedIn, self.AUDIENCES[audience['id']]))
                            else:
                                graph.add((node, RDF.type, self.SCHEMA.path))
                                graph.add((node, self.AUDIENCES.usedIn, self.AUDIENCES[audience['id']]))
                                graph.add((node, self.SCHEMA.usedIn, RDF.nil))
                        if path == 'xEvent':
                            node = self.SCHEMA[path.replace('{}', '').replace('[]', '')]
                            graph.add((self.AUDIENCES[audience['id']], self.AUDIENCES.behavior, Literal("Event-based")))
                            graph.add((node, self.AUDIENCES.usedIn, self.AUDIENCES[audience['id']]))
                            graph.add((node, self.SCHEMA.usedIn, RDF.nil))
                        if '@' in path:
                            graph.add((self.AUDIENCES[audience['id']], self.AUDIENCES.behavior, Literal("Relationship-based")))
            self.global_graph = graph
            return self.global_graph
        else:
            return graph

    def _build_schema_managers_(self, schema_ids: list) -> list[SchemaManager]:
        """
        Instantiate SchemaManager instances in parallel for each schema ID.
        Arguments:
            schema_ids : list of schema $id or altId strings.
        Returns a list of SchemaManager instances.
        """
        def _build(schema_id: str) -> SchemaManager:
            return SchemaManager(schema=schema_id, schemaAPI=self.schemaAPI)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return list(executor.map(_build, schema_ids))
    
    def _build_flow_managers_(self, flow_ids: list) -> list[flowservice.FlowManager]:
        """
        Instantiate FlowManager instances in parallel for each flow ID.
        Arguments:
            flow_ids : list of flow $id or altId strings.
        Returns a list of FlowManager instances.
        """
        def _build(flow_id: str) -> flowservice.FlowManager:
            return flowservice.FlowManager(flowId=flow_id,config=self.config)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return list(executor.map(_build, flow_ids))
    
    def _build_observable_schema_(self, dataset_ids: list) -> list[SchemaManager]:
        """
        Retrieve observable schemas.
        Arguments:
            dataset_ids : list of dataset Id .
        Returns a list of SchemaManager instances.
        """
        def _get(dsId: str) -> SchemaManager:
            return self.catalogAPI.getDataSetObservableSchema(dsId)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return list(executor.map(_get, dataset_ids))


    def buildSchemaRelationships(self, detail: bool = False) -> Graph:
        """
        Build relationships between schemas and their XDM artefacts (class, fieldgroup, datatype).
        Does not include datasets, identities, audiences, or merge policies.
        """
        self.schema_graph = self.buildKnowledgeGraph(detail=detail, only_schema=True)
        return self.schema_graph

    def addPathAttributes(self, path: str, attributes: dict, graph: Graph = None) -> Graph:
        """
        Attach custom attributes to an existing schema path node.
        The path node must already exist in the graph (created when buildKnowledgeGraph
        or buildSchemaRelationships was run with detail=True).
        Arguments:
            path       : REQUIRED : the XDM field path (dot notation, e.g. "person.name.firstName").
            attributes : REQUIRED : dictionary of {predicate: value} to add on that path node as literal triples.
            graph      : OPTIONAL : graph to mutate. Defaults to self.global_graph, then self.schema_graph.
        Returns the mutated graph.
        """
        g = graph or self.global_graph or self.schema_graph
        if g is None:
            raise RuntimeError("No graph built. Call buildKnowledgeGraph() or buildSchemaRelationships() first.")
        node = self.SCHEMA[path.replace('{}', '').replace('[]', '')]
        if (node, self.SCHEMA.path, None) not in g:
            raise ValueError(f"Path '{path}' not found in the schema graph. Build the graph with detail=True first.")
        for key, value in attributes.items():
            g.add((node, self.SCHEMA[key], Literal(value)))
        return g

    ## ------------------------------------------------------------------ ##
    ## export helpers                                                     ##
    ## ------------------------------------------------------------------ ##

    def _inject_legend_html(self, path: Union[str, Path]) -> None:
        """Inject a fixed-position colour legend into a pyvis-generated HTML file."""
        legend_entries = [
            ("Class",        "#9b59b6"),
            ("Schema",       "#5b9bd5"),
            ("Field group",  "#70ad47"),
            ("Datatype",     "#ffc000"),
            ("Dataset",      "#ed7d31"),
            ("Identity",     "#e74c3c"),
            ("Other",        "#aaaacc"),
        ]
        items_html = "\n".join(
            f'<div style="display:flex;align-items:center;margin-bottom:5px;">'
            f'<span style="display:inline-block;width:14px;height:14px;background:{color};'
            f'border-radius:3px;margin-right:8px;flex-shrink:0;"></span>'
            f'<span>{label}</span></div>'
            for label, color in legend_entries
        )
        legend_html = (
            '<div style="position:fixed;bottom:20px;left:20px;'
            'background:rgba(26,26,46,0.93);padding:12px 16px;'
            'border-radius:8px;border:1px solid #555577;'
            'color:white;font-family:arial;font-size:12px;z-index:9999;">'
            '<div style="font-weight:bold;margin-bottom:8px;font-size:13px;">Node types</div>'
            f'{items_html}'
            '</div>'
        )
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")
        content = content.replace("</body>", legend_html + "\n</body>")
        file_path.write_text(content, encoding="utf-8")

    def _build_display_data(
        self, g: Graph, simplified: bool = False
    ) -> tuple[dict, list]:
        """
        Derive node metadata and edge list from an rdflib Graph for rendering.

        When simplified=True only schema, dataset, and identity nodes are kept,
        and labels (RDFS.label / DCTERMS.title) replace raw URI fragments.

        Returns:
            nodes : {uri_str: {"label": str, "color": str, "title": str}}
            edges : [(source_uri, target_uri, predicate_label)]
        """
        def _short(uri, max_len: int = 35) -> str:
            label = str(uri).rsplit("/", 1)[-1].rsplit("#", 1)[-1]
            return label if len(label) <= max_len else label[:max_len - 1] + "…"

        type_colors = {
            str(self.SCHEMA.schema):     "#5b9bd5",
            str(self.SCHEMA.fieldgroup): "#70ad47",
            str(self.SCHEMA.datatype):   "#ffc000",
            str(DCAT.Dataset):           "#ed7d31",
            str(self.SCHEMA["class"]):   "#9b59b6",
        }
        identity_color = "#e74c3c"

        # First pass: collect labels, rdf:type, and identity nodes
        labels: dict[str, str] = {}
        node_type_uris: dict[str, str] = {}
        identity_nodes: set[str] = set()

        for s, p, o in g:
            s_str, o_str = str(s), str(o)
            if p in (RDFS.label, DCTERMS.title) and isinstance(o, Literal):
                labels[s_str] = str(o)
            if p == RDF.type:
                node_type_uris[s_str] = o_str
            if p == self.IDENTITY.linked and not isinstance(o, Literal):
                identity_nodes.add(o_str)
            if p == self.SANDBOX.contains and o_str == str(self.IDENTITY.identity):
                identity_nodes.add(s_str)

        # When simplified, keep only class, schema, dataset, and identity nodes
        if simplified:
            keep_nodes: set[str] | None = (
                {s for s, t in node_type_uris.items() if t in (str(self.SCHEMA.schema), str(DCAT.Dataset), str(self.SCHEMA["class"]))}
                | identity_nodes
            )
        else:
            keep_nodes = None

        def _make_node(uri_str: str) -> dict:
            is_identity = uri_str in identity_nodes
            if is_identity:
                color = identity_color
            else:
                color = type_colors.get(node_type_uris.get(uri_str, ""), "#aaaacc")
            return {
                "label": labels.get(uri_str, _short(uri_str)),
                "color": color,
                "title": labels.get(uri_str, _short(uri_str)),
                "type_uri": node_type_uris.get(uri_str, ""),
                "is_identity": is_identity,
            }

        # Only expose proper AEP artifact nodes — those with an explicit rdf:type
        # or recognised identity nodes. Structural/intermediate URIs (CATALOG_NODE,
        # PROFILE_NODE, self.IDENTITY.identity, self.SCHEMA.descriptors, …) are
        # excluded so they never appear as unlabelled nodes in the diagram.
        artifact_nodes: set[str] = set(node_type_uris.keys()) | identity_nodes

        if keep_nodes is not None:
            artifact_nodes &= keep_nodes

        nodes: dict[str, dict] = {}
        edges: list[tuple[str, str, str]] = []

        for s, p, o in g:
            if isinstance(o, Literal):
                continue
            s_str, o_str = str(s), str(o)
            if s_str not in artifact_nodes or o_str not in artifact_nodes:
                continue
            if s_str not in nodes:
                nodes[s_str] = _make_node(s_str)
            if o_str not in nodes:
                nodes[o_str] = _make_node(o_str)
            edges.append((s_str, o_str, _short(p)))

        return nodes, edges

    ## ------------------------------------------------------------------ ##
    ## export                                                              ##
    ## ------------------------------------------------------------------ ##

    def loadGraph(self, path: Union[str, Path], format: str = "turtle", target: str = "global") -> Graph:
        """
        Load a previously exported RDF graph from disk into memory, so diagrams
        can be regenerated (exportInteractiveDiagram, exportNodeDiagram, ...)
        without re-crawling the sandbox.
        Arguments:
            path   : REQUIRED : path to the serialized graph file (e.g. produced by exportTurtle).
            format : OPTIONAL : rdflib serialization format of the file ("turtle", "xml", "n3", "nt", "json-ld", ...).
                                Default "turtle".
            target : OPTIONAL : where to store the loaded graph - "global" (self.global_graph) or
                                "schema" (self.schema_graph). Default "global".
        Returns the loaded Graph.
        """
        if target not in ("global", "schema"):
            raise ValueError("target must be either 'global' or 'schema'")
        g = Graph()
        g.parse(source=str(path), format=format)
        if target == "schema":
            self.schema_graph = g
        else:
            self.global_graph = g
        return g

    def exportTurtle(self, path: Union[str, Path] = None, graph: Graph = None) -> None:
        """
        Serialize the graph to RDF Turtle format.
        Arguments:
            path  : OPTIONAL : if provided, writes the Turtle to this file.
            graph : OPTIONAL : graph to export. Defaults to self.global_graph, then self.schema_graph.
        Returns the Turtle string.
        """
        g = graph or self.global_graph or self.schema_graph
        if g is None:
            raise RuntimeError("No graph built. Call buildKnowledgeGraph() or buildSchemaRelationships() first.")
        turtle = g.serialize(format="turtle")
        if path is not None:
            Path(path).write_text(turtle, encoding="utf-8")
        return None

    def exportInteractiveDiagram(self, path: Union[str, Path], graph: Graph = None, simplified: bool = False) -> None:
        """
        Render the graph to an interactive HTML file using pyvis.
        Opens in any browser; supports zoom, pan, drag, and physics simulation.
        Requires: pip install pyvis
        Arguments:
            path       : REQUIRED : output file path, should end with .html.
            graph      : OPTIONAL : graph to render. Defaults to self.global_graph, then self.schema_graph.
            simplified : OPTIONAL : if True, only class, schemas, datasets, and identity nodes are shown,
                                    with human-readable labels instead of URI fragments. Default False.
        """
        try:
            from pyvis.network import Network
        except ImportError:
            raise ImportError(
                "exportInteractiveDiagram requires pyvis. "
                "Install with `pip install pyvis`."
            )
        g = graph or self.global_graph or self.schema_graph
        if g is None:
            raise RuntimeError("No graph built. Call buildKnowledgeGraph() or buildSchemaRelationships() first.")

        nodes, edges = self._build_display_data(g, simplified)

        net = Network(height="95vh", width="100%", directed=True, bgcolor="#1a1a2e", font_color="white")
        net.set_options("""{
            "physics": {
                "solver": "forceAtlas2Based",
                "forceAtlas2Based": {
                    "gravitationalConstant": -80,
                    "centralGravity": 0.01,
                    "springLength": 180,
                    "springConstant": 0.06,
                    "damping": 0.5,
                    "avoidOverlap": 0.8
                },
                "stabilization": { "iterations": 300 }
            },
            "edges": {
                "arrows": { "to": { "enabled": true, "scaleFactor": 0.6 } },
                "color": { "inherit": false, "color": "#7777aa" },
                "smooth": { "type": "continuous" },
                "width": 1.0
            },
            "nodes": {
                "shape": "box",
                "borderWidth": 1.5,
                "font": { "size": 13, "face": "arial" },
                "margin": 8
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 100,
                "navigationButtons": true,
                "keyboard": true
            }
        }""")

        # Degree = total number of edges touching a node (in + out)
        from collections import Counter
        degree: Counter = Counter()
        for s_id, o_id, _ in edges:
            degree[s_id] += 1
            degree[o_id] += 1
        max_degree = max(degree.values(), default=1)
        MIN_SIZE, MAX_SIZE = 15, 50

        uri_to_id: dict[str, int] = {}
        for i, (uri_str, data) in enumerate(nodes.items()):
            uri_to_id[uri_str] = i
            deg = degree.get(uri_str, 0)
            size = MIN_SIZE + (deg / max_degree) * (MAX_SIZE - MIN_SIZE)
            title = f"{data['title']} ({deg} connection{'s' if deg != 1 else ''})"
            net.add_node(i, label=data["label"], title=title, color=data["color"], size=round(size, 1))

        for s_id, o_id, p_label in edges:
            net.add_edge(uri_to_id[s_id], uri_to_id[o_id], title=p_label)

        net.save_graph(str(path))
        self._inject_legend_html(path)

    def exportNodeDiagram(
        self,
        node: str,
        path: Union[str, Path],
        graph: Graph = None,
        format: str = "html",
    ) -> None:
        """
        Export a single node and all its direct connections.
        Arguments:
            node   : REQUIRED : node to focus on — full URI or (partial) label.
                                If multiple nodes match a partial label a ValueError is raised.
            path   : REQUIRED : output file path (.html / .png / .svg).
            graph  : OPTIONAL : source graph. Defaults to self.global_graph, then self.schema_graph.
            format : OPTIONAL : "html" (default, interactive pyvis diagram),
                                "png" or "svg" (static hierarchical diagram via graphviz).
                                PNG/SVG require: pip install graphviz  and the Graphviz binaries
                                from https://graphviz.org/download/
        """
        g = graph or self.global_graph or self.schema_graph
        if g is None:
            raise RuntimeError("No graph built. Call buildKnowledgeGraph() or buildSchemaRelationships() first.")

        all_nodes, all_edges = self._build_display_data(g, simplified=False)

        # Resolve node argument to a URI key present in all_nodes
        target_uri: str | None = None
        if node in all_nodes:
            target_uri = node
        else:
            exact = [uri for uri, data in all_nodes.items() if data["label"].lower() == node.lower()]
            if len(exact) == 1:
                target_uri = exact[0]
            elif len(exact) > 1:
                raise ValueError(f"Multiple nodes with label '{node}': {[all_nodes[u]['label'] for u in exact]}")
            else:
                partial = [uri for uri, data in all_nodes.items() if node.lower() in data["label"].lower()]
                if len(partial) == 1:
                    target_uri = partial[0]
                elif len(partial) > 1:
                    raise ValueError(f"Partial label '{node}' matches multiple nodes: {[all_nodes[u]['label'] for u in partial]}")
                else:
                    raise ValueError(f"No node found matching '{node}'.")

        # Collect the target node + every node directly connected to it
        connected_uris: set[str] = {target_uri}
        connected_edges: list[tuple[str, str, str]] = []
        for s_id, o_id, p_label in all_edges:
            if s_id == target_uri or o_id == target_uri:
                connected_uris.add(s_id)
                connected_uris.add(o_id)
                connected_edges.append((s_id, o_id, p_label))

        if format == "html":
            self._export_node_html(target_uri, connected_uris, connected_edges, all_nodes, path)
        elif format in ("png", "svg"):
            self._export_node_static(target_uri, connected_uris, connected_edges, all_nodes, path, format)
        else:
            raise ValueError(f"Unsupported format '{format}'. Use 'html', 'png', or 'svg'.")

    def _export_node_html(
        self,
        target_uri: str,
        connected_uris: set,
        connected_edges: list,
        all_nodes: dict,
        path: Union[str, Path],
    ) -> None:
        """Render the node neighbourhood to an interactive pyvis HTML file."""
        try:
            from pyvis.network import Network
        except ImportError:
            raise ImportError("HTML export requires pyvis. Install with `pip install pyvis`.")

        net = Network(height="95vh", width="100%", directed=True, bgcolor="#1a1a2e", font_color="white")
        net.set_options("""{
            "physics": {
                "solver": "forceAtlas2Based",
                "forceAtlas2Based": {
                    "gravitationalConstant": -80,
                    "centralGravity": 0.01,
                    "springLength": 180,
                    "springConstant": 0.06,
                    "damping": 0.5,
                    "avoidOverlap": 0.8
                },
                "stabilization": { "iterations": 300 }
            },
            "edges": {
                "arrows": { "to": { "enabled": true, "scaleFactor": 0.6 } },
                "color": { "inherit": false, "color": "#7777aa" },
                "smooth": { "type": "continuous" },
                "width": 1.5,
                "font": { "size": 11, "color": "#ccccdd", "align": "middle" }
            },
            "nodes": {
                "shape": "box",
                "borderWidth": 1.5,
                "font": { "size": 13, "face": "arial", "color": "white" },
                "margin": 10
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 100,
                "navigationButtons": true,
                "keyboard": true
            }
        }""")

        uri_to_id: dict[str, int] = {}
        for i, uri_str in enumerate(connected_uris):
            data = all_nodes[uri_str]
            border_width = 3 if uri_str == target_uri else 1.5
            uri_to_id[uri_str] = i
            net.add_node(
                i,
                label=data["label"],
                title=data["title"],
                color={"background": data["color"], "border": "white" if uri_str == target_uri else data["color"]},
                shape="box",
                borderWidth=border_width,
                borderWidthSelected=4,
                font={"color": "white", "size": 13},
            )

        for s_id, o_id, p_label in connected_edges:
            net.add_edge(uri_to_id[s_id], uri_to_id[o_id], title=p_label, label=p_label)

        net.save_graph(str(path))
        self._inject_legend_html(path)

    def _export_node_static(
        self,
        target_uri: str,
        connected_uris: set,
        connected_edges: list,
        all_nodes: dict,
        path: Union[str, Path],
        fmt: str,
    ) -> None:
        """
        Render a static hierarchical PNG or SVG diagram using graphviz DOT layout.
        Requires: pip install graphviz  +  Graphviz binaries (https://graphviz.org/download/)
        """
        try:
            import graphviz as gv
        except ImportError:
            raise ImportError(
                "PNG/SVG export requires the graphviz Python package and Graphviz binaries.\n"
                "  pip install graphviz\n"
                "  Download Graphviz from https://graphviz.org/download/"
            )

        # Map URI → safe DOT node ID (URIs contain characters that break DOT syntax)
        uri_to_id = {uri: f"n{i}" for i, uri in enumerate(connected_uris)}

        dot = gv.Digraph(
            engine="dot",
            graph_attr={
                "rankdir": "TB",
                "bgcolor": "#1a1a2e",
                "fontname": "Arial",
                "splines": "ortho",
                "nodesep": "0.8",
                "ranksep": "1.2",
                "pad": "0.6",
            },
            node_attr={
                "shape": "box",
                "style": "filled,rounded",
                "fontname": "Arial",
                "fontcolor": "white",
                "fontsize": "13",
                "margin": "0.2,0.12",
            },
            edge_attr={
                "color": "#7777aa",
                "fontcolor": "#ccccdd",
                "fontname": "Arial",
                "fontsize": "11",
                "arrowsize": "0.7",
            },
        )

        # Group nodes by XDM type into same-rank subgraphs so the DOT layout
        # rank=same subgraphs fix the row in DOT layout.
        # Dataset shares r0 with Class (top-level concepts).
        # Identity shares r2 with FieldGroup so it appears as a side branch
        # of Schema, visually separate from the XDM composition branch.
        type_ranks = {
            str(self.SCHEMA["class"]):   "r0",
            str(DCAT.Dataset):           "r0",
            str(self.SCHEMA.schema):     "r1",
            str(self.SCHEMA.fieldgroup): "r2",
            str(self.SCHEMA.datatype):   "r3",
        }
        rank_groups: dict[str, list[str]] = {}
        for uri in connected_uris:
            data = all_nodes[uri]
            rk = "r2" if data.get("is_identity") else type_ranks.get(data.get("type_uri", ""), "r1")
            rank_groups.setdefault(rk, []).append(uri_to_id[uri])

        for uri in connected_uris:
            data = all_nodes[uri]
            is_target = uri == target_uri
            dot.node(
                uri_to_id[uri],
                label=data["label"],
                fillcolor=data["color"],
                color="white" if is_target else data["color"],
                penwidth="3.0" if is_target else "1.0",
            )

        for s, o, label in connected_edges:
            dot.edge(uri_to_id[s], uri_to_id[o], label=f"  {label}  ")

        for rk in sorted(rank_groups):
            with dot.subgraph() as sg:
                sg.attr(rank="same")
                for nid in rank_groups[rk]:
                    sg.node(nid)

        # Legend as a sink cluster so it sits below the main graph
        legend_entries = [
            ("Class",       "#9b59b6"),
            ("Schema",      "#5b9bd5"),
            ("Field group", "#70ad47"),
            ("Datatype",    "#ffc000"),
            ("Dataset",     "#ed7d31"),
            ("Identity",    "#e74c3c"),
        ]
        with dot.subgraph(name="cluster_legend") as leg:
            leg.attr(
                rank="sink",
                label="Node types",
                fontcolor="white",
                color="#555577",
                style="filled",
                fillcolor="#252540",
                fontname="Arial",
                fontsize="11",
            )
            prev = None
            for lbl, color in legend_entries:
                lid = f"leg_{lbl.replace(' ', '_')}"
                leg.node(
                    lid, label=lbl, fillcolor=color, fontcolor="white",
                    style="filled,rounded", shape="box",
                    fontname="Arial", fontsize="11",
                    width="1.2", height="0.35", margin="0.1,0.05",
                    color=color,
                )
                if prev:
                    leg.edge(prev, lid, style="invis")
                prev = lid

        path = Path(path)
        dot.format = fmt
        dot.render(outfile=str(path), cleanup=True)

