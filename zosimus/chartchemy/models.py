import base64
import string
from collections import defaultdict, OrderedDict

import sqlalchemy
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django_fields.fields import EncryptedCharField
from sqlalchemy import orm

from exceptions import UnsupportedDatabaseError, ChartCreationError
from utils import render_highcharts_options

try:
    import cPickle as pickle  # @UnusedImport
except:
    import pickle  # @Reimport


class TableBases(object):
    """A collection (``dict``) of ``Base`` table classes corresponding to a ``datasource`` model instance.

    In SQLAlchemy, introspecting a table returns instances of Table class. But Table classes are lower
    level. To get the goodness of higher level ORM API, we need Declarative Base classes that are
    *mapped* to the Table class. ``TableBases`` is such a collection.
    """

    def __init__(self, datasource, *args, **kwargs):
        self.datasource = datasource
        self._bases = {}

    def __getitem__(self, table_name):
        """Returns a ``Base`` table class for the corresponding ``table_name``.

        It is expensive to generate a class. So do it lazily, i.e. create the class the first time it is
        accessed and save it in the ``_bases`` dict.
        """

        # NOTE: The current solution (even though it uses lazy loading is still not completely efficient).
        # Because we create a Base class for every datasource instance even if all the datasource instances
        # all have same parameters. For example in the same python process if we do ::
        #
        #     ds_a = Datasource.objects.get(pk=1)
        #     ds_b = Datasource.objects.get(pk=1)
        #
        # Then ``ds_a.bases['Customers'] is ds_b.bases['Customers']`` returns ``False``. So the
        # ``BaseCustomers`` class is created twice.
        #
        # A better solution is to bind a TableBases object to the parameters of the datasource and return
        # same TableBases object for all the datasource objects that share same parameters.
        #
        # But the current setup will do in a pinch.

        # Lazily create a Base class and *map* it to the corresponding table on the instance.
        if self._bases.get(table_name) is None:
            # Note: When creating a class dynamically using ``type(name, bases, attr_dict)`` function,
            # as far as I can tell (and tested) *any*name is legal. For example
            # ``type(" 42!   worlds ", (object, ), {})`` will return ``__main__. 42!   worlds ``
            # However for the sake of making classes look pretty, we are going to strip punctuation
            # and spaces and prefix class name with Base. So in the above case we'll generate a class
            # ``__main__.Base42Wworlds``
            klass_name = table_name.encode('ascii', 'ignore').strip().title().replace(" ", "")
            trans = string.maketrans("", "")
            klass_name = 'Base' + klass_name.translate(trans, string.punctuation)
            # Now generate the class
            # NOTE 2: Note that we are ignoring ``Foreign Keys``. A more complete solution will involve
            # creating a ``relationship`` attribute for every foreign key in the Table object.
            klass = type(klass_name, (object, ), {})
            # Map this newly generated declarative base to the Table object.
            orm.mapper(klass, self.datasource.tables[table_name])
            # Now add it to the bases
            self._bases[table_name] = klass
        return self._bases[table_name]


