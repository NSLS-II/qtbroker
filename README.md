# qtbroker

This is a temporary repo. It will probably be merged into NSLS-II/databroker
in the future. This is barely usable and not stable or officially supported.

## Getting Started

You need a databroker with some data in it. A quick way to obtain one is to
download the [tutorial](https://github.com/NSLS-II/tutorial):

```
git clone https://github.com/NSLS-II/tutorial
ipython
%run tutorial/startup.py  # defines a db and subscribed it to a RunEngine RE
%run -i tutorial/generate_data.py  # executes some plans using RE, generating data in db
```

Now run the files in this repo.

```
%run qtbroker/qtbroker.py
%run qtbroker/cross_section_2d.py  # optional
```

And now set up a ``BrowserWindow`` instance. The tutorial has an example you can
just run:

```
%run -i tutorial/start_run_browser.py
browse()  # launches app
```

No runs will be displayed until you start typing search text.
