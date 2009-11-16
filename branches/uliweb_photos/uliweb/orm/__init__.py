# This module is used for wrapping SqlAlchemy to a simple ORM
# Author: limodou <limodou@gmail.com>
# 2008.06.11


__all__ = ['Field', 'get_connection', 'Model', 'create_all',
    'set_debug_query', 'set_auto_create', 'set_connection',
    'CHAR', 'BLOB', 'TEXT', 'DECIMAL', 'Index', 'datetime', 'decimal',
    'BlobProperty', 'BooleanProperty', 'DateProperty', 'DateTimeProperty',
    'TimeProperty', 'DecimalProperty', 'FloatProperty', 'SQLStorage',
    'IntegerProperty', 'Property', 'StringProperty', 'CharProperty',
    'TextProperty', 'UnicodeProperty', 'Reference', 'ReferenceProperty',
    'SelfReference', 'SelfReferenceProperty', 'OneToOne', 'ManyToMany',
    'ReservedWordError', 'BadValueError', 'DuplicatePropertyError', 
    'ModelInstanceError', 'KindError', 'ConfigurationError',
    'BadPropertyTypeError']

__default_connection__ = None  #global connection instance
__auto_create__ = True
__debug_query__ = None
__default_encoding__ = 'utf-8'

import decimal
import threading
import datetime
from uliweb.utils import date
from sqlalchemy import *
from sqlalchemy.sql import select

now = date.now

_default_metadata = MetaData()

class Error(Exception):pass
class ReservedWordError(Error):pass
class ModelInstanceError(Error):pass
class DuplicatePropertyError(Error):
  """Raised when a property is duplicated in a model definition."""
class BadValueError(Error):pass
class BadPropertyTypeError(Error):pass
class KindError(Error):pass
class ConfigurationError(Error):pass

_SELF_REFERENCE = object()

def set_auto_create(flag):
    global __auto_create__
    __auto_create__ = flag
    
def set_debug_query(flag):
    global __debug_query__
    __debug_query__ = flag
    
def set_encoding(encoding):
    global __default_encoding__
    __default_encoding__ = encoding

def get_connection(connection='', metadata=_default_metadata, default=True, debug=None, **args):
    """
    default encoding is utf-8
    """
    global __default_connection__
  
    debug = debug or __debug_query__
    
    if default and __default_connection__:
        return __default_connection__
    
    if 'strategy' not in args:
        args['strategy'] = 'threadlocal'
        
    if isinstance(connection, (str, unicode)):
        db = create_engine(connection, **args)
    else:
        db = connection
    if default:
        __default_connection__ = db
        
    if debug:
        db.echo = debug
        
    if not metadata:
        metadata = MetaData(db)
    else:
        metadata.bind = db
        
    db.metadata = metadata
    create_all(db)
    return db

def set_connection(db, default=True, debug=False):
    global __default_connection__

    if default:
        __default_connection__ = db
    if debug:
        db.echo = debug
    metadata = MetaData(db)
    db.metadata = metadata

class SQLStorage(dict):
    """
    a dictionary that let you do d['a'] as well as d.a
    """
    def __getattr__(self, key): return self[key]
    def __setattr__(self, key, value):
        if self.has_key(key):
            raise SyntaxError, 'Object exists and cannot be redefined'
        self[key] = value
    def __repr__(self): return '<SQLStorage ' + dict.__repr__(self) + '>'

def check_reserved_word(f):
    if f in ['put', 'save'] or f in dir(Model):
        raise ReservedWordError(
            "Cannot define property using reserved word '%s'. " % f
            )

__models__ = {}

def create_all(db=None):
    global __models__
    for cls in __models__.values():
        if not cls['created'] and cls['model']:
            cls['model'].bind(db.metadata, auto_create=True)
            cls['created'] = True
        
def set_model(model, tablename=None, created=None):
    """
    Register an model and tablename to a global variable.
    model could be a string format, i.e., 'uliweb.contrib.auth.models.User'
    """
    global __models__
    if isinstance(model, type) and issubclass(model, Model):
        tablename = model.tablename
    item = __models__.setdefault(tablename, {})
    if created is not None:
        item['created'] = created
    else:
        item['created'] = None
    if isinstance(model, (str, unicode)):
        model_name = model
        model = None
    else:
        model_name = ''
    item['model'] = model
    item['model_name'] = model_name
    
def get_model(model):
    """
    Return a real model object, so if the model is already a Model class, then
    return it directly. If not then import it.
    """
    global __models__
    if model is _SELF_REFERENCE:
        return model
    if isinstance(model, type) and issubclass(model, Model):
        return model
    if model in __models__:
        item = __models__[model]
        m = item['model']
        if isinstance(m, type)  and issubclass(m, Model):
            return m
        else:
            m, name = item['model_name'].rsplit('.', 1)
            try:
                mod = __import__(m, {}, {}, [''])
                model = getattr(mod, name)
                item['model'] = model
                return model
            except:
                raise Error("Can't import the model %s from %s" % (name, m))
    else:
        raise Error("Can't found the model %s" % model)
    