class Datasource(models.Model):
    """Defines a specific database and connection parameters owned by a specific user to connect with a
    particular db.
    """
    user = models.ForeignKey(User)
    name = models.CharField(max_length=100)
    dbtype = models.CharField(max_length=100, choices=(('MYSQL', 'MySQL'),), default='mysql')
    dbname = models.CharField(max_length=100)
    dbusername = models.CharField(max_length=100)
    dbpassword = EncryptedCharField(max_length=100)
    dbhost = models.CharField(max_length=100)  # Must either be an IP address or URL
    # Pickled dict of db table names and sqlalchemy Table objects
    pickled_tables = models.TextField(null=True)
    pickled_measures = models.TextField(null=True)
    pickled_dimensions = models.TextField(null=True)
    time_introspected = models.DateTimeField(null=True)

    @property
    def engine(self):
        """ Returns the SQLAlchemy engine for the datasource. Creates one if there isn't one already.
        """

        # Every instance gets a different engine. Can be optimized further. See the NOTE in TableBases.
        try:
            return self._engine
        except AttributeError:
            conn_param = {'username': self.dbusername,
                          'password': self.dbpassword,
                          'host': self.dbhost,
                          'dbname': self.dbname,
                          }
            conn_template = "%(dialect_driver)s://%(username)s:%(password)s@%(host)s/%(dbname)s"

            if self.dbtype == 'MYSQL':
                conn_param['dialect_driver'] = 'mysql+mysqldb'
            else:
                raise UnsupportedDatabaseError("This database is not supported")
            conn_string = conn_template % conn_param
            self._engine = sqlalchemy.create_engine(conn_string, echo=settings.ECHO)
        return self._engine

    def _pickle_tables(self):
        """Reflects the database pointed to by the datasource, pickles all the Table objects returned
        and sets the ``pickled_tables`` field.

        See Also: tables
        """
        metadata = sqlalchemy.MetaData()
        metadata.reflect(bind=self.engine)
        pickled_tables = pickle.dumps(dict(metadata.tables.items()))
        # NOTE: Need to base64 encode it since django tries to convert to Unicode covert stuff by
        # default which causes issues which storing and retrieving from database.
        # See the implementation of ``django.sessions.base`` for an example of base64 encoding a pickled
        # object before saving in db.
        self.pickled_tables = base64.b64encode(pickled_tables)

    def _pickle_measures_and_dimensions(self):
        """Reflects the database columns and sets the ``pickled_measures`` and ``pickled_dimensions`` fields.

        The logic is rather simple minded ... if a column is an integer or numeric (float or double), then
        the column is considered a measure. If it is a string type, it is considered a dimension. Note that
        we conveniently ignore date and time columns. Oh well.

        See Also: _pickle_tables()
        """
        measures, dimensions = defaultdict(list), defaultdict(list)
        for table_name, table in self.tables.items():
            for column in table.columns:
                if isinstance(column.type, (sqlalchemy.types.Integer, sqlalchemy.Numeric)):
                    measures[table_name].append(column.name)
                elif isinstance(column.type, sqlalchemy.types.String):
                    dimensions[table_name].append(column.name)
        # NOTE: see note in _pickle_tables() for an explanation of why we need to base64 encode.
        self.pickled_measures = base64.b64encode(pickle.dumps(OrderedDict(measures)))
        self.pickled_dimensions = base64.b64encode(pickle.dumps(OrderedDict(dimensions)))

    def _pickle_all(self):
        """Introspects the db and pickles the tables and the measures and dimensions.
        """
        self._pickle_tables()
        self._pickle_measures_and_dimensions()

    @property
    def tables(self):
        """Reads the ``pickled_tables`` field and unpickles the data and returns a dict of table names
        and corresponding sqlalchemy.schema.Table objects. If the ``pickled_tables`` field is empty,
        introspects db first and then returns the tables.

        See Also: _pickle_tables()
        """
        try:
            return self._tables
        except AttributeError:
            if self.pickled_tables is None:
                self._pickle_tables()
            # NOTE: see note in _pickle_tables() for an explanation of why pickled fields are
            # base64 encoded.
            self._tables = pickle.loads(base64.b64decode(self.pickled_tables))
        return self._tables

    @property
    def measures(self):
        """Reads the ``pickled_measures`` field and unpickles the data and returns a dict of table names and
        and list of column names that are measures. If the ``pickled_measures`` field is empty,
        introspects db first and then returns the measures.

        See Also: _pickle_measures_and_dimensions()
        """
        try:
            return self._measures
        except AttributeError:
            if self.pickled_measures is None:
                self._picke_measures_and_dimensions()
            self._measures = pickle.loads(base64.b64decode(self.pickled_measures))
        return self._measures

    @property
    def dimensions(self):
        """Reads the ``pickled_dimensions`` field and unpickles the data and returns a dict of table names and
        and list of column names that are dimensions. If the ``pickled_dimensions`` field is empty,
        introspects db first and then returns the dimensions.

        See Also: _pickle_measures_and_dimensions()
        """
        try:
            return self._dimensions
        except AttributeError:
            if self.pickled_dimensions is None:
                self._picke_measures_and_dimensions()
            self._dimensions = pickle.loads(base64.b64decode(self.pickled_dimensions))
        return self._dimensions

    @property
    def bases(self):
        """Returns a TableBases collection. Lazily creates an loads a (declarative) Base object mapped
         to the corresponding table name.

        See Also: TableBases class.
        """
        try:
            return self._bases
        except AttributeError:
            self._bases = TableBases(self)
        return self._bases

    @bases.setter
    def bases(self, value):
        raise AttributeError("Cannot set bases")

    @bases.deleter
    def bases(self):
        raise AttributeError("Cannot delete bases")

    def __unicode__(self):
        return self.name

    def clean(self):
        """Tries to connect to the database based on the supplied parameters.

        Raises ValidationError if it can't connect to the database.

        NOTE: This method is called automatically by Django during the validation phase. In effect,
        if the supplied parameters are incorrect, a new datasource record will not be created.
        """
        try:
            self.engine.connect()
        except (sqlalchemy.exc.OperationalError, UnsupportedDatabaseError):
            raise ValidationError("Something wrong with the parameters. Can't connect to the DB.")

    @property
    def session(self):
        """Returns a session (``sqlalchemy.orm.session``) corresponding to the datasource.
        """
        # NOTE: Each instance gets its own session. Can be optimized further. See note in
        # TableBases.__getitem__
        try:
            return self._session
        except AttributeError:
            Session = orm.sessionmaker()
            Session.configure(bind=self.engine)
            self._session = Session()
            return self._session


