from ast import arg
from matplotlib.pyplot import table
import aepp
from aepp import synchronizer, schema, schemamanager, fieldgroupmanager, datatypemanager, identity, queryservice,catalog,flowservice
import argparse, cmd, shlex, json
from functools import wraps
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from pathlib import Path
from io import FileIO
import pandas as pd
from datetime import datetime
import urllib.parse

# --- 1. The Decorator (The Gatekeeper) ---
def login_required(f):
    """Decorator to block commands if not logged in."""
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'config') or self.config is None:
            print("(!) Access Denied: You must setup config first.")
            return
        return f(self, *args, **kwargs)
    return wrapper

console = Console()

# --- 2. The Interactive Shell ---
class ServiceShell(cmd.Cmd):
    def __init__(self, **kwargs):
        super().__init__()
        self.config = None
        self.connectInstance = True
        config_path = Path(kwargs.get("config_file"))
        if not config_path.is_absolute():
            config_path = Path.cwd() / config_path
        if config_path.exists() and kwargs.get("config_file") is not None:
            dict_config = json.load(FileIO(config_path))
            self.sandbox = kwargs.get("sandbox",dict_config.get("sandbox-name","prod"))
            self.secret = dict_config.get("secret",kwargs.get("secret"))
            self.org_id = dict_config.get("org_id",kwargs.get("org_id"))
            self.client_id = dict_config.get("client_id",kwargs.get("client_id"))
            self.scopes = dict_config.get("scopes",kwargs.get("scopes"))
        else:
            self.sandbox = kwargs.get("sandbox","prod")
            self.secret = kwargs.get("secret")
            self.org_id = kwargs.get("org_id")
            self.client_id = kwargs.get("client_id")
            self.scopes = kwargs.get("scopes")
        self.connectInstance = True
        if self.sandbox is not None and self.secret is not None and self.org_id is not None and self.client_id is not None and self.scopes is not None:
            print("Configuring connection...")
            self.config = aepp.configure(
                connectInstance=self.connectInstance,
                sandbox=self.sandbox,
                secret=self.secret,
                org_id=self.org_id,
                client_id=self.client_id,
                scopes=self.scopes
            )
            self.prompt = f"{self.config.sandbox}> "
            console.print(Panel(f"Connected to [bold green]{self.sandbox}[/bold green]", style="blue"))
        
    # # --- Commands ---
    def do_config(self, arg):
        """connect to an AEP instance"""
        parser = argparse.ArgumentParser(prog='config', add_help=True)
        parser.add_argument("-sx", "--sandbox", help="Auto-login sandbox")
        parser.add_argument("-s", "--secret", help="Secret")
        parser.add_argument("-o", "--org_id", help="Auto-login org ID")
        parser.add_argument("-sc", "--scopes", help="Scopes")
        parser.add_argument("-cid", "--client_id", help="Auto-login client ID")
        parser.add_argument("-cf", "--config_file", help="Path to config file", default=None)
        args = parser.parse_args(shlex.split(arg))
        if args.config_file:
            mypath = Path.cwd()
            dict_config = json.load(FileIO(mypath / Path(args.config_file)))
            self.sandbox = args.sandbox if args.sandbox else dict_config.get("sandbox-name",args.sandbox)
            self.secret = dict_config.get("secret",args.secret)
            self.org_id = dict_config.get("org_id",args.org_id)
            self.client_id = dict_config.get("client_id",args.client_id)
            self.scopes = dict_config.get("scopes",args.scopes)
            self.connectInstance = True
        else:
            if args.sandbox: self.sandbox = args.sandbox
            if args.secret: self.secret = args.secret
            if args.org_id: self.org_id = args.org_id
            if args.scopes: self.scopes = args.scopes
            if args.client_id: self.client_id = args.client_id
        console.print("Configuring connection...", style="blue")
        self.config = aepp.configure(
            connectInstance=self.connectInstance,
            sandbox=self.sandbox,
            secret=self.secret,
            org_id=self.org_id,
            client_id=self.client_id,
            scopes=self.scopes
        )
        console.print(Panel(f"Connected to [bold green]{self.sandbox}[/bold green]", style="blue"))
        self.prompt = f"{self.config.sandbox}> "
        return 

    def do_change_sandbox(self, args):
        """Change the current sandbox after configuration"""
        parser = argparse.ArgumentParser(prog='change sandbox', add_help=True)
        parser.add_argument("sandbox", help="sandbox name to switch to")
        args = parser.parse_args(shlex.split(args))
        self.sandbox = args.sandbox if args.sandbox else console.print(Panel("(!) Please provide a sandbox name using -sx or --sandbox", style="red"))
        if self.config is not None:
            if args.sandbox:
                self.config.setSandbox(args.sandbox)
                self.prompt = f"{self.config.sandbox}> "
                console.print(Panel(f"Sandbox changed to: [bold green]{self.config.sandbox}[/bold green]", style="blue"))
        else:
            console.print(Panel("(!) You must configure the connection first using the 'config' command.", style="red"))
    
    
    @login_required
    def do_get_schemas(self, args):
        """List all schemas in the current sandbox"""
        parser = argparse.ArgumentParser(prog='get_schemas', add_help=True)
        parser.add_argument("-sv", "--save",help="Save schemas to CSV file")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            schemas = aepp_schema.getSchemas()
            if len(schemas) > 0:
                if args.save:
                    df_schemas = pd.DataFrame(schemas)
                    df_schemas.to_csv(f"{self.config.sandbox}_schemas.csv", index=False)
                    console.print(f"Schemas exported to {self.config.sandbox}_schemas.csv", style="green")
                table = Table(title=f"Schemas in Sandbox: {self.config.sandbox}")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Version", style="green")
                for sch in schemas:
                    table.add_row(
                        sch.get("meta:altId","N/A"),
                        sch.get("title","N/A"),
                        str(sch.get("version","N/A")),
                    )
                console.print(table)
            else:
                console.print("(!) No schemas found.", style="red")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return

    @login_required
    def do_get_ups_schemas(self, args):
        """List all schemas enabled for Profile in the current sandbox"""
        parser = argparse.ArgumentParser(prog='get_schemas_enabled', add_help=True)
        parser.add_argument("-sv", "--save",help="Save enabled schemas to CSV file")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            union_schemas = aepp_schema.getUnions()
            schemas = aepp_schema.getSchemas()
            enabled_schemas = []
            for union in union_schemas:
                for member in union.get("meta:extends",[]):
                    if 'schema' in member:
                        enabled_schemas.append(member)
            list_enabled_schemas = []
            list_enabled_schemas = [sc for sc in schemas if sc.get("$id") in enabled_schemas]
            if len(list_enabled_schemas) > 0:
                if args.save:
                    df_schemas = pd.DataFrame(list_enabled_schemas)
                    df_schemas.to_csv(f"{self.config.sandbox}_enabled_schemas.csv", index=False)
                    console.print(f"Enabled Schemas exported to {self.config.sandbox}_enabled_schemas.csv", style="green")
                table = Table(title=f"Enabled Schemas in Sandbox: {self.config.sandbox}")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Version", style="green")
                for sch in list_enabled_schemas:
                    table.add_row(
                        sch.get("meta:altId","N/A"),
                        sch.get("title","N/A"),
                        str(sch.get("version","N/A")),
                    )
                console.print(table)
            else:
                console.print("(!) No enabled schemas found.", style="red")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    @login_required
    def do_get_ups_fieldgroups(self, args):
        """List all field groups enabled for Profile in the current sandbox"""
        parser = argparse.ArgumentParser(prog='get_fieldgroups_enabled', add_help=True)
        parser.add_argument("-sv", "--save",help="Save enabled field groups to CSV file")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            union_schemas = aepp_schema.getUnions()
            fgs = aepp_schema.getFieldGroups()
            enabled_fgs = []
            for union in union_schemas:
                for member in union.get("meta:extends",[]):
                    if 'mixins' in member:
                        enabled_fgs.append(member)
            list_enabled_fgs = []
            list_enabled_fgs = [f for f in fgs if f.get("$id") in enabled_fgs]
            if len(list_enabled_fgs) > 0:
                if args.save:
                    df_fgs = pd.DataFrame(list_enabled_fgs)
                    df_fgs.to_csv(f"{self.config.sandbox}_enabled_field_groups.csv", index=False)
                    console.print(f"Enabled Field Groups exported to {self.config.sandbox}_enabled_field_groups.csv", style="green")
                table = Table(title=f"Enabled Field Groups in Sandbox: {self.config.sandbox}")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Version", style="green")
                for sch in list_enabled_fgs:
                    table.add_row(
                        sch.get("meta:altId","N/A"),
                        sch.get("title","N/A"),
                        str(sch.get("version","N/A")),
                    )
                console.print(table)
            else:
                console.print("(!) No enabled field groups found.", style="red")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_profile_schemas(self,args):
        """Get the current profile schema"""
        parser = argparse.ArgumentParser(prog='get_schemas_enabled', add_help=True)
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            profile_schemas = aepp_schema.getSchemas(classFilter="https://ns.adobe.com/xdm/context/profile")
            if profile_schemas:
                table = Table(title=f"Profile Schemas in Sandbox: {self.config.sandbox}")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Version", style="green")
                for sch in profile_schemas:
                    table.add_row(
                        sch.get("meta:altId","N/A"),
                        sch.get("title","N/A"),
                        str(sch.get("version","N/A")),
                    )
                console.print(table)
            else:
                console.print("(!) No profile schemas found.", style="red")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_union_profile_json(self,args):
        """Get the current Profile union schema"""
        parser = argparse.ArgumentParser(prog='get_union_profile', add_help=True)
        try:
            args = parser.parse_args(shlex.split(args))
            profile_union = schemamanager.SchemaManager('https://ns.adobe.com/xdm/context/profile__union',config=self.config)
            data = profile_union.to_dict()
            with open(f"{self.config.sandbox}_profile_union_schema.json", 'w') as f:
                json.dump(data, f, indent=4)
            console.print(f"Profile Union Schema exported to {self.config.sandbox}_profile_union_schema.json", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_union_profile_csv(self,args):
        """Get the current Profile union schema"""
        parser = argparse.ArgumentParser(prog='get_union_profile', add_help=True)
        parser.add_argument("-f","--full",default=False,help="Get full schema information with all details",type=bool)
        try:
            args = parser.parse_args(shlex.split(args))
            profile_union = schemamanager.SchemaManager('https://ns.adobe.com/xdm/context/profile__union',config=self.config)
            df = profile_union.to_dataframe(full=args.full)
            df.to_csv(f"{self.config.sandbox}_profile_union_schema.csv", index=False)
            console.print(f"Profile Union Schema exported to {self.config.sandbox}_profile_union_schema.csv", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_union_event_json(self,args):
        """Get the current Experience Event union schema"""
        parser = argparse.ArgumentParser(prog='get_union_event', add_help=True)
        try:
            args = parser.parse_args(shlex.split(args))
            event_union = schemamanager.SchemaManager('https://ns.adobe.com/xdm/context/experienceevent__union',config=self.config)
            data = event_union.to_dict()
            with open(f"{self.config.sandbox}_event_union_schema.json", 'w') as f:
                json.dump(data, f, indent=4)
            console.print(f"Event Union Schema exported to {self.config.sandbox}_event_union_schema.json", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_union_event_csv(self,args):
        """Get the current Experience Event union schema"""
        parser = argparse.ArgumentParser(prog='get_union_event', add_help=True)
        parser.add_argument("-f","--full",default=False,help="Get full schema information with all details",type=bool)
        try:
            args = parser.parse_args(shlex.split(args))
            event_union = schemamanager.SchemaManager('https://ns.adobe.com/xdm/context/experienceevent__union',config=self.config)
            df = event_union.to_dataframe(full=args.full)
            df.to_csv(f"{self.config.sandbox}_event_union_schema.csv", index=False)
            console.print(f"Event Union Schema exported to {self.config.sandbox}_event_union_schema.csv", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_event_schemas(self,args):
        """Get the current Experience Event schemas"""
        parser = argparse.ArgumentParser(prog='get_event_schemas', add_help=True)
        parser.add_argument("-sv", "--save",help="Save event schemas to CSV file")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            event_schemas = aepp_schema.getSchemas(classFilter="https://ns.adobe.com/xdm/context/experienceevent")
            if args.save:
                df_schemas = pd.DataFrame(event_schemas)
                df_schemas.to_csv(f"{self.config.sandbox}_event_schemas.csv", index=False)
                console.print(f"Event Schemas exported to {self.config.sandbox}_event_schemas.csv", style="green")
            if event_schemas:
                table = Table(title=f"Event Schemas in Sandbox: {self.config.sandbox}")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Version", style="green")
                for sch in event_schemas:
                    table.add_row(
                        sch.get("meta:altId","N/A"),
                        sch.get("title","N/A"),
                        str(sch.get("version","N/A")),
                    )
                console.print(table)
            else:
                console.print("(!) No event schemas found.", style="red")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_union_event_json(self,args):
        """Get the current Experience Event union schema"""
        parser = argparse.ArgumentParser(prog='get_union_event', add_help=True)
        try:
            args = parser.parse_args(shlex.split(args))
            event_union = schemamanager.SchemaManager('https://ns.adobe.com/xdm/context/experienceevent__union',config=self.config)
            data = event_union.to_dict()
            with open(f"{self.config.sandbox}_event_union_schema.json", 'w') as f:
                json.dump(data, f, indent=4)
            console.print(f"Event Union Schema exported to {self.config.sandbox}_event_union_schema.json", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
         

    @login_required
    def do_get_schema_xdm(self, arg):
        """Get schema JSON by name or ID"""
        parser = argparse.ArgumentParser(prog='get_schema_xdm', add_help=True)
        parser.add_argument("schema", help="Schema title, $id or alt:Id to retrieve")
        parser.add_argument("-f","--full",default=False,help="Get full schema with all details",type=bool)
        try:
            args = parser.parse_args(shlex.split(arg))
            aepp_schema = schema.Schema(config=self.config)
            schemas = aepp_schema.getSchemas()
            print(args.schema)
            ## chech if schema title is found
            if args.schema in [sch for sch in aepp_schema.data.schemas_altId.keys()]:
                schema_json = aepp_schema.getSchema(
                    schemaId=aepp_schema.data.schemas_altId[args.schema],
            )
            else:
                
                schema_json = aepp_schema.getSchema(
                    schemaId=args.schema
            )
            if 'title' in schema_json.keys():
                filename = f"{schema_json['title']}_xdm.json"
                with open(filename, 'w') as f:
                    json.dump(schema_json, f, indent=4)
                console.print(f"Schema '{args.schema}' saved to {filename}.", style="green")
            else:
                console.print(f"(!) Schema '{args.schema}' not found.", style="red")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_schema_csv(self, arg):
        """Get schema CSV by name or ID"""
        parser = argparse.ArgumentParser(prog='get_schema_csv', add_help=True)
        parser.add_argument("schema", help="Schema $id or alt:Id to retrieve")
        parser.add_argument("-f","--full",default=False,help="Get full schema information with all details",type=bool)
        try:
            args = parser.parse_args(shlex.split(arg))
            aepp_schema = schema.Schema(config=self.config)
            schemas = aepp_schema.getSchemas()
            ## chech if schema title is found
            if args.schema in [sch for sch in aepp_schema.data.schemas_altId.keys()]:
                my_schema_manager = schemamanager.SchemaManager(
                    schema=aepp_schema.data.schemas_altId[args.schema],
                    config=self.config
                )
                df = my_schema_manager.to_dataframe(full=args.full)
            else:
                my_schema_manager = schemamanager.SchemaManager(
                    schema=args.schema,
                    config=self.config
                )
            df = my_schema_manager.to_dataframe(full=args.full)
            df.to_csv(f"{my_schema_manager.title}_schema.csv", index=False)
            console.print(f"Schema exported to {my_schema_manager.title}_schema.csv", style="green")  
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_schema_json(self, args):
        """Get schema JSON by name or ID"""
        parser = argparse.ArgumentParser(prog='get_schema_json', add_help=True)
        parser.add_argument("schema", help="Schema $id or alt:Id to retrieve")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            schemas = aepp_schema.getSchemas()
            ## chech if schema title is found
            if args.schema in [sch for sch in aepp_schema.data.schemas_altId.keys()]:
                my_schema_manager = schemamanager.SchemaManager(
                    schema=aepp_schema.data.schemas_altId[args.schema],
                    config=self.config
                )
            else:
                my_schema_manager = schemamanager.SchemaManager(
                    schema=args.schema,
                    config=self.config
                )
            data = my_schema_manager.to_dict()
            with open(f"{my_schema_manager.title}.json", 'w') as f:
                json.dump(data, f, indent=4)
            console.print(f"Schema exported to {my_schema_manager.title}.json", style="green")  
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_fieldgroups(self, args):
        """List all field groups in the current sandbox"""
        parser = argparse.ArgumentParser(prog='get_fieldgroups', add_help=True)
        parser.add_argument("-sv", "--save",help="Save field groups to CSV file")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            fieldgroups = aepp_schema.getFieldGroups()
            if args.save:
                df_fgs = pd.DataFrame(fieldgroups)
                df_fgs.to_csv(f"{self.config.sandbox}_fieldgroups.csv",index=False)
                console.print(f"Field Groups exported to {self.config.sandbox}_fieldgroups.csv", style="green")
            if fieldgroups:
                table = Table(title=f"Field Groups in Sandbox: {self.config.sandbox}")
                table.add_column("altId", style="cyan")
                table.add_column("Title", style="magenta")
                for fg in fieldgroups:
                    table.add_row(
                        fg.get("meta:altId","N/A"),
                        fg.get("title","N/A"),
                    )
                console.print(table)
            else:
                console.print("(!) No field groups found.", style="red")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_fieldgroup_json(self, args):
        """Get field group JSON by name or ID"""
        parser = argparse.ArgumentParser(prog='get_fieldgroup_json', add_help=True)
        parser.add_argument("fieldgroup", help="Field Group name, $id or alt:Id to retrieve")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            fieldgroups = aepp_schema.getFieldGroups()
            ## chech if schema title is found
            if args.fieldgroup in [fg for fg in aepp_schema.data.fieldGroups_altId.keys()]:
                my_fieldgroup_manager = fieldgroupmanager.FieldGroupManager(
                    fieldgroup=aepp_schema.data.fieldGroups_altId[args.fieldgroup],
                    config=self.config
                )
            else:
                my_fieldgroup_manager = fieldgroupmanager.FieldGroupManager(
                    fieldgroup=args.fieldgroup,
                    config=self.config
                )
            data = my_fieldgroup_manager.to_dict()
            with open(f"{my_fieldgroup_manager.title}_fieldgroup.json", 'w') as f:
                json.dump(data, f, indent=4)
            console.print(f"Field Group exported to {my_fieldgroup_manager.title}_fieldgroup.json", style="green")  
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_fieldgroup_csv(self, args):
        """Get field group CSV by name or ID"""
        parser = argparse.ArgumentParser(prog='get_fieldgroup_csv', add_help=True)
        parser.add_argument("fieldgroup", help="Field Group name, $id or alt:Id to retrieve")
        parser.add_argument("-f","--full",default=False,help="Get full field group information with all details",type=bool)
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            fieldgroups = aepp_schema.getFieldGroups()
            ## chech if schema title is found
            if args.fieldgroup in [fg for fg in aepp_schema.data.fieldGroups_altId.keys()]:
                my_fieldgroup_manager = fieldgroupmanager.FieldGroupManager(
                    fieldgroup=aepp_schema.data.fieldGroups_altId[args.fieldgroup],
                    config=self.config
                )
            else:
                my_fieldgroup_manager = fieldgroupmanager.FieldGroupManager(
                    fieldgroup=args.fieldgroup,
                    config=self.config
                )
            df = my_fieldgroup_manager.to_dataframe(full=args.full)
            df.to_csv(f"{my_fieldgroup_manager.title}_fieldgroup.csv", index=False)
            console.print(f"Field Group exported to {my_fieldgroup_manager.title}_fieldgroup.csv", style="green")  
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
        
    def do_get_datatypes(self, args):
        """List all data types in the current sandbox"""
        parser = argparse.ArgumentParser(prog='get_datatypes', add_help=True)
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            datatypes = aepp_schema.getDataTypes()
            if datatypes:
                table = Table(title=f"Data Types in Sandbox: {self.config.sandbox}")
                table.add_column("altId", style="cyan")
                table.add_column("Title", style="magenta")
                for dt in datatypes:
                    table.add_row(
                        dt.get("meta:altId","N/A"),
                        dt.get("title","N/A"),
                    )
                console.print(table)
            else:
                console.print("(!) No data types found.", style="red")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_datatype_csv(self, args):
        """Get data type CSV by name or ID"""
        parser = argparse.ArgumentParser(prog='get_datatype_csv', add_help=True)
        parser.add_argument("datatype", help="Data Type name, $id or alt:Id to retrieve")
        parser.add_argument("-f","--full",default=False,help="Get full data type information with all details",type=bool)
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            datatypes = aepp_schema.getDataTypes()
            ## chech if schema title is found
            if args.datatype in [dt for dt in aepp_schema.data.dataTypes_altId.keys()]:
                my_datatype_manager = datatypemanager.DataTypeManager(
                    datatype=aepp_schema.data.dataTypes_altId[args.datatype],
                    config=self.config
                )
            else:
                my_datatype_manager = datatypemanager.DataTypeManager(
                    datatype=args.datatype,
                    config=self.config
                )
            df = my_datatype_manager.to_dataframe(full=args.full)
            df.to_csv(f"{my_datatype_manager.title}_datatype.csv", index=False)
            console.print(f"Data Type exported to {my_datatype_manager.title}_datatype.csv", style="green")  
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_datatype_json(self, args):
        """Get data type JSON by name or ID"""
        parser = argparse.ArgumentParser(prog='get_datatype_json', add_help=True)
        parser.add_argument("datatype", help="Data Type name, $id or alt:Id to retrieve")
        parser.add_argument("-f","--full",default=False,help="Get full data type information with all details",type=bool)
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            datatypes = aepp_schema.getDataTypes()
            ## chech if schema title is found
            if args.datatype in [dt for dt in aepp_schema.data.dataTypes_altId.keys()]:
                my_datatype_manager = datatypemanager.DataTypeManager(
                    datatype=aepp_schema.data.dataTypes_altId[args.datatype],
                    config=self.config
                )
            else:
                my_datatype_manager = datatypemanager.DataTypeManager(
                    datatype=args.datatype,
                    config=self.config
                )
            data = my_datatype_manager.to_dict()
            with open(f"{my_datatype_manager.title}_datatype.json", 'w') as f:
                json.dump(data, f, indent=4)
            console.print(f"Data Type exported to {my_datatype_manager.title}_datatype.json", style="green")  
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_enable_schema_for_ups(self, args):
        """Enable a schema for Profile"""
        parser = argparse.ArgumentParser(prog='enable_schema_for_ups', add_help=True)
        parser.add_argument("schema_id", help="Schema ID to enable for Profile")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_schema = schema.Schema(config=self.config)
            result = aepp_schema.enableSchemaForUPS(schemaId=args.schema_id)
            console.print(f"Schema '{args.schema_id}' enabled for Profile.", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_upload_fieldgroup_definition_csv(self,args):
        """Upload a field group definition from a CSV file"""
        parser = argparse.ArgumentParser(prog='upload_fieldgroup_definition_csv', add_help=True)
        parser.add_argument("csv_path", help="Path to the field group CSV file")
        parser.add_argument("-ts","--test",help="Test upload without uploading it to AEP",default=False,type=bool)
        try:
            args = parser.parse_args(shlex.split(args))
            myfg = fieldgroupmanager.FieldGroupManager(config=self.config)
            myfg.importFieldGroupDefinition(fieldgroup=args.csv_path)
            if args.test:
                data = myfg.to_dict()
                with open(f"test_{myfg.title}_fieldgroup.json", 'w') as f:
                    json.dump(data, f, indent=4)
                console.print(f"Field Group definition test exported to test_{myfg.title}_fieldgroup.json", style="green")
                console.print_json(data=data)
                return
            res = myfg.createFieldGroup()
            console.print(f"Field Group uploaded with ID: {res.get('meta:altId')}", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_upload_fieldgroup_definition_xdm(self,args):
        """Upload a field group definition from a JSON XDM file"""
        parser = argparse.ArgumentParser(prog='upload_fieldgroup_definition_xdm', add_help=True)
        parser.add_argument("xdm_path", help="Path to the field group JSON XDM file")
        parser.add_argument("-ts","--test",help="Test upload without uploading it to AEP",default=False,type=bool)
        try:
            args = parser.parse_args(shlex.split(args))
            with open(args.xdm_path, 'r') as f:
                xdm_data = json.load(f)
            myfg = fieldgroupmanager.FieldGroupManager(xdm_data,config=self.config)
            if args.test:
                data = myfg.to_dict()
                with open(f"test_{myfg.title}_fieldgroup.json", 'w') as f:
                    json.dump(data, f, indent=4)
                console.print(f"Field Group definition test exported to test_{myfg.title}_fieldgroup.json", style="green")
                console.print_json(data=data)
                return
            res = myfg.createFieldGroup()
            console.print(f"Field Group uploaded with ID: {res.get('meta:altId')}", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
        
    @login_required
    def do_get_datasets(self, args):
        """List all datasets in the current sandbox"""
        parser = argparse.ArgumentParser(prog='get_datasets', add_help=True)
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_cat = catalog.Catalog(config=self.config)
            datasets = aepp_cat.getDataSets(output='list')
            df_datasets = pd.DataFrame(datasets)
            df_datasets.to_csv(f"{self.config.sandbox}_datasets.csv",index=False)
            console.print(f"Datasets exported to {self.config.sandbox}_datasets.csv", style="green")
            table = Table(title=f"Datasets in Sandbox: {self.config.sandbox}")
            table.add_column("ID", style="white")
            table.add_column("Name", style="white",no_wrap=True)
            table.add_column("Created At", style="yellow")
            table.add_column("Data Ingested", style="magenta")
            table.add_column("Data Type", style="red")
            for ds in datasets:
                table.add_row(
                    ds.get("id","N/A"),
                    ds.get("name","N/A"),
                    datetime.fromtimestamp(ds.get("created",1000)/1000).isoformat().split('T')[0],
                    str(ds.get("dataIngested",False)),
                    ds.get("classification",{}).get("dataBehavior","unknown")
                )
            console.print(table)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_datasets_infos(self, args):
        """List all datasets in the current sandbox"""
        parser = argparse.ArgumentParser(prog='get_datasets_infos', add_help=True)
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_cat = catalog.Catalog(config=self.config)
            datasets = aepp_cat.getDataSets()
            aepp_cat.data.infos.to_csv(f"{aepp_cat.sandbox}_datasets_infos.csv",index=False)
            console.print(f"Datasets infos exported to {aepp_cat.sandbox}_datasets_infos.csv", style="green")
            table = Table(title=f"Datasets in Sandbox: {self.config.sandbox}")
            table.add_column("ID", style="white")
            table.add_column("Name", style="white",no_wrap=True)
            table.add_column("Datalake_rows", style="blue")
            table.add_column("Datalake_storage", style="blue")
            table.add_column("UPS_rows", style="magenta")
            table.add_column("UPS_storage", style="magenta")
            for _, ds in aepp_cat.data.infos.iterrows():
                table.add_row(
                    ds.get("id","N/A"),
                    ds.get("name","N/A"),
                    str(ds.get("datalake_rows","N/A")),
                    str(ds.get("datalake_storageSize","N/A")),
                    str(ds.get("ups_rows","N/A")),
                    str(ds.get("ups_storageSize","N/A"))
                )
            console.print(table)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return

    @login_required
    def do_createDataset(self, args):
        """Create a new dataset in the current sandbox"""
        parser = argparse.ArgumentParser(prog='createDataset', add_help=True)
        parser.add_argument("dataset_name", help="Name of the dataset to create")
        parser.add_argument("schema_id", help="Schema ID to associate with the dataset")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_cat = catalog.Catalog(config=self.config,region=args.region)
            dataset_id = aepp_cat.createDataSet(dataset_name=args.dataset_name,schemaId=args.schema_id)
            console.print(f"Dataset '{args.dataset_name}' created with ID: {dataset_id[0]}", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_enable_dataset_for_ups(self, args):
        """Enable a dataset for Profile"""
        parser = argparse.ArgumentParser(prog='enable_dataset_for_ups', add_help=True)
        parser.add_argument("dataset", help="Dataset ID or Dataset Name to enable for Profile")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_cat = catalog.Catalog(config=self.config)
            datasets = aepp_cat.getDataSets(output='list')
            for ds in datasets:
                if ds.get("name","") == args.dataset or ds.get("id","") == args.dataset:
                    datasetId = ds.get("id")
            result = aepp_cat.enableDatasetProfile(datasetId=datasetId)
            console.print(f"Dataset '{datasetId}' enabled for Profile.", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return

    @login_required
    def do_get_identities(self, args):
        """List all identities in the current sandbox"""
        parser = argparse.ArgumentParser(prog='get_identities', add_help=True)
        parser.add_argument("-r","--region", help="Region to get identities from: 'ndl2' (default), 'va7', 'aus5', 'can2', 'ind2'", default='ndl2')
        parser.add_argument("-co","--custom_only",help="Get only custom identities", default=False,type=bool)
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_identity = identity.Identity(config=self.config,region=args.region)
            identities = aepp_identity.getIdentities(only_custom=args.custom_only)
            df_identites = pd.DataFrame(identities)
            df_identites.to_csv(f"{self.config.sandbox}_identities.csv",index=False)
            console.print(f"Identities exported to {self.config.sandbox}_identities.csv", style="green")
            table = Table(title=f"Identities in Sandbox: {self.config.sandbox}")
            table.add_column("Code", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("id", style="white")
            table.add_column("namespaceType", style="green")
            for _, iden in df_identites.iterrows():
                table.add_row(
                    iden.get("code","N/A"),
                    iden.get("name","N/A"),
                    str(iden.get("id","N/A")),
                    iden.get("namespaceType","N/A"),
                )
            console.print(table)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_flows(self, args):
        """List flows in the current sandbox based on parameters provided. By default, list all sources and destinations."""
        parser = argparse.ArgumentParser(prog='get_flows', add_help=True)
        parser.add_argument("-i","--internal_flows",help="Get internal flows", default=False,type=bool)
        parser.add_argument("-adv","--advanced",help="Get advanced information about runs", default=False,type=bool)
        parser.add_argument("-ao","--active_only",help="Get only active flows during that time period", default=True,type=bool)
        parser.add_argument("-mn","--minutes", help="Timeframe in minutes to check for errors, default 0", default=0,type=int)
        parser.add_argument("-H","--hours", help="Timeframe in hours to check for errors, default 0", default=0,type=int)
        parser.add_argument("-d","--days", help="Timeframe in days to check for errors, default 0", default=0,type=int)
        try:
            args = parser.parse_args(shlex.split(args))
            timetotal_minutes = args.minutes + (args.hours * 60) + (args.days * 1440)
            if timetotal_minutes == 0:
                timetotal_minutes = 1440  # default to last 24 hours
            timereference = int(datetime.now().timestamp()*1000) - (timetotal_minutes * 60 * 1000)
            aepp_flow = flowservice.FlowService(config=self.config)
            flows = aepp_flow.getFlows(n_results="inf")
            runs = None
            if args.active_only:
                runs = aepp_flow.getRuns(n_results="inf",prop=[f'metrics.durationSummary.startedAtUTC>{timereference}'])
                active_flow_ids = list(set([run.get("flowId") for run in runs]))            
            source_flows = aepp_flow.getFlows(onlySources=True)
            destinations_flows = aepp_flow.getFlows(onlyDestinations=True)
            list_source_ids = [f.get("id") for f in source_flows]
            list_destination_ids = [f.get("id") for f in destinations_flows]
            if args.internal_flows:
                list_flows = flows
            else:
                list_flows = source_flows + destinations_flows
            if args.active_only:
                list_flows = [fl for fl in list_flows if fl.get("id") in active_flow_ids]
            if args.advanced:
                if runs is None:
                    runs = aepp_flow.getRuns(n_results="inf",prop=[f'metrics.durationSummary.startedAtUTC>{timereference}'])
                runs_by_flow = {}
                for run in runs:
                    flow_id = run.get("flowId")
                    if flow_id not in runs_by_flow:
                        runs_by_flow[flow_id] = {
                            "total_runs": 0,
                            "failed_runs": 0,
                            "success_runs": 0,
                            "partial_success":0,
                        }
                    runs_by_flow[flow_id]["total_runs"] += 1
                    status = run.get("metrics",{}).get("statusSummary",{}).get("status","unknown")
                    if status == "failed":
                        runs_by_flow[flow_id]["failed_runs"] += 1
                    elif status == "success":
                        runs_by_flow[flow_id]["success_runs"] += 1
                    elif status == "partialSuccess":
                        runs_by_flow[flow_id]["partial_success"] += 1
            report_flows = []
            for fl in list_flows:
                obj = {
                    "id": fl.get("id","N/A"),
                    "name": fl.get("name","N/A"),
                    "created": fl.get("createdAt",1000),
                    "flowSpec": fl.get("flowSpec",{}).get('id','N/A'),
                    "sourceConnectionId": fl.get("sourceConnectionIds",["N/A"])[0],
                    "targetConnectionId": fl.get("targetConnectionIds",["N/A"])[0],
                    "connectionSpec": fl.get("inheritedAttributes",{}).get('sourceConnections',[{}])[0].get('connectionSpec',{}).get('id'),
                    "type": fl.get("inheritedAttributes",{}).get('properties','N/A'),
                }
                if obj.get("id") in list_source_ids:
                    obj["type"] = "Source"
                elif obj.get("id") in list_destination_ids:
                    obj["type"] = "Destination"
                else:
                    obj["type"] = "Internal"
                if fl.get('transformations') and len(fl.get('transformations')) > 0:
                    obj["Transformation"] = True
                else:
                    obj["Transformation"] = False
                if args.advanced:
                    run_info = runs_by_flow.get(obj.get("id"),{"total_runs":0,"failed_runs":0,"success_runs":0})
                    obj["Total Runs"] = run_info.get("total_runs",0)
                    obj["Failed Runs"] = run_info.get("failed_runs",0)
                    obj["Successful Runs"] = run_info.get("success_runs",0)
                    obj["Partial Success Runs"] = run_info.get("partial_success",0)
                report_flows.append(obj)
            df_flows = pd.DataFrame(list_flows)
            filename = f"{self.config.sandbox}_flows_{timereference/1000}"
            if args.advanced:
                filename = f"{filename}_advanced"
            if args.active_only == False:
                filename = f"{filename}_all"
            if args.internal_flows:
                filename = f"{filename}_internal"
            df_flows.to_csv(f"{filename}.csv",index=False)
            console.print(f"Flows exported to {filename}.csv", style="green")
            table = Table(title=f"Flows in Sandbox: {self.config.sandbox}")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Type", style="white")
            if args.advanced == False:
                table.add_column("Created", style="white")
                table.add_column("Transformation", style="white")
                table.add_column("Flow Spec", style="white")
                table.add_column("Source Conn ID", style="white")
                table.add_column("Target Conn ID", style="white")
            if args.advanced:
                table.add_column("Total Runs", style="blue")
                table.add_column("Successful", style="green")
                table.add_column("Failed", style="red")
                table.add_column("Partial Success", style='orange1')
                table.add_column("Success Rate", style="green")
                table.add_column("Failure Rate", style="red")
                
            for fl in report_flows:
                row_data = []
                if args.advanced:
                    if fl.get("Failed Runs",0) > 0:
                        colorStart = "[red]"
                        colorEnd = "[/red]"
                    else:
                        colorStart = "[green]"
                        colorEnd = "[/green]"
                else:
                    colorStart = ""
                    colorEnd = ""
                row_data = [
                    f"{colorStart}{fl.get('id','N/A')}{colorEnd}",
                    f"{colorStart}{fl.get('name','N/A')}{colorEnd}",
                    f"{colorStart}{fl.get('type','N/A')}{colorEnd}",
                ]
                if args.advanced == False:
                    row_data.extend([
                        f"{colorStart}{datetime.fromtimestamp(fl.get('created',1000)/1000).isoformat().split('T')[0]}{colorEnd}",
                        f"{colorStart}{str(fl.get('Transformation', False))}{colorEnd}",
                        f"{colorStart}{fl.get('flowSpec','N/A')}{colorEnd}",
                        f"{colorStart}{fl.get('sourceConnectionId','N/A')}{colorEnd}",
                        f"{colorStart}{fl.get('targetConnectionId','N/A')}{colorEnd}",
                    ])
                if args.advanced:
                    total_runs = fl.get("Total Runs", 0)
                    successful_runs = fl.get("Successful Runs", 0)
                    failed_runs = fl.get("Failed Runs", 0)
                    partial_success = fl.get('Partial Success Runs',0)
                    if partial_success>0:
                        partialColorStart = "[orange1]"
                        partialColorEnd = "[/orange1]"
                    else:
                        partialColorStart = colorStart
                        partialColorEnd = colorEnd
                    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
                    failure_rate = (failed_runs / total_runs * 100) if total_runs > 0 else 0
                    row_data.extend([
                        f"{colorStart}{str(total_runs)}{colorEnd}",
                        f"{colorStart}{str(successful_runs)}{colorEnd}",
                        f"{colorStart}{str(failed_runs)}{colorEnd}",
                        f"{partialColorStart}{str(partial_success)}{partialColorEnd}",
                        f"{colorStart}{success_rate:.0f}%{colorEnd}",
                        f"{colorStart}{failure_rate:.0f}%{colorEnd}"
                    ])
                table.add_row(*row_data)
            console.print(table)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_flow_errors(self,args):
        """Get errors for a specific flow, saving it in a JSON file for specific timeframe, default last 24 hours."""
        parser = argparse.ArgumentParser(prog='get_flow_errors', add_help=True)
        parser.add_argument("flow_id", help="Flow ID to get errors for")
        parser.add_argument("-mn","--minutes", help="Timeframe in minutes to check for errors, default 0", default=0,type=int)
        parser.add_argument("-H","--hours", help="Timeframe in hours to check for errors, default 0", default=0,type=int)
        parser.add_argument("-d","--days", help="Timeframe in days to check for errors, default 0", default=0,type=int)
        try:
            args = parser.parse_args(shlex.split(args))
            timetotal_minutes = args.minutes + (args.hours * 60) + (args.days * 1440)
            if timetotal_minutes == 0:
                timetotal_minutes = 1440  # default to last 24 hours
            aepp_flow = flowservice.FlowService(config=self.config)
            timereference = int(datetime.now().timestamp()*1000) - (timetotal_minutes * 60 * 1000)
            failed_runs = aepp_flow.getRuns(prop=['metrics.statusSummary.status==failed',f'flowId=={args.flow_id}',f'metrics.durationSummary.startedAtUTC>{timereference}'],n_results="inf")
            with open(f"flow_{args.flow_id}_errors.json", 'w') as f:
                json.dump(failed_runs, f, indent=4)
            console.print(f"Flow errors exported to flow_{args.flow_id}_errors.json", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_create_dataset_http_source(self,args):
        """Create an HTTP Source connection for a specific dataset, XDM compatible data only."""
        parser = argparse.ArgumentParser(prog='do_create_dataset_http_source', add_help=True)
        parser.add_argument("dataset", help="Name or ID of the Dataset Source connection to create")
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_cat = catalog.Catalog(config=self.config)
            datasets = aepp_cat.getDataSets(output='list')
            if args.dataset in [ds.get("name","") for ds in datasets]:
                for ds in datasets:
                    if ds.get("name","") == args.dataset:
                        datasetId = ds.get("id")
            else:
                datasetId = args.dataset
            flw = flowservice.FlowService(config=self.config)
            res = flw.createFlowStreaming(datasetId=datasetId)
            console.print(f"HTTP Source connection created with Flow ID: {res.get('flow',{}).get('id')}", style="green")
            source_id = res.get('source_connection_id',{}).get('id')
            sourceConnection = flw.getSourceConnection(sourceConnectionId=source_id)
            console.print(f"Endpoint URL: {sourceConnection.get('params',{}).get('inletUrl')}", style="green")
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
    
    @login_required
    def do_get_DLZ_credential(self,args):
        """Get Data Lake Zone credential for the current sandbox"""
        parser = argparse.ArgumentParser(prog='get_DLZ_credential', add_help=True)
        parser.add_argument("type",nargs='?',help="Type of credential to retrieve: 'user_drop_zone' or 'dlz_destination'",default="user_drop_zone")
        try:
            args = parser.parse_args(shlex.split(args))
            flw = flowservice.FlowService(config=self.config)
            cred = flw.getLandingZoneCredential(dlz_type=args.type)
            console.print(f"Data Lake Zone Credential for sandbox '{self.config.sandbox}':", style="green")
            console.print_json(data=cred)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return

    @login_required
    def do_get_queries(self, args):
        """List top 1000 queries in the current sandbox for the last 24 hours by default, optionally filtered by dataset ID"""
        parser = argparse.ArgumentParser(prog='get_queries', add_help=True)
        parser.add_argument("-ds","--dataset", help="Dataset ID to filter queries", default=None)
        parser.add_argument("-st","--state", help="State to filter queries (running, completed, failed)", default=None)
        parser.add_argument("-H","--hours", help="Timeframe in hours to check for errors, default 0", default=0,type=int)
        parser.add_argument("-d","--days", help="Timeframe in days to check for errors, default 0", default=0,type=int)
        parser.add_argument("-mn","--minutes", help="Timeframe in minutes to check for errors, default 0", default=0,type=int)  
        try:
            args = parser.parse_args(shlex.split(args))
            timetotal_minutes = args.minutes + (args.hours * 60) + (args.days * 1440)
            if timetotal_minutes == 0:
                timetotal_minutes = 1440  # default to last 24 hours
            time_reference = int(datetime.now().timestamp()) - (timetotal_minutes * 60)
            time_reference_z = datetime.fromtimestamp(time_reference).isoformat() + 'Z'
            params = {'property':f'created>={time_reference_z}','orderBy':'-created'}
            if args.dataset:
                if params['property'] == '':
                    params['property'] = f'referenced_datasets=={args.dataset}'
                else:
                    params['property'] += f',referenced_datasets=={args.dataset}'
            if params['property'] == '':
                params = None
            else:
                params['property'] = urllib.parse.quote(params['property'])
            aepp_query = queryservice.QueryService(config=self.config)
            queries = aepp_query.getQueries(property=params['property'] if params else None, orderby=params['orderBy'])
            list_queries = []
            for q in queries:
                if q['client'] == "Adobe Query Service UI" or q["client"] == 'Generic PostgreSQL':
                    list_queries.append(q) 
            for q in list_queries:
                obj = {
                    "id": q.get("id","N/A"),
                    "created": q.get("created"),
                    "client": q.get("client","N/A"),
                    "elapsedTime": q.get("elapsedTime","N/A"),
                    "userId": q.get("userId","N/A"),
                }
                list_queries.append(obj)
            df_queries = pd.DataFrame(list_queries)
            df_queries.to_csv(f"{self.config.sandbox}_queries.csv",index=False)
            console.print(f"Queries exported to {self.config.sandbox}_queries.csv", style="green")
            table = Table(title=f"Queries in Sandbox: {self.config.sandbox}")
            table.add_column("ID", style="cyan")
            table.add_column("Created", style="yellow")
            table.add_column("Client", style="white")
            table.add_column("Elapsed Time (ms)", style="white")
            for q in queries:
                table.add_row(
                    q.get("id","N/A"),
                    q.get("created","N/A"),
                    q.get("client","N/A"),
                    str(q.get("elapsedTime","N/A"))
                )
            console.print(table)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return
        
    @login_required
    def do_query(self,args):
        """Execute a SQL query against the current sandbox"""
        parser = argparse.ArgumentParser(prog='query', add_help=True)
        parser.add_argument("sql_query", help="SQL query to execute",type=str)
        try:
            args = parser.parse_args(shlex.split(args))
            aepp_query = queryservice.QueryService(config=self.config)
            conn = aepp_query.connection()
            iqs2 = queryservice.InteractiveQuery2(conn)
            result:pd.DataFrame = iqs2.query(sql=args.sql_query)
            result.to_csv(f"query_result_{int(datetime.now().timestamp())}.csv", index=False)
            console.print(f"Query result exported to query_result_{int(datetime.now().timestamp())}.csv", style="green")
            console.print(result)
        except Exception as e:
            console.print(f"(!) Error: {str(e)}", style="red")
        except SystemExit:
            return


    @login_required
    def do_extractArtefacts(self,args):
        """extractArtefacts localfolder"""
        console.print("Extracting artefacts...", style="blue")
        parser = argparse.ArgumentParser(prog='extractArtefacts', description='Extract artefacts from AEP')
        parser.add_argument('-lf','--localfolder', help='Local folder to extract artefacts to', default='./extractions')
        parser.add_argument('-rg','--region', help='Region to extract artefacts from: "ndl2" (default), "va7", "aus5", "can2", "ind2"',default='ndl2')
        try:
            args = parser.parse_args(shlex.split(args))
            aepp.extractSandboxArtefacts(
                sandbox=self.config,
                localFolder=args.localfolder,
                region=args.region
            )
            console.print(Panel("Extraction completed!", style="green"))
        except SystemExit:
            return

    @login_required
    def do_extractArtefact(self,args):
        """extractArtefacts localfolder"""
        console.print("Extracting artefact...", style="blue")
        parser = argparse.ArgumentParser(prog='extractArtefact', description='Extract artefacts from AEP')
        parser.add_argument('artefact', help='artefact to extract (name or id): "schema","fieldgroup","datatype","descriptor","dataset","identity","mergepolicy","audience"')
        parser.add_argument('-at','--artefactType', help='artefact type ')
        parser.add_argument('-lf','--localfolder', help='Local folder to extract artefacts to',default='extractions')
        parser.add_argument('-rg','--region', help='Region to extract artefacts from: "ndl2" (default), "va7", "aus5", "can2", "ind2"',default='ndl2')
        
        try:
            args = parser.parse_args(shlex.split(args))
            aepp.extractSandboxArtefact(
                artefact=args.artefact,
                artefactType=args.artefactType,
                sandbox=self.config,
                localFolder=args.localfolder
            )
            console.print("Extraction completed!", style="green")
        except SystemExit:
            return

    @login_required
    def do_sync(self,args):
        """extractArtefacts localfolder"""
        console.print("Syncing artefact...", style="blue")
        parser = argparse.ArgumentParser(prog='extractArtefact', description='Extract artefacts from AEP')
        parser.add_argument('artefact', help='artefact to extract (name or id): "schema","fieldgroup","datatype","descriptor","dataset","identity","mergepolicy","audience"')
        parser.add_argument('-at','--artefactType', help='artefact type ')
        parser.add_argument('-t','--targets', help='target sandboxes')
        parser.add_argument('-lf','--localfolder', help='Local folder to extract artefacts to',default='extractions')
        parser.add_argument('-b','--baseSandbox', help='Base sandbox for synchronization')
        parser.add_argument('-rg','--region', help='Region to extract artefacts from: "ndl2" (default), "va7", "aus5", "can2", "ind2"',default='ndl2')
        parser.add_argument('-v','--verbose', help='Enable verbose output',default=True)
        try:
            args = parser.parse_args(shlex.split(args))
            if ',' in args.targets:
                args.targets = args.targets.split(',')
            else:
                args.targets = [args.targets]
            console.print("Initializing Synchronizor...", style="blue")
            if args.baseSandbox:
                synchronizor = synchronizer.Synchronizer(
                    config=self.config,
                    targets=args.targets,
                    region=args.region,
                    baseSandbox=args.baseSandbox,
                )
            elif args.localfolder:
                synchronizor = synchronizer.Synchronizer(
                    config=self.config,
                    targets=args.targets,
                    region=args.region,
                    localFolder=args.localfolder,
            )
            console.print("Starting Sync...", style="blue")
            synchronizor.syncComponent(
                component=args.artefact,
                componentType=args.artefactType,
                verbose=args.verbose
            )
            console.print("Sync completed!", style="green")
        except SystemExit:
            return
    
    
    def do_exit(self, args):
        """Exit the application"""
        console.print(Panel("Exiting...", style="blue"))
        return True  # Stops the loop

    def do_EOF(self, args):
        """Handle Ctrl+D"""
        console.print(Panel("Exiting...", style="blue"))
        return True

# --- 3. The Entry Point ---#

def main():
    # ARGPARSE: Handles the initial setup flags
    parser = argparse.ArgumentParser(description="Interactive Client Tool",add_help=True)
    
    # Optional: Allow passing user/pass via flags to skip the interactive login step
    parser.add_argument("-sx", "--sandbox", help="Auto-login sandbox")
    parser.add_argument("-s", "--secret", help="Secret")
    parser.add_argument("-o", "--org_id", help="Auto-login org ID")
    parser.add_argument("-sc", "--scopes", help="Scopes")
    parser.add_argument("-cid", "--client_id", help="Auto-login client ID")
    parser.add_argument("-cf", "--config_file", help="Path to config file", default=None)
    args = parser.parse_args() 
    shell = ServiceShell(**vars(args))
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        console.print(Panel("\nForce closing...", style="red"))

if __name__ == "__main__":
    main()