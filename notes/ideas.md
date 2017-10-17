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
# 'apache' as a string, means that we look up the function in the same file
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

The `yaml` alternative is:

```yaml
--- the 'config' is implicitly defined and loaded.
source:
  interface: mysql
function:
  name: apache
  function: lib.functions.apache
  depends-on:
    - mysql
    - config
output:
  file:
    name: /etc/apache/apache.conf
  depends-on: apache

```
There's a forward reference there, which looks awkward.  It might have to be
done as a string.  I don't really want them to be decorators, as the intention
is too keep all the declarations near to each other.

### Referring to the context object

It would be really useful to be able to refer to the parts of the context
object, rather than only the top level key.  This is particularly
important for the `yaml` definitions, where we might want to depend on
a subkey.

The most compatible separator is probably a `:` character.  This means
that keys can have `.` and `/` characters (typically in filenames) whilst
still be resolvable.

Thus, `config:vip` would be the VIP config property, and if that was
a `depends-on` key, then it would only look at that value changing.

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

And a possible `yaml` alternative:

```yaml
variable:
  name: openstack_version
  from: lib.something.determine_os_version

action:
  name: install_packages
  depends-on: openstack_version
```

## What about tagging of schemas?

The idea is that we want to have the same names but allow different contexts to
evolve due to different versions.

The idea is to solve the problem of calling a different version of the function
based on tag(s) that are calculated during the initialisation phase of the
charm.

```python
declare.variable('openstack_version', determine_os_version)
# not sure where to go from here ...
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

And if we wanted a `yaml` version:

```yaml
variable:
  name: os_release
  from: lib.something.determine_os_release
predicate:
  name: >mitaka
  function: lib.something.predicate_cmp_os_release
  depends-on: os_release
action:
  name: do_action
  function: lib.something.do_action
  predicates:
    - >mitaka
  depends-on:
    - shared_db
