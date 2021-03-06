# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2013 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    porch.database
    ~~~~~~~~~~~~~~

    Database Support
'''
# pylint: disable=E8221,C0103

# Import Python libs
from datetime import datetime

# Import 3rd-party plugins
from sqlalchemy import orm
from flask_sqlalchemy import SQLAlchemy as _SQLAlchemy
from jenkinsapi.jenkins import Jenkins

# Import POrch libs
from porch.signals import application_configured


# ----- Simplify * Imports ---------------------------------------------------------------------->
ALL_DB_IMPORTS = [
    'db',
    'Account',
    'Group',
    'Privilege',
    'BuildServer',
    'Builder'
]
__all__ = ALL_DB_IMPORTS + ['ALL_DB_IMPORTS']
# <---- Simplify * Imports -----------------------------------------------------------------------


# ----- Instantiate the Plugin ------------------------------------------------------------------>
class SQLAlchemy(_SQLAlchemy):

    def update_dbentry_from_form(self, dbentry, form):
        for name in form._fields.keys():
            column_value = getattr(dbentry, name, None)
            form_value = form._fields[name].data
            if isinstance(column_value, orm.collections.InstrumentedSet):
                form_value = orm.collections.InstrumentedSet(form_value)
                # if column_value and form_value != column_value:
                # setattr(dbentry, name, form._fields[name].data)
            if form_value != column_value:
                setattr(dbentry, name, form._fields[name].data)


db = SQLAlchemy()


@application_configured.connect
def configure_sqlalchemy(app):
    db.init_app(app)
# <---- Instantiate the Plugin -------------------------------------------------------------------


# ----- Define the Models ----------------------------------------------------------------------->
class AccountQuery(db.Query):

    def get(self, id_or_login):
        if isinstance(id_or_login, basestring):
            return self.filter(Account.login == id_or_login).first()
        return db.Query.get(self, id_or_login)

    def from_github_token(self, token):
        return self.filter(Account.token == token).first()


class Account(db.Model):
    __tablename__   = 'accounts'

    id              = db.Column('github_id', db.Integer, primary_key=True)
    login           = db.Column('github_login', db.String(100))
    name            = db.Column('github_name', db.String(100))
    email           = db.Column('github_email', db.String(254))
    token           = db.Column('github_access_token', db.String(100), index=True, unique=True)
    avatar_url      = db.Column(db.String(2000))
    last_login      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    register_date   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    locale          = db.Column(db.String(10), default=lambda: 'en')
    timezone        = db.Column(db.String(25), default=lambda: 'UTC')

    # Consider https://github.com/dfm/osrc/blob/master/osrc/timezone.py

    query_class     = AccountQuery

    # Relations
    groups          = None  # Defined on Group
    privileges      = db.relation('Privilege', secondary='account_privileges',
                                  backref='privileged_accounts', lazy=True, collection_class=set,
                                  cascade='all, delete')

    def __init__(self, id_, login, name, email, token, avatar_url):
        self.id = id_
        self.login = login
        self.name = name
        self.email = email
        self.token = token
        self.avatar_url = avatar_url

    def update_last_login(self):
        self.last_login = datetime.utcnow()


class GroupQuery(db.Query):

    def get(self, privilege):
        if isinstance(privilege, basestring):
            return self.filter(Group.name == privilege).first()
        return db.Query.get(self, privilege)


class Group(db.Model):
    __tablename__ = 'groups'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(30))

    accounts      = db.dynamic_loader('Account', secondary='group_accounts',
                                      backref=db.backref(
                                          'groups', lazy=True, collection_class=set
                                      ))
    privileges    = db.relation('Privilege', secondary='group_privileges',
                                backref='privileged_groups', lazy=True, collection_class=set,
                                cascade='all, delete')

    query_class   = GroupQuery

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return u'<{0} {1!r}:{2!r}>'.format(self.__class__.__name__, self.id, self.name)


group_accounts = db.Table(
    'group_accounts', db.metadata,
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id')),
    db.Column('account_github_id', db.Integer, db.ForeignKey('accounts.github_id'))
)


group_privileges = db.Table(
    'group_privileges', db.metadata,
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id')),
    db.Column('privilege_id', db.Integer, db.ForeignKey('privileges.id'))
)


class PrivilegeQuery(orm.Query):
    def get(self, privilege):
        if not isinstance(privilege, basestring):
            try:
                privilege = privilege.name
            except AttributeError:
                # It's a Need
                try:
                    privilege = privilege.value
                except AttributeError:
                    raise
        return self.filter(Privilege.name == privilege).first()


class Privilege(db.Model):
    __tablename__   = 'privileges'

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(50), nullable=False, unique=True)

    query_class     = PrivilegeQuery

    def __init__(self, privilege_name):
        if not isinstance(privilege_name, basestring):
            try:
                privilege_name = privilege_name.name
            except AttributeError:
                # It's a Need
                try:
                    privilege_name = privilege_name.need
                except AttributeError:
                    raise
        self.name = privilege_name

    def __repr__(self):
        return '<{0} {1!r}>'.format(self.__class__.__name__, self.name)


# Association table
account_privileges = db.Table(
    'account_privileges', db.metadata,
    db.Column('account_github_id', db.Integer, db.ForeignKey('accounts.github_id'), nullable=False),
    db.Column('privilege_id', db.Integer, db.ForeignKey('privileges.id'), nullable=False)
)


class BuildServerQuery(db.Query):

    def get(self, id_or_address):
        if isinstance(id_or_address, basestring):
            return self.filter(BuildServer.address == id_or_address).first()
        return db.Query.get(self, id_or_address)

    def from_address(self, address):
        return self.filter(BuildServer.address == address).first()


class BuildServer(db.Model):
    __tablename__   = 'build_servers'

    id              = db.Column(db.Integer, primary_key=True)
    address         = db.Column(db.String(256), nullable=False, unique=True)
    username        = db.Column(db.String(128), nullable=False)
    access_token    = db.Column(db.String(128), nullable=False)

    # Query attribute
    query_class     = BuildServerQuery

    # Relationships
    builders        = db.relation('Builder', backref='server', lazy=True,
                                  collection_class=set, cascade='all, delete')


    def __init__(self, address, username, access_token):
        self.address = address
        self.username = username
        self.access_token = access_token

    @property
    def jenkins_instance(self):
        return Jenkins(self.address, self.username, self.access_token)


class Builder(db.Model):
    __tablename__   = 'builders'

    name            = db.Column(db.String(256), primary_key=True)
    display_name    = db.Column(db.String(128))
    description     = db.Column(db.String)
    removed         = db.Column(db.Boolean, default=lambda: False, nullable=False)
    builder_id      = db.Column(db.ForeignKey('build_servers.id'), nullable=False)

    def __init__(self, name, display_name, description, active=True):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.active = active
# <---- Define the Models ------------------------------------------------------------------------
