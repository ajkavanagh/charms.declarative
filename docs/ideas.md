# Ideas for how to implement various parts of declarative

## The 'context' object

It's read only, apart from by the framework.  i.e. apart from adding new bits
to the top level of the context, the other parts are read-only, and we should
enforce this by python read-only accesses.

Secondly, it should be lazy.  i.e. at anypoint, there can be a callable, which
is called and then instituted into the context object.

```python
# synonymous with declare.var("mysql", interface_context_callable_from("mysql", json_schema="mysql"))
declare.source(interface('mysql'))
# synonymous with declare.var("config", make_config_context_callable)
declare.source(config())
# 'apacge' as a string, means that we look up the function in the same file
declare.function('apache', 'mysql', 'config')
# alternative:
declare.function('apache', callable=do_apache_function, 'mysql', 'config')
declare.output(file('apache.conf', 'apache'))

def apache(context):
    """create the apache context from the config and mysql"""
    # this is contrived, as probably the apache.conf could be computed
    # from the config and mysql relation directly
    return {
        "some_value": context.config.https + context.mysql.url,
    }
```

There's a forward reference there, which looks awkward.  It might have to be
done as a string.  I don't really want them to be decorators, as the intention
is too keep all the declarations near to each other.

## How about doing an installation?

```python
declare.variable('openstack_version', 'determine_os_version')
delcare.action('install_packages', 'openstack_version')


def determine_os_version(_):
    """Workout what our version is"""
    return charmhelpers....determine_os_version()


def install_packages(context):
    """Install the packages; context.openstack_version contains the version
    and it will definitely have changed (or this is the first time).
    """
    current_version = context.last.openstack_version
    new_version = context.openstack_version
    current_packages = if current_version then PACKAGES[current_version] else []
    new_packages = PACKAGES[new_version]
    # uninstall current_packages not in new_packages.
    # install new packages not in current_packages.
    # and that would be it.
```

## What about tagging of schemas?

The idea is that we want to have the same names but allow different contexts to
evolve due to different versions.

The idea is to solve the problem of calling a different version of the function
based on tag(s) that are calculated during the initialisation phase of the
charm.

```python
declare.variable('openstack_version', determine_os_version)
declare.action
```
## Another approach

Using `P` for predicate:

```python
from utils import cmp_os_release
from lib import determine_os_release, do_action

declare.var("os_release", determine_os_release)
decleare.predicate('cmp_os_release', lambda ctx, cmp: cmp_os_release(ctx.os_release, cmp))

declare.action("do_action", do_action, "shared_db", P("cmp_os_release", ">mitaka"))
```

So the theory is that we say that "do_action" is called when any of following has changed:

* the `shared_db` *interface* is different to last time
* the *predicate* indicating the openstack release is greater than `mitaka` is true.

Note we have to be careful to remember that *any* of these conditions can
result in do_action being called, which is probably not what we want.

Thus we have to think about the context as *immutable* in creation, and then
using *actions* to achieve either changes on the payload, writing config
files/restarting services, or setting things on interfaces.

## so how do all the declarations work?

We have three types of things:

1. An *input variable*.  This defines a top-level name in the context.  e.g.
   'config', accessable as ctx.config
2. A *function* that takes multiple predicates that it resolves and decides
   whether to call the function.  The function returns a new part of the
   context.
3. An *action* that also takes multiple predicates that it resolves and decides
   whether to call the action.  The difference, is that an *action* doesn't
   return a new context segment.
