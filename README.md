# About

A distribution tool of a selection of
[temurin17-binaries](https://github.com/adoptium/temurin17-binaries),
as the GWF behavior is weird while downloading jre etc., with Python scripts. 

# How To

```
    Upto 0.1.0, JRE-Mirror is only tested on Ubuntu 22.0.4 and Python 3.12 
```

The sub-folders in temurin17-binaries can be deployed as a website root path.
In the sub-folders, run the Python module, jre-mirror to download the selected
binary distributions, with proxy configured in proxy.json.

Download the JRE-Mirror-jdk17.zip from the release section. Configure the list.json,
which is the download tasks configuration, where

```
    mirroring: a list of target binaries to bo downloaded from temurin17
    resources: a list of target binaries completed, and is locally available
```

Start the jre-mirror Python module to download the mirrors.

```code
    # (Tested on Ubuntu 24.0.4)
    cd JRE-Mirror/temurin17-binaries/jdk-17.0.17+10
    python3 -m venv .env
    source .env/bin/activate
    pip install jre-mirror
    python3 -m jre-mirror
```

Now configure the resources a Nginx static site or, If you need more fine control,
use the [Html-service](https://github.com/odys-z/html-service) as the web service,
with which a simple Windows service can be setup as a static web site.

A sample configuration of html-service's configuration can be:

```
    { "type": "io.oz.srv.WebConfig",
      "port": 1984,
      "paths": [
        {"path": "/jre-17/*", "resource": "$HOME/JRE-Mirror/temurin17-binaries/jdk-17.0.17+10"}],
      "welcomepages": [],
      "startHandler": []
    }
```

Restart the service, if you followed the steps in the README of html-service.

```
    sudo systemctl restart html-service.service
```

Try

```
    http://127.0.0.1:1984/jre-17/list.json
```

The binaries and the json file can be available online now.

## About Proxy

To configure the proxy, in list.json, specify the configuration file path:

```
    # list.json
    { ...
      "proxy": "proxy.json"
      ...
    }
```

And in proxy.json, configure the proxy string following the general proxy string
format of Python:

```
   { "type": "io.oz.edge.Proxy",
     "http": "http://user:passwd@127.0.0.1:port",,
     "https":"http://user:passwd@127.0.0.1:port"
   }
```

#### Note: all the *type* fields in json files are neccessary.

# Credits:

## [temurin17-binaries](https://github.com/adoptium/temurin17-binaries)
The home for releases and nightlies for all Temurin17 variants and platforms

## [OpenJDK Mirror Scripts](https://github.com/adoptium/mirror-scripts)

These scripts are run at https://ci.adoptopenjdk.net/view/git-mirrors/ and are responsible for updating the Eclipse Adoptium clones of the various OpenJDK Skara github repositories that we are interested in building.

## [jyksnw/install-jdk](https://github.com/jyksnw/install-jdk)

Python package that simplifies the process of installing OpenJDK on Windows, macOS, Linux and other supported operating systems, saving time and effort. 

### So no equivolent?