def valid_model(model):
    global __models__
    if isinstance(model, type) and issubclass(model, Model):
        return True
    return model in __models__
        
class ModelMetaclass(type):
    def __init__(cls, name, bases, dct):
        super(ModelMetaclass, cls).__init__(name, bases, dct)
        if name == 'Model':
            return
        cls._set_tablename()
        
        cls.properties = {}
        defined = set()
        for base in bases:
            if hasattr(base, 'properties'):
                property_keys = base.properties.keys()
                duplicate_properties = defined.intersection(property_keys)
                if duplicate_properties:
                    raise DuplicatePropertyError(
                        'Duplicate properties in base class %s already defined: %s' %
                        (base.__name__, list(duplicate_properties)))
                defined.update(property_keys)
                cls.properties.update(base.properties)
        
        for attr_name in dct.keys():
            attr = dct[attr_name]
            if isinstance(attr, Property):
                check_reserved_word(attr_name)
                if attr_name in defined:
                    raise DuplicatePropertyError('Duplicate property: %s' % attr_name)
                defined.add(attr_name)
                cls.properties[attr_name] = attr
                attr.__property_config__(cls, attr_name)
                
        #if there is already defined primary_key, the id will not be primary_key
        has_primary_key = bool([v for v in cls.properties.itervalues() if 'primary_key' in v.kwargs])
        
        if 'id' not in cls.properties:
            cls.properties['id'] = f = Field(int, autoincrement=True, 
                primary_key=not has_primary_key, default=None)
            f.__property_config__(cls, 'id')
            setattr(cls, 'id', f)

        fields_list = [(k, v) for k, v in cls.properties.items() if not isinstance(v, ManyToMany)]
        fields_list.sort(lambda x, y: cmp(x[1].creation_counter, y[1].creation_counter))
        cls._fields_list = fields_list
        
        cls.bind(auto_create=__auto_create__)
        
class Property(object):
    data_type = str
    field_class = String
    creation_counter = 0

    def __init__(self, verbose_name=None, name=None, default=None,
         required=False, validators=None, choices=None, max_length=None, **kwargs):
        self.verbose_name = verbose_name
        self.property_name = None
        self.name = name
        self.default = default
        self.required = required
        self.validators = validators or []
        if not isinstance(self.validators, (tuple, list)):
            self.validators = [self.validators]
        self.choices = choices
        self.max_length = max_length
        self.kwargs = kwargs
        self.creation_counter = Property.creation_counter
        self.value = None
        Property.creation_counter += 1
        
    def create(self, cls):
        args = self.kwargs.copy()
        args['key'] = self.name
        if callable(self.default):
            args['default'] = self.default
        args['primary_key'] = self.kwargs.pop('primary_key', False)
        args['autoincrement'] = self.kwargs.pop('autoincrement', False)
        args['index'] = self.kwargs.pop('index', False)
        args['unique'] = self.kwargs.pop('unique', False)
        args['nullable'] = self.kwargs.pop('nullable', True)
        f_type = self._create_type()
        return Column(self.property_name, f_type, **args)

    def _create_type(self):
        if self.max_length:
            f_type = self.field_class(self.max_length)
        else:
            f_type = self.field_class
        return f_type
    
    def __property_config__(self, model_class, property_name):
        self.model_class = model_class
        self.property_name = property_name
        if not self.name:
            self.name = property_name

    def __get__(self, model_instance, model_class):
        if model_instance is None:
            return self

        try:
            return getattr(model_instance, self._attr_name())
        except AttributeError:
            return None
        
    def __set__(self, model_instance, value):
        if model_instance is None:
            return
        
        value = self.validate(value)
        #add value to model_instance._changed_value, so that you can test if
        #a object really need to save
        setattr(model_instance, self._attr_name(), value)

    def default_value(self, model_instance=None):
        if callable(self.default):
            return self.default(model_instance)
        return self.default

    def validate(self, value):
        if self.empty(value):
            if self.required:
                raise BadValueError('Property %s is required' % self.name)
        else:
            if self.choices:
                match = False
                for choice in self.choices:
                    if isinstance(choice, tuple):
                        if choice[0] == value:
                            match = True
                    else:
                        if choice == value:
                            match = True
                    if match:
                        break
                if not match:
                    c = []
                    for choice in self.choices:
                        if isinstance(choice, tuple):
                            c.append(choice[0])
                        else:
                            c.append(choice)
                    raise BadValueError('Property %s is %r; must be one of %r' %
                        (self.name, value, c))
        if (value is not None) and self.data_type and (not isinstance(value, self.data_type)):
            try:
                value = self.convert(value)
            except TypeError, err:
                raise BadValueError('Property %s must be convertible '
                    'to a string or unicode (%s)' % (self.name, err))
        
        for v in self.validators:
            v(value)
        return value

    def empty(self, value):
        return value is None

    def get_value_for_datastore(self, model_instance):
        return self.__get__(model_instance, model_instance.__class__)

    def make_value_from_datastore(self, value):
        return value
    
    def convert(self, value):
        return self.data_type(value)
    
    def __repr__(self):
        return ("<%s 'type':%r, 'verbose_name':%r, 'name':%r, " 
            "'default':%r, 'required':%r, 'validator':%r, "
            "'chocies':%r, 'max_length':%r, 'kwargs':%r>"
            % (
            self.__class__.__name__,
            self.data_type, 
            self.verbose_name,
            self.name,
            self.default,
            self.required,
            self.validator,
            self.choices,
            self.max_length,
            self.kwargs)
            )
            
    def _attr_name(self):
        return '_' + self.name + '_'
    
    def to_str(self, v):
        return str(v)
    
