# Some notes on declarative

charms.declarative is an alternative `reactive` framework to make writing
charms in Python much, much eaiser.  This is largely because I think that
charms.reactive is too conceptually hard to work with.

The key concepts in charms.declarative are:

* Data-driven
* Functional rather than Object Orientated
* Uses orthogonal tagging of data schemas for versioning, feature selection,
  etc.
* Uses charm-tool's layers to separate functionality.
* Like charms.reactive, doesn't 'care' what the hook event is.
* Drives towards the configured system using data, rather than imperative
  functions.

One of the key differences from `charms.reactive` is that it doesn't uses
states/flags to record that some condition has been reached.  Instead, it
tracks data changes to drive new behaviour in a reactive fashion.  i.e. when
data changes declared actions occur.  This may change other data, which in turn
potentially triggers new actions.

So data cascades through the charm and ends up either in config files, on
relations, or via commands on the payload software.  These latter actions are
essentially monadic; the rest of the framework tries very hard to be
functional.

The data in the framework is held on a single structure called the `context`.
This is *read-only* in actions, but actions can return new parts that are
inserted into the `context`.

# Things that can be declared

The following helpers declare contexts that we need to be able to use.
Some of them will be implicit (or at lease defined in a layer) and others
will be useful for charm authors to use.

Note that in the case of *every* declaration, the 'persistence' of the
result of the declaration can be specified as to whether to remember it
between invocations of the hook, or whether to start again with each run.
This controls whether functions get called depending on when the inputs
(variable) change.

## config

The 'config' context will be loaded by the framework, automatically, using
the `config.yaml` to determine the basic types the config supports.  It
will be available as `context.config.<key>`.

## interfaces

The interfaces defined in the `metadata.yaml` will be discovered.  The
charm author will be able to declare a schema against each interface.
This will be applied at the data level (i.e. after `rid:uid` subkeys).

A snippet of the `metadata.yaml` file is:

```yaml
requires:
  shared-db:
    interface: mysql-shared
  pgsql-db:
    interface: pgsql
```


In this case, the interface `mysql-shared` will be called `shared-db` as
a key on the context, and as `context.shared_db` in as a Python dot
notation.  Obviously, the `rid` and `uid` subkeys need to be traversed as
well.

In order to associate a schema with the interface `mysql-shared`:

```python
declare.interface_scheme('mysql-shared', 'mysql-shared-schema.yaml',
                         persistent=True)
```

And in `yaml`:

```yaml
interface-schema:
  interface: mysql-shared
  schema-file: mysql-shared-schema.yaml
  persistent: True
```

This will then automatically apply the schema to the keys in the
interface, validate them, and only add the data if the the schema
validates.

## Variables

Variables are *nameable* entities that are put on the context, and thus
are available to any function that is put on the context.  They are like
a global variable.  Note that they are immutable once they are on the
context.  Also, they can be *callables* so that they are lazily evaluated.
This is true at any level of the context.

In Python:

```python
declare.var('name', value-or-callable, persistent=True)
```

In yaml:

```yaml
variable:
  name: name
  value: <string>
  type: (int | float | string | callable)
  persistent: True
```

## Functions

Functions are callables that resolve to a value that is placed on the
context (note that the value may also be a callable - they are resolved at
access rather than placement).  They are used to build out the context
which is given to any of the functions.

The difference from a variable, is that a function has dependencies, which
cause the function to be called *only* when one of the dependencies values
has changed from hook invocation to invocation.

In python:

```python
declare.function('name', callable, [dependencies], persistent=True,
                 predicates=None)
```

In yaml:

```yaml
function:
  name: name
  function: callable
  dependencies:
    - list of names of other contexts
  persistent: True
  predicates:
   - list of functions that resolve to truth

```

An alternative `@decorator` syntax for a function, would look like:

```python
@declare.function('name', [dependencies], persistent=True, predicates=None)
def name1(context):
    pass
```

The runtime attempts to ensure that there are no circular dependencies,
and that the dependencies are all resolvable before starting.

## Actions

Actions are callables that don't resolve to a value, and so are not added
to the context.  They are called purely for their side-effects.  Although
a 'None' is entered into the context, they are not able to be referred to
by dependency lists and thus cannot trigger other actions.  They are used
(via construction) for writing output files.

In Python:

```python
declare.action('name', callable, [dependencies], persistent=True, predicates=None)
```

In yaml:

```yaml
action:
  name: name
  function: callable
  dependencies:
   - list of names of other contexts
  persistent: True
  predicates:
   - list of functions that resolve to truth
```

And as a decorator:

```python
@declare.action('name', [dependencies], persistent=True, predicates=None)
def name1(context):
    pass
```

