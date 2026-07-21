Once you have created your knowledge graph, you can start using it to enhance your applications and services.\
The main aspect of the Knowledge Graph is its usage with an AI model to provide more accurate and context-aware responses. By integrating your knowledge graph with AI, you can improve the performance of your applications in various ways.\
In this documentation, we will review the creation of the knowledge graph and how to use it with an AI model.

## Menu



## Generate Knowledge Graph
In order to generate the knowledge graph, 2 options are available:
- via the CLI, which allows you to create a knowledge graph from your data using a single command.
- via a notebook, which allows you to create a knowledge graph from your data using a step-by-step approach.

Both approach would require you to have access to AEP via API and have a configuration setup for the connection to the AEP API. The configuration setup is explained in some of the documentation: 
[aepp CLI getting Started](./get-started-cli.md#create-a-config-file-and-use-it-to-start-the-cli)
[aepp getting Started](./getting-started.md#create-a-developer-project)

### CLI approach 

The CLI approach is the easiest way to create a knowledge graph from your data. It allows you to create a knowledge graph from your data using a single command. The CLI approach is recommended for users who want to quickly create a knowledge graph from their data without having to write any code.

Once `python` and `aepp` are installed, and you have a configuration file ready to use.

```bash
python -m aepp.cli -cf my_config_file.json -sx prod
prod> build_graph -ex True ## build the graph and export it to a turtle file
```


### Notebook approach 

The notebook approach will allow you to better control the step of creation and the possibility to add nodes and edges to the knowledge graph. It is a more flexible approach, but it requires higher understanding of the python eco-system and the knowledge graph structure. The notebook approach is recommended for advanced users who want to have more control over the creation of the knowledge graph.

```py
import aepp
from aepp import knowledgegraph

prod = aepp.importConfigFile("my_config_file.json", sandbox="prod",connectInstance=True)

kn = knowledgegraph.KnowledgeGraph(config=prod)
graph = kn.buildGraph(detail=True, enabled=True)
```

If you want, you can add an additional literal nodes and predicates to any of the path that are existing in the knowledge graph. For example, if you want to add a new attribute to a path, you can use the `addPathAttribute` method. This method will allow you to add a new attribute to a path in the knowledge graph. 

```py
kn.addPathAttribute(path="_tenant.path.field", attributes={"my_attribute": "my_value"})
```

This makes it available for you to add additional information to the knowledge graph that is not available in the AEP instance. Once you have added the new attribute, you can export the knowledge graph to a turtle file.

```py
kn.exportTurtle(path=f"{prod.sandbox}.ttl")
```

## Prepare for usage

There are multiple ways to load a knowledge graph into your AI application. The most advanced users would be able to load the knowledge graph directly into their application using an API.\
However, for most users, who wants to work locally, I will provide a way to load the knowledge graph into a local environment via a simple and local MCP server, that you can connect to your AI application. 

**NOTE**: The MCP server will run locally, so it cannot be accessed by cloud applications. It means that the AI tools used in a browser or in a cloud environment will not be able to access the knowledge graph. If you want to use the knowledge graph with a cloud application, you will need to deploy the MCP server on a cloud server or use one of the cloud-based knowledge graph services available.

### Create a Folder for the Knowledge Graph 

My first recommendation would be to create a folder for the knowledge graph(s) that you have exported.
Example of a structure of my project

`./` 
`./client_project/` ## for my client
`./client_project/graph/` ## for the knowledge graph(s) exported from the AEP instance
`./client_project/API/ `## This folder contains notebooks and credential for connection

After loading your knowledge graphs, your graphs/ folder should look like this: 

`./client_project/graph/`
`./client_project/graph/prod.ttl`
`./client_project/graph/prod-2.ttl`
`./client_project/graph/dev.ttl`

### Create a local MCP server file
In the `client_project/graphs/` folder, create a file called `local_mcp.py`. This file will contain the configuration for the MCP server. The configuration will contain the path to the knowledge graph(s) that you want to load into the MCP server. 

Example of configuration, saved in a file named `local_mcp.py`:

```py
from mcp.server.fastmcp import FastMCP
import rdflib

mcp = FastMCP("knowledge-graphs")

GRAPHS = {
    "prod": {"path": r"C:\Users\xxxxx\Documents\Clients\client_project\Graph\prod.ttl", "desc": "Adobe Experience Platform Sandbox PROD knowledge graph."},
    "prod-2": {"path": r"C:\Users\piccini\Clients\client_project\Graph\prod-2.ttl", "desc": "Adobe Experience Platform Sandbox PROD 2 knowledge graph."},
    "dev": {"path": r"C:\Users\piccini\Documents\Clients\client_project\Graph\dev.ttl", "desc": "Adobe Experience Platform Sandbox DEV knowledge graph."}
}

_cache = {}
def get_graph(name: str) -> rdflib.Graph:
    if name not in _cache:
        _cache[name] = rdflib.Graph().parse(str(GRAPHS[name]["path"]), format="turtle")
    return _cache[name]

@mcp.tool()
def list_graphs() -> str:
    """List available knowledge graphs and what each one contains. Call this first."""
    return "\n".join(f"{k}: {v['desc']}" for k, v in GRAPHS.items())

@mcp.tool()
def get_schema(graph: str) -> str:
    """Return the predicates for one graph so a SPARQL query can be built."""
    preds = sorted({str(p) for p in get_graph(graph).predicates()})
    return "Predicates:\n" + "\n".join(preds)

@mcp.tool()
def run_sparql(graph: str, query: str) -> str:
    """Run a SPARQL query against the named graph and return rows."""
    try:
        rows = list(get_graph(graph).query(query))
        return "\n".join(str(r) for r in rows) if rows else "No results."
    except Exception as e:
        return f"Query error: {e}"

if __name__ == "__main__":
    mcp.run()
```

## Connect this MCP to your AI application

For these settings, I will provide several examples to connect the MCP server to your AI application. 

### Claude 

In Claude, if you have the Desktop application, you can connect to the MCP server via the `Settings`, and then go to `Developer`.\
It will provide you with a way to config your connection to MCP server, and you can `Edit Config`. 

This opens the claude_desktop_config.json file, where you can add the following configuration: 

```json
"mcpServers": {
    "AEP-turtle-graph": {
      "command": "python",
      "args": [
        "C:\\Users\\piccini\\Documents\\Clients\\client_project\\Graph\\local_mcp.py"
      ]
    }
  },
```

NOTE: In case you already have configured other MCP servers, you can add this configuration to the existing `mcpServers` object.


### ChatGPT

Unlike Claude Desktop, ChatGPT cannot launch a local script over stdio and it cannot reach a plain `localhost` address. ChatGPT connectors are configured as a **URL** pointing to an MCP server that speaks the *streamable HTTP* transport and that is reachable over the public internet (even if that server happens to be running on your own machine).\
This means two changes are needed compared to the Claude setup above:

1. Run `local_mcp.py` with the HTTP transport instead of the default stdio transport, by changing the last line of the file:

```py
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
```

2. Expose that local port to the internet with a tunneling tool, for example [ngrok](https://ngrok.com/):

```bash
python local_mcp.py          # terminal 1 - starts the MCP server on port 8000
ngrok http 8000               # terminal 2 - exposes it publicly, e.g. https://abc123.ngrok.app
```

Then, in ChatGPT:

1. Go to `Settings` > `Connectors` > `Advanced`, and turn on `Developer mode` (available on Plus, Pro, Business, Enterprise and Edu plans; on Business/Enterprise/Edu it may need to be enabled by a workspace admin).
2. Back in `Settings` > `Connectors`, click `Create`, give the connector a name (e.g. `AEP-turtle-graph`), and set the `MCP Server URL` to your tunnel URL with the `/mcp/` path, e.g. `https://abc123.ngrok.app/mcp/`.
3. Check "I trust this application" and save. ChatGPT will call the server and list the tools it exposes (`list_graphs`, `get_schema`, `run_sparql`).
4. In a chat, click `+` > `More`, enable the connector under `Developer mode`, and it will be available for that conversation.

**NOTE**: The tunnel URL changes every time you restart ngrok (unless you use a paid/reserved domain), so you will need to update the connector's URL after each restart. Keep in mind that anyone who guesses/obtains that URL could query your knowledge graph while the tunnel is open, so treat it like a temporary, semi-public endpoint rather than a private local one.

### Gemini

Gemini support depends on which surface you use:

- **Gemini CLI** behaves like Claude Desktop: it can launch a local stdio MCP server directly, no tunnel required. Add the server to `~/.gemini/settings.json` (or a project-level `.gemini/settings.json`):

```json
{
  "mcpServers": {
    "AEP-turtle-graph": {
      "command": "python",
      "args": [
        "C:\\Users\\piccini\\Documents\\Clients\\client_project\\Graph\\local_mcp.py"
      ]
    }
  }
}
```

  You can also register it from the command line instead of editing the file by hand:

```bash
gemini mcp add AEP-turtle-graph python "C:\Users\piccini\Documents\Clients\client_project\API\Graph\local_mcp.py"
```

  Keep `local_mcp.py` on the default stdio transport (`mcp.run()`) for this path.

- **Gemini web app / Gemini in Google Workspace** works like ChatGPT: it only supports remote, URL-based MCP connectors, so a plain `localhost` server is not reachable. If you want to use the knowledge graph from the Gemini web app rather than the CLI, run `local_mcp.py` with `transport="streamable-http"` as described in the ChatGPT section above, expose it with a tunnel, and register the resulting public URL as an extension/connector in the Gemini web app settings.

### Adding the dictionary to the AI model

In aepp, the knowledge graph documentation is providing the different descriptions available for the entities and their predicates. This is a dictionary that can be used to provide more context to the AI model. The dictionary is available in this section: [Knowledge Graph Ontology](./knowledge-graph.md#Ontology).

There are several ways to integrates this ontology explanation.

1. Directly in the MCP as a new method

In that sense, you can create a new method in the `local_mcp.py` file that will return the ontology description. This method will be available in the MCP server and can be called by the AI model to get the ontology description. 

```py
@mcp.tool()
def get_ontology_description() -> str:
    """
    Returns the complete Markdown documentation of the Sandbox Knowledge Graph ontology.
    Includes all valid URIs, node types (XDM, IDENTITY, FLOWS, etc.), and predicates.
    """
    return """[Your Markdown Table String Here]"""
```

You can save context window by adding a multi step process when the AI wants to query your graph. 

2. Adding it as a resource in your Local MCP

This time, we will add the ontology as a resource in the MCP server. This way, the AI model can access the ontology description without having to call a method. 

```py
LOCAL_FILE_PATH = r"C:\Users\piccini\Clients\client_project\Graph\ontology_description.md"
# Convert the Windows path to a valid file:// URI for the MCP server
RESOURCE_URI = Path(LOCAL_FILE_PATH).as_uri()

@mcp.resource(RESOURCE_URI)
def get_graph_ontology() -> str:
    """
    Returns the complete Sandbox Knowledge Graph ontology documentation 
    read dynamically from the local markdown file.
    """
    path = Path(LOCAL_FILE_PATH)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"Error: Ontology file not found at {LOCAL_FILE_PATH}"
```

Because the read_text() function fires every time the resource is requested, you can edit ontology_description.md on the fly. The next time the AI builds a query, it pulls the freshest version of your rules.


3. SKILLS.md, cursorrules, etc... 

Finally, you can also directly add this documentation in your SKILLS.md file, or similar, in order to provide information and context about the knowledge graph to the AI model. This way, the AI model can access the ontology description without having to call a method or a resource.
This method works well when you have a setup in place with already SKILLS.md files and want to add the knowledge graph ontology description to the existing documentation.