class CharProperty(Property):
    data_type = unicode
    field_class = CHAR
    
    def __init__(self, verbose_name=None, default='', max_length=30, **kwds):
        super(CharProperty, self).__init__(verbose_name, default=default, max_length=max_length, **kwds)
    
    def empty(self, value):
        return not value
    
    def convert(self, value):
        if isinstance(value, str):
            return unicode(value, __default_encoding__)
        else:
            return self.data_type(value)
    
    def _create_type(self):
        if self.max_length:
            f_type = self.field_class(self.max_length, convert_unicode=True)
        else:
            f_type = self.field_class
        return f_type
    
    def to_str(self, v):
        return v
    
class StringProperty(CharProperty):
    field_class = String
    
class UnicodeProperty(CharProperty):
    field_class = Unicode
    
class TextProperty(StringProperty):
    field_class = Text
    
    def __init__(self, verbose_name=None, default='', **kwds):
        super(TextProperty, self).__init__(verbose_name, default=default, max_length=None, **kwds)
    
class BlobProperty(StringProperty):
    field_class = BLOB
    
    def __init__(self, verbose_name=None, default='', **kwds):
        super(BlobProperty, self).__init__(verbose_name, default=default, max_length=None, **kwds)
    
class DateTimeProperty(Property):
    data_type = datetime.datetime
    field_class = DateTime
    
    def __init__(self, verbose_name=None, auto_now=False, auto_now_add=False,
            format=None, **kwds):
        super(DateTimeProperty, self).__init__(verbose_name, **kwds)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        self.format = format

    def validate(self, value):
        value = super(DateTimeProperty, self).validate(value)
        if value and not isinstance(value, self.data_type):
            raise BadValueError('Property %s must be a %s' %
                (self.name, self.data_type.__name__))
        return value
    
    @staticmethod
    def now():
        return now()

    def convert(self, value):
        d = date.to_datetime(value, format=self.format)
        if d:
            return d
        raise BadValueError('The datetime value is not a valid format')
    
    def to_str(self, v):
        return v.strftime('%Y-%m-%d %H:%M:%S')
    
class DateProperty(DateTimeProperty):
    data_type = datetime.date
    field_class = Date
    
    def validate(self, value):
        value = super(DateProperty, self).validate(value)
        if value:
            return date.to_date(value)
        return value
    
    def make_value_from_datastore(self, value):
        if value is not None:
            value = date.to_date(value)
        return value

    #if the value is datetime.datetime, this convert will not be invoked at all
    #Todo: so if I need to fix it?
    #this is fixed by call date.to_date(value) in validate() method
    def convert(self, value):
        assert isinstance(value, (str, unicode, datetime.datetime)), \
            'The value of DataProperty should be str, unicode, or datetime.datetime type.'\
            'But it is %s' % type(value).__name__
        if isinstance(value, datetime.datetime):
            return date.to_date(value)
        else:
            d = date.to_datetime(value)
            if d:
                return date.to_date(d)
            raise BadValueError('The date value is not a valid format')
    
    def to_str(self, v):
        return v.strftime('%Y-%m-%d')
        
class TimeProperty(DateTimeProperty):
    """A time property, which stores a time without a date."""

    data_type = datetime.time
    field_class = Time
    
    def make_value_from_datastore(self, value):
        if value is not None:
            value = date.to_time(value)
        return value

    def convert(self, value):
        assert isinstance(value, (str, unicode, datetime.datetime)), \
            'The value of DataProperty should be str, unicode, or datetime.datetime type.'\
            'But it is %s' % type(value).__name__
        if isinstance(value, datetime.datetime):
            return date.to_time(value)
        else:
            d = date.to_datetime(value)
            if d:
                return date.to_time(d)
            raise BadValueError('The time value is not a valid format')
    
    def to_str(self, v):
        return v.strftime('%H:%M:%S')
        
class IntegerProperty(Property):
    """An integer property."""

    data_type = int
    field_class = Integer
    
    def __init__(self, verbose_name=None, default=0, **kwds):
        super(IntegerProperty, self).__init__(verbose_name, default=default, **kwds)
    
    def validate(self, value):
        value = super(IntegerProperty, self).validate(value)
        if value and not isinstance(value, (int, long, bool)):
            raise BadValueError('Property %s must be an int, long or bool, not a %s'
                % (self.name, type(value).__name__))
        return value

