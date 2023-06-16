# Logging in aepp

The loggin capability enables you to log the activities of the modules in a file.

## Configuration

You can enable logging capability when instantiating the different classes in the submodules.

It requires to pass an object during the class instantiation process, to the parameter `loggingObject`.\
A template of the object can be created via the `generateLoggingObject` method, available directly in the `aepp` module.\
This method takes no argument and returns the following object:

```python
{'level': 'WARNING',
 'stream': True,
 'file': False,
 'format': '%(asctime)s::%(name)s::%(funcName)s::%(levelname)s::%(message)s::%(lineno)d',
 'filename': 'aepp.log'}
```

Here are some description of the different keys:

* level : Level of the logger to display information (NOTSET, DEBUG,INFO,WARNING,EROR,CRITICAL)
* stream : If the logger should display print statements
* file : If the logger should write the messages to a file
* filename : name of the file where log are written
* format : format of the logs in string or an instance of the logging.Formatter class.

As pythonista may have realized, the logging capability has been created based on the native `logging` module of python.\
Documentation can be found [here](https://docs.python.org/3/library/logging.html).\
It also means that it doesn't require any new module import.

Example of instantiation of a class with the logging object:

```python
import aepp
aepp.importConfigFile('myconfig.json')
myLogging = aepp.generateLoggingObject()
from aepp import catalog
cat = catalog.Catalog(loggingObject=myLogging)

```

## Capabilities

The new functionality can either:

*   Stream data to the console. In that case, it will progressively replace some of the verbose option.

*   Write data to a log file. In that case, the default name of the log file will be `aepp.log`. You can change that in the config object.

Be careful at which level you are instanciating the logging capability. The default level is `WARNING`.

## Format of the logs

Here is the possible options for the format of the logs.\
Copy of the table available [here](https://docs.python.org/3/library/logging.html#:~:text=available%20to%20you.-,Attribute%20name,-Format)

|     Attribute name      |     Format      |   Description |
| ------------------------|-----------------|---------------|
|  asctime   |  %(asctime)s   | Human-readable time when the LogRecord was created. By default this is of the form '2003-07-08 16:49:45,896' |
|  created   |  %(created)f   | Time when the LogRecord was created (as returned by `time.time())`. |
|  filename  |  %(filename)s  | Filename portion of pathname. |
|  funcName  |  %(funcName)s  | Name of function containing the logging call. |
|  levelname |  %(levelname)s | Text logging level for the message ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'). |
|  levelno   |  %(levelno)s   | Numeric logging level for the message (DEBUG, INFO, WARNING, ERROR, CRITICAL). |
|  lineno    |  %(lineno)d    | Source line number where the logging call was issued (if available). |
|  message   |  %(message)s   | The logged message, computed as msg % args. This is set when `Formatter.format()` is invoked. |
|  module    |  %(module)s    | Module (name portion of filename). |
|  msecs     |  %(name)s      | Millisecond portion of the time when the LogRecord was created. |
|  name      |  %(pathname)s  | Name of the logger used to log the call. |
|  process   |  %(process)d   | Process ID (if available). |
|  processName| %(processName)s| Process name (if available). |
|  relativeCreated| %(relativeCreated)d| Time in milliseconds when the LogRecord was created, relative to the time the logging module was loaded. |
|  thread    |  %(thread)d    | Thread ID (if available). |
|  threadName|  %(threadName)s| Thread name (if available). |