@receiver(post_save, sender=Datasource)
def introspect_db(sender, instance, created, raw, using, **kwargs):
    """The first time the datasource parameters are saved, introspect the db and save the
    structure in the fields pickled_*
    """
    if created:
        instance._pickle_all()
        instance.time_introspected = timezone.now()
        instance.save()


class Chart(models.Model):
    """Stores the parameters required to create a chart for a particular user with a specific datasource.
    """
    user = models.ForeignKey(User)
    name = models.CharField(max_length=100)
    datasource = models.ForeignKey(Datasource)
    table_name = models.CharField(max_length=100, null=True, blank=True)
    x_axis = models.CharField(max_length=100, null=True, blank=True)
    y_axis = models.CharField(max_length=100, null=True, blank=True)
    aggr_func_name = models.CharField(max_length=100, null=True, blank=True)
    time_created = models.DateTimeField(null=True, blank=True)

    def _get_column_chart_data(self):
        session = self.datasource.session
        aggr_func = getattr(sqlalchemy.func, str(self.aggr_func_name))
        table_base = self.datasource.bases[self.table_name]
        print str(self.x_axis), str(self.y_axis)  # TODO: Fix the name.
        try:
            return session.query(getattr(table_base, str(self.x_axis)),
                             aggr_func(getattr(table_base, str(self.y_axis))))\
                          .group_by(getattr(table_base, str(self.x_axis))).all()
        except sqlalchemy.exc.OperationalError:
            raise ChartCreationError

    def _plot_column_chart(self):
        data = self._get_column_chart_data()
        categories, series = zip(*data)
        title = self.name
        x_axis_title, y_axis_title = str(self.x_axis), str(self.y_axis)
        series_name = '%s(%s)' % (str(self.aggr_func_name), str(self.y_axis))
        return render_highcharts_options('chartchemy_chart', categories, series,
                                         title, x_axis_title, y_axis_title,
                                         series_name)