class FloatProperty(Property):
    """A float property."""

    data_type = float
    field_class = Float
    
    def __init__(self, verbose_name=None, default=0.0, **kwds):
        super(FloatProperty, self).__init__(verbose_name, default=default, **kwds)
        precision = 10
        if self.max_length:
            precision = self.max_length
        if self.kwargs.get('precision', None):
            precision = self.kwargs.pop('precision')
        self.precision = precision
        
        length = 2
        if self.kwargs.get('length', None):
            length = self.kwargs.pop('length')
        self.length = length
        
    def _create_type(self):
        f_type = self.field_class(**dict(precision=self.precision, length=self.length))
        return f_type
    
    def validate(self, value):
        value = super(FloatProperty, self).validate(value)
        if value is not None and not isinstance(value, float):
            raise BadValueError('Property %s must be a float, not a %s' 
                % (self.name, type(value).__name__))
        return value
    
class DecimalProperty(Property):
    """A float property."""

    data_type = decimal.Decimal
    field_class = Numeric
    
    def __init__(self, verbose_name=None, default='0.0', **kwds):
        super(DecimalProperty, self).__init__(verbose_name, default=default, **kwds)
   
    def validate(self, value):
        value = super(DecimalProperty, self).validate(value)
        if value is not None and not isinstance(value, decimal.Decimal):
            raise BadValueError('Property %s must be a decimal, not a %s'
                % (self.name, type(value).__name__))
        return value

class BooleanProperty(Property):
    """A boolean property."""

    data_type = bool
    field_class = Boolean
    
    def __init__(self, verbose_name=None, default=False, **kwds):
        super(BooleanProperty, self).__init__(verbose_name, default=default, **kwds)
    
    def validate(self, value):
        value = super(BooleanProperty, self).validate(value)
        if value is not None and not isinstance(value, bool):
            raise BadValueError('Property %s must be a boolean, not a %s' 
                % (self.name, type(value).__name__))
        return value

class ReferenceProperty(Property):
    """A property that represents a many-to-one reference to another model.
    """
    field_class = Integer

    def __init__(self, reference_class=None, verbose_name=None, collection_name=None, 
        reference_fieldname=None, **attrs):
        """Construct ReferenceProperty.

        Args:
            reference_class: Which model class this property references.
            verbose_name: User friendly name of property.
            collection_name: If provided, alternate name of collection on
                reference_class to store back references.    Use this to allow
                a Model to have multiple fields which refer to the same class.
            reference_fieldname used to specify which fieldname of reference_class
                should be referenced
        """
        super(ReferenceProperty, self).__init__(verbose_name, **attrs)

        self.collection_name = collection_name
        self.reference_fieldname = reference_fieldname

        if reference_class is None:
            reference_class = Model
            
        if not (
                (isinstance(reference_class, type) and issubclass(reference_class, Model)) or
                reference_class is _SELF_REFERENCE or
                valid_model(reference_class)):
            raise KindError('reference_class must be Model or _SELF_REFERENCE')
        self.reference_class = self.data_type = get_model(reference_class)
        
    def create(self, cls):
        args = self.kwargs.copy()
        args['key'] = self.name
        if not callable(self.default):
            args['default'] = self.default
        args['primary_key'] = self.kwargs.pop('primary_key', False)
        args['autoincrement'] = self.kwargs.pop('autoincrement', False)
        args['index'] = self.kwargs.pop('index', False)
        args['unique'] = self.kwargs.pop('unique', False)
        args['nullable'] = self.kwargs.pop('nullable', True)
        f_type = self._create_type()
