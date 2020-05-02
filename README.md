# Approx Redirector

This simple Python 3 script does redirect all entries in your `sources.list` and `sources.list.d` files to a given approx instance.
It redirects all entries cached by the approx server
but does not change uncached repositories.

## Features

- Looks up cacheable repositories
- Supports ≈99.9 % of all approx configurations out there (except approx forcing https)
- Verboses changes if requested
- Can rewrite sources files if run as `root`
- Does backup old sources files for easy restoring

### ToDo

- Support https for approx
- Implement '--mirror' mode

## Usage

- Obviously requires a Debian-based system
- Requires `python3` and `python3-request` to be installed

Assuming `approx` is the hostname of the approx cache you want to use.
You can use an IP address instead.
You can append a port by using `approx:9999`.
By default `http://` will be used
but you can specify https as protocol, too: `https://approx` (**not supported yet**).

```
./redirect.py -v approx
```

The script will check which entries can be redirected
and report these to stdout.
If you want to approve these changes, run as `root`:

```
./redirect.py -vc approx
```

Now your system will use the approx cache.
The old entries are commented out.

## Contribute

Feel free to contribute to this project.
Please follow the common [style guide for Python](https://www.python.org/dev/peps/pep-0008/).

## License

This project is licensed under MIT.
