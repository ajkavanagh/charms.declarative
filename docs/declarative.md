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