#        return Column(self.property_name, f_type, ForeignKey("%s.id" % self.reference_class.tablename), **args)
        return Column(self.property_name, f_type, **args)
    
    def __property_config__(self, model_class, property_name):
        """Loads all of the references that point to this model.
        """
        super(ReferenceProperty, self).__property_config__(model_class, property_name)

        if self.reference_class is _SELF_REFERENCE:
            self.reference_class = self.data_type = model_class

        if self.collection_name is None:
            self.collection_name = '%s_set' % (model_class.tablename)
        if hasattr(self.reference_class, self.collection_name):
            raise DuplicatePropertyError('Class %s already has property %s'
                 % (self.reference_class.__name__, self.collection_name))
        setattr(self.reference_class, self.collection_name,
            _ReverseReferenceProperty(model_class, property_name, self._id_attr_name()))

    def __get__(self, model_instance, model_class):
        """Get reference object.

        This method will fetch unresolved entities from the datastore if
        they are not already loaded.

        Returns:
            ReferenceProperty to Model object if property is set, else None.
        """
        if model_instance is None:
            return self
        if hasattr(model_instance, self._id_attr_name()):
            reference_id = getattr(model_instance, self._attr_name())
        else:
            reference_id = None
        if reference_id is not None:
            #this will cache the reference object
            resolved = getattr(model_instance, self._resolved_attr_name())
            if resolved is not None:
                return resolved
            else:
                id_field = self._id_attr_name()
                d = self.reference_class.c[id_field]
                instance = self.reference_class.get(d==reference_id)
                if instance is None:
                    raise Error('ReferenceProperty failed to be resolved')
                setattr(model_instance, self._resolved_attr_name(), instance)
                return instance
        else:
            return None
        
    def get_value_for_datastore(self, model_instance):
        if not model_instance:
            return None
        else:
            return getattr(model_instance, self._attr_name(), None)

    def __set__(self, model_instance, value):
        """Set reference."""
        value = self.validate(value)
        if value is not None:
            if isinstance(value, (int, long)):
                setattr(model_instance, self._attr_name(), value)
                setattr(model_instance, self._resolved_attr_name(), None)
            else:
                setattr(model_instance, self._attr_name(), value.id)
                setattr(model_instance, self._resolved_attr_name(), value)
        else:
            setattr(model_instance, self._attr_name(), None)
            setattr(model_instance, self._resolved_attr_name(), None)

    def validate(self, value):
        """Validate reference.

        Returns:
            A valid value.

        Raises:
            BadValueError for the following reasons:
                - Value is not saved.
                - Object not of correct model type for reference.
        """
        if isinstance(value, (int, long)):
            return value

        if value is not None and not value.is_saved():
            raise BadValueError(
                    '%s instance must be saved before it can be stored as a '
                    'reference' % self.reference_class.__class__.__name__)

        value = super(ReferenceProperty, self).validate(value)

        if value is not None and not isinstance(value, self.reference_class):
            raise KindError('Property %s must be an instance of %s' %
                    (self.name, self.reference_class.__class__.__name__))

        return value

    def _id_attr_name(self):
        """Get attribute of referenced id.
        #todo add id function or key function to model
        """
        if not self.reference_fieldname:
            self.reference_fieldname = 'id'
        return self.reference_fieldname

    def _resolved_attr_name(self):
        """Get attribute of resolved attribute.

        The resolved attribute is where the actual loaded reference instance is
        stored on the referring model instance.

        Returns:
            Attribute name of where to store resolved reference model instance.
        """
        return '_RESOLVED' + self._attr_name()

Reference = ReferenceProperty

class OneToOne(ReferenceProperty):
    def create(self, cls):
        args = self.kwargs.copy()
        args['key'] = self.name
        if not callable(self.default):
            args['default'] = self.default
        args['primary_key'] = self.kwargs.pop('primary_key', False)
        args['autoincrement'] = self.kwargs.pop('autoincrement', False)
        args['index'] = self.kwargs.pop('index', False)
        args['unique'] = self.kwargs.pop('unique', True)
        args['nullable'] = self.kwargs.pop('nullable', True)
        f_type = self._create_type()
#        return Column(self.property_name, f_type, ForeignKey("%s.id" % self.reference_class.tablename), **args)
        return Column(self.property_name, f_type, **args)

    def __property_config__(self, model_class, property_name):
        """Loads all of the references that point to this model.
        """
        super(ReferenceProperty, self).__property_config__(model_class, property_name)
    
        if self.reference_class is _SELF_REFERENCE:
            self.reference_class = self.data_type = model_class
    
        if self.collection_name is None:
            self.collection_name = '%s' % (model_class.tablename)
        if hasattr(self.reference_class, self.collection_name):
            raise DuplicatePropertyError('Class %s already has property %s'
                 % (self.reference_class.__name__, self.collection_name))
        setattr(self.reference_class, self.collection_name,
            _OneToOneReverseReferenceProperty(model_class, property_name, self._id_attr_name()))
    
class Result(object):
    def __init__(self, model=None, condition=None, *args, **kwargs):
        self.model = model
        self.condition = condition
        self.columns = [self.model.table]
        self.funcs = []
        self.args = args
        self.kwargs = kwargs
        self.result = None
        
    def all(self):
        return self
    
    def count(self):
        if not self.model or not self.condition:
            return 0
        return self.model.count(self.condition)

    def delete(self):
        if not self.model or not self.condition:
            return
        return self.model.remove(self.condition)
    
    def filter(self, condition):
        self.condition = condition & self.condition
        return self
    
    def order_by(self, *args, **kwargs):
        self.funcs.append(('order_by', args, kwargs))
        return self
    
    def values(self, *args, **kwargs):
        self.funcs.append(('with_only_columns', (args,), kwargs))
        return self.run()
    
    def values_one(self, *args, **kwargs):
        self.funcs.append(('with_only_columns', (args,), kwargs))
        self.run()
        result = self.result.fetchone()
        return result

    def distinct(self, *args, **kwargs):
        self.funcs.append(('distinct', args, kwargs))
        return self
    
    def limit(self, *args, **kwargs):
        self.funcs.append(('limit', args, kwargs))
        return self

    def offset(self, *args, **kwargs):
        self.funcs.append(('offset', args, kwargs))
        return self
    
    def run(self):
        query = select(self.columns, self.condition)
        for func, args, kwargs in self.funcs:
            query = getattr(query, func)(*args, **kwargs)
        self.result = query.execute()
        return self.result
    
    def one(self):
        self.run()
        result = self.result.fetchone()
        if result:
            d = self.model._data_prepare(result)
            o = self.model(**d)
            o._set_saved()
            return o
    
    def __del__(self):
        if self.result:
            self.result.close()

    def __iter__(self):
        self.result = self.run()
        while 1:
            obj = self.result.fetchone()
            if not obj:
                raise StopIteration
            d = self.model._data_prepare(obj)
            o = self.model(**d)
            o._set_saved()
            yield o
   