```

So the theory is that we say that "do_action" is called when any of
following has changed:

* the `shared_db` *interface* is different to last time
* the *predicate* indicating the openstack release is greater than `mitaka` is true.

Note we have to be careful to remember that *any* of these conditions can
result in do_action being called, which is probably not what we want.

Thus we have to think about the context as *immutable* in creation, and then
using *actions* to achieve either changes on the payload, writing config
files/restarting services, or setting things on interfaces.

Implementation in the reactor will be tricky; it'll need to be a wrapper
function, that uses the predicate to decide whether to call the function if the
input changes.  This means that `action` will translate into a reactor
function and a that will do the action.

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

## Declaring services, config files and whether they should be running.

Writing configuration files and (re)starting services is the core *raison
d'être* of writing charms; it's what charms are supposed to do.  However, it
also needs to be flexible.  The most common usecase can be described as:

"A change in an relation or config should cause the config file to be written
and the associated service to be restarted."

So we work backwards.  We can:

1. Declare a service.  This is a name, details on how to stop/start it.
2. Declare a config file.  This is a local name, filename + path, template.
3. Declare context(s) that contain the information for the config file.
4. Declare someway to link these items together.

The theory then is, that when the contexts change, it will lead to the config
files being written and services being changes.  We do have to track whether
the file changes, as it's the only reliable indictor for whether to restart the
file.

It's tempting to put the details into the context, as that's whether everything
should go. Should it also go in the reactor?

Some ideas of how it would go:

### A config file that only depends on an interface (just the one!)

```python
declare.config()
declare.relation('something', declare.load_and_validate("something-schema.json")
declare.context('else', lambda: SomeContext()())
declare.config_file('/some/config/file.conf', 'something', 'else', 'config')
declare.service(service='some_service',
                run_only_when_valid=True,
                dependencies=('/some/config/file.conf', ))
```

And a possible `yaml` alternative:

```yaml
--- the 'config' is implicitly defined and loaded.
relation:
  name: something
  load_and_validate: something-schema.json
context:
  name: else
  function: lib.something.SomeContext
config-file:
  filename: /some/config/file.conf
  depends-on:
    - something
    - else
    - config
service:
  name: some_service
  run-only-when-valid: true
  depends-on: /some/config/file.conf
```

This would rely on a `something-schema.json` which describes the valid data on
the *relation* `something` which is found in the charm's `metadata.yaml` file.

So taking this line-by-line:

1. `declare.config()` takes the config.yaml, parses it, and loads it into the
   context `config`.
2. The *relation* declared as `something` uses a helper to load the *json* file
   and then use that to validate the data on the relation. This would either
   result in a `None` or a context value.
3. The *context* `else` uses a helper `SomeContext` from `charm-helpers` to
   resolve whether the relation (or indeed config, or both) is valid, and adds
   it to the overall context.  Again, this is `not None` when the data is valid
   to be used.
4. The configuration file `/some/config/file.conf` is dependent on the context
   values `something`, `else`, and `config`.  When these are valid (or have
   changed) then the config file is (re)written.
5. The `declare.service()` declaration names the service as `some_service`
   (this goes into the context with this value), and then indicates that is it
   only started when it has a valid (`not None`) dependencies.  If it is valid
   then the service is started.  If *any* of the dependencies has changed, then
   the service is restarted.

### If one service restarts, then we have to restart another service

E.g. if we restart apache2, then we have to restart haproxy.  We don't want to
have to code this; we want to declare our intentions and get *declarative* to
do the work for us.

```python
declare.service(service='apache2',
                service_name='apache2',
                run_only_when_valid=False,
                dependencies=('/some/apache2/conf', ),
                run_before='haproxy')
declare.service(service='haproxy',
                run_only_when_valid=False,
                dependencies=('/some/haproxy.conf', ),
                restart_with='apache2')
```

So, in theory, `haproxy` will now restart with `apache2`, but `apache2` will be
started *before* haproxy, and stopped *after* haproxy.  Any restart needed for
`haproxy` would required `apache2` to also be restarted (note, as an example,
this is not particularly useful!)

### custom start/stop functions.

Sometimes more work than just starting on stopping the service using the
`charm-helpers` helper functions is needed.  In this case, a callable can be
provided to `declare.service()` to perform the necessary function.  However,
this should not be abused; we want to avoid imperative code as much as
possible.

```python
declare.service(service='some-special-service',
                ...
                start_stop_callable=lambda x: custom_start_stop(x),
                ...)


def custom_start_stop(state):
    """Start the service is 'state' is 'start', stop it if it is 'stop' and
    restart it if it is 'restart'.
    """
    pass
```

And the `yaml` equivalent:

```yaml
service:
  name: some-special-service
  start_stop_callable: lib.something.custom_start_stop
```

Note we used the `lambda x: ...` as a convenient way of being able to define
the function later in the file. If it had been imported, or defined further up
the file, then `custom_start_stop` could have been used instead.

## Understanding relations

Relations are key to how configuration and control in charms is processed.
Relations are 'loaded' into the `context` either directly using a validation
function, or indirectly (and merged with other data) using a `charm-helpers`
Context() function.  It is *simpler* to consider pulling relation data into the
context on an individual basis, and then using the `reactor` to merge the data
with other relation data and config items to build more useful context values.
However, in the interest of code reuse, the *context* supports the use of
`charm-helper` context classes.

Relations are defined in the `metadata.yaml` file in the charm, and
`charms.declarative` reads that file to find out the names of the relations,
and name those in the *context*.

A typical `metadata.yaml` might look like the following (this is the OpenStack
heat charm):

```yaml
name: heat
summary: OpenStack orchestration engine
maintainer: OpenStack Charmers <openstack-charmers@lists.ubuntu.com>
description: |
  Heat is the main project in the OpenStack Orchestration program. It implements an
  orchestration engine to launch multiple composite cloud applications based on
  templates in the form of text files that can be treated like code.
tags:
  - openstack
series:
  - xenial
  - zesty
  - trusty
extra-bindings:
  public:
  admin:
  internal:
requires:
  shared-db:
    interface: mysql-shared
  amqp:
    interface: rabbitmq
  identity-service:
    interface: keystone
  ha:
    interface: hacluster
    scope: container
peers:
  cluster:
    interface: heat-ha
```

So this charm *requires* 4 relations that it will have a conversation with.
Each of the relations is to a 'service' that supports multiple clients; but in
this case this charm provides no 'service' to another charm.  Hence it doesn't
have *provides* relations.

Taking just the *shared-db* relation; in the charm the relation's name is
'shared-db'.  The relations hooks will be 'shared-db-relation-*', where '*' is
one of *joined*, *changed*, *broken*, *departed*.

Not units (an instance of the heat application, say) can be related to multiple
other units in other applications.  This means that, despite heat only needing
*one* database connection, `charms.declarative` has to be able to model
multiple connections.

The unit addresses are *opaque*, as in, the are only meaningful to Juju and
should just be treated as unique strings to the charm.

The keystone charm, has an 'interface' named 'keystone'.  It's `metadata.yaml`
(simplified) looks a bit like:

```yaml
name: keystone
summary: OpenStack identity service
maintainer: OpenStack Charmers <openstack-charmers@lists.ubuntu.com>
description: |
 Keystone is an OpenStack project that provides Identity, Token, Catalog and
 Policy services for use specifically by projects in the OpenStack family. It
 implements OpenStack’s Identity API.
...
provides:
  ...
  identity-service:
    interface: keystone
  ...
requires:
  shared-db:
    interface: mysql-shared
  ...
peers:
  cluster:
    interface: keystone-ha
```

So keystone provides the 'keystone' interface (which is just an identifying
*string*; there's no other data associated with it at the Juju level, except
that the same string == the same interface for plugging charms together.)
Internally to the charm, that interface is the 'relation' *identity-service*,
which is how it is referred to in relation hooks (e.g.
identity-service-relation-joined), and how the declarative helpers use it (by
parsing `metadata.yaml` and then listing the units, etc.)

In the keystone charm's case, it will have *multiple* identity-service
connections (both applications and units in those applications).  It will also
have (probably) multiple units in one application interface.  e.g. if the
shared-db is *clustered* then the keystone charm will have a relation with all
(hopefully!) of the shared-db related units, but only the 'leader' of that
group will actually have set data back.

### Scope in relations

There are two scopes:

- *global* scope; every relation knows about all the other units in the
  relation 'globally' in the model.
- *container* scope; for *principal-subordinate* charm relations, they are
  scoped (i.e. can see) just each other on the relation.

### Summarising the parameters around relations

- *name* - the name of the relation is defined in the `metadata.yaml`
- *interface* - a unique strings that allows charms to be plugged into each
   other.
- *scope* - global or container scope (subordinate charms)
- *relation id* - a unique, opaque, string to identity the relation between
  two applications.  Note that a charm **never** knows what the other
  *application* is, just that it provides or consumes (requires) a particular
  *interface* name.
- *unit name* - a unique, opaque, string to identify a particular unit on a
  *relation id* relation.
- *key=value* data - the data on a relation is just strings associated with
  key strings.  i.e. no interpretation.

### Modelling relations in charms.declarative

We want to be able to set and get data on relations really, really, easily.  We
also really, really, want to avoid using objects tied to specific
'conversations'.  This stuff is hard to reason about as it is, without trying
to hide implementation details.

`something.{relation_id}.{unit_id}.{key=value}`

is what we have to model *incoming* and:

`something.{relation_id}.{key=value}`

for *outgoing* data (or rather setting the data for the unit on the relation).

i.e. this means that you can read other individual units' data, and set
your own unit for each relation.

So the challenge: how to provide the the data from the various units in
a coherent fashion?

If we use the `:` separator, then the context can be `relation:rid:uid`.
The `rid` is a number, and so is prefixed with an `r`, whereas the `uid`
is opaque, and thus doesn't need a prefix.

Is it impossible to depend on an *rid* or *uid* because they are dynamic
and, thus will change between each unit.

So we can only depend on the top level keys.  This means that functions
need to resolve what they need using the `rid` and `uid` subkeys.  I don't
think there's a nice, declarative, way around this.



### Different types of relation

We have three different types of relation:

- ordinary relations (units, etc.)
- peer relations (sharing data with the same units as yourself)
- leader settings (for the leader to set, and the followers to read)


