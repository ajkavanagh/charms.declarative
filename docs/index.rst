charms.declarative
==================

This module serves as the basis for creating charms and relation
implementations using the declarative pattern.


Overview
--------

Juju is an open source tool for modelling a connected set of applications in a
way that allows for that model to be deployed repeatably and consistently
across different clouds and substrates.  Juju Charms implement the model for
individual applications, their configuration, and the relations between them
and other applications.

In order for the charm to know what actions to take, Juju informs it of
life-cycle events in the form of hooks.  These hooks inform the charm of things
like the initial installation event, changes to charm config, attachment of
storage, and adding and removing of units of related applications.

(This is just a placeholder document - it will be extended over time)