class ManyResult(Result):
    def __init__(self, modela, modelb, table, fielda, fieldb, valuea):
        self.modela = modela
        self.modelb = modelb
        self.table = table
        self.fielda = fielda
        self.fieldb = fieldb
        self.valuea = valuea
        self.columns = [self.modelb.table]
        self.condition = None
        self.funcs = []
        self.result = None
        
    def add(self, *objs):
        for o in objs:
            assert isinstance(o, (int, long, Model)), 'Value should be Integer or instance of Property, but it is %s' % type(o).__name__
            if isinstance(o, (int, long)):
                v = o
            else:
                v = o.id
            d = {self.fielda:self.valuea, self.fieldb:v}
            self.table.insert().execute(**d)
            
    def clear(self):
        self.delete()
            
    def delete(self, *objs):
        if objs:
            ids = []
            for o in objs:
                assert isinstance(o, (int, long, Model)), 'Value should be Integer or instance of Property, but it is %s' % type(o).__name__
                if isinstance(o, (int, long)):
                    ids.append(o)
                else:
                    ids.append(o.id)
            self.table.delete((self.table.c[self.fielda]==self.valuea) & (self.table.c[self.fieldb].in_(ids))).execute()
        else:
            self.table.delete(self.table.c[self.fielda]==self.valuea).execute()
    
    def count(self):
        result = self.table.count(self.table.c[self.fielda]==self.valuea).execute()
        count = 0
        if result:
            r = result.fetchone()
            if r:
                count = r[0]
        else:
            count = 0
        return count
    
    def run(self):
        query = select([self.table.c[self.fieldb]], self.table.c[self.fielda]==self.valuea)
        ids = [x[0] for x in query.execute()]
        query = select(self.columns, self.modelb.c.id.in_(ids) & self.condition)
        for func, args, kwargs in self.funcs:
            query = getattr(query, func)(*args, **kwargs)
        self.result = query.execute()
        return self.result
        
    def one(self):
        self.run()
        result = self.result.fetchone()
        if result:
            d = self.modelb._data_prepare(result)
            o = self.modelb(**d)
            o._set_saved()
            return o

    def __del__(self):
        if self.result:
            self.result.close()
    
    def __iter__(self):
        self.run()
        while 1:
            obj = self.result.fetchone()
            if not obj:
                raise StopIteration
            d = self.modelb._data_prepare(obj)
            o = self.modelb(**d)
            o._set_saved()
            yield o
        
class ManyToMany(ReferenceProperty):
    def create(self, cls):
        self.fielda = a = "%s_id" % self.model_class.tablename
        self.fieldb = b = "%s_id" % self.reference_class.tablename
        a_id = "%s.id" % self.model_class.tablename
        b_id = "%s.id" % self.reference_class.tablename
        
        #add autoincrement=False according to:
        #http://www.sqlalchemy.org/docs/05/reference/dialects/mysql.html#keys
        self.table = Table(self.tablename, cls.metadata,
            Column(a, Integer, primary_key=True, autoincrement=False),
            Column(b, Integer, primary_key=True, autoincrement=False),
#            ForeignKeyConstraint([a], [a_id]),
#            ForeignKeyConstraint([b], [b_id]),
        )
        cls.manytomany.append(self.table)
        return
    
    def __property_config__(self, model_class, property_name):
        """Loads all of the references that point to this model.
        """
        super(ReferenceProperty, self).__property_config__(model_class, property_name)
    
        if self.reference_class is _SELF_REFERENCE:
            self.reference_class = self.data_type = model_class
        self.tablename = '%s_%s_%s' % (model_class.tablename, self.reference_class.tablename, property_name)
        if self.collection_name is None:
            self.collection_name = '%s_set' % (model_class.tablename)
        if hasattr(self.reference_class, self.collection_name):
            raise DuplicatePropertyError('Class %s already has property %s'
                 % (self.reference_class.__name__, self.collection_name))
        setattr(self.reference_class, self.collection_name,
            _ManyToManyReverseReferenceProperty(self, self._id_attr_name()))
    
    def __get__(self, model_instance, model_class):
        """Get reference object.
    
        This method will fetch unresolved entities from the datastore if
        they are not already loaded.
    
        Returns:
            ReferenceProperty to Model object if property is set, else None.
        """
        if model_instance:
            if hasattr(model_instance, self._id_attr_name()):
                reference_id = getattr(model_instance, self._id_attr_name())
            else:
                reference_id = None
            x = ManyResult(self.model_class, self.reference_class, self.table,
                self.fielda, self.fieldb, reference_id)
            return x
        else:
            return self
    
    def __set__(self, model_instance, value):
        pass
    
    def get_value_for_datastore(self, model_instance):
        """Get key of reference rather than reference itself."""
        return getattr(model_instance, self._id_attr_name())
    
def SelfReferenceProperty(verbose_name=None, collection_name=None, **attrs):
    """Create a self reference.
    """
    if 'reference_class' in attrs:
        raise ConfigurationError(
                'Do not provide reference_class to self-reference.')
    return ReferenceProperty(_SELF_REFERENCE, verbose_name, collection_name, **attrs)

SelfReference = SelfReferenceProperty

class _ReverseReferenceProperty(Property):
    """The inverse of the Reference property above.

    We construct reverse references automatically for the model to which
    the Reference property is pointing to create the one-to-many property for
    that model.    For example, if you put a Reference property in model A that
    refers to model B, we automatically create a _ReverseReference property in
    B called a_set that can fetch all of the model A instances that refer to
    that instance of model B.
    """

    def __init__(self, model, reference_id, reversed_id):
        """Constructor for reverse reference.

        Constructor does not take standard values of other property types.

        """
        self._model = model
        self._reference_id = reference_id    #B Reference(A) this is B's id
        self._reversed_id = reversed_id    #A's id

    def __get__(self, model_instance, model_class):
        """Fetches collection of model instances of this collection property."""
        if model_instance is not None:
            _id = getattr(model_instance, self._reversed_id, None)
            if _id is not None:
                b_id = self._reference_id
                d = self._model.c[self._reference_id]
                return Result(self._model, d==_id)
            else:
                return Result()
        else:
            return self

    def __set__(self, model_instance, value):
        """Not possible to set a new collection."""
        raise BadValueError('Virtual property is read-only')
    
class _OneToOneReverseReferenceProperty(_ReverseReferenceProperty):
    def __init__(self, model, reference_id, reversed_id):
        """Constructor for reverse reference.
    
        Constructor does not take standard values of other property types.
    
        """
        self._model = model
        self._reference_id = reference_id    #B Reference(A) this is B's id
        self._reversed_id = reversed_id    #A's id

    def __get__(self, model_instance, model_class):
        """Fetches collection of model instances of this collection property."""
        if model_instance:
            _id = getattr(model_instance, self._reversed_id, None)
            if _id is not None:
                b_id = self._reference_id
                d = self._model.c[self._reference_id]
                return self._model.get(d==_id)
            else:
                return None
        else:
            return self
    
class _ManyToManyReverseReferenceProperty(_ReverseReferenceProperty):
    def __init__(self, reference_property, reversed_id):
        """Constructor for reverse reference.
    
        Constructor does not take standard values of other property types.
    
        """
        self.reference_property = reference_property
        self._reversed_id = reversed_id

    def __get__(self, model_instance, model_class):
        """Fetches collection of model instances of this collection property."""
        if model_instance:
            if hasattr(model_instance, self._reversed_id):
                reference_id = getattr(model_instance, self._reversed_id)
            else:
                reference_id = None
            x = ManyResult(self.reference_property.reference_class, 
                self.reference_property.model_class, self.reference_property.table,
                self.reference_property.fieldb, self.reference_property.fielda, reference_id)
            return x
        else:
            return self


_fields_mapping = {
    str:StringProperty,
    CHAR:CharProperty,
    unicode: UnicodeProperty,
    TEXT:TextProperty,
    BLOB:BlobProperty,
#    file:FileProperty,
    int:IntegerProperty,
    float:FloatProperty,
    bool:BooleanProperty,
    datetime.datetime:DateTimeProperty,
    datetime.date:DateProperty,
    datetime.time:TimeProperty,
    decimal.Decimal:DecimalProperty,
    DECIMAL:DecimalProperty,
}
def Field(type, **kwargs):
    t = _fields_mapping.get(type, type)
    return t(**kwargs)

class Model(object):

    __metaclass__ = ModelMetaclass
    
    _lock = threading.Lock()
    _c_lock = threading.Lock()
    
    def __init__(self, **kwargs):
        self._old_values = {}
        for prop in self.properties.values():
            if not isinstance(prop, ManyToMany):
                if prop.name in kwargs:
                    value = kwargs[prop.name]
                else:
                    value = prop.default_value(self)
                prop.__set__(self, value)
        
    def _set_saved(self):
        self._old_values = self.to_dict()
        
    def to_dict(self, *fields):
        d = {}
        for k, v in self.properties.items():
            if fields and not k in fields:
                continue
            if not isinstance(v, ManyToMany):
                t = v.get_value_for_datastore(self)
                if isinstance(t, Model):
                    t = t.id
                d[k] = self.field_str(t)
        return d
    
    def field_str(self, v):
        if isinstance(v, datetime.datetime):
            return v.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(v, datetime.date):
            return v.strftime('%Y-%m-%d')
        elif isinstance(v, datetime.time):
            return v.strftime('%H:%M:%S')
        elif isinstance(v, decimal.Decimal):
            return str(v)
        else:
            return v
           
    def _get_data(self):
        """
        Get the changed property, it'll be used to save the object
        """
        if self.id is None:
            d = {}
            for k, v in self.properties.items():
                if not isinstance(v, ManyToMany):
                    x = v.get_value_for_datastore(self)
                    if isinstance(x, Model):
                        x = x.id
                    if isinstance(v, DateTimeProperty) and v.auto_now_add:
                        d[k] = v.now()
                    elif x is not None:
                        d[k] = x
                    else:
                        x = v.default_value(self)
                        if x:
                            d[k] = x
        else:
            d = {}
            d['id'] = self.id
            for k, v in self.properties.items():
                if not isinstance(v, ManyToMany):
                    t = self._old_values.get(k, None)
                    x = v.get_value_for_datastore(self)
                    if isinstance(x, Model):
                        x = x.id
                    if isinstance(v, DateTimeProperty) and v.auto_now:
                        d[k] = v.now()
                    elif (x is not None) and (t != self.field_str(x)):
                        d[k] = x
        
        return d
            
    def is_saved(self):
        return bool(self.id) 
            
    def put(self):
        d = self._get_data()
        if d:
            if not self.id:
                obj = self.table.insert().execute(**d)
                setattr(self, 'id', obj.lastrowid)
            else:
                _id = d.pop('id')
                if d:
                    self.table.update(self.table.c.id == self.id).execute(**d)
            for k, v in d.items():
                x = self.properties[k].get_value_for_datastore(self)
                if self.field_str(x) != self.field_str(v):
                    setattr(self, k, v)
            self._set_saved()
        return self
    
    save = put
    
    def delete(self):
        self.table.delete(self.table.c.id==self.id).execute()
        self.id = None
        self._old_values = {}
            
    def __repr__(self):
        s = []
        for k, v in self._fields_list:
            s.append('%r:%r' % (k, getattr(self, k, None)))
        return ('<%s {' % self.__class__.__name__) + ','.join(s) + '}>'
           
    #classmethod========================================================

    @classmethod
    def _set_tablename(cls, appname=None):
        if not hasattr(cls, '__tablename__'):
            name = cls.__name__.lower()
        else:
            name = cls.__tablename__
        if appname:
            name = appname.lower() + '_' + name
        cls.tablename = name
        
    @classmethod
    def bind(cls, metadata=None, auto_create=False):
        cls._lock.acquire()
        try:
            cls.metadata = metadata or _default_metadata
            if cls.metadata and not hasattr(cls, '_bound'):
                cols = []
                cls.manytomany = []
                for k, f in cls.properties.items():
                    c = f.create(cls)
                    if c:
                        cols.append(c)
                        
                #if there is already a same name table, then remove the old one
                #replace with new one
                t = cls.metadata.tables.get(cls.tablename, None)
                if t:
                    cls.metadata.remove(t)
                args = getattr(cls, '__table_args__', {})
                args['mysql_charset'] = 'utf8'
                cls.table = Table(cls.tablename, cls.metadata, *cols, **args)
                
                cls.c = cls.table.c
                cls.columns = cls.table.c
                
                if hasattr(cls, 'OnInit'):
                    cls.OnInit()
                
                cls._bound = True
            if cls._bound:
                if auto_create:
                    #only metadata is _default_metadata and bound 
                    #then the table will be created
                    #otherwise the creation of tables will be via: create_all(db)
                    if cls.metadata == _default_metadata and cls.metadata.bind:
                        cls.create()
                        set_model(cls, created=True)
                    else:
                        set_model(cls)
        finally:
            cls._lock.release()
            
    @classmethod
    def create(cls):
        cls._c_lock.acquire()
        try:
            if not cls.table.exists():
                cls.table.create(checkfirst=True)
            for x in cls.manytomany:
                if not x.exists():
                    x.create(checkfirst=True)
        finally:
            cls._c_lock.release()
            
    @classmethod
    def get(cls, condition=None, **kwargs):
        if isinstance(condition, (int, long)):
            return cls.filter(cls.c.id==condition).one()
        else:
            return cls.filter(condition).one()
    
    @classmethod
    def _data_prepare(cls, record):
        d = {}
        for k, v in record.items():
            p = cls.properties.get(k)
            if p and not isinstance(p, ManyToMany):
                d[str(k)] = p.make_value_from_datastore(v)
            else:
                d[str(k)] = v
        return d
    
    @classmethod
    def all(cls):
        return Result(cls)
        
    @classmethod
    def filter(cls, condition=None, **kwargs):
        return Result(cls, condition, **kwargs)
            
    @classmethod
    def remove(cls, condition=None, **kwargs):
        if isinstance(condition, (int, long)):
            cls.table.delete(cls.c.id==condition, **kwargs).execute()
        elif isinstance(condition, (tuple, list)):
            cls.table.delete(cls.c.id.in_(condition)).execute()
        else:
            cls.table.delete(condition, **kwargs).execute()
            
    @classmethod
    def count(cls, condition=None, **kwargs):
        obj = cls.table.count(condition, **kwargs).execute()
        count = 0
        if obj:
            r = obj.fetchone()
            if r:
                count = r[0]
        else:
            count = 0
        return count
            